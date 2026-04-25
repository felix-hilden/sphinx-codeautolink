from __future__ import annotations

import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

if typing.TYPE_CHECKING:
    from .foo import Foo

if False:
    pass


def pick(items: Collection[str]) -> Foo:
    """Return value whose annotation references a name guarded by
    ``if TYPE_CHECKING: ...``
    """
