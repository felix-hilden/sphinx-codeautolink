"""Unit tests for sphinx_codeautolink.extension.resolve helpers."""

import ast

from sphinx_codeautolink.extension.resolve import collect_type_checking_aliases


class TestTypeChecking:
    def test_type_checking(self):
        tree = ast.parse("from typing import TYPE_CHECKING")
        assert collect_type_checking_aliases(tree) == {"TYPE_CHECKING"}

    def test_type_checking_aliased(self):
        tree = ast.parse(
            "from typing import TYPE_CHECKING as _TYPE_CHECKING"
        )
        assert collect_type_checking_aliases(tree) == {"_TYPE_CHECKING"}
