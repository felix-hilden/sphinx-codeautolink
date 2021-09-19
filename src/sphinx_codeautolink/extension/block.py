"""Code block processing."""
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


class CodeBlockAnalyser(nodes.SparseNodeVisitor):
    """Transform literal blocks of Python with links to reference documentation."""

    def __init__(self, *args, concat_default: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.code_refs = {}
        self.current_document = Path(self.document['source']).stem
        self.title_stack = []
        self.source_transforms: List[SourceTransforms] = []
        self.implicit_imports = []
        assert concat_default in ('none', 'section', 'file')
        self.concat_default = concat_default
        self.concat_current = None
        self.concat_sources = []
        self.autolink_skip = None

    def unknown_visit(self, node):
        """Handle and delete custom directives, ignore others."""
        if isinstance(node, ConcatBlocksMarker):
            assert node.level in ('none', 'section', 'file', 'reset')
            self.concat_sources = []
            self.concat_current = node.level if node.level != 'reset' else None
            node.parent.remove(node)
        elif isinstance(node, ImplicitImportMarker):
            assert '\n' not in node.content
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

    def depart_title(self, node):
        """Pop latest title."""
        # TODO: currently does not get called
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
        names = parse_names(modified_source)
        if implicit_imports or self.concat_sources:
            concat_lens = [source.count('\n') + 1 for source in self.concat_sources]
            hidden_len = len(implicit_imports) + sum(concat_lens)
            for name in names:
                name.lineno -= hidden_len
                name.end_lineno -= hidden_len

        if self._concat_mode() != 'none':
            self.concat_sources.extend(implicit_imports + [source])

        transforms = SourceTransforms(source, [])
        example = CodeExample(self.current_document, list(self.title_stack))
        for name in names:
            if name.lineno != name.end_lineno:
                msg = (
                    'sphinx-codeautolinks: multiline names are not supported! '
                    f'Found `{name.used_name}` in {node.document["source"]}'
                )
                warn(msg, RuntimeWarning)
                continue

            transforms.names.append(name)
            self.code_refs.setdefault(name.import_name, []).append(example)
        self.source_transforms.append(transforms)


def link_html(document: Path, transforms: List[SourceTransforms], links: dict):
    """Inject links to code blocks on disk."""
    text = document.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = soup.find_all('div', attrs={'class': 'highlight-python notranslate'})
    inners = [block.select('div > pre')[0] for block in blocks]

    link_pattern = '<a href="{link}" title="{title}">{text}</a>'
    name_pattern = '<span class="n">{name}</span>'
    period = '<span class="o">.</span>'

    for trans in transforms:
        for ix in range(len(inners)):
            if trans.source == ''.join(inners[ix].strings).rstrip():
                inner = inners.pop(ix)
                break
        else:
            warn('Could not match a code example to HTML!', RuntimeWarning)
            continue

        lines = str(inner).split('\n')

        for name in trans.names:
            if name.import_name not in links:
                continue

            html = period.join(
                name_pattern.format(name=part) for part in name.used_name.split('.')
            )
            line = lines[name.lineno - 1]
            first = line.find(html)
            second = line[first + 1:].find(html)
            if first == -1 or second != -1:
                warn('Could not match transformation to line!', RuntimeWarning)
                continue

            link = link_pattern.format(
                link=links[name.import_name],
                title=name.import_name,
                text=html
            )
            lines[name.lineno - 1] = line.replace(html, link)

        inner.replace_with(BeautifulSoup('\n'.join(lines), 'html.parser'))

    document.write_text(str(soup), 'utf-8')
