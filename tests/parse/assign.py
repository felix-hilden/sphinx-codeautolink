import sys
import pytest

from ._util import refs_equal


class TestAssign:
    @refs_equal
    def test_assign_before_import(self):
        s = 'a = 1\nimport a\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_assign_after_import(self):
        s = 'import a\na = 1\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_assign_uses_and_assigns_imported(self):
        s = 'import a\na = a\na'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_unpack_assign_starred(self):
        s = '*a, b = c'
        refs = []
        return s, refs

    @refs_equal
    def test_unpack_assign_uses_and_overwrites(self):
        s = 'import a\na, b = a\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_multilevel_unpack_assign_uses_and_overwrites(self):
        s = 'import a\n(a, b), c = a\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_multitarget_assign_uses_and_overwrites(self):
        s = 'import a\na = b = a\na, b'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a'), ('a', 'b')]
        return s, refs

    @refs_equal
    def test_assign_uses_and_assigns_modified_imported(self):
        s = 'import a\na = a + 1\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_assign_subscript_uses(self):
        s = 'import a\na.b[0] = 1'
        refs = [('a', 'a'), ('a.b', 'a.b')]
        return s, refs

    @refs_equal
    def test_assign_call_subscript_uses(self):
        s = 'import a\na.b()[0] = 1'
        refs = [('a', 'a'), ('a.b', 'a.b')]
        return s, refs

    @refs_equal
    def test_augassign_uses_imported(self):
        s = 'import a\na += 1\na'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_augassign_uses_and_assigns_imported(self):
        s = 'import a\na += a\na'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_annassign_uses_imported(self):
        s = 'import a\na: b = 1\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_annassign_uses_and_assigns_imported(self):
        s = 'import a\na: b = a\na'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_annassign_why_would_anyone_do_this(self):
        s = 'import a\na: a = a\na'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_annassign_without_value_overrides_annotation_but_not_linked(self):
        s = 'import a\na: b\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @pytest.mark.skipif(
        sys.version_info < (3, 8), reason='Walrus introduced in Python 3.8.'
    )
    @refs_equal
    def test_walrus_uses_imported(self):
        s = 'import a\n(a := 1)\na'
        refs = [('a', 'a')]
        return s, refs

    @pytest.mark.skipif(
        sys.version_info < (3, 8), reason='Walrus introduced in Python 3.8.'
    )
    @refs_equal
    def test_walrus_uses_and_assigns_imported(self):
        s = 'import a\n(a := a)\na'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @pytest.mark.skipif(
        sys.version_info < (3, 8), reason='Walrus introduced in Python 3.8.'
    )
    @refs_equal
    def test_walrus_uses_and_assigns_modified_imported(self):
        s = 'import a\n(a := a + 1)\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_dotted_import_overwrites_all_components(self):
        s = 'class a:\n  b = 1\nimport a.b\na.b'
        refs = [('a.b', 'a.b'), ('a.b', 'a.b')]
        return s, refs

    @pytest.mark.xfail(reason='Following assigns into imports would be a pain.')
    @refs_equal
    def test_partially_overwrite_dotted_import(self):
        s = 'import a.b.c\na.b = 1\na\na.b\na.b.c'
        refs = [('a.b.c', 'a.b.c'), ('a', 'a')]
        return s, refs


class TestFollowAssignment:
    @refs_equal
    def test_follow_simple_assign(self):
        s = 'import a\nb = a\nb'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'b')]
        return s, refs

    @refs_equal
    def test_follow_simple_assign_attr(self):
        s = 'import a\nb = a\nb.c'
        refs = [('a', 'a'), ('a', 'a'), ('a.c', 'b.c')]
        return s, refs

    @refs_equal
    def test_follow_attr_assign(self):
        s = 'import a\nc = a.b\nc'
        refs = [('a', 'a'), ('a.b', 'a.b'), ('a.b', 'c')]
        return s, refs

    @refs_equal
    def test_follow_attr_assign_attr(self):
        s = 'import a\nc = a.b\nc.d'
        refs = [('a', 'a'), ('a.b', 'a.b'), ('a.b.d', 'c.d')]
        return s, refs

    @refs_equal
    def test_follow_attr_call_assign_attr(self):
        s = 'import a\nc = a.b()\nc.d'
        refs = [('a', 'a'), ('a.b', 'a.b'), ('a.b.().d', 'c.d')]
        return s, refs

    @refs_equal
    def test_follow_attr_call_assign_attr_call(self):
        s = 'import a\nc = a.b()\nc.d()'
        refs = [('a', 'a'), ('a.b', 'a.b'), ('a.b.().d', 'c.d')]
        return s, refs

    @refs_equal
    def test_follow_through_two_complex_assignments(self):
        s = 'import a\nd = a.b().c\ne = d().f'
        refs = [
            ('a', 'a'),
            ('a.b', 'a.b'),
            ('a.b.().c', 'c'),
            ('a.b.().c', 'd'),
            ('a.b.().c.().f', 'f'),
        ]
        return s, refs


class TestAssignLike:
    @refs_equal
    def test_with_uses_imported(self):
        s = 'import a\nwith a as b:\n  a'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_with_overwrites_imported(self):
        s = 'import a\nwith 1 as a:\n  a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_with_uses_and_overwrites_imported(self):
        s = 'import a\nwith a as a:\n  a'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_for_uses_imported(self):
        s = 'import a\nfor b in a:\n  a'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_for_overwrites_imported(self):
        s = 'import a\nfor a in b:\n  a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_for_uses_and_overwrites_imported(self):
        s = 'import a\nfor a in a:\n  a'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_async_for_uses(self):
        s = 'import a\nasync def f():\n  async for b in a:\n    a'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_for_else_uses(self):
        s = 'import a\nfor b in c:\n  pass\nelse:\n  a'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs
