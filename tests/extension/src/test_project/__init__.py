"""Docstring."""

from .sub import SubBar, subfoo  # noqa: F401


class Baz:
    """Baz test class."""

    bute = 1


class Foo:
    """Foo test class."""

    attr: str = "test"
    type_attr = Baz

    def meth(self) -> Baz:
        """Test method."""

    def selfref(self) -> "Foo":
        """Return self."""

    def __call__(self) -> Baz:
        """Test call."""


def bar() -> Foo:
    """Bar test function."""


def optional() -> Foo | None:
    """Return optional type."""


def optional_manual() -> None | Foo:
    """Return manually constructed optional type."""


def optional_counter() -> Foo | Baz:
    """Failing case for incorrect optional type handling."""


def compile():  # noqa: A001
    """Shadows built in compile function."""


class Child(Foo):
    """Foo child class."""


def sub_return() -> SubBar:
    """Returns a type in a submodule."""
