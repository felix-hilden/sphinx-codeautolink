"""Sphinx extension implementation."""
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from typing import Dict, List, Optional, Tuple, Any, Set
from pathlib import Path

from sphinx.ext.intersphinx import InventoryAdapter

from .backref import CodeRefsVisitor, CodeExample
from .block import CodeBlockAnalyser, SourceTransform, link_html, Name, NameBreak
from .cache import DataCache


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

    def build_inited(self, app):
        """Handle initial setup."""
        if app.builder.name != 'html':
            self.do_nothing = True
            return

        self.cache = DataCache(app.srcdir)
        self.cache.read()
        self.outdated_docs = {str(Path(d)) for d in app.builder.get_outdated_docs()}

        # Append static resources path so references in setup() are valid
        app.config.html_static_path.append(
            str(Path(__file__).parent.with_name('static').absolute())
        )

    def autodoc_process_docstring(self, app, what, name, obj, options, lines):
        """Handle autodoc-process-docstring event."""
        if self.do_nothing:
            return

        if app.config.codeautolink_autodoc_inject:
            lines.append(f'.. code-refs:: {name}')

    def parse_blocks(self, app, doctree):
        """Parse code blocks for later link substitution."""
        if self.do_nothing:
            return

        visitor = CodeBlockAnalyser(doctree, source_dir=app.srcdir)
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
            file = (Path(app.outdir) / doc).with_suffix('.html')
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


def resolve_location(chain: Name) -> Optional[str]:
    """Find the final type that a name refers to."""
    comps = []
    for comp in chain.import_components:
        if comp == NameBreak.call:
            new = locate_type(tuple(comps))
            if new is None:
                return
            comps = new.split('.')
        else:
            comps.append(comp)
    return '.'.join(comps)


@lru_cache(maxsize=None)
def locate_type(components: Tuple[str]) -> Optional[str]:
    """Find type hint and resolve to new location."""
    value, index = closest_module(components)
    if index is None or index == len(components):
        return
    remaining = components[index:]
    real_location = '.'.join(components[:index])
    for component in remaining:
        value = getattr(value, component, None)
        real_location += '.' + component
        if value is None:
            return

        if isinstance(value, type):
            # We don't differentiate between classmethods and ordinary methods,
            # as we can't guarantee correct runtime behavior anyway.
            real_location = fully_qualified_name(value)

    # A possible function / method call needs to be last in the chain.
    # Otherwise we might follow return types on function attribute access.
    if callable(value):
        ret_annotation = value.__annotations__.get('return', None)
        if not ret_annotation or hasattr(ret_annotation, '__origin__'):
            return
        real_location = fully_qualified_name(ret_annotation)

    return real_location


def fully_qualified_name(type_: type) -> str:
    """Construct the fully qualified name of a type."""
    return getattr(type_, '__module__', '') + '.' + getattr(type_, '__qualname__', '')


@lru_cache(maxsize=None)
def closest_module(components: Tuple[str]) -> Tuple[Any, Optional[int]]:
    """Find closest importable module."""
    mod = None
    for i in range(1, len(components) + 1):
        try:
            mod = import_module('.'.join(components[:i]))
        except ImportError:
            break
    else:
        return None, None

    return mod, i - 1
