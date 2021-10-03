"""Resolve import locations and type hints."""
from functools import lru_cache
from importlib import import_module
from typing import Optional, Tuple, Any, Union
from .block import Name, NameBreak


def resolve_location(chain: Name) -> Optional[str]:
    """Find the final type that a name refers to."""
    comps = []
    for comp in chain.import_components:
        if comp == NameBreak.call:
            new = locate_type(tuple(comps))
            if new is None:
                return
            comps = new.split('.')
        else:
            comps.append(comp)
    return '.'.join(comps)


@lru_cache(maxsize=None)
def locate_type(components: Tuple[str]) -> Optional[str]:
    """Find type hint and resolve to new location."""
    value, index = closest_module(components)
    if index is None or index == len(components):
        return
    remaining = components[index:]
    real_location = '.'.join(components[:index])
    for i, component in enumerate(remaining):
        value = getattr(value, component, None)
        real_location += '.' + component
        if value is None:
            return

        if isinstance(value, type):
            # We don't differentiate between classmethods and ordinary methods,
            # as we can't guarantee correct runtime behavior anyway.
            real_location = fully_qualified_name(value)

        # A possible function / method call needs to be last in the chain.
        # Otherwise we might follow return types on function attribute access.
        elif callable(value) and i == len(remaining) - 1:
            ret_annotation = value.__annotations__.get('return', None)

            # Inner type from typing.Optional (Union[T, None])
            origin = getattr(ret_annotation, '__origin__', None)
            args = getattr(ret_annotation, '__args__', None)
            if origin is Union and len(args) == 2 and isinstance(None, args[1]):
                ret_annotation = args[0]

            if not ret_annotation or hasattr(ret_annotation, '__origin__'):
                return
            real_location = fully_qualified_name(ret_annotation)

    return real_location


def fully_qualified_name(type_: type) -> str:
    """Construct the fully qualified name of a type."""
    return getattr(type_, '__module__', '') + '.' + getattr(type_, '__qualname__', '')


@lru_cache(maxsize=None)
def closest_module(components: Tuple[str]) -> Tuple[Any, Optional[int]]:
    """Find closest importable module."""
    mod = None
    for i in range(1, len(components) + 1):
        try:
            mod = import_module('.'.join(components[:i]))
        except ImportError:
            break
    else:
        return None, None

    return mod, i - 1
