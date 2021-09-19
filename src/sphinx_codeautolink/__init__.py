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
state = SphinxCodeAutoLink()


def setup(app: Sphinx):
    """Set up extension, directives and events."""
    app.add_config_value('codeautolink_concat_blocks', 'none', 'html', types=[str])
    app.add_directive('concat-blocks', ConcatBlocks)
    app.add_directive('code-refs', CodeReferences)
    app.add_directive('implicit-import', ImplicitImport)
    app.add_directive('autolink-skip', AutoLinkSkip)

    app.connect('builder-inited', state.builder_inited)
    app.connect('doctree-read', state.doctree_read)
    app.connect('doctree-resolved', state.doctree_resolved)
    app.connect('build-finished', state.build_finished)
    return {'version': __version__}
