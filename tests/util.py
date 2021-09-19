from functools import wraps
from sphinx_codeautolink.parse import parse_names


def refs_equal(func):
    @wraps(func)
    def wrapper(self):
        source, expected = func(self)
        names = parse_names(source)
        names = sorted(names, key=lambda name: name.lineno)
        for n, e in zip(names, expected):
            assert n.import_name == e[0], f'Wrong import name! Expected\n{e}\ngot\n{n}'
            assert n.used_name == e[1], f'Wrong used name! Expected\n{e}\ngot\n{n}'

        assert len(names) == len(expected), 'Wrong number of nodes!'
    return wrapper
