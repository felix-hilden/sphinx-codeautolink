"""
Automatic links from code examples to reference documentation.

Online documentation on `Read The Docs <https://sphinx-codeautolink.rtfd.org>`_
"""
import os as _os
from pathlib import Path as _Path

_version_file = _Path(_os.path.realpath(__file__)).parent / "VERSION"
__version__ = _version_file.read_text().strip()
