import sys
import pytest

from ._util import refs_equal


class TestFunction:
    @refs_equal
    def test_func_uses(self):
        s = 'import a\ndef f():\n  a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_func_name_shadows(self):
        s = 'import a\ndef a():\n  pass\n  a'
        refs = []
        return s, refs

    @refs_equal
    def test_func_name_shadows_inside(self):
        s = 'import a\ndef a():\n  a'
        refs = []
        return s, refs

    @refs_equal
    def test_func_assigns_then_uses(self):
        s = 'import a\ndef f():\n  a = 1\n  a'
        refs = []
        return s, refs

    @refs_equal
    def test_func_assigns_then_used_outside(self):
        s = 'import a\ndef f():\n  a = 1\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_func_annotations_then_assigns(self):
        s = 'import a\ndef f(arg: a) -> a:\n  a = 1'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_func_arg_shadows(self):
        s = 'import a\ndef f(a):\n  a'
        refs = []
        return s, refs

    @refs_equal
    def test_func_decorator_uses(self):
        s = 'import a\n@a\ndef f():\n  pass'
        refs = [('a', 'a')]
        return s, refs

    @pytest.mark.xfail(reason='Assignments are not tracked.')
    @refs_equal
    def test_func_uses_overrided_later(self):
        s = 'import a\ndef f():\n  a\na = 1\nf()'
        refs = []
        return s, refs

    @refs_equal
    def test_lambda_uses(self):
        s = 'import a\nlambda: a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_lambda_arg_shadows(self):
        s = 'import a\nlambda a: a'
        refs = []
        return s, refs

    @refs_equal
    def test_lambda_arg_default_uses(self):
        s = 'import a\nlambda x=a: x'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_lambda_arg_default_uses_then_shadows(self):
        s = 'import a\nlambda a=a: a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_lambda_arg_shadows_used_outside(self):
        s = 'import a\nlambda a: a\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_global_hits_import_after_inner_shadow(self):
        s = 'import a\ndef f():\n  a = 1\n  def g():\n    global a\n    a'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_global_skips_inner_import(self):
        s = 'a = 1\ndef f():\n  import a\n  def g():\n    global a\n    a'
        refs = []
        return s, refs

    @refs_equal
    def test_global_overwritten_then_used_in_inner(self):
        s = 'import a\ndef f():\n  global a\n  a = 1\n  a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_global_overwrite_in_next_call_then_used_in_outer_before(self):
        s = 'import a\ndef f():\n  global a\n  a = 1\na\nf()'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @pytest.mark.xfail(reason='Global assigns not tracked to outer scopes.')
    @refs_equal
    def test_global_overwritten_then_used_in_outer(self):
        s = 'import a\ndef f():\n  global a\n  a = 1\nf()\na'
        refs = [('a', 'a')]  # ref only in global statement
        return s, refs

    @refs_equal
    def test_nonlocal_hits_import_after_outer_assign(self):
        s = 'a = 1\ndef f():\n  import a\n  def g():\n    nonlocal a\n    a'
        refs = [('a', 'a'), ('a', 'a')]
        return s, refs

    @refs_equal
    def test_nonlocal_skips_outer_import(self):
        s = 'import a\ndef f():\n  a = 1\n  def g():\n    nonlocal a\n    a'
        refs = []
        return s, refs

    @refs_equal
    def test_nonlocal_overwritten_then_used(self):
        s = 'a = 1\ndef f():\n  import a\n  def g():\n    nonlocal a\n    a = 1\n    a'
        refs = [('a', 'a')]
        return s, refs

    @pytest.mark.xfail(reason='Global deletes not tracked to outer scopes.')
    @refs_equal
    def test_global_deleted_then_used_in_outer(self):
        s = 'import a\ndef f():\n  global a\n  del a\nf()\na'
        refs = [('a', 'a'), ('a', 'a')]  # refs in global and del
        return s, refs


class TestComprehension:
    @refs_equal
    def test_comp_uses_in_value(self):
        s = 'import a\n[a for _ in range(2)]'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_comp_uses_in_ifs(self):
        s = 'import a\n[_ for _ in range(2) if a]'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_comp_uses_in_iter(self):
        s = 'import a\n[_ for _ in range(a)]'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_comp_overrides(self):
        s = 'import a\n[a for a in range(2) if a]'
        refs = []
        return s, refs

    @refs_equal
    def test_comp_overrides_used_after(self):
        s = 'import a\n[a for a in range(2)]\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_multicomp_overrides(self):
        s = 'import a\n[a for a in range(2) for b in a]'
        refs = []
        return s, refs

    @refs_equal
    def test_multicomp_uses_then_overrides(self):
        s = 'import a\n[a for b in range(a) for a in b]'
        refs = [('a', 'a')]
        return s, refs

    @pytest.mark.skipif(
        sys.version_info < (3, 8), reason='Walrus introduced in Python 3.8.'
    )
    @pytest.mark.xfail(reason='Assignments are not tracked.')
    @refs_equal
    def test_comp_leaks_walrus(self):
        s = 'import a\n[a := i for i in range(2)]\na'
        refs = []
        return s, refs


class TestClass:
    @refs_equal
    def test_class_name_shadows(self):
        s = 'import a\nclass a:\n  pass\na'
        refs = []
        return s, refs

    @refs_equal
    def test_class_bases_uses(self):
        s = 'import a\nclass A(a):\n  pass'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_keyword_uses(self):
        s = 'import a\nclass A(kw=a):\n  pass'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_starargs_uses(self):
        s = 'import a\nclass A(*a):\n  pass'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_kwargs_uses(self):
        s = 'import a\nclass A(**a):\n  pass'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_decorator_uses(self):
        s = 'import a\n@a\nclass A:\n  pass'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_body_pseudo_assigns(self):
        s = 'import a\nclass A:\n  a = 1\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_body_pseudo_shadows_for_method(self):
        s = 'import a\nclass A:\n  a = 1\n  def f(s):\n    a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_method_pseudo_shadows_inside(self):
        s = 'import a\nclass A:\n  def a(s):\n    a'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_method_pseudo_shadows_after(self):
        s = 'import a\nclass A:\n  def a(s):\n    pass\na'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_method_shadows_body(self):
        s = 'import a\nclass A:\n  def a(s):\n    pass\n  a'
        refs = []
        return s, refs

    @refs_equal
    def test_class_lambda_uses_outer(self):
        s = 'import a\nclass A:\n  b = lambda: a\na = 1'
        refs = [('a', 'a')]
        return s, refs

    @refs_equal
    def test_class_lambda_skips_body(self):
        s = 'import a\nclass A:\n  a = 2\n  b = lambda: a'
        refs = [('a', 'a')]
        return s, refs
