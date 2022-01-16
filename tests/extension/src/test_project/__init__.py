"""Docstring."""
from typing import Optional, Union

from .sub import subfoo  # NOQA


class Baz:
    """Baz test class."""

    bute = 1


class Foo:
    """Foo test class."""

    attr: str = 'test'
    type_attr = Baz

    def meth(self) -> Baz:
        """Test method."""

    def selfref(self) -> "Foo":
        """Return self."""

    def __call__(self) -> Baz:
        """Test call."""


def bar() -> Foo:
    """bar test function."""


def optional() -> Optional[Foo]:
    """Return optional type."""


def optional_manual() -> Union[None, Foo]:
    """Return manually constructed optional type."""


def optional_counter() -> Union[Foo, Baz]:
    """Failing case for incorrect optional type handling."""


def compile():
    """Shadows built in compile function."""


class Child(Foo):
    """Foo child class."""
