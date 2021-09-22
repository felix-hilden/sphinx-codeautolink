"""Code block processing."""
import re

from typing import List
from pathlib import Path
from warnings import warn
from dataclasses import dataclass

from bs4 import BeautifulSoup
from docutils import nodes

from ..parse import parse_names, Name
from .backref import CodeExample
from .directive import ConcatBlocksMarker, ImplicitImportMarker, AutoLinkSkipMarker


@dataclass
class SourceTransforms:
    """Transforms on source code."""

    source: str
    names: List[Name]


class ParsingError(Exception):
    """Error in sphinx-autocodelink parsing."""


class UserError(Exception):
    """Error in sphinx-autocodelink usage."""


class CodeBlockAnalyser(nodes.SparseNodeVisitor):
    """Transform literal blocks of Python with links to reference documentation."""

    def __init__(self, *args, concat_default: str, source_dir: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.code_refs = {}
        relative_path = Path(self.document['source']).relative_to(source_dir)
        self.current_document = str(relative_path.with_suffix(''))
        self.title_stack = []
        self.current_refid = None
        self.source_transforms: List[SourceTransforms] = []
        self.implicit_imports = []
        if concat_default not in ('none', 'section', 'file'):
            raise UserError(
                f'Invalid concatenation default value in "conf.py": `{concat_default}`'
            )
        self.concat_default = concat_default
        self.concat_current = None
        self.concat_sources = []
        self.autolink_skip = None

    def unknown_visit(self, node):
        """Handle and delete custom directives, ignore others."""
        if isinstance(node, ConcatBlocksMarker):
            if node.level not in ('none', 'section', 'file', 'reset'):
                raise UserError(
                    f'Invalid concatenation argument: `{node.level}` '
                    f'in document "{self.current_document}"'
                )

            self.concat_sources = []
            self.concat_current = node.level if node.level != 'reset' else None
            node.parent.remove(node)
        elif isinstance(node, ImplicitImportMarker):
            if '\n' in node.content:
                raise UserError(
                    'Implicit import may not contain a newline, found newline '
                    f'in `{node.content}`, document "{self.current_document}"'
                )
            self.implicit_imports.append(node.content)
            node.parent.remove(node)
        elif isinstance(node, AutoLinkSkipMarker):
            assert node.level in ('next', 'section', 'file', 'none')
            self.autolink_skip = node.level if node.level != 'none' else None
            node.parent.remove(node)

    def _concat_mode(self) -> str:
        return self.concat_current or self.concat_default

    def unknown_departure(self, node):
        """Ignore unknown nodes."""

    def visit_title(self, node):
        """Track section names and break concatenation and skipping."""
        self.title_stack.append(node.astext())
        if self._concat_mode() == 'section':
            self.concat_sources = []
        if self.autolink_skip == 'section':
            self.autolink_skip = None

    def visit_section(self, node):
        """Record first section ID."""
        self.current_refid = node['ids'][0]

    def depart_section(self, node):
        """Pop latest title."""
        self.title_stack.pop()

    def visit_literal_block(self, node: nodes.literal_block):
        """Analyse Python code blocks."""
        implicit_imports = self.implicit_imports
        self.implicit_imports = []

        if (
            len(node.children) != 1
            or not isinstance(node.children[0], nodes.Text)
            or node.get('language', None) not in ('py', 'python')
        ):
            return

        source = node.children[0].astext()

        if self.autolink_skip:
            self.source_transforms.append(SourceTransforms(source, []))
            if self.autolink_skip == 'next':
                self.autolink_skip = None
            return

        modified_source = '\n'.join(self.concat_sources + implicit_imports + [source])
        try:
            names = parse_names(modified_source)
        except SyntaxError as e:
            msg = '\n'.join([
                str(e) + f' in document "{self.current_document}"',
                'Parsed source:',
                source,
            ])
            raise ParsingError(msg) from e

        if implicit_imports or self.concat_sources:
            concat_lens = [s.count('\n') + 1 for s in self.concat_sources]
            hidden_len = len(implicit_imports) + sum(concat_lens)
            for name in names:
                name.lineno -= hidden_len
                name.end_lineno -= hidden_len

        if self._concat_mode() != 'none':
            self.concat_sources.extend(implicit_imports + [source])

        transforms = SourceTransforms(source, [])
        example = CodeExample(
            self.current_document, self.current_refid, list(self.title_stack)
        )
        for name in names:
            if name.lineno < 1:
                continue  # From concatenated source

            if name.lineno != name.end_lineno:
                msg = (
                    'sphinx-codeautolinks: multiline names are not supported, '
                    f'found `{name.used_name}` in document {self.current_document} '
                    f'on lines {name.lineno} - {name.end_lineno}'
                )
                warn(msg, RuntimeWarning)
                continue

            transforms.names.append(name)
            self.code_refs.setdefault(name.import_name, []).append(example)
        self.source_transforms.append(transforms)


def link_html(
    document: Path, out_dir: str, transforms: List[SourceTransforms], inventory: dict
):
    """Inject links to code blocks on disk."""
    text = document.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = soup.find_all('div', attrs={'class': 'highlight-python notranslate'})
    inners = [block.select('div > pre')[0] for block in blocks]

    up_lvls = len(document.relative_to(out_dir).parents) - 1
    link_pattern = '<a href="' + '../' * up_lvls + '{link}" title="{title}">{text}</a>'
    name_pattern = '<span class="n">{name}</span>'
    period = '<span class="o">.</span>'

    for trans in transforms:
        for ix in range(len(inners)):
            if trans.source == ''.join(inners[ix].strings).rstrip():
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

        # Expression asserts no dots before or after content nor a link after,
        # i.e. a self-contained name or attribute that hasn't been linked yet
        # so we are free to replace any occurrences, since the order of
        # multiple identical replacements doesn't matter.
        ex = r'(?<!<span class="o">\.</span>){content}(?!(<span class="o">\.)|(</a>))'
        for name in trans.names:
            if name.import_name not in inventory:
                continue

            html = period.join(
                name_pattern.format(name=part) for part in name.used_name.split('.')
            )
            line = lines[name.lineno - 1]

            # Reverse because a.b = a.b should replace from the right
            matches = list(re.finditer(ex.format(content=html), line))[::-1]
            if not matches:
                msg = (
                    f'Could not match transformation of `{name.used_name}` '
                    f'on source line {name.lineno} in document "{document}", '
                    f'source:\n{trans.source}'
                )
                warn(msg, RuntimeWarning)
                continue

            link = link_pattern.format(
                link=inventory[name.import_name],
                title=name.import_name,
                text=html
            )
            start, end = matches[0].span()
            lines[name.lineno - 1] = line[:start] + link + line[end:]

        inner.replace_with(BeautifulSoup('\n'.join(lines), 'html.parser'))

    document.write_text(str(soup), 'utf-8')
