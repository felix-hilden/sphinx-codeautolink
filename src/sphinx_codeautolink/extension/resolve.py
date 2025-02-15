"""Resolve import locations and type hints."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from functools import cache
from importlib import import_module
from inspect import isclass, isroutine
from types import UnionType
from typing import Any, Union, get_type_hints

from sphinx_codeautolink.parse import Name, NameBreak


def resolve_location(chain: Name, inventory) -> str:
    """Find the final type that a name refers to."""
    comps = []
    cursor = None
    for comp in chain.import_components:
        if comp != NameBreak.call:
            comps.append(comp)
            continue

        if cursor is None:
            comps, cursor = make_cursor(comps)

        cursor = locate_type(cursor, tuple(comps), inventory)
        call_value(cursor)
        comps = []

    if cursor is None:
        try:
            comps, cursor = make_cursor(comps)
        except CouldNotResolve:
            # Last ditch effort to locate based on the string only
            return ".".join(comps)

    cursor = locate_type(cursor, tuple(comps), inventory)
    return cursor.location if cursor is not None else None


class CouldNotResolve(Exception):  # noqa: N818
    """Could not resolve type to inventory."""


@dataclass
class Cursor:
    """Cursor to follow imports, attributes and calls to the final type."""

    location: str
    value: Any
    instance: bool


def make_cursor(components: list[str]) -> tuple[list[str], Cursor]:
    """Divide components into module and rest, create cursor for following the rest."""
    value, index = closest_module(tuple(components))
    location = ".".join(components[:index])
    return components[index:], Cursor(location, value, instance=False)


def locate_type(cursor: Cursor, components: tuple[str, ...], inventory) -> Cursor:
    """Find type hint and resolve to new location."""
    previous = cursor
    for i, component in enumerate(components):
        cursor = Cursor(
            cursor.location + "." + component,
            getattr(cursor.value, component, None),
            cursor.instance,
        )

        if cursor.value is None:
            msg = f"{cursor.location} does not exist."
            raise CouldNotResolve(msg)

        if isclass(cursor.value):
            cursor.instance = False

        if isclass(cursor.value) or (
            isroutine(cursor.value) and cursor.location not in inventory
        ):
            # Normalise location of type or imported function
            # If odd construct encountered: don't try to be clever but continue
            with suppress(AttributeError, TypeError):
                cursor.location = fully_qualified_name(cursor.value)

        # Check bases if member not found in current class
        if isclass(previous.value) and cursor.location not in inventory:
            for val in previous.value.__mro__[1:]:
                name = fully_qualified_name(val)
                if name + "." + component in inventory:
                    previous.location = name
                    return locate_type(previous, components[i:], inventory)

        previous = cursor

    return cursor


def call_value(cursor: Cursor) -> None:
    """Call class, instance or function."""
    if isclass(cursor.value) and not cursor.instance:
        # class definition: "instantiate" class
        cursor.instance = True
        return

    if callable(cursor.value) and not isroutine(cursor.value):
        # callable class instance
        cursor.value = cursor.value.__call__
    elif not isroutine(cursor.value):
        raise CouldNotResolve  # not a function either

    cursor.value = get_return_annotation(cursor.value)
    cursor.location = fully_qualified_name(cursor.value)
    cursor.instance = True


def get_return_annotation(func: Callable) -> type | None:
    """Determine the target of a function return type hint."""
    try:
        annotation = get_type_hints(func).get("return")
    except (NameError, TypeError) as e:
        msg = f"Unable to follow return annotation of {get_name_for_debugging(func)}."
        raise CouldNotResolve(msg) from e

    # Inner type from typing.Optional or Union[None, T]
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", None)
    if (origin is Union or isinstance(annotation, UnionType)) and len(args) == 2:  # noqa: PLR2004
        nonetype = type(None)
        if args[0] is nonetype:
            annotation = args[1]
        elif args[1] is nonetype:
            annotation = args[0]

    if (
        not annotation
        or not isinstance(annotation, type)
        or hasattr(annotation, "__origin__")
    ):
        msg = f"Unable to follow return annotation of {get_name_for_debugging(func)}."
        raise CouldNotResolve(msg)

    return annotation


def fully_qualified_name(thing: type | Callable) -> str:
    """Construct the fully qualified name of a type."""
    return thing.__module__ + "." + thing.__qualname__


def get_name_for_debugging(thing: type | Callable) -> str:
    """Construct the fully qualified name or some readable information of a type."""
    try:
        return fully_qualified_name(thing)
    except (AttributeError, TypeError):
        return repr(thing)


@cache
def closest_module(components: tuple[str, ...]) -> tuple[Any, int]:
    """Find closest importable module."""
    try:
        mod = import_module(components[0])
    except ImportError as e:
        msg = f"Could not import {components[0]}."
        raise CouldNotResolve(msg) from e

    for i in range(1, len(components)):
        try:
            mod = import_module(".".join(components[: i + 1]))
        except ImportError:  # noqa: PERF203
            # import failed, exclude previously added item
            return mod, i
    # imports succeeded, include all items
    return mod, len(components)
