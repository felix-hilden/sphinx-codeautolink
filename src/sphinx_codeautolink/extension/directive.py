"""Directive implementations."""

from __future__ import annotations

from typing import ClassVar

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx import addnodes


class DeferredExamples(nodes.Element):
    """Deferred node for substitution later when references are known."""

    def __init__(self, ref: str, collapse: bool) -> None:  # noqa: FBT001
        super().__init__()
        self.ref = ref
        self.collapse = collapse

    def copy(self):
        """Copy element."""
        return self.__class__(self.ref, self.collapse)


class Examples(Directive):
    """Gather and display references in code examples."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    option_spec: ClassVar = {"collapse": directives.flag, "type": directives.unchanged}

    def run(self):
        """Run directive to insert a :class:`DeferredExamples`."""
        name = self.arguments[0]
        collapse = self.options.get("collapse", False) is None
        par = nodes.paragraph()
        deferred = DeferredExamples(name, collapse)
        par += deferred
        ref = addnodes.pending_xref(
            refdomain="py",
            refexplicit=False,
            refwarn=False,
            reftype=self.options.get("type", "class"),
            reftarget=name,
        )
        ref += nodes.literal(classes=["xref", "py", "py-class"], text=name)
        deferred += ref
        return [par]


class ConcatMarker(nodes.Element):
    """Marker for :class:`Concat`."""

    def __init__(self, mode: str | None = None) -> None:
        super().__init__()
        self.mode = mode

    def copy(self):
        """Copy element."""
        return self.__class__(self.mode)


class Concat(Directive):
    """Toggle and cut block concatenation in a document."""

    has_content = False
    required_arguments = 0
    optional_arguments = 1

    def run(self):
        """Insert :class:`ConcatMarker`."""
        arg = self.arguments[0] if self.arguments else "on"
        return [ConcatMarker(arg)]


class PrefaceMarker(nodes.Element):
    """Marker for :class:`Preface`."""

    def __init__(self, content: str, level: str) -> None:
        super().__init__()
        self.content = content
        self.level = level

    def copy(self):
        """Copy element."""
        return self.__class__(self.content)


class Preface(Directive):
    """Include a preface in the next code block."""

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec: ClassVar = {"level": directives.unchanged}

    def run(self):
        """Insert :class:`PrefaceMarker`."""
        lines = list(self.arguments) + list(self.content)
        level = self.options.get("level", "next")
        return [PrefaceMarker("\n".join(lines), level)]


class SkipMarker(nodes.Element):
    """Marker for :class:`Skip`."""

    def __init__(self, level: str) -> None:
        super().__init__()
        self.level = level

    def copy(self):
        """Copy element."""
        return self.__class__(self.level)


class Skip(Directive):
    """Skip auto-linking next code block."""

    has_content = False
    required_arguments = 0
    optional_arguments = 1

    def run(self):
        """Insert :class:`SkipMarker`."""
        arg = self.arguments[0] if self.arguments else "next"
        return [SkipMarker(arg)]


class RemoveExtensionVisitor(nodes.SparseNodeVisitor):
    """Silently remove all codeautolink directives."""

    def unknown_departure(self, node) -> None:
        """Ignore unknown nodes."""

    def unknown_visit(self, node) -> None:
        """Remove nodes."""
        if isinstance(node, DeferredExamples):
            # Remove surrounding paragraph too
            node.parent.parent.remove(node.parent)
        if isinstance(node, ConcatMarker | PrefaceMarker | SkipMarker):
            node.parent.remove(node)
