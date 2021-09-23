"""Directive implementations."""
from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx import addnodes


class DeferredCodeReferences(nodes.Element):
    """Deferred literal type for substitution later when references are known."""

    def __init__(self, ref: str = None):
        super().__init__()
        self.ref = ref

    def copy(self):
        """Copy element."""
        return self.__class__(self.ref)


class CodeReferences(Directive):
    """Gather and display references in code examples."""

    has_content = False
    required_arguments = 1
    optional_arguments = 1

    def run(self):
        """Run directive to insert a :class:`DeferredCodeReferences`."""
        name = self.arguments[0]
        type_ = self.arguments[1] if len(self.arguments) > 1 else 'class'
        par = nodes.paragraph()
        deferred = DeferredCodeReferences(name)
        par += deferred
        ref = addnodes.pending_xref(
            refdomain='py',
            refexplicit=False,
            refwarn=False,
            reftype=type_,
            reftarget=name,
        )
        ref += nodes.literal(classes=['xref', 'py', 'py-class'], text=name)
        deferred += ref
        return [par]


class ConcatBlocksMarker(nodes.Element):
    """Marker for :class:`ConcatBlocks` with attribute :attr:`level`."""

    def __init__(self, mode: str = None):
        super().__init__()
        self.mode = mode

    def copy(self):
        """Copy element."""
        return self.__class__(self.mode)


class ConcatBlocks(Directive):
    """Toggle and cut literal block concatenation in a document."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0

    def run(self):
        """Insert :class:`ConcatBlocksMarker`."""
        return [ConcatBlocksMarker(self.arguments[0])]


class ImplicitImportMarker(nodes.Element):
    """Marker for :class:`ImplicitImport` with attribute :attr:`content`."""

    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def copy(self):
        """Copy element."""
        return self.__class__(self.content)


class ImplicitImport(Directive):
    """Include implicit import in the next code block."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        """Insert :class:`ImplicitImportMarker`."""
        return [ImplicitImportMarker(self.arguments[0])]


class AutoLinkSkipMarker(nodes.Element):
    """Marker for :class:`AutoLinkSkip` with attribute :attr:`level`."""

    def __init__(self, level: str):
        super().__init__()
        self.level = level

    def copy(self):
        """Copy element."""
        return self.__class__(self.level)


class AutoLinkSkip(Directive):
    """Skip auto-linking next code block."""

    has_content = False
    required_arguments = 0
    optional_arguments = 1

    def run(self):
        """Insert :class:`AutoLinkSkipMarker`."""
        arg = self.arguments[0] if self.arguments else 'next'
        return [AutoLinkSkipMarker(arg)]
