from functools import wraps
from sphinx_codeautolink.parse import parse_names


def refs_equal(func):
    @wraps(func)
    def wrapper(self):
        source, expected = func(self)
        names = parse_names(source, doctree_node=None)
        names = sorted(names, key=lambda name: name.lineno)
        print('All names:')
        [print(n) for n in names]
        for n, e in zip(names, expected):
            s = '.'.join(c for c in n.import_components)
            assert s == e[0], f'Wrong import! Expected\n{e}\ngot\n{n}'
            assert n.code_str == e[1], f'Wrong code str! Expected\n{e}\ngot\n{n}'

        msg = f'Wrong number of nodes! Expected {len(expected)}, got {len(names)}'
        assert len(names) == len(expected), msg
    return wrapper
