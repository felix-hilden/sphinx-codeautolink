import pytest
from ._util import refs_equal


class TestSimple:
    @refs_equal
    def test_empty_source(self):
        return '', []

    @refs_equal
    def test_no_imports(self):
        return '1\na = 2\nb()', []

    @refs_equal
    def test_import_from(self):
        s = 'from lib import a'
        refs = [('lib', 'lib'), ('lib.a', 'a')]
        return s, refs

    @refs_equal
    def test_import_from_as(self):
        s = 'from lib import a as b'
        refs = [('lib', 'lib'), ('lib.a', 'a')]
        return s, refs

    @refs_equal
    def test_import_from_multiline(self):
        s = 'from lib import (\n  a,\n  b,\n)'
        refs = [('lib', 'lib'), ('lib.a', 'a'), ('lib.b', 'b')]
        return s, refs

    @refs_equal
    def test_import_from_as_multiline(self):
        s = 'from lib import (\n  a as b,\n  c as d,\n)'
        refs = [('lib', 'lib'), ('lib.a', 'a'), ('lib.c', 'c')]
        return s, refs

    @refs_equal
    def test_simple_import_then_access(self):
        s = 'import lib\nlib'
        refs = [('lib', 'lib'), ('lib', 'lib')]
        return s, refs

    @refs_equal
    def test_simple_import_then_attrib(self):
        s = 'import lib\nlib.attr'
        refs = [('lib', 'lib'), ('lib.attr', 'lib.attr')]
        return s, refs

    @refs_equal
    def test_import_as_then_attrib(self):
        s = 'import lib as b\nb.attr'
        refs = [('lib', 'lib'), ('lib.attr', 'b.attr')]
        return s, refs

    @refs_equal
    def test_import_from_then_attrib(self):
        s = 'from lib import a\na.attr'
        refs = [('lib', 'lib'), ('lib.a', 'a'), ('lib.a.attr', 'a.attr')]
        return s, refs

    @refs_equal
    def test_import_from_as_then_attrib(self):
        s = 'from lib import a as b\nb.attr'
        refs = [('lib', 'lib'), ('lib.a', 'a'), ('lib.a.attr', 'b.attr')]
        return s, refs

    @refs_equal
    def test_dotted_import(self):
        s = 'import a.b\na.b'
        refs = [('a.b', 'a.b'), ('a.b', 'a.b')]
        return s, refs

    @refs_equal
    def test_dotted_import_then_only_part(self):
        s = 'import a.b\na'
        refs = [('a.b', 'a.b'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_dotted_import_then_attrib(self):
        s = 'import a.b\na.b.c'
        refs = [('a.b', 'a.b'), ('a.b.c', 'a.b.c')]
        return s, refs

    @refs_equal
    def test_relative_import_is_noop(self):
        s = 'from .a import b\nb'
        refs = []
        return s, refs

    @refs_equal
    def test_del_removes_import(self):
        s = 'import a\ndel a\na'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_del_dotted_removes_only_part(self):
        s = 'import a.b\ndel a.b\na'
        refs = [('a.b', 'a.b'), ('a.b', 'a.b'), ('a', 'a')]
        return s, refs

    @pytest.mark.xfail(reason='Assignments to imports are not tracked.')
    @refs_equal
    def test_overwrite_dotted_not_tracked(self):
        s = 'import a.b\na.b = 1\na.b.c'
        refs = [('a.b', 'a.b')]
        return s, refs

    @refs_equal
    def test_import_star(self):
        s = 'from sphinx_codeautolink import *\nsetup'
        refs = [
            ('sphinx_codeautolink', 'sphinx_codeautolink'),
            ('sphinx_codeautolink.setup', 'setup')
        ]
        return s, refs
