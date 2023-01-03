import pytest

from ._util import refs_equal, skip_match


@skip_match
class TestMatch:
    @refs_equal
    def test_match_link_nothing(self):
        s = "match a:\n  case b(c, d=e):\n    pass"
        refs = []
        return s, refs

    @refs_equal
    def test_match_target_linked(self):
        s = "import a\nmatch a:\n  case _:\n    pass"
        refs = [("a", "a"), ("a", "a")]
        return s, refs

    @refs_equal
    def test_case_class_linked(self):
        s = "import a\nmatch _:\n  case a.C():\n    pass"
        refs = [("a", "a"), ("a.C", "a.C")]
        return s, refs

    @refs_equal
    def test_case_inner_attribute_linked(self):
        s = "import a\nmatch _:\n  case a.C(attr=0):\n    pass"
        refs = [("a", "a"), ("a.C", "a.C"), ("a.C.().attr", "attr")]
        return s, refs

    @refs_equal
    def test_case_inner_pattern_linked(self):
        s = "import a\nmatch _:\n  case C(a.b):\n    pass"
        refs = [("a", "a"), ("a.b", "a.b")]
        return s, refs

    @refs_equal
    def test_case_inner_kw_pattern_linked(self):
        s = "import a\nmatch _:\n  case C(attr=a.b):\n    pass"
        refs = [("a", "a"), ("a.b", "a.b")]
        return s, refs

    @refs_equal
    def test_case_inner_kw_pattern_class_linked(self):
        s = "import a\nmatch _:\n  case C(attr=a.C()):\n    pass"
        refs = [("a", "a"), ("a.C", "a.C")]
        return s, refs

    @refs_equal
    def test_case_inner_pattern_with_single_name_overrides(self):
        s = "import a\nmatch _:\n  case C(a):\n    a"
        refs = [("a", "a")]
        return s, refs

    @refs_equal
    def test_case_inner_pattern_overrides_but_able_to_use_simultaneously(self):
        s = "import a\nmatch _:\n  case C(a, a.b):\n    a"
        refs = [("a", "a"), ("a.b", "a.b")]
        return s, refs

    @refs_equal
    def test_case_nested_class_linked(self):
        s = "import a\nmatch _:\n  case C(attr=[a.D()]):\n    pass"
        refs = [("a", "a"), ("a.D", "a.D")]
        return s, refs

    @refs_equal
    def test_case_class_attr_target_linked(self):
        s = "import a\nmatch _:\n  case a.C(attr=x):\n    pass"
        refs = [
            ("a", "a"),
            ("a.C", "a.C"),
            ("a.C.().attr", "attr"),
            ("a.C.().attr", "x"),
        ]
        return s, refs

    @refs_equal
    def test_case_kw_pattern_overrides(self):
        s = "import a\nmatch _:\n  case a.C(attr=a):\n    a"
        refs = [
            ("a", "a"),
            ("a.C", "a.C"),
            ("a.C.().attr", "attr"),
            ("a.C.().attr", "a"),
            ("a.C.().attr", "a"),
        ]
        return s, refs

    @pytest.mark.xfail(reason="Match overriding not implemented.")
    @refs_equal
    def test_case_pattern_overrides_but_able_to_use_simultaneously(self):
        s = "import a\nmatch _:\n  case a.C(a, attr=a.b):\n    a"
        refs = [("a", "a"), ("a.C", "a.C"), ("a.C.().attr", "attr"), ("a.b", "a.b")]
        return s, refs

    @pytest.mark.xfail(reason="Match overriding not implemented.")
    @refs_equal
    def test_case_kw_pattern_overrides_but_able_to_use_simultaneously(self):
        s = "import a\nmatch _:\n  case a.C(attr=a, bttr=a.b):\n    pass"
        refs = [
            ("a", "a"),
            ("a.C", "a.C"),
            ("a.C.().attr", "attr"),
            ("a.C.().attr", "a"),
            ("a.C.().bttr", "bttr"),
            ("a.b", "a.b"),
        ]
        return s, refs

    @refs_equal
    def test_case_nested_patterns_override_but_able_to_use_simultaneously(self):
        s = "import a\nmatch _:\n  case a.B(a, a.C(a, a.d, a), a):\n    a"
        refs = [("a", "a"), ("a.B", "a.B"), ("a.C", "a.C"), ("a.d", "a.d")]
        return s, refs

    @refs_equal
    def test_case_nested_class_attr_target_linked(self):
        s = "import a\nmatch _:\n  case C(attr=[a.C(attr=x)]):\n    pass"
        refs = [
            ("a", "a"),
            ("a.C", "a.C"),
            ("a.C.().attr", "attr"),
            ("a.C.().attr", "x"),
        ]
        return s, refs
