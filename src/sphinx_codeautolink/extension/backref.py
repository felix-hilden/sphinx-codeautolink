"""Backreference tables implementation."""
from dataclasses import dataclass
from typing import Dict, List

from docutils import nodes

from .directive import DeferredCodeReferences


@dataclass
class CodeExample:
    """Code example in the documentation."""

    document: str
    ref_id: str
    headings: List[str]


class CodeRefsVisitor(nodes.SparseNodeVisitor):
    """Replace :class:`DeferredCodeReferences` with table of concrete references."""

    def __init__(
        self,
        *args,
        code_refs: Dict[str, List[CodeExample]],
        remove_directives: bool,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.code_refs = code_refs
        self.remove_directives = remove_directives

    def unknown_departure(self, node):
        """Ignore unknown nodes."""

    def unknown_visit(self, node):
        """Insert table in :class:`DeferredCodeReferences`."""
        if not isinstance(node, DeferredCodeReferences):
            return

        items = []
        for ref in self.code_refs.get(node.ref, []):
            link = ref.document + '.html'
            if ref.ref_id is not None:
                link += f'#{ref.ref_id}'
            items.append((link, ' / '.join(ref.headings)))

        items = sorted(set(items))

        if self.remove_directives:
            # Remove surrounding paragraph too
            node.parent.parent.remove(node.parent)
            return

        orig_ref = node.children[0]
        node.parent.remove(node)

        table = nodes.table()
        tgroup = nodes.tgroup(cols=1)
        table += tgroup
        tgroup += nodes.colspec(colwidth=1)

        thead = nodes.thead()
        tgroup += thead
        row = nodes.row()
        thead += row
        entry = nodes.entry()
        row += entry
        par = nodes.paragraph()
        entry += par
        par += nodes.Text('References to ')
        par += orig_ref

        tbody = nodes.tbody()
        tgroup += tbody
        for link, text in items:
            row = nodes.row()
            tbody += row

            entry = nodes.entry()
            par = nodes.paragraph()
            par += nodes.reference(internal=True, refuri=link, text=text)
            entry += par
            row += entry

        parent_par = nodes.paragraph()
        parent_par += table
        node.parent.replace_self(parent_par)
