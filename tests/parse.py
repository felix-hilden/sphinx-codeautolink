import sys
import pytest
from .util import refs_equal


class TestSimple:
    @refs_equal
    def test_empty_source(self):
        return '', []

    @refs_equal
    def test_no_imports(self):
        return '1\na = 2\nb()', []

    @refs_equal
    def test_simple_import(self):
        s = 'import lib\nlib'
        refs = [('lib', 'lib')]
        return s, refs

    @refs_equal
    def test_simple_import_then_attrib(self):
        s = 'import lib\nlib.attr'
        refs = [('lib.attr', 'lib.attr')]
        return s, refs

    @refs_equal
    def test_import_as_then_attrib(self):
        s = 'import lib as b\nb.attr'
        refs = [('lib.attr', 'b.attr')]
        return s, refs

    @refs_equal
    def test_import_from_then_attrib(self):
        s = 'from lib import a\na.attr'
        refs = [('lib.a.attr', 'a.attr')]
        return s, refs

    @refs_equal
    def test_import_from_as_then_attrib(self):
        s = 'from lib import a as b\nb.attr'
        refs = [('lib.a.attr', 'b.attr')]
        return s, refs

    @refs_equal
    def test_import_then_call_attrib(self):
        s = 'import a\na.attr().b'
        refs = [('a.attr', 'a.attr')]
        return s, refs

    @refs_equal
    def test_dotted_import(self):
        s = 'import a.b\na.b'
        refs = [('a.b', 'a.b')]
        return s, refs

    @refs_equal
    def test_dotted_import_then_only_part(self):
        s = 'import a.b\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_dotted_import_then_attrib(self):
        s = 'import a.b\na.b.c'
        refs = [('a.b.c', 'a.b.c')]
        return s, refs

    @refs_equal
    def test_relative_import_is_noop(self):
        s = 'from .a import b\nb'
        refs = []
        return s, refs


class TestAssign:
    @refs_equal
    def test_assign_before_import(self):
        s = 'a = 1\nimport a\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_assign_after_import(self):
        s = 'import a\na = 1\na'
        refs = []
        return s, refs

    @refs_equal
    def test_assign_uses_and_assigns_imported(self):
        s = 'import a\na = a\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_assign_subscript_uses(self):
        s = 'import a\na.b[0] = 1'
        refs = [('a.b', 'a.b')]
        return s, refs

    @refs_equal
    def test_assign_call_subscript_uses(self):
        s = 'import a\na.b()[0] = 1'
        refs = [('a.b', 'a.b')]
        return s, refs

    @refs_equal
    def test_augassign_uses_imported(self):
        s = 'import a\na += 1\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_augassign_uses_and_assigns_imported(self):
        s = 'import a\na += a\na'
        refs = [('a', 'a'), ('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_annassign_uses_imported(self):
        s = 'import a\na: str = 1\na'
        refs = []
        return s, refs

    @refs_equal
    def test_annassign_uses_and_assigns_imported(self):
        s = 'import a\na: str = a\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_annassign_why_would_anyone_do_this(self):
        s = 'import a\na: a = a\na'
        refs = [('a', 'a')]
        return s, refs

    @pytest.mark.skipif(
        sys.version_info < (3, 8), reason='Walrus introduced in Python 3.8.'
    )
    @refs_equal
    def test_walrus_uses_imported(self):
        s = 'import a\n(a := 1)\na'
        refs = []
        return s, refs

    @pytest.mark.skipif(
        sys.version_info < (3, 8), reason='Walrus introduced in Python 3.8.'
    )
    @refs_equal
    def test_walrus_uses_and_assigns_imported(self):
        s = 'import a\n(a := a)\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_dotted_import_overwrites_all_components(self):
        s = 'class a:\n  b = 1\nimport a.b\na.b'
        refs = [('a.b', 'a.b')]
        return s, refs

    @pytest.mark.xfail(reason='Following assigns into imports would be a pain.')
    @refs_equal
    def test_partially_overwrite_dotted_import(self):
        s = 'import a.b.c\na.b = 1\na\na.b\na.b.c'
        refs = [('a', 'a')]
        return s, refs


class TestAssignLike:
    @refs_equal
    def test_with_uses_imported(self):
        s = 'import a\nwith a as b:\n  a'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_with_overwrites_imported(self):
        s = 'import a\nwith 1 as a:\n  a'
        refs = []
        return s, refs

    @refs_equal
    def test_with_uses_and_overwrites_imported(self):
        s = 'import a\nwith a as a:\n  a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_for_uses_imported(self):
        s = 'import a\nfor b in a:\n  a'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_for_overwrites_imported(self):
        s = 'import a\nfor a in b:\n  a'
        refs = []
        return s, refs

    @refs_equal
    def test_for_uses_and_overwrites_imported(self):
        s = 'import a\nfor a in a:\n  a'
        refs = [('a', 'a')]
        return s, refs
