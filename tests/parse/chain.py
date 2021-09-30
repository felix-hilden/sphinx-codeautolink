from ._util import refs_equal


class TestChain:
    @refs_equal
    def test_attr_call_doesnt_contain_call(self):
        s = 'import a\na.attr()'
        refs = [('a.attr', 'a.attr')]
        return s, refs

    @refs_equal
    def test_attr_call_attr_split_in_two(self):
        s = 'import a\na.attr().b'
        refs = [('a.attr', 'a.attr'), ('a.attr.().b', 'b')]
        return s, refs

    @refs_equal
    def test_attr_call_attr_call_attr_split_in_three(self):
        s = 'import a\na.attr().b().c'
        refs = [('a.attr', 'a.attr'), ('a.attr.().b', 'b'), ('a.attr.().b.().c', 'c')]
        return s, refs
