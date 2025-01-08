import pytest

from ._util import refs_equal, skip_type_union


class TestFunction:
    @refs_equal
    def test_func_uses(self):
        s = "import a\ndef f():\n  a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_async_func_uses(self):
        s = "import a\nasync def f():\n  a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_func_name_shadows(self):
        s = "import a\ndef a():\n  pass\n  a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_func_name_shadows_inside(self):
        s = "import a\ndef a():\n  a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_func_assigns_then_uses(self):
        s = "import a\ndef f():\n  a = 1\n  a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_func_assigns_then_used_outside(self):
        s = "import a\ndef f():\n  a = 1\na"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_func_annotates_then_uses(self):
        s = "import a\ndef f(arg: a):\n  arg.b"
        refs = [("a", "a"), ("a", "a"), ("a.()", "arg"), ("a.().b", "arg.b")]
        return s, refs

    @refs_equal
    def test_func_annotates_then_assigns(self):
        # Note: inner nodes after outer ones
        s = "import a\ndef f(arg: a) -> a:\n  a = 1"
        refs = [("a", "a"), ("a", "a"), ("a", "a"), ("a.()", "arg")]
        return s, refs

    @refs_equal
    def test_func_annotates_as_generic_then_uses(self):
        s = "import a\ndef f(arg: a[0]):\n  arg.b"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_func_annotates_inside_generic_then_uses(self):
        s = "import a\ndef f(arg: b[a]):\n  arg.b"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @skip_type_union
    @refs_equal
    def test_func_annotates_union_then_uses(self):
        s = "import a\ndef f(arg: a | 1):\n  arg.b"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_func_kw_default_uses_not_assigned(self):
        s = "import a\ndef f(*_, c, b=a):\n  b"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_func_arg_shadows(self):
        s = "import a\ndef f(a):\n  a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_func_decorator_uses(self):
        s = "import a\n@a\ndef f():\n  pass"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @pytest.mark.xfail(reason="Assignments are not tracked.")
    @refs_equal
    def test_func_uses_overrided_later(self):
        s = "import a\ndef f():\n  a\na = 1\nf()"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_lambda_uses(self):
        s = "import a\nlambda: a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_lambda_arg_shadows(self):
        s = "import a\nlambda a: a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_lambda_arg_default_uses_not_assigned(self):
        s = "import a\nlambda x=a: x"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_lambda_arg_default_uses_then_shadows(self):
        s = "import a\nlambda a=a: a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_lambda_arg_shadows_used_outside(self):
        s = "import a\nlambda a: a\na"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_lambda_kw_default_uses(self):
        s = "import a\nlambda *b, c, d=a: 1"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @pytest.mark.xfail(reason="No reason to do this in the real world.")
    @refs_equal
    def test_global_in_outermost_scope(self):
        s = "import a\nglobal a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_global_hits_import_after_inner_shadow(self):
        s = "import a\ndef f():\n  a = 1\n  def g():\n    global a\n    a"
        refs = [("a", "a"), ("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_global_skips_inner_import(self):
        s = "a = 1\ndef f():\n  import a\n  def g():\n    global a\n    a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_global_overwritten_then_used_in_inner(self):
        s = "import a\ndef f():\n  global a\n  a = 1\n  a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_global_overwrite_in_next_call_then_used_in_outer_before(self):
        s = "import a\ndef f():\n  global a\n  a = 1\na\nf()"
        refs = [("a", "a"), ("a", "a"), ("a", "a")]
        return s, refs

    @pytest.mark.xfail(reason="Global assigns not tracked to outer scopes.")
    @refs_equal
    def test_global_overwritten_then_used_in_outer(self):
        s = "import a\ndef f():\n  global a\n  a = 1\nf()\na"
        refs = [("a", "a"), ("a", "a")]  # ref only in global statement
        return s, refs

    @refs_equal
    def test_nonlocal_hits_import_after_outer_assign(self):
        s = "a = 1\ndef f():\n  import a\n  def g():\n    nonlocal a\n    a"
        refs = [("a", "a"), ("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_nonlocal_skips_outer_import(self):
        s = "import a\ndef f():\n  a = 1\n  def g():\n    nonlocal a\n    a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_nonlocal_overwritten_then_used(self):
        s = "a = 1\ndef f():\n  import a\n  def g():\n    nonlocal a\n    a = 1\n    a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @pytest.mark.xfail(reason="Global deletes not tracked to outer scopes.")
    @refs_equal
    def test_global_deleted_then_used_in_outer(self):
        s = "import a\ndef f():\n  global a\n  del a\nf()\na"
        refs = [("a", "a"), ("a", "a"), ("a", "a")]  # refs in global and del
        return s, refs


class TestComprehension:
    @refs_equal
    def test_comp_uses_in_value(self):
        s = "import a\n[a for b in c]"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_setcomp_uses_in_value(self):
        s = "import a\n{a for b in c}"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_dictcomp_uses_in_value(self):
        s = "import a\n{a: a for b in c}"
        refs = [("a", "a"), ("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_generator_uses_in_value(self):
        s = "import a\n(a for b in c)"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_comp_uses_in_ifs(self):
        s = "import a\n[_ for _ in b if a]"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_comp_uses_in_iter(self):
        s = "import a\n[_ for _ in b(a)]"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_comp_overrides(self):
        s = "import a\n[a for a in b if a]"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_comp_overrides_used_after(self):
        s = "import a\n[a for a in b]\na"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_multicomp_overrides(self):
        s = "import a\n[a for a in b for b in a]"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_multicomp_uses_then_overrides(self):
        s = "import a\n[a for b in c(a) for a in b]"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @pytest.mark.xfail(reason='Assignments are not tracked outside of a "scope".')
    @refs_equal
    def test_comp_leaks_walrus(self):
        s = "import a\n[a := i for i in b]\na"
        refs = [("a", "a")]
        return s, refs


class TestClass:
    @refs_equal
    def test_class_name_shadows(self):
        s = "import a\nclass a:\n  pass\na"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_class_bases_uses(self):
        s = "import a\nclass A(a):\n  pass"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_keyword_uses(self):
        s = "import a\nclass A(kw=a):\n  pass"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_starargs_uses(self):
        s = "import a\nclass A(*a):\n  pass"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_kwargs_uses(self):
        s = "import a\nclass A(**a):\n  pass"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_decorator_uses(self):
        s = "import a\n@a\nclass A:\n  pass"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_body_pseudo_assigns(self):
        s = "import a\nclass A:\n  a = 1\na"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_body_pseudo_shadows_for_method(self):
        s = "import a\nclass A:\n  a = 1\n  def f(s):\n    a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_method_pseudo_shadows_inside(self):
        s = "import a\nclass A:\n  def a(s):\n    a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_method_pseudo_shadows_after(self):
        s = "import a\nclass A:\n  def a(s):\n    pass\na"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_method_shadows_body(self):
        s = "import a\nclass A:\n  def a(s):\n    pass\n  a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_class_lambda_uses_outer(self):
        s = "import a\nclass A:\n  b = lambda: a\na = 1"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_class_lambda_skips_body(self):
        s = "import a\nclass A:\n  a = 2\n  b = lambda: a"
        refs = [("a", "a"), ("a", "a")]
        return s, refs
