import os
import sys
from pathlib import Path

from sphinx_codeautolink import __version__, clean_pycon

# Insert package root to path
_src_dir = Path(os.path.realpath(__file__)).parent
_package_root = _src_dir.parent.parent / "src"
sys.path.insert(0, str(_package_root))
sys.path.insert(0, str(_src_dir))

project = "sphinx-codeautolink"
author = "Felix Hildén"
copyright = "2021-2025, Felix Hildén"
version = __version__
release = version

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx_rtd_theme",
    "sphinx_codeautolink",
    "matplotlib.sphinxext.plot_directive",
    "sphinx.ext.doctest",
    "IPython.sphinxext.ipython_directive",
    "IPython.sphinxext.ipython_console_highlighting",
]

# Builtin options
html_theme = "sphinx_rtd_theme"
python_use_unqualified_type_names = True
show_warning_types = True

# Extension options
codeautolink_autodoc_inject = True
codeautolink_custom_blocks = {"python3": None, "pycon3": clean_pycon}
suppress_warnings = ["config.cache"]

autodoc_default_options = {"members": True, "undoc-members": True}
autodoc_typehints = "description"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}
extlinks = {
    "issue": ("https://github.com/felix-hilden/sphinx-codeautolink/issues/%s", "#%s")
}
# Copy plot directive options from Seaborn
# Include the example source for plots in API docs
plot_include_source = True
plot_formats = [("png", 90)]
plot_html_show_formats = False
plot_html_show_source_link = False

html_static_path = ["static"]
html_css_files = ["custom.css"]


def setup(app) -> None:
    app.add_object_type(
        "confval",
        "confval",
        objname="configuration value",
        indextemplate="pair: %s; configuration value",
    )
