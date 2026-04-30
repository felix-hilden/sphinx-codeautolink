"""Resolve import locations and type hints."""

from __future__ import annotations

import ast
import inspect
from collections import abc
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from functools import cache
from importlib import import_module
from inspect import isclass, ismodule, isroutine
from types import ModuleType, UnionType
from typing import Any, Union, get_type_hints

from sphinx_codeautolink.parse import Name, NameBreak

# Containers whose first generic argument is the element type produced
# by iteration. ``tuple`` only fits ``tuple[T, ...]``; for mixed tuples
# like ``tuple[int, str]`` we pick the first arg, which may be wrong.
ITERABLE_ORIGINS = frozenset(
    {
        abc.Iterable,
        abc.Iterator,
        abc.Generator,
        abc.AsyncIterable,
        abc.AsyncIterator,
        abc.AsyncGenerator,
        abc.Collection,
        abc.Sequence,
        abc.MutableSequence,
        abc.Set,
        abc.MutableSet,
        abc.Mapping,
        abc.MutableMapping,
        list,
        set,
        frozenset,
        tuple,
        dict,
    }
)


def resolve_location(chain: Name, inventory) -> str:
    """Find the final type that a name refers to."""
    segments: list[tuple[list[str], NameBreak | None]] = []
    current: list[str] = []
    for comp in chain.import_components:
        if comp in (NameBreak.call, NameBreak.for_iter):
            segments.append((current, NameBreak(comp)))
            current = []
        else:
            current.append(comp)
    segments.append((current, None))

    cursor = None
    last = len(segments) - 1
    for i, (segment, terminator) in enumerate(segments):
        comps = segment
        if cursor is None:
            try:
                comps, cursor = make_cursor(comps)
            except CouldNotResolve:
                if i == last:
                    # Last ditch effort to locate based on the string only
                    return ".".join(comps)
                raise
        cursor = locate_type(cursor, tuple(comps), inventory)
        if terminator == NameBreak.call:
            call_value(cursor)
        elif terminator == NameBreak.for_iter:
            iter_value(cursor)
    return cursor.location if cursor is not None else None


class CouldNotResolve(Exception):  # noqa: N818
    """Could not resolve type to inventory."""


@dataclass
class Cursor:
    """Cursor to follow a component path to the final type."""

    location: str
    value: Any
    instance: bool
    annotation: Any = None


def make_cursor(components: list[str]) -> tuple[list[str], Cursor]:
    """Divide components into module and rest, create cursor for following the rest."""
    value, index = closest_module(tuple(components))
    location = ".".join(components[:index])
    return components[index:], Cursor(location, value, instance=False)


def locate_type(cursor: Cursor, components: tuple[str, ...], inventory) -> Cursor:
    """Find type hint and resolve to new location."""
    previous = cursor
    for i, component in enumerate(components):
        previous = cursor

        # When descending through an instance or alias
        # try to normalise to the original type if possible
        if previous.value is not None and not (
            isclass(previous.value)
            or ismodule(previous.value)
            or isroutine(previous.value)
        ):
            with suppress(AttributeError, TypeError):
                previous.value = type(previous.value)
                previous.location = fully_qualified_name(previous.value)

        annotation = None
        with suppress(NameError, TypeError):
            annotation = get_type_hints(previous.value).get(component)
        cursor = Cursor(
            previous.location + "." + component,
            getattr(previous.value, component, None),
            previous.instance,
            annotation=annotation,
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

    annotation = get_return_annotation(cursor.value)
    type_ = origin_type(annotation)
    if not isinstance(type_, type):
        msg = f"Unable to follow return annotation of {annotation!r}."
        raise CouldNotResolve(msg)
    cursor.value = type_
    cursor.location = fully_qualified_name(type_)
    cursor.instance = True
    cursor.annotation = annotation


def iter_value(cursor: Cursor) -> None:
    """Unwrap the iterable cursor points to into its element type."""
    element = unwrap_iterable(strip_optional(cursor.annotation))
    if not isinstance(element, type):
        msg = (
            f"Unable to unwrap iterable element type of"
            f" {get_name_for_debugging(cursor.value)}."
        )
        raise CouldNotResolve(msg)
    cursor.value = element
    cursor.location = fully_qualified_name(element)
    cursor.instance = True
    cursor.annotation = None


def strip_optional(annotation: Any) -> Any:
    """Reduce ``Optional[T]`` / ``T | None`` to ``T``; otherwise return as-is."""
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", None)
    if (origin is Union or isinstance(annotation, UnionType)) and args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def origin_type(annotation: Any) -> Any:
    """Return underlying type of an annotation (e.g. ``list`` from ``list[Foo]``)."""
    return getattr(annotation, "__origin__", None) or annotation


def unwrap_iterable(annotation: Any) -> type | None:
    """Return the element type of an iterable annotation, or None."""
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", None)
    if origin in ITERABLE_ORIGINS and args:
        return args[0]
    return None


def get_return_annotation(func: Callable) -> Any:
    """Determine the target of a function return type hint."""
    try:
        annotation = get_type_hints(func).get("return")
    except (NameError, TypeError) as e:
        msg = f"Unable to follow return annotation of {get_name_for_debugging(func)}."
        raise CouldNotResolve(msg) from e
    if not annotation:
        msg = f"No return annotation on {get_name_for_debugging(func)}."
        raise CouldNotResolve(msg)
    return strip_optional(annotation)


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
    populate_type_checking(mod)

    for i in range(1, len(components)):
        try:
            mod = import_module(".".join(components[: i + 1]))
        except ImportError:
            # import failed, exclude previously added item
            return mod, i
        populate_type_checking(mod)
    # imports succeeded, include all items
    return mod, len(components)


populated_modules: set[int] = set()


def populate_type_checking(mod: ModuleType) -> None:
    """
    Execute top-level TYPE_CHECKING blocks into ``mod.__dict__``.

    At runtime TYPE_CHECKING is False, so names imported under such gates
    are never bound on the module. ``get_type_hints`` then fails to resolve
    annotations that reference them. Re-execute the gated bodies in the
    module's own namespace so those names become available.
    """
    if id(mod) in populated_modules:
        return
    populated_modules.add(id(mod))

    try:
        source = inspect.getsource(mod)
    except (OSError, TypeError):
        return

    tree = ast.parse(source)
    aliases = collect_type_checking_aliases(tree)

    filename = getattr(mod, "__file__", None) or "<type_checking>"
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        if not is_type_checking_test(node.test, aliases):
            continue
        body = ast.Module(body=node.body, type_ignores=[])
        # Catch e.g. optional deps and cyclic imports
        with suppress(Exception):
            exec(compile(body, filename, "exec"), mod.__dict__)  # noqa: S102


def collect_type_checking_aliases(tree: ast.Module) -> set[str]:
    """Walk top-level imports, return names bound to ``typing.TYPE_CHECKING``."""
    aliases: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            for alias in node.names:
                if alias.name in ("TYPE_CHECKING", "MYPY"):
                    aliases.add(alias.asname or alias.name)
    return aliases


def is_type_checking_test(
    expr: ast.expr, aliases: frozenset[str] | set[str] = frozenset()
) -> bool:
    """Determine if expr is a test for type checking."""
    if isinstance(expr, ast.Name):
        return expr.id in ("TYPE_CHECKING", "MYPY") or expr.id in aliases
    if isinstance(expr, ast.Attribute):
        return expr.attr in ("TYPE_CHECKING", "MYPY")
    return False
