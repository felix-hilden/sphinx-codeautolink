import sphinx_codeautolink


class TestPackage:
    def test_version(self):
        assert sphinx_codeautolink.__version__

    def test_clean_pycon_public(self):
        assert sphinx_codeautolink.clean_pycon

    def test_clean_ipython_public(self):
        assert sphinx_codeautolink.clean_ipython
