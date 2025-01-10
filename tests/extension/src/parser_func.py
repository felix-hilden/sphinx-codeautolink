# noqa: INP001
def clean(s):
    """Custom parser for tests."""
    return s, s.replace("-*-", "")


def syntax_error(_):
    raise SyntaxError


def manipulate_original_source(s):
    return s + "\na = 1", s
