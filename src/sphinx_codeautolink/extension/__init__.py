"""Sphinx extension implementation."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from pathlib import Path

from sphinx.ext.intersphinx import InventoryAdapter

from .backref import CodeRefsVisitor, CodeExample
from .block import CodeBlockAnalyser, SourceTransform, link_html
from .cache import DataCache
from .resolve import resolve_location


@dataclass
class DocumentedObject:
    """Autodoc-documented code object."""

    what: str
    obj: object
    return_type: str = None


class SphinxCodeAutoLink:
    """Provide functionality and manage state between events."""

    def __init__(self):
        self.do_nothing = False
        self.cache: Optional[DataCache] = None
        self.code_refs: Dict[str, List[CodeExample]] = {}
        self._inventory = {}
        self.outdated_docs: Set[str] = set()
        self.global_preface: List[str] = []

    def build_inited(self, app):
        """Handle initial setup."""
        if app.builder.name != 'html':
            self.do_nothing = True
            return

        self.cache = DataCache(app.doctreedir, app.srcdir)
        self.cache.read()
        self.outdated_docs = {str(Path(d)) for d in app.builder.get_outdated_docs()}

        # Append static resources path so references in setup() are valid
        app.config.html_static_path.append(
            str(Path(__file__).parent.with_name('static').absolute())
        )

        preface = app.config.codeautolink_global_preface
        if preface:
            self.global_preface = preface.split('\n')

    def autodoc_process_docstring(self, app, what, name, obj, options, lines):
        """Handle autodoc-process-docstring event."""
        if self.do_nothing:
            return

        if app.config.codeautolink_autodoc_inject:
            lines.append('')
            lines.append('.. autolink-examples:: ' + name)
            lines.append('   :collapse:')

    def parse_blocks(self, app, doctree):
        """Parse code blocks for later link substitution."""
        if self.do_nothing:
            return

        visitor = CodeBlockAnalyser(
            doctree, source_dir=app.srcdir, global_preface=self.global_preface
        )
        doctree.walkabout(visitor)
        self.cache.transforms[visitor.current_document] = visitor.source_transforms

    def once_on_doctree_resolved(self, app):
        """Clean source transforms and create code references."""
        if self.code_refs or self.do_nothing:
            return

        for transforms in self.cache.transforms.values():
            self.filter_and_resolve(transforms, app)
            for transform in transforms:
                for name in transform.names:
                    self.code_refs.setdefault(name.resolved_location, []).append(
                        transform.example
                    )

    def generate_backref_tables(self, app, doctree, docname):
        """Generate backreference tables."""
        self.once_on_doctree_resolved(app)
        visitor = CodeRefsVisitor(
            doctree,
            code_refs=self.code_refs,
            remove_directives=self.do_nothing,
        )
        doctree.walk(visitor)

    def filter_and_resolve(self, transforms: List[SourceTransform], app):
        """Try to link name chains to objects."""
        inventory = self.make_inventory(app)
        for transform in transforms:
            filtered = []
            for name in transform.names:
                key = resolve_location(name)
                if not key or key not in inventory:
                    continue
                name.resolved_location = key
                filtered.append(name)
            transform.names = filtered

    def make_inventory(self, app):
        """Create object inventory from local info and intersphinx."""
        if self._inventory:
            return self._inventory

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
        self._inventory = transposed
        return self._inventory

    def apply_links(self, app, exception):
        """Apply links to HTML output and write refs file."""
        if self.do_nothing or exception is not None:
            return

        for doc, transforms in self.cache.transforms.items():
            if not transforms or str(Path(doc)) not in self.outdated_docs:
                continue
            file = Path(app.outdir) / (doc + '.html')
            link_html(file, app.outdir, transforms, self.make_inventory(app))

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
