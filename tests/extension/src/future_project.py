# noqa: INP001
from __future__ import annotations

from typing import Optional


class Foo:
    """Foo test class."""

    attr: str = "test"


def optional() -> Optional[Foo]:  # noqa: UP045
    """Return optional type."""


def optional_manual() -> None | Foo:
    """Return manually constructed optional type."""


def invalid_ref() -> NotAClass:  # noqa: F821
    """Reference to a nonexistent class."""
