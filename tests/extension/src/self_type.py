# noqa: INP001
# Test resolving `typing.Self` return annotations, see #147 for details.

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self


class Base:
    """Base class defining a method that returns `Self`."""

    def make(self) -> Self:
        """Return an instance of whatever class this was accessed through."""
        return self


class Derived(Base):
    """Combines a `Self`-returning base with its own method, like a mixin."""

    def own(self) -> Self:
        """Test method defined directly on the subclass."""
        return self
