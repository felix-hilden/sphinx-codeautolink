"""Sphinx extension implementation."""
import json
import posixpath

from typing import Dict, List
from pathlib import Path
from warnings import warn

from sphinx.ext.intersphinx import fetch_inventory, INVENTORY_FILENAME, InventoryAdapter

from .backref import CodeRefsVisitor, CodeExample
from .block import CodeBlockAnalyser, link_html


class SphinxCodeAutoLink:
    """Provide functionality and manage state between events."""

    code_refs_file = 'sphinx-codeautolink-refs.json'

    def __init__(self):
        self.code_refs: Dict[str, Dict[str, List[CodeExample]]] = {}
        self.block_visitors: List[CodeBlockAnalyser] = []
        self.do_nothing = False
        self._flat_refs = {}

    @property
    def flat_refs(self):
        """Flattened version of :attr:`code_refs`."""
        if not self._flat_refs:
            for refs in self.code_refs.values():
                for doc, examples in refs.items():
                    self._flat_refs.setdefault(doc, []).extend(examples)

        return self._flat_refs

    def read_references(self, app):
        """Nullify extension if not on HTML builder, read ref file."""
        if app.builder.name != 'html':
            self.do_nothing = True
            return

        refs_file = Path(app.srcdir) / self.code_refs_file
        if not refs_file.exists():
            return
        content = json.loads(refs_file.read_text('utf-8'))
        for file, ref in content.items():
            full_path = Path(app.srcdir) / (file + '.rst')
            if not full_path.exists():
                continue
            self.code_refs[file] = {
                obj: [
                    CodeExample(e['document'], e['ref_id'], e['headings'])
                    for e in examples
                ]
                for obj, examples in ref.items()
            }

    def parse_blocks(self, app, doctree):
        """Parse code blocks for later link substitution."""
        if self.do_nothing:
            return

        visitor = CodeBlockAnalyser(
            doctree,
            concat_default=app.config.codeautolink_concat_blocks,
            source_dir=app.srcdir,
        )
        doctree.walkabout(visitor)
        self.code_refs[visitor.current_document] = visitor.code_refs
        self.block_visitors.append(visitor)

    def generate_backref_tables(self, app, doctree, docname):
        """Generate backreference tables."""
        visitor = CodeRefsVisitor(
            doctree,
            code_refs=self.flat_refs,
            remove_directives=self.do_nothing,
        )
        doctree.walk(visitor)

    def apply_links(self, app, exception):
        """Apply links to HTML output and write refs file."""
        if self.do_nothing or exception is not None:
            return

        inv_file = posixpath.join(app.outdir, INVENTORY_FILENAME)
        if not Path(inv_file).exists():
            msg = (
                'sphinx-codeautolink: cannot locate object inventory '
                f' in {INVENTORY_FILENAME}, no links applied'
            )
            warn(msg, RuntimeWarning)
            return

        inv = fetch_inventory(app, app.outdir, inv_file)
        inter_inv = InventoryAdapter(app.env).main_inventory
        transposed = transpose_inventory(inter_inv, relative_to=app.outdir)
        transposed.update(transpose_inventory(inv, relative_to=app.outdir))

        for visitor in self.block_visitors:
            if not visitor.source_transforms:
                continue
            file = Path(app.outdir) / (visitor.current_document + '.html')
            link_html(file, app.outdir, visitor.source_transforms, transposed)

        refs_file = Path(app.srcdir) / self.code_refs_file
        refs = {}
        for file, ref in self.code_refs.items():
            refs[file] = {
                obj: [
                    {'document': e.document, 'ref_id': e.ref_id, 'headings': e.headings}
                    for e in examples
                ]
                for obj, examples in ref.items()
            }
        refs_file.write_text(json.dumps(refs, indent=4), 'utf-8')

    def autodoc_process_docstring(self, app, what, name, obj, options, lines):
        """Inject code-refs tables to docstrings."""
        if not app.config.codeautolink_autodoc_inject or self.do_nothing:
            return

        lines.append(f'.. code-refs:: {name}')


def transpose_inventory(inv: dict, relative_to: str):
    """
    Transpose Sphinx inventory from {type: {name: (..., location)}} to {name: location}.

    Parameters
    ----------
    inv
        Sphinx inventory
    relative_to
        if a local file is found, transform it to be relative to this dir
    """
    transposed = {}
    for _, items in inv.items():
        for item, info in items.items():
            location = info[2]
            if not location.startswith('http'):
                location = str(Path(location).relative_to(relative_to))
            transposed[item] = location
    return transposed
