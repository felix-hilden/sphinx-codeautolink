# noqa: INP001
# Test an edge case that happens in the inspect module, see #165 for details


class _empty:  # noqa: N801
    pass


class Parameter:
    empty = _empty
