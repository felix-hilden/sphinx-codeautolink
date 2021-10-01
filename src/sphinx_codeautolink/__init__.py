"""Sphinx extension for linking code examples to reference documentation."""
import os as _os
from pathlib import Path as _Path

from sphinx.application import Sphinx
from .extension import SphinxCodeAutoLink
from .extension.directive import (
    CodeReferences, ImplicitImport, ConcatBlocks, AutoLinkSkip
)

_version_file = _Path(_os.path.realpath(__file__)).parent / "VERSION"
__version__ = _version_file.read_text().strip()


def setup(app: Sphinx):
    """Set up extension, directives and events."""
    state = SphinxCodeAutoLink()
    app.add_css_file('sphinx-codeautolink.css')
    app.add_config_value('codeautolink_autodoc_inject', True, 'html', types=[bool])

    app.add_directive('concat-blocks', ConcatBlocks)
    app.add_directive('code-refs', CodeReferences)
    app.add_directive('implicit-import', ImplicitImport)
    app.add_directive('autolink-skip', AutoLinkSkip)

    app.connect('builder-inited', state.build_inited)
    app.connect('autodoc-process-docstring', state.autodoc_process_docstring)
    app.connect('doctree-read', state.parse_blocks)
    app.connect('doctree-resolved', state.generate_backref_tables)
    app.connect('build-finished', state.apply_links)
    return {'version': __version__}
