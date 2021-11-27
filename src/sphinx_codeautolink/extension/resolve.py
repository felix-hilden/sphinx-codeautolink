"""Resolve import locations and type hints."""
from functools import lru_cache
from importlib import import_module
from typing import Optional, Tuple, Any, Union, Callable
from ..parse import Name, NameBreak


def resolve_location(chain: Name, inventory) -> Optional[str]:
    """Find the final type that a name refers to."""
    comps = []
    for comp in chain.import_components:
        if comp == NameBreak.call:
            new = locate_type(tuple(comps), inventory, ends_with_call=True)
            if new is None:
                return
            comps = new.split('.')
        else:
            comps.append(comp)

    imported_loc = locate_type(tuple(comps), inventory, ends_with_call=False)
    return imported_loc or '.'.join(comps)


def locate_type(
    components: Tuple[str], inventory, ends_with_call: bool
) -> Optional[str]:
    """Find type hint and resolve to new location."""
    value, index = closest_module(components)
    if index is None or index == len(components):
        return
    remaining = components[index:]
    location = '.'.join(components[:index])

    prev_val = None
    for component in remaining:
        value = getattr(value, component, None)
        location += '.' + component
        if value is None:
            return

        if isinstance(value, type) or (callable(value) and location not in inventory):
            try:
                location = fully_qualified_name(value)
            except (AttributeError, TypeError):
                # Odd construct encountered: don't try to be clever but continue
                pass

        if isinstance(prev_val, type) and location not in inventory:
            for val in prev_val.mro():
                loc = fully_qualified_name(val) + '.' + component
                if loc in inventory:
                    return locate_type(tuple(loc.split('.')), inventory, ends_with_call)

        prev_val = value

    # A possible function / method call needs to be last in the chain.
    # Otherwise we might follow return types on function attribute access.
    if (
        ends_with_call
        and remaining
        and callable(value)
        and not isinstance(value, type)
    ):
        location = follow_return_annotation(value)

    return location


def follow_return_annotation(func: Callable) -> Optional[str]:
    """Determine the target of a function return type hint."""
    annotations = getattr(func, '__annotations__', {})
    ret_annotation = annotations.get('return', None)

    # Inner type from typing.Optional (Union[T, None])
    origin = getattr(ret_annotation, '__origin__', None)
    args = getattr(ret_annotation, '__args__', None)
    if origin is Union and len(args) == 2 and isinstance(None, args[1]):
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
        return

    return fully_qualified_name(ret_annotation)


def fully_qualified_name(thing: Union[type, Callable]) -> str:
    """Construct the fully qualified name of a type."""
    return thing.__module__ + '.' + thing.__qualname__


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
