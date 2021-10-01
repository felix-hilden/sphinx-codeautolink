"""Docstring."""


class Baz:
    """Baz test class."""


class Foo:
    """Foo test class."""

    attr: str = 'test'

    def meth(self) -> Baz:
        """Test method."""


def bar() -> Foo:
    """bar test function."""
