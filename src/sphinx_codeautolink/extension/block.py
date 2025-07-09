"""Code block processing."""

from __future__ import annotations

import re
from collections.abc import Callable
from copy import copy
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from docutils import nodes

from sphinx_codeautolink.parse import LinkContext, Name, parse_names
from sphinx_codeautolink.warn import logger, warn_type

from .backref import CodeExample
from .directive import ConcatMarker, PrefaceMarker, SkipMarker

# list from https://pygments.org/docs/lexers/#pygments.lexers.python.PythonLexer
BUILTIN_BLOCKS = {
    "default": None,
    "python": None,
    "Python": None,
    "python3": None,
    "py": None,
    "py3": None,
    "pyi": None,
    "sage": None,
    "bazel": None,
    "starlark": None,
}


@dataclass
class SourceTransform:
    """Transforms on source code."""

    source: str
    names: list[Name]
    example: CodeExample
    doc_lineno: int


def clean_pycon(source: str) -> tuple[str, str]:
    """Clean up Python console syntax to pure Python."""
    in_statement = False
    source = re.sub(r"^\s*<BLANKLINE>", "", source, flags=re.MULTILINE)
    clean_lines = []
    for line in source.split("\n"):
        if line.startswith(">>> "):
            in_statement = True
            clean_lines.append(line[4:])
        elif in_statement and line.startswith("..."):
            clean_lines.append(line[4:])
        else:
            in_statement = False
            clean_lines.append("")
    return source, "\n".join(clean_lines)


BUILTIN_BLOCKS["pycon"] = clean_pycon


def _exclude_ipython_output(source: str) -> str:
    in_regex = r"In \[[0-9]+\]: "
    # If the first line doesn't begin with a console prompt,
    # assume the entire block to be purely IPython *code*.
    # An arbitrary number of comments and empty lines are exempt.
    if not re.match(rf"^(\s*(#[^\n]*)?\n)*{in_regex}", source):
        return source

    clean_lines = []
    for line in source.split("\n"):
        # Space after "In" is required by transformer but removed in RST preprocessing.
        # All comment are passed through even if they are strictly not input to allow
        # leading comment lines to not be stripped by the IPython transformer.
        if (
            re.match(rf"^{in_regex}", line)
            or re.match(r"^\s*\.*\.\.\.: ", line)
            or re.match(r"^\s*#", line)
        ):
            in_statement = True
        else:
            in_statement = False
        clean_lines.append(line * in_statement)
    return "\n".join(clean_lines)


def clean_ipython(source: str) -> tuple[str, str]:
    """Clean up IPython magics and console syntax to pure Python."""
    from IPython.core.inputtransformer2 import TransformerManager  # noqa: PLC0415

    clean = _exclude_ipython_output(source)
    return source, TransformerManager().transform_cell(clean)


try:
    import IPython
except ImportError:
    pass
else:
    del IPython
    BUILTIN_BLOCKS["ipython"] = clean_ipython
    BUILTIN_BLOCKS["ipython3"] = clean_ipython


class CodeBlockAnalyser(nodes.SparseNodeVisitor):
    """Transform blocks of Python with links to reference documentation."""

    def __init__(
        self,
        *args,
        source_dir: str,
        global_preface: list[str],
        custom_blocks: dict[str, Callable[[str], str]],
        concat_default: bool,
        default_highlight_lang: str | None,
        warn_default_parse_fail: bool,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.source_transforms: list[SourceTransform] = []
        relative_path = Path(self.document["source"]).relative_to(source_dir)
        self.current_document = str(relative_path.with_suffix(""))
        self.global_preface = global_preface
        self.file_preface = []
        self.prefaces = []
        self.doctest_preface: dict[str, list[str]] = {}
        self.transformers = BUILTIN_BLOCKS.copy()
        self.transformers.update(custom_blocks)
        self.valid_blocks = self.transformers.keys()
        self.title_stack = []
        self.current_refid = None
        self.concat_global = concat_default
        self.concat_section = False
        self.concat_sources = []
        self.skip = None
        self.highlight_lang = default_highlight_lang
        self.warn_default_parse_fail = warn_default_parse_fail

    def unknown_visit(self, node) -> None:
        """Handle and delete custom directives, ignore others."""
        if isinstance(node, ConcatMarker):
            if node.mode not in ("off", "section", "on"):
                msg = f"Invalid concatenation argument: `{node.mode}`"
                logger.error(
                    msg, type=warn_type, subtype="invalid_argument", location=node
                )

            self.concat_sources = []
            if node.mode == "section":
                self.concat_section = True
            else:
                self.concat_section = False
                self.concat_global = node.mode == "on"
            node.parent.remove(node)
        elif isinstance(node, PrefaceMarker):
            lines = node.content.split("\n") or []
            if node.level == "next":
                self.prefaces.extend(lines)
            elif node.level == "file":
                self.file_preface = lines
            else:
                msg = f"Invalid preface argument: `{node.level}`"
                logger.error(
                    msg, type=warn_type, subtype="invalid_argument", location=node
                )
            node.parent.remove(node)
        elif isinstance(node, SkipMarker):
            if node.level not in ("next", "section", "file", "off"):
                msg = f"Invalid skipping argument: `{node.level}`"
                logger.error(
                    msg, type=warn_type, subtype="invalid_argument", location=node
                )
            self.skip = node.level if node.level != "off" else None
            node.parent.remove(node)

    def unknown_departure(self, node) -> None:
        """Ignore unknown nodes."""

    def visit_highlightlang(self, node) -> None:
        """Set expected highlight language."""
        self.highlight_lang = node["lang"]

    def visit_title(self, node) -> None:
        """Track section names and break concatenation and skipping."""
        self.title_stack.append(node.astext())
        if self.concat_section:
            self.concat_section = False
            self.concat_sources = []
        if self.skip == "section":
            self.skip = None

    def visit_section(self, node) -> None:
        """Record first section ID."""
        self.current_refid = node["ids"][0]

    def depart_section(self, node) -> None:
        """Pop latest title."""
        self.title_stack.pop()

    def visit_doctest_block(self, node: nodes.doctest_block):
        """Visit a Python doctest block."""
        return self.parse_source(node, "pycon")

    def visit_comment(self, node: nodes.comment):
        """Visit an ext.doctest setup block."""
        if node.get("testnodetype") == "testsetup":
            groups = node["groups"]
            lines = [ln for c in node.children for ln in c.astext().split("\n")]
            for g in groups:
                if g == "*":
                    self.doctest_preface = {"*": lines}
                else:
                    self.doctest_preface[g] = lines

    def visit_literal_block(self, node: nodes.literal_block):
        """Visit a generic literal block."""
        return self.parse_source(node, node.get("language", self.highlight_lang))

    def parse_source(  # noqa: C901,PLR0912
        self, node: nodes.literal_block | nodes.doctest_block, language: str | None
    ) -> None:
        """Analyse Python code blocks."""
        prefaces = self.prefaces
        self.prefaces = []

        if node.get("testnodetype") == "doctest":
            groups = node["groups"]
            doctest_prefaces = [
                ln
                for g in groups
                for ln in self.doctest_preface.get(g, self.doctest_preface.get("*", []))
            ]
            prefaces = doctest_prefaces + prefaces

        skip = self.skip
        if skip == "next":
            self.skip = None

        if (
            len(node.children) != 1
            or not isinstance(node.children[0], nodes.Text)
            or language not in self.valid_blocks
        ):
            return

        source = node.children[0].astext()
        example = CodeExample(
            self.current_document, self.current_refid, list(self.title_stack)
        )
        transform = SourceTransform(source, [], example, node.line)
        self.source_transforms.append(transform)

        if skip:
            return

        # Sphinx uses a similar trick to use pycon implicitly (#168)
        pycon_candidates = ("py", "python", "py3", "python3", "default", "pycon3")
        if source.startswith(">>>") and language in pycon_candidates:
            language = "pycon"

        transformer = self.transformers[language]
        if transformer:
            try:
                source, clean_source = transformer(source)
            except SyntaxError as e:
                msg = self._parsing_error_msg(e, language, source)
                logger.warning(
                    msg, type=warn_type, subtype="clean_block", location=node
                )
                return
        else:
            clean_source = source
        transform.source = source

        full_source = "\n".join(
            self.global_preface
            + self.file_preface
            + self.concat_sources
            + prefaces
            + [clean_source]
        )
        try:
            names = parse_names(full_source, node)
        except SyntaxError as e:
            if language == "default" and not self.warn_default_parse_fail:
                return

            show_source = self._format_source_for_error(
                self.global_preface,
                self.file_preface,
                self.concat_sources,
                prefaces,
                transform.source,
            )
            msg = self._parsing_error_msg(e, language, show_source)
            logger.warning(msg, type=warn_type, subtype="parse_block", location=node)
            return
        except Exception as e:
            show_source = self._format_source_for_error(
                self.global_preface,
                self.file_preface,
                self.concat_sources,
                prefaces,
                transform.source,
            )
            msg = self._parsing_error_msg(e, language, show_source)
            raise type(e)(msg) from e

        if prefaces or self.concat_sources or self.global_preface or self.file_preface:
            concat_lens = [s.count("\n") + 1 for s in self.concat_sources]
            hidden_len = len(prefaces + self.global_preface + self.file_preface) + sum(
                concat_lens
            )
            for name in names:
                name.lineno -= hidden_len
                name.end_lineno -= hidden_len

        if self.concat_section or self.concat_global:
            self.concat_sources.extend([*prefaces, clean_source])

        # Remove transforms from concatenated sources
        transform.names.extend([n for n in names if n.lineno > 0])

    @staticmethod
    def _format_source_for_error(
        global_preface: list[str],
        file_preface: list[str],
        concat_sources: list[str],
        prefaces: list[str],
        source: str,
    ) -> str:
        lines = (
            global_preface
            + file_preface
            + concat_sources
            + prefaces
            + source.split("\n")
        )
        guides = [""] * len(lines)
        ix = 0
        if global_preface:
            guides[ix] = "global preface:"
            ix += len(global_preface)
        if file_preface:
            guides[ix] = "file preface:"
            ix += len(concat_sources)
        if concat_sources:
            guides[ix] = "concatenations:"
            ix += len(concat_sources)
        if prefaces:
            guides[ix] = "local preface:"
            ix += len(prefaces)
        guides[ix] = "block source:"
        pad = max(len(i) + 1 for i in guides)
        guides = [g.ljust(pad) for g in guides]
        return "\n".join([g + s for g, s in zip(guides, lines, strict=True)])

    def _parsing_error_msg(self, error: Exception, language: str, source: str) -> str:
        return "\n".join(
            [
                str(error) + f" in document {self.current_document!r}",
                f"Parsed source in `{language}` block:",
                source,
                "",
            ]
        )


def link_html(
    document: str,
    out_dir: str,
    transforms: list[SourceTransform],
    inventory: dict,
    custom_blocks: dict,
    search_css_classes: list,
    builder_name: str = "html",
) -> None:
    """Inject links to code blocks on disk."""
    if builder_name == "dirhtml" and Path(document).name != "index":
        html_file = Path(out_dir) / document / "index.html"
    else:
        html_file = Path(out_dir) / (document + ".html")

    text = html_file.read_text("utf-8")
    soup = BeautifulSoup(text, "html.parser")

    block_types = BUILTIN_BLOCKS.keys() | custom_blocks.keys()
    classes = [f"highlight-{t}" for t in block_types] + ["doctest"]
    classes += search_css_classes

    blocks = []
    for c in classes:
        blocks.extend(list(soup.find_all("div", attrs={"class": c})))
    unique_blocks = {b.sourceline: b for b in blocks}.values()
    blocks = sorted(unique_blocks, key=lambda b: b.sourceline)
    inners = [block.select("div > pre")[0] for block in blocks]

    up_lvls = len(html_file.relative_to(out_dir).parents) - 1
    local_prefix = "../" * up_lvls
    link_pattern = (
        '<a href="{link}" title="{title}" class="sphinx-codeautolink-a">{text}</a>'
    )

    for trans in transforms:
        for ix in range(len(inners)):
            candidate = copy(inners[ix])

            # remove line numbers for matching
            for lineno in candidate.find_all("span", attrs={"class": "linenos"}):
                lineno.extract()

            if trans.source.rstrip() == "".join(candidate.strings).rstrip():
                inner = inners.pop(ix)
                break
        else:
            msg = f"Could not match a code example to HTML, source:\n{trans.source}"
            logger.warning(
                msg, type=warn_type, subtype="match_block", location=document
            )
            continue

        lines = str(inner).split("\n")

        for name in trans.names:
            begin_line = name.lineno - 1
            end_line = name.end_lineno - 1
            selection = "\n".join(lines[begin_line : end_line + 1])

            # Reverse because a.b = a.b should replace from the right
            matches = list(re.finditer(construct_name_pattern(name), selection))[::-1]
            if not matches:
                msg = (
                    f"Could not match transformation of `{name.code_str}` "
                    f"on source lines {name.lineno}-{name.end_lineno}, "
                    f"source:\n{trans.source}"
                )
                logger.warning(
                    msg, type=warn_type, subtype="match_name", location=document
                )
                continue

            start, end = matches[0].span()
            start += len(matches[0].group(1))
            location = inventory[name.resolved_location]
            if not any(location.startswith(s) for s in ("http://", "https://")):
                location = local_prefix + location
            link = link_pattern.format(
                link=location, title=name.resolved_location, text=selection[start:end]
            )
            transformed = selection[:start] + link + selection[end:]
            lines[begin_line : end_line + 1] = transformed.split("\n")

        inner.replace_with(BeautifulSoup("\n".join(lines), "html.parser"))

    html_file.write_text(str(soup), "utf-8")


# ---------------------------------------------------------------
# Patterns for different types of name access in highlighted HTML
# ---------------------------------------------------------------
period = r'\s*<span class="o">.</span>\s*'
name_pattern = '<span class="n">{name}</span>'
# Pygments has special classes for different types of nouns
# which are also highlighted in import statements
first_name_pattern = '<span class="[a-z]+">@?{name}</span>'
import_target_pattern = '<span class="[a-z]+">{name}</span>'
import_from_pattern = '<span class="nn">{name}</span>'

# The builtin re doesn't support variable-width lookbehind,
# so instead we use a match groups in all pre patterns to remove the non-content.
no_dot_pre = r'(?<!<span class="o">\.</span>)()'
# Potentially instead assert an initial closing parenthesis followed by a dot.
call_dot_pre = r'(\)</span>\s*<span class="o">\.</span>\s*)'
no_dot_post = r'(?!(<span class="o">\.)|(</a>))'

# Pygments 2.19 changed import whitespace highlighting so we need to support both
# with "w" class and raw whitespace for now (see #152)
whitespace = r'(<span class="w">\s*</span>)|(\s*)'
import_pre = (
    rf'((<span class="kn">import</span>{whitespace}(<span class="p">\(</span>\s*)?)'
    rf'|(<span class="[op]">,</span>{whitespace}))'
)
import_post = r'(?=($)|(\s+)|(<span class="[opw]">))(?!</a>)'

from_pre = rf'(<span class="kn">from</span>{whitespace})'
from_post = rf'(?={whitespace}<span class="kn">import</span>)'


def construct_name_pattern(name: Name) -> str:
    """Construct a regex pattern for searching a name in HTML."""
    if name.context == LinkContext.none:
        parts = name.code_str.split(".")
        pattern = period.join(
            [first_name_pattern.format(name=parts[0])]
            + [name_pattern.format(name=p) for p in parts[1:]]
        )
        return no_dot_pre + pattern + no_dot_post
    if name.context == LinkContext.after_call:
        parts = name.code_str.split(".")
        pattern = period.join(
            [first_name_pattern.format(name=parts[0])]
            + [name_pattern.format(name=p) for p in parts[1:]]
        )
        return call_dot_pre + pattern + no_dot_post
    if name.context == LinkContext.import_from:
        pattern = import_from_pattern.format(name=name.code_str)
        return from_pre + pattern + from_post
    if name.context == LinkContext.import_target:
        pattern = import_target_pattern.format(name=name.code_str)
        return import_pre + pattern + import_post
    return None
