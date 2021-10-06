"""Code block processing."""
import re

from typing import List
from pathlib import Path
from warnings import warn
from dataclasses import dataclass

from bs4 import BeautifulSoup
from docutils import nodes

from ..parse import parse_names, Name, NameBreak
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

    def visit_literal_block(self, node: nodes.literal_block):
        """Analyse Python code blocks."""
        prefaces = self.prefaces
        self.prefaces = []

        skip = self.skip
        if skip == 'next':
            self.skip = None

        if (
            len(node.children) != 1
            or not isinstance(node.children[0], nodes.Text)
            or node.get('language', None) not in ('py', 'python', 'pycon')
        ):
            return

        example = CodeExample(
            self.current_document, self.current_refid, list(self.title_stack)
        )
        source = node.children[0].astext()
        transform = SourceTransform(source, [], example)
        self.source_transforms.append(transform)

        if skip:
            return

        if node['language'] == 'pycon':
            in_statement = False
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

        for name in names:
            if name.lineno < 1:
                continue  # From concatenated source

            if name.lineno != name.end_lineno:
                msg = (
                    'sphinx-codeautolinks: multiline names are not supported, '
                    f'found `{name.code_str}` in document {self.current_document} '
                    f'on lines {name.lineno} - {name.end_lineno}'
                )
                warn(msg, RuntimeWarning)
                continue

            transform.names.append(name)


def link_html(
    document: Path, out_dir: str, transforms: List[SourceTransform], inventory: dict
):
    """Inject links to code blocks on disk."""
    text = document.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = (
        list(soup.find_all('div', attrs={'class': 'highlight-python notranslate'}))
        + list(soup.find_all('div', attrs={'class': 'highlight-pycon notranslate'}))
    )
    inners = [block.select('div > pre')[0] for block in blocks]

    up_lvls = len(document.relative_to(out_dir).parents) - 1
    link_pattern = (
        '<a href="' + '../' * up_lvls
        + '{link}" title="{title}" class="sphinx-codeautolink-a">{text}</a>'
    )
    name_pattern = '<span class="n">{name}</span>'
    # Pygments has special classes for decorators (nd) and builtins (nb)
    first_item_pattern = '<span class="n[bd]?">@?{name}</span>'
    period = '<span class="o">.</span>'

    # Expression asserts no dots before or after content nor a link after,
    # i.e. a self-contained name or attribute that hasn't been linked yet
    # so we are free to replace any occurrences, since the order of
    # multiple identical replacements doesn't matter.
    base_ex = r'(?<!<span class="o">\.</span>){content}(?!(<span class="o">\.)|(</a>))'
    # Potentially instead assert an initial closing parenthesis followed by a dot
    call_ex = (
        r'(?<=\)</span><span class="o">\.</span>)'
        r'{content}(?!(<span class="o">\.)|(</a>))'
    )

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

        for name in trans.names:
            parts = name.code_str.split('.')
            pattern = period.join(
                [first_item_pattern.format(name=parts[0])]
                + [name_pattern.format(name=p) for p in parts[1:]]
            )

            line = lines[name.lineno - 1]

            # Reverse because a.b = a.b should replace from the right
            ex = call_ex if name.previous == NameBreak.call else base_ex
            matches = list(re.finditer(ex.format(content=pattern), line))[::-1]
            if not matches:
                msg = (
                    f'Could not match transformation of `{name.code_str}` '
                    f'on source line {name.lineno} in document "{document}", '
                    f'source:\n{trans.source}'
                )
                warn(msg, RuntimeWarning)
                continue

            start, end = matches[0].span()
            link = link_pattern.format(
                link=inventory[name.resolved_location],
                title=name.resolved_location,
                text=line[start:end]
            )
            lines[name.lineno - 1] = line[:start] + link + line[end:]

        inner.replace_with(BeautifulSoup('\n'.join(lines), 'html.parser'))

    document.write_text(str(soup), 'utf-8')
