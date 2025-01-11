# noqa: INP001
from __future__ import annotations

from typing import Optional


class Foo:
    """Foo test class."""

    attr: str = "test"


def optional() -> Optional[Foo]:  # noqa: UP007
    """Return optional type."""


def optional_manual() -> None | Foo:
    """Return manually constructed optional type."""
