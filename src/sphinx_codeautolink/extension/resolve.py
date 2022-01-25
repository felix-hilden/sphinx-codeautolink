"""Resolve import locations and type hints."""
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from inspect import isclass, isroutine
from typing import Optional, Tuple, Any, Union, Callable, List
from ..parse import Name, NameBreak


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
        if cursor is None:
            raise CouldNotResolve()

        call_value(cursor)
        comps = []

    if cursor is None:
        try:
            comps, cursor = make_cursor(comps)
        except CouldNotResolve:
            # Last ditch effort to locate based on the string only
            return '.'.join(comps)

    cursor = locate_type(cursor, tuple(comps), inventory)
    return cursor.location if cursor is not None else None


class CouldNotResolve(Exception):
    """Could not resolve type to inventory."""


@dataclass
class Cursor:
    """Cursor to follow imports, attributes and calls to the final type."""

    location: str
    value: Any
    instance: bool


def make_cursor(components: List[str]) -> Tuple[List[str], Cursor]:
    """Divide components into module and rest, create cursor for following the rest."""
    value, index = closest_module(tuple(components))
    if value is None or index is None:
        raise CouldNotResolve()
    location = '.'.join(components[:index])
    return components[index:], Cursor(location, value, False)


def locate_type(
    cursor: Cursor, components: Tuple[str, ...], inventory
) -> Cursor:
    """Find type hint and resolve to new location."""
    previous = cursor
    for i, component in enumerate(components):
        cursor = Cursor(
            cursor.location + '.' + component,
            getattr(cursor.value, component, None),
            cursor.instance,
        )

        if cursor.value is None:
            raise CouldNotResolve()

        if isclass(cursor.value):
            cursor.instance = False

        if (
            isclass(cursor.value)
            or (isroutine(cursor.value) and cursor.location not in inventory)
        ):
            # Normalise location of type or imported function
            try:
                cursor.location = fully_qualified_name(cursor.value)
            except (AttributeError, TypeError):
                # Odd construct encountered: don't try to be clever but continue
                pass

        if isclass(previous.value) and cursor.location not in inventory:
            for val in previous.value.mro():
                name = fully_qualified_name(val)
                if name + '.' + component in inventory:
                    previous.location = name
                    return locate_type(previous, components[i:], inventory)

        previous = cursor

    return cursor


def call_value(cursor: Cursor):
    """Call class, instance or function."""
    if isclass(cursor.value) and not cursor.instance:
        # class definition: "instantiate" class
        cursor.instance = True
        return

    if callable(cursor.value) and not isroutine(cursor.value):
        # callable class instance
        cursor.value = cursor.value.__call__
    elif not isroutine(cursor.value):
        raise CouldNotResolve()  # not a function either

    cursor.value = get_return_annotation(cursor.value)
    cursor.location = fully_qualified_name(cursor.value)
    cursor.instance = True


def get_return_annotation(func: Callable) -> Optional[type]:
    """Determine the target of a function return type hint."""
    annotations = getattr(func, '__annotations__', {})
    ret_annotation = annotations.get('return', None)

    # Inner type from typing.Optional or Union[None, T]
    origin = getattr(ret_annotation, '__origin__', None)
    args = getattr(ret_annotation, '__args__', None)
    if origin is Union and len(args) == 2:
        nonetype = type(None)
        if args[0] is nonetype:
            ret_annotation = args[1]
        elif args[1] is nonetype:
            ret_annotation = args[0]

    # Try to resolve a string annotation in the module scope
    if isinstance(ret_annotation, str):
        location = fully_qualified_name(func)
        mod, _ = closest_module(tuple(location.split('.')))
        ret_annotation = getattr(mod, ret_annotation, ret_annotation)

    if (
        not ret_annotation
        or not isinstance(ret_annotation, type)
        or hasattr(ret_annotation, '__origin__')
    ):
        raise CouldNotResolve()

    return ret_annotation


def fully_qualified_name(thing: Union[type, Callable]) -> str:
    """Construct the fully qualified name of a type."""
    return thing.__module__ + '.' + thing.__qualname__


@lru_cache(maxsize=None)
def closest_module(components: Tuple[str, ...]) -> Tuple[Any, Optional[int]]:
    """Find closest importable module."""
    try:
        mod = import_module(components[0])
    except ImportError:
        return None, None

    for i in range(1, len(components)):
        try:
            mod = import_module('.'.join(components[:i + 1]))
        except ImportError:
            # import failed, exclude previously added item
            return mod, i
    # imports succeeded, include all items
    return mod, len(components)
