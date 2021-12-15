"""Sphinx extension implementation."""
from dataclasses import dataclass
from functools import wraps
from typing import Dict, List, Optional, Set
from traceback import print_exc
from pathlib import Path

from sphinx.util import import_object
from sphinx.ext.intersphinx import InventoryAdapter

from .backref import CodeRefsVisitor, CodeExample
from .block import (
    CodeBlockAnalyser, SourceTransform, link_html, UserError, ParsingError
)
from .directive import RemoveExtensionVisitor
from .cache import DataCache
from .resolve import resolve_location


@dataclass
class DocumentedObject:
    """Autodoc-documented code object."""

    what: str
    obj: object
    return_type: str = None


def print_exceptions(append_source: bool = False):
    """
    Print the traceback of uncaught and unexpected exceptions.

    This is done because the Sphinx process masks the traceback
    and only displays the main error message making debugging difficult.
    If append_source is set, information about the currently processed document
    is pulled from the second argument named "doctree" and added to the message.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (UserError, ParsingError):
                raise
            except Exception as e:
                print_exc()
                if append_source:
                    doctree = args[2] if len(args) > 1 else kwargs['doctree']
                    source = doctree['source']
                    msg = f'in document `{source}`'
                    if e.args:
                        e.args = (e.args[0] + f' ({msg})',) + e.args[1:]
                    else:
                        e.args = (f'Unexpected error {msg}',)
                raise
        return wrapper
    return decorator


class SphinxCodeAutoLink:
    """Provide functionality and manage state between events."""

    def __init__(self):
        # Configuration
        self.do_nothing = False
        self.global_preface: List[str] = []
        self.custom_blocks = None
        self.concat_default = None
        self.search_css_classes = None

        # Populated once
        self.outdated_docs: Set[str] = set()
        self.inventory = {}
        self.code_refs: Dict[str, List[CodeExample]] = {}

        # Changing state
        self.cache: Optional[DataCache] = None

    @print_exceptions()
    def build_inited(self, app):
        """Handle initial setup."""
        if app.builder.name != 'html':
            self.do_nothing = True
            return

        self.cache = DataCache(app.doctreedir, app.srcdir)
        self.cache.read()
        app.env.sphinx_codeautolink_transforms = self.cache.transforms
        self.outdated_docs = {str(Path(d)) for d in app.builder.get_outdated_docs()}
        self.custom_blocks = app.config.codeautolink_custom_blocks
        for k, v in self.custom_blocks.items():
            if isinstance(v, str):
                self.custom_blocks[k] = import_object(v)
        self.concat_default = app.config.codeautolink_concat_default
        self.search_css_classes = app.config.codeautolink_search_css_classes

        # Append static resources path so references in setup() are valid
        app.config.html_static_path.append(
            str(Path(__file__).parent.with_name('static').absolute())
        )

        preface = app.config.codeautolink_global_preface
        if preface:
            self.global_preface = preface.split('\n')

    @print_exceptions()
    def autodoc_process_docstring(self, app, what, name, obj, options, lines):
        """Handle autodoc-process-docstring event."""
        if self.do_nothing:
            return

        if app.config.codeautolink_autodoc_inject:
            lines.append('')
            lines.append('.. autolink-examples:: ' + name)
            lines.append('   :collapse:')

    @print_exceptions(append_source=True)
    def parse_blocks(self, app, doctree):
        """Parse code blocks for later link substitution."""
        if self.do_nothing:
            return

        visitor = CodeBlockAnalyser(
            doctree,
            source_dir=app.srcdir,
            global_preface=self.global_preface,
            custom_blocks=self.custom_blocks,
            concat_default=self.concat_default,
        )
        doctree.walkabout(visitor)
        self.cache.transforms[visitor.current_document] = visitor.source_transforms

    @staticmethod
    def merge_environments(app, env, docnames, other):
        """Merge transform information."""
        env.sphinx_codeautolink_transforms.update(
            other.sphinx_codeautolink_transforms
        )

    def purge_doc_from_environment(self, app, env, docname):
        """Remove transforms from cache."""
        if self.cache:
            self.cache.transforms.pop(docname, None)

    @staticmethod
    def make_inventory(app):
        """Create object inventory from local info and intersphinx."""
        inv_parts = {
            k: str(
                Path(app.outdir)
                / (app.builder.get_target_uri(v.docname) + f'#{v.node_id}')
            )
            for k, v in app.env.domains['py'].objects.items()
        }
        inventory = {'py:class': {
            k: (None, None, v, None) for k, v in inv_parts.items()
        }}
        inter_inv = InventoryAdapter(app.env).main_inventory
        transposed = transpose_inventory(inter_inv, relative_to=app.outdir)
        transposed.update(transpose_inventory(inventory, relative_to=app.outdir))
        return transposed

    @print_exceptions()
    def create_references(self, app, env):
        """Clean source transforms and create code references."""
        if self.do_nothing:
            return

        self.inventory = self.make_inventory(app)
        for transforms in self.cache.transforms.values():
            self.filter_and_resolve(transforms)
            for transform in transforms:
                for name in transform.names:
                    self.code_refs.setdefault(name.resolved_location, []).append(
                        transform.example
                    )

    def filter_and_resolve(self, transforms: List[SourceTransform]):
        """Try to link name chains to objects."""
        for transform in transforms:
            filtered = []
            for name in transform.names:
                key = resolve_location(name, self.inventory)
                if not key or key not in self.inventory:
                    continue
                name.resolved_location = key
                filtered.append(name)
            transform.names = filtered

    @print_exceptions(append_source=True)
    def generate_backref_tables(self, app, doctree, docname):
        """Generate backreference tables."""
        if self.do_nothing:
            rm_vis = RemoveExtensionVisitor(doctree)
            return doctree.walkabout(rm_vis)

        visitor = CodeRefsVisitor(doctree, code_refs=self.code_refs)
        doctree.walk(visitor)

    @print_exceptions()
    def apply_links(self, app, exception):
        """Apply links to HTML output and write refs file."""
        if self.do_nothing or exception is not None:
            return

        for doc, transforms in self.cache.transforms.items():
            if not transforms or str(Path(doc)) not in self.outdated_docs:
                continue
            file = Path(app.outdir) / (doc + '.html')
            link_html(
                file,
                app.outdir,
                transforms,
                self.inventory,
                self.custom_blocks,
                self.search_css_classes,
            )

        self.cache.write()


def transpose_inventory(inv: dict, relative_to: str):
    """
    Transpose Sphinx inventory from {type: {name: (..., location)}} to {name: location}.

    Also filters the inventory to Python domain only.

    Parameters
    ----------
    inv
        Sphinx inventory
    relative_to
        if a local file is found, transform it to be relative to this dir
    """
    transposed = {}
    for type_, items in inv.items():
        if not type_.startswith('py:'):
            continue
        for item, info in items.items():
            location = info[2]
            if not location.startswith('http'):
                location = str(Path(location).relative_to(relative_to))
            transposed[item] = location
    return transposed
