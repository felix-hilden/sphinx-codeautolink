# noqa: INP001
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection


class Foo:
    """Foo test class."""

    attr: str = "test"


def pick(items: Collection[str]) -> Foo:
    """Return value whose annotation references a name guarded by
    ``if TYPE_CHECKING: ...``
    """
