"""Code block processing."""
import re

from typing import List, Union, Optional
from pathlib import Path
from warnings import warn
from dataclasses import dataclass

from bs4 import BeautifulSoup
from docutils import nodes

from ..parse import parse_names, Name, LinkContext
from .backref import CodeExample
from .directive import ConcatMarker, PrefaceMarker, SkipMarker


@dataclass
class SourceTransform:
    """Transforms on source code."""

    source: str
    names: List[Name]
    example: CodeExample


class ParsingError(Exception):
    """Error in sphinx-autocodelink parsing."""


class UserError(Exception):
    """Error in sphinx-autocodelink usage."""


class CodeBlockAnalyser(nodes.SparseNodeVisitor):
    """Transform literal blocks of Python with links to reference documentation."""

    def __init__(self, *args, source_dir: str, global_preface: List[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.source_transforms: List[SourceTransform] = []
        relative_path = Path(self.document['source']).relative_to(source_dir)
        self.current_document = str(relative_path.with_suffix(''))
        self.title_stack = []
        self.current_refid = None
        self.global_preface = global_preface
        self.prefaces = []
        self.concat_global = False
        self.concat_section = False
        self.concat_sources = []
        self.skip = None

    def unknown_visit(self, node):
        """Handle and delete custom directives, ignore others."""
        if isinstance(node, ConcatMarker):
            if node.mode not in ('off', 'section', 'on'):
                raise UserError(
                    f'Invalid concatenation argument: `{node.mode}` '
                    f'in document "{self.current_document}"'
                )

            self.concat_sources = []
            if node.mode == 'section':
                self.concat_section = True
            else:
                self.concat_section = False
                self.concat_global = (node.mode == 'on')
            node.parent.remove(node)
        elif isinstance(node, PrefaceMarker):
            self.prefaces.extend(node.content.split('\n'))
            node.parent.remove(node)
        elif isinstance(node, SkipMarker):
            if node.level not in ('next', 'section', 'file', 'off'):
                raise UserError(
                    f'Invalid skipping argument: `{node.level}` '
                    f'in document "{self.current_document}"'
                )
            self.skip = node.level if node.level != 'off' else None
            node.parent.remove(node)

    def unknown_departure(self, node):
        """Ignore unknown nodes."""

    def visit_title(self, node):
        """Track section names and break concatenation and skipping."""
        self.title_stack.append(node.astext())
        if self.concat_section:
            self.concat_section = False
            self.concat_sources = []
        if self.skip == 'section':
            self.skip = None

    def visit_section(self, node):
        """Record first section ID."""
        self.current_refid = node['ids'][0]

    def depart_section(self, node):
        """Pop latest title."""
        self.title_stack.pop()

    def visit_doctest_block(self, node):
        """Visit a Python doctest block."""
        return self.parse_source(node, 'pycon')

    def visit_literal_block(self, node: nodes.literal_block):
        """Visit a generic literal block."""
        return self.parse_source(node, node.get('language', None))

    def parse_source(
        self,
        node: Union[nodes.literal_block, nodes.doctest_block],
        language: Optional[str]
    ):
        """Analyse Python code blocks."""
        prefaces = self.prefaces
        self.prefaces = []

        skip = self.skip
        if skip == 'next':
            self.skip = None

        if (
            len(node.children) != 1
            or not isinstance(node.children[0], nodes.Text)
            or language not in ('py', 'python', 'pycon')
        ):
            return

        example = CodeExample(
            self.current_document, self.current_refid, list(self.title_stack)
        )
        source = node.children[0].astext()

        if skip:
            return

        if language == 'pycon':
            in_statement = False
            source = re.sub(r'^\s*<BLANKLINE>', '', source, flags=re.MULTILINE)
            clean_lines = []
            for line in source.split('\n'):
                if line.startswith('>>> '):
                    in_statement = True
                    clean_lines.append(line[4:])
                elif in_statement and line.startswith('... '):
                    clean_lines.append(line[4:])
                else:
                    in_statement = False
                    clean_lines.append('')
            clean_source = '\n'.join(clean_lines)
        else:
            clean_source = source

        transform = SourceTransform(source, [], example)
        self.source_transforms.append(transform)

        modified_source = '\n'.join(
            self.global_preface
            + self.concat_sources
            + prefaces
            + [clean_source]
        )
        try:
            names = parse_names(modified_source)
        except SyntaxError as e:
            msg = '\n'.join([
                str(e) + f' in document "{self.current_document}"',
                f'Parsed source in `{node["language"]}` block:',
                source,
            ])
            raise ParsingError(msg) from e

        if prefaces or self.concat_sources or self.global_preface:
            concat_lens = [s.count('\n') + 1 for s in self.concat_sources]
            hidden_len = (
                len(prefaces) + sum(concat_lens) + len(self.global_preface)
            )
            for name in names:
                name.lineno -= hidden_len
                name.end_lineno -= hidden_len

        if self.concat_section or self.concat_global:
            self.concat_sources.extend(prefaces + [clean_source])

        # Remove transforms from concatenated sources
        transform.names.extend([n for n in names if n.lineno > 0])


def link_html(
    document: Path, out_dir: str, transforms: List[SourceTransform], inventory: dict
):
    """Inject links to code blocks on disk."""
    text = document.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = (
        list(soup.find_all('div', attrs={'class': 'highlight-python notranslate'}))
        + list(soup.find_all('div', attrs={'class': 'highlight-pycon notranslate'}))
        + list(soup.find_all('div', attrs={'class': 'doctest'}))
    )
    blocks = sorted(blocks, key=lambda tag: tag.sourceline)
    inners = [block.select('div > pre')[0] for block in blocks]

    up_lvls = len(document.relative_to(out_dir).parents) - 1
    link_pattern = (
        '<a href="' + '../' * up_lvls
        + '{link}" title="{title}" class="sphinx-codeautolink-a">{text}</a>'
    )

    for trans in transforms:
        for ix in range(len(inners)):
            if trans.source.rstrip() == ''.join(inners[ix].strings).rstrip():
                inner = inners.pop(ix)
                break
        else:
            msg = (
                f'Could not match a code example to HTML in document "{document}", '
                f'source:\n{trans.source}'
            )
            warn(msg, RuntimeWarning)
            continue

        lines = str(inner).split('\n')

        for name in trans.names:
            begin_line = name.lineno - 1
            end_line = name.end_lineno - 1
            selection = '\n'.join(lines[begin_line:end_line + 1])

            # Reverse because a.b = a.b should replace from the right
            matches = list(re.finditer(construct_name_pattern(name), selection))[::-1]
            if not matches:
                msg = (
                    f'Could not match transformation of `{name.code_str}` '
                    f'on source lines {name.lineno}-{name.end_lineno} '
                    f'in document "{document}", source:\n{trans.source}'
                )
                warn(msg, RuntimeWarning)
                continue

            start, end = matches[0].span()
            start += len(matches[0].group(1))
            link = link_pattern.format(
                link=inventory[name.resolved_location],
                title=name.resolved_location,
                text=selection[start:end]
            )
            transformed = selection[:start] + link + selection[end:]
            lines[begin_line:end_line + 1] = transformed.split('\n')

        inner.replace_with(BeautifulSoup('\n'.join(lines), 'html.parser'))

    document.write_text(str(soup), 'utf-8')


# ---------------------------------------------------------------
# Patterns for different types of name access in highlighted HTML
# ---------------------------------------------------------------
period = r'\s*<span class="o">.</span>\s*'
name_pattern = '<span class="n">{name}</span>'
# Pygments has special classes for decorators (nd) and builtins (nb),
# which are also highlighted in import statements
first_name_pattern = '<span class="n[bd]?">@?{name}</span>'
import_target_pattern = '<span class="n[nb]?">{name}</span>'
import_from_pattern = '<span class="nn">{name}</span>'

# The builtin re doesn't support variable-width lookbehind,
# so instead we use a match groups in all pre patterns to remove the non-content.
no_dot_prere = r'(?<!<span class="o">\.</span>)()'
# Potentially instead assert an initial closing parenthesis followed by a dot.
call_dot_prere = r'(\)</span>\s*<span class="o">\.</span>\s*)'
import_prere = (
    r'((<span class="kn">import</span>\s+(<span class="p">\(</span>\s*)?)'
    r'|(<span class="p">,</span>\s*))'
)
from_prere = r'(<span class="kn">from</span>\s+)'

no_dot_postre = r'(?!(<span class="o">\.)|(</a>))'
import_postre = r'(?=($)|(\s+)|(<span class="p">,</span>)|(<span class="p">\)))(?!</a>)'
from_postre = r'(?=\s*<span class="kn">import</span>)'


def construct_name_pattern(name: Name) -> str:
    """Construct a regex pattern for searching a name in HTML."""
    if name.context == LinkContext.none:
        parts = name.code_str.split('.')
        pattern = period.join(
            [first_name_pattern.format(name=parts[0])]
            + [name_pattern.format(name=p) for p in parts[1:]]
        )
        return no_dot_prere + pattern + no_dot_postre
    elif name.context == LinkContext.after_call:
        parts = name.code_str.split('.')
        pattern = period.join(
            [first_name_pattern.format(name=parts[0])]
            + [name_pattern.format(name=p) for p in parts[1:]]
        )
        return call_dot_prere + pattern + no_dot_postre
    elif name.context == LinkContext.import_from:
        pattern = import_from_pattern.format(name=name.code_str)
        return from_prere + pattern + from_postre
    elif name.context == LinkContext.import_target:
        pattern = import_target_pattern.format(name=name.code_str)
        return import_prere + pattern + import_postre
