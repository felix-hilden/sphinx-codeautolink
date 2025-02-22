import sys
from functools import wraps

import pytest

from sphinx_codeautolink.parse import parse_names

skip_type_union = pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Type union introduced in Python 3.10."
)

skip_match = pytest.mark.skipif(
    sys.version_info < (3, 10), reason="Match introduced in Python 3.10."
)


def refs_equal(func):
    @wraps(func)
    def wrapper(self):
        source, expected = func(self)
        names = parse_names(source, doctree_node=None)
        names = sorted(names, key=lambda name: name.lineno)
        print("Source:\n" + source)
        print("\nExpected names:")
        for components, code_str in expected:
            print(f"components={components}, code_str={code_str}")
        print("\nParsed names:")
        for n in names:
            print(
                f"components={'.'.join(n.import_components)}, code_str={n.code_str},"
                f"lines=({n.lineno}, {n.end_lineno})"
            )
        for n, e in zip(names, expected, strict=True):
            s = ".".join(c for c in n.import_components)
            assert s == e[0], f"Wrong import! Expected\n{e}\ngot\n{n}"
            assert n.code_str == e[1], f"Wrong code str! Expected\n{e}\ngot\n{n}"

        msg = f"Wrong number of nodes! Expected {len(expected)}, got {len(names)}"
        assert len(names) == len(expected), msg

    return wrapper
