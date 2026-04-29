from __future__ import annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

if _TYPE_CHECKING:
    from collections.abc import Collection

    from .foo import Foo


def pick(items: Collection[str]) -> Foo:
    """Return value whose annotation references a name guarded by an
    aliased ``if TYPE_CHECKING: ...``
    """
