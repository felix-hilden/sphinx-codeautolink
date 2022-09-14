import sys
import pytest

from functools import wraps
from sphinx_codeautolink.parse import parse_names

skip_walrus = pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason='Walrus introduced in Python 3.8.',
)

skip_type_union = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason='Type union introduced in Python 3.10.',
)

skip_match = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason='Match introduced in Python 3.10.',
)


def refs_equal(func):
    @wraps(func)
    def wrapper(self):
        source, expected = func(self)
        names = parse_names(source, doctree_node=None)
        names = sorted(names, key=lambda name: name.lineno)
        print('Source:\n' + source)
        print('\nExpected names:')
        for components, code_str in expected:
            print(f'components={components}, code_str={code_str}')
        print('\nParsed names:')
        [print(n) for n in names]
        for n, e in zip(names, expected):
            s = '.'.join(c for c in n.import_components)
            assert s == e[0], f'Wrong import! Expected\n{e}\ngot\n{n}'
            assert n.code_str == e[1], f'Wrong code str! Expected\n{e}\ngot\n{n}'

        msg = f'Wrong number of nodes! Expected {len(expected)}, got {len(names)}'
        assert len(names) == len(expected), msg
    return wrapper
