"""Sphinx extension implementation."""
import json

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

from sphinx.ext.intersphinx import InventoryAdapter

from .backref import CodeRefsVisitor, CodeExample
from .block import CodeBlockAnalyser, link_html, Name, NameBreak


@dataclass
class DocumentedObject:
    """Autodoc-documented code object."""

    what: str
    obj: object
    return_type: str = None


class SphinxCodeAutoLink:
    """Provide functionality and manage state between events."""

    code_refs_file = 'sphinx-codeautolink-refs.json'

    def __init__(self):
        self.code_refs: Dict[str, Dict[str, List[CodeExample]]] = {}
        self._flat_refs: Dict[str, List[CodeExample]] = {}
        self.block_visitors: List[CodeBlockAnalyser] = []
        self.do_nothing = False
        self.objects: Dict[str, DocumentedObject] = {}
        self._inventory = {}

    def make_flat_refs(self, app):
        """Flattened version of :attr:`code_refs`."""
        if self._flat_refs:
            return self._flat_refs

        self.parse_transforms(app)

        for refs in self.code_refs.values():
            for doc, examples in refs.items():
                self._flat_refs.setdefault(doc, []).extend(examples)

        return self._flat_refs

    def parse_transforms(self, app):
        """Construct code_refs and try to link name chains."""
        inventory = self.make_inventory(app)
        for visitor in self.block_visitors:
            refs = {}
            for transform in visitor.source_transforms:
                filtered = []
                for name in transform.names:
                    key = self.find_in_objects(name)
                    if not key or key not in inventory:
                        continue
                    name.resolved_location = key
                    filtered.append(name)
                    refs.setdefault(key, []).append(transform.example)
                transform.names = filtered
            self.code_refs[visitor.current_document] = refs

    def find_in_objects(self, chain: Name) -> Optional[str]:
        """Find the final type that a name refers to."""
        comps = []
        for comp in chain.import_components:
            if comp.name == NameBreak.call:
                name = '.'.join(comps)
                if name in self.objects and self.objects[name].return_type:
                    comps = [self.objects[name].return_type]
                    continue
                else:
                    return
            comps.append(comp.name)
        return '.'.join(comps)

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

    def build_inited(self, app):
        """Handle initial setup."""
        if app.builder.name != 'html':
            self.do_nothing = True
            return

        # Append static resources path so references in setup() are valid
        app.config.html_static_path.append(
            str(Path(__file__).parent.with_name('static').absolute())
        )

        # Read serialised references from last build
        refs_file = Path(app.srcdir) / self.code_refs_file
        if not refs_file.exists():
            return
        content = json.loads(refs_file.read_text('utf-8'))
        for file, ref in content.items():
            full_path = Path(app.srcdir) / (file + '.rst')
            if not full_path.exists():
                continue
            self.code_refs[file] = {
                obj: [CodeExample(**e) for e in examples]
                for obj, examples in ref.items()
            }

    def autodoc_process_docstring(self, app, what, name, obj, options, lines):
        """Handle autodoc-process-docstring event."""
        if self.do_nothing:
            return

        if app.config.codeautolink_autodoc_inject:
            lines.append(f'.. code-refs:: {name}')

        d_obj = DocumentedObject(what, obj)
        if what in ('class', 'exception'):
            d_obj.annotation = name
        elif what in ('function', 'method'):
            ret_annotation = obj.__annotations__.get('return', None)
            if ret_annotation and not hasattr(ret_annotation, '__origin__'):
                d_obj.annotation = getattr(ret_annotation, '__name__', None)
        self.objects[name] = d_obj

    def parse_blocks(self, app, doctree):
        """Parse code blocks for later link substitution."""
        if self.do_nothing:
            return

        visitor = CodeBlockAnalyser(doctree, source_dir=app.srcdir)
        doctree.walkabout(visitor)
        self.block_visitors.append(visitor)

    def generate_backref_tables(self, app, doctree, docname):
        """Generate backreference tables."""
        visitor = CodeRefsVisitor(
            doctree,
            code_refs=self.make_flat_refs(app),
            remove_directives=self.do_nothing,
        )
        doctree.walk(visitor)

    def apply_links(self, app, exception):
        """Apply links to HTML output and write refs file."""
        if self.do_nothing or exception is not None:
            return

        for visitor in self.block_visitors:
            if not visitor.source_transforms:
                continue
            file = Path(app.outdir) / (visitor.current_document + '.html')
            link_html(
                file, app.outdir, visitor.source_transforms, self.make_inventory(app)
            )

        refs_file = Path(app.srcdir) / self.code_refs_file
        refs = {}
        for file, ref in self.code_refs.items():
            refs[file] = {
                obj: [asdict(e) for e in examples]
                for obj, examples in ref.items()
            }
        refs_file.write_text(json.dumps(refs, indent=4), 'utf-8')


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
