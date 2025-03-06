"""Backreference tables implementation."""

from dataclasses import dataclass

from docutils import nodes
from sphinx.builders import Builder

from sphinx_codeautolink.warn import logger, warn_type

from .directive import DeferredExamples
from .translation import tr


@dataclass
class CodeExample:
    """Code example in the documentation."""

    document: str
    ref_id: str
    headings: list[str]


class DetailsNode(nodes.Element):
    """Collapsible details node for HTML."""

    def copy(self):
        """Copy element."""
        return self.__class__()


def visit_details(self, node: DetailsNode) -> None:
    """Insert a details tag."""
    self.body.append("<details>")


def depart_details(self, node: DetailsNode) -> None:
    """Close a details tag."""
    self.body.append("</details>")


class SummaryNode(nodes.TextElement):
    """Summary node inside a DetailsNode for HTML."""

    def copy(self):
        """Copy element."""
        return self.__class__()


def visit_summary(self, node: SummaryNode) -> None:
    """Insert a summary tag."""
    self.body.append("<summary>")


def depart_summary(self, node: SummaryNode) -> None:
    """Close a summary tag."""
    self.body.append("</summary>")


class CodeRefsVisitor(nodes.SparseNodeVisitor):
    """Replace :class:`DeferredCodeReferences` with table of concrete references."""

    def __init__(
        self,
        *args,
        code_refs: dict[str, list[CodeExample]],
        docname: str,
        builder: Builder,
        warn_no_backreference: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.code_refs = code_refs
        self.docname = docname
        self.builder = builder
        self.warn_no_backreference = warn_no_backreference

    def unknown_departure(self, node) -> None:
        """Ignore unknown nodes."""

    def unknown_visit(self, node) -> None:
        """Insert table in :class:`DeferredExamples`."""
        if not isinstance(node, DeferredExamples):
            return

        items = []
        for ref in self.code_refs.get(node.ref, []):
            link = self.builder.get_relative_uri(self.docname, ref.document)
            if ref.ref_id is not None:
                link += f"#{ref.ref_id}"
            items.append((link, " / ".join(ref.headings)))

        items = sorted(set(items))

        if not items:
            if self.warn_no_backreference:
                msg = f"No backreference for: '{node.ref}'"
                logger.warning(
                    msg, type=warn_type, subtype="no_backreference", location=node
                )
            # Remove surrounding paragraph too
            node.parent.parent.remove(node.parent)
            return

        orig_ref = node.children[0]
        node.parent.remove(node)

        # Table definition
        table = nodes.table()
        tgroup = nodes.tgroup(cols=1)
        table += tgroup
        tgroup += nodes.colspec(colwidth=1)

        if not node.collapse:
            thead = nodes.thead()
            tgroup += thead
            row = nodes.row()
            thead += row
            entry = nodes.entry()
            row += entry
            title = nodes.paragraph()
            title += nodes.Text(tr("References to") + " ")
            title += orig_ref
            entry += title

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
        if node.collapse:
            details = DetailsNode()
            summary = SummaryNode()
            summary += nodes.Text(tr("Expand for references to") + " ")
            summary += orig_ref
            details += summary
            details += table
            parent_par += details
        else:
            parent_par += table
        node.parent.replace_self(parent_par)
