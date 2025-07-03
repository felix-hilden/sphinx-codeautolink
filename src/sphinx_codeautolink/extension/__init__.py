"""Sphinx extension implementation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from traceback import print_exc

from sphinx import version_info as sphinx_version
from sphinx.ext.intersphinx import InventoryAdapter
from sphinx.util import import_object

from sphinx_codeautolink.parse import Name
from sphinx_codeautolink.warn import logger, warn_type

from .backref import CodeExample, CodeRefsVisitor
from .block import CodeBlockAnalyser, SourceTransform, link_html
from .cache import DataCache
from .directive import RemoveExtensionVisitor
from .resolve import CouldNotResolve, resolve_location


@dataclass
class DocumentedObject:
    """Autodoc-documented code object."""

    what: str
    obj: object
    return_type: str = None


def print_exceptions(*, append_source: bool = False):
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
            except Exception as e:
                print_exc()
                if append_source:
                    doctree = args[2] if len(args) > 1 else kwargs["doctree"]
                    source = doctree["source"]
                    msg = f"in document `{source}`"
                    if e.args:
                        e.args = (e.args[0] + f" ({msg})", *e.args[1:])
                    else:
                        e.args = (f"Unexpected error {msg}",)
                raise

        return wrapper

    return decorator


class SphinxCodeAutoLink:
    """Provide functionality and manage state between events."""

    def __init__(self) -> None:
        # Configuration
        self.do_nothing = False
        self.global_preface: list[str] = []
        self.custom_blocks = None
        self.concat_default = None
        self.search_css_classes = None
        self.inventory_map: dict[str, str] = {}
        self.warn_missing_inventory = None
        self.warn_failed_resolve = None
        self.warn_no_backreference = None
        self.warn_default_parse_fail = None
        self.highlight_lang = None

        # Populated once
        self.outdated_docs: set[str] = set()
        self.inventory = {}
        self.code_refs: dict[str, list[CodeExample]] = {}

        # Changing state
        self.cache: DataCache | None = None

    @print_exceptions()
    def build_inited(self, app) -> None:
        """Handle initial setup."""
        if app.builder.name not in ("html", "dirhtml"):
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
        self.inventory_map = app.config.codeautolink_inventory_map
        self.warn_missing_inventory = app.config.codeautolink_warn_on_missing_inventory
        self.warn_failed_resolve = app.config.codeautolink_warn_on_failed_resolve
        self.warn_no_backreference = app.config.codeautolink_warn_on_no_backreference
        self.warn_default_parse_fail = (
            app.config.codeautolink_warn_on_default_parse_fail
        )
        self.highlight_lang = app.config.highlight_language

        # Append static resources path so references in setup() are valid
        app.config.html_static_path.append(
            str(Path(__file__).parent.with_name("static").absolute())
        )

        preface = app.config.codeautolink_global_preface
        if preface:
            self.global_preface = preface.split("\n")

    @print_exceptions()
    def autodoc_process_docstring(self, app, what, name, obj, options, lines) -> None:
        """Handle autodoc-process-docstring event."""
        if self.do_nothing:
            return

        if app.config.codeautolink_autodoc_inject:
            lines.append("")
            lines.append(".. autolink-examples:: " + name)
            lines.append("   :collapse:")

    @print_exceptions(append_source=True)
    def parse_blocks(self, app, doctree) -> None:
        """Parse code blocks for later link substitution."""
        if self.do_nothing:
            return

        visitor = CodeBlockAnalyser(
            doctree,
            source_dir=app.srcdir,
            global_preface=self.global_preface,
            custom_blocks=self.custom_blocks,
            concat_default=self.concat_default,
            default_highlight_lang=self.highlight_lang,
            warn_default_parse_fail=self.warn_default_parse_fail,
        )
        doctree.walkabout(visitor)
        self.cache.transforms[visitor.current_document] = visitor.source_transforms

    def merge_environments(self, app, env, docnames, other) -> None:
        """Merge transform information."""
        if self.do_nothing:
            return

        env.sphinx_codeautolink_transforms.update(other.sphinx_codeautolink_transforms)

    def purge_doc_from_environment(self, app, env, docname) -> None:
        """Remove transforms from cache."""
        if self.cache:
            self.cache.transforms.pop(docname, None)

    @staticmethod
    def make_inventory(app):
        """Create object inventory from local info and intersphinx."""
        inv_parts = {
            k: str(
                Path(app.outdir)
                / (app.builder.get_target_uri(v.docname) + f"#{v.node_id}")
            )
            for k, v in app.env.domains["py"].objects.items()
        }
        inventory = {
            "py:class": {k: (None, None, v, None) for k, v in inv_parts.items()}
        }
        inter_inv = InventoryAdapter(app.env).main_inventory
        transposed = transpose_inventory(inter_inv, relative_to=app.outdir)
        transposed.update(
            transpose_inventory(inventory, relative_to=app.outdir, use_tuple=True)
        )
        return transposed

    @print_exceptions()
    def create_references(self, app, env) -> None:
        """Clean source transforms and create code references."""
        if self.do_nothing:
            return

        skipped = set()
        self.inventory = self.make_inventory(app)
        for doc, transforms in self.cache.transforms.items():
            self.filter_and_resolve(transforms, skipped, doc)
            for transform in transforms:
                for name in transform.names:
                    self.code_refs.setdefault(name.resolved_location, []).append(
                        transform.example
                    )
        if skipped and self.warn_missing_inventory:
            tops = sorted({s.split(".")[0] for s in skipped})
            msg = (
                f"Cannot locate modules: {str(tops)[1:-1]}"
                "\n  because of missing intersphinx or documentation entries"
            )
            logger.warning(msg, type=warn_type, subtype="missing_inventory")

    def filter_and_resolve(
        self, transforms: list[SourceTransform], skipped: set[str], doc: str
    ) -> None:
        """Try to link name chains to objects."""
        for transform in transforms:
            filtered = []
            for name in transform.names:
                if not name.code_str:
                    continue  # empty transform target (2 calls in a row)
                try:
                    key = resolve_location(name, self.inventory)
                except CouldNotResolve as e:
                    if self.warn_failed_resolve:
                        path = ".".join(name.import_components).replace(".()", "()")
                        msg = (
                            f"Could not resolve {self._resolve_msg(name)}"
                            f" using path `{path}`.\n{e!s}"
                        )
                        logger.warning(
                            msg,
                            type=warn_type,
                            subtype="failed_resolve",
                            location=(doc, transform.doc_lineno),
                        )
                    continue
                key = self.inventory_map.get(key, key)
                if key not in self.inventory:
                    if self.warn_missing_inventory:
                        msg = (
                            f"Inventory missing `{key}`"
                            f" when resolving {self._resolve_msg(name)}."
                            "\nPossibly missing documentation entry entirely,"
                            " or the object has been relocated from the source file."
                        )
                        logger.warning(
                            msg,
                            type=warn_type,
                            subtype="missing_inventory",
                            location=(doc, transform.doc_lineno),
                        )
                    skipped.add(key)
                    continue
                name.resolved_location = key
                filtered.append(name)
            transform.names = filtered

    @staticmethod
    def _resolve_msg(name: Name) -> str:
        if name.lineno == name.end_lineno:
            line = f"line {name.lineno}"
        else:
            line = f"lines {name.lineno}-{name.end_lineno}"

        return f"`{name.code_str}` on {line}"

    @print_exceptions(append_source=True)
    def generate_backref_tables(self, app, doctree, docname):
        """Generate backreference tables."""
        if self.do_nothing:
            rm_vis = RemoveExtensionVisitor(doctree)
            return doctree.walkabout(rm_vis)

        visitor = CodeRefsVisitor(
            doctree,
            code_refs=self.code_refs,
            docname=docname,
            builder=app.builder,
            warn_no_backreference=self.warn_no_backreference,
        )
        doctree.walk(visitor)
        return None

    @print_exceptions()
    def apply_links(self, app, exception) -> None:
        """Apply links to HTML output and write refs file."""
        if self.do_nothing or exception is not None:
            return

        for doc, transforms in self.cache.transforms.items():
            if not transforms or str(Path(doc)) not in self.outdated_docs:
                continue
            link_html(
                doc,
                app.outdir,
                transforms,
                self.inventory,
                self.custom_blocks,
                self.search_css_classes,
                builder_name=app.builder.name,
            )

        self.cache.write()


def transpose_inventory(
    inv: dict, relative_to: str, *, use_tuple: bool = False
) -> dict[str, str]:
    """
    Transpose Sphinx inventory from {type: {name: (..., location)}} to {name: location}.

    Also filters the inventory to Python domain only.

    Parameters
    ----------
    inv
        Sphinx inventory
    relative_to
        if a local file is found, transform it to be relative to this dir
    use_tuple
        force using Sphinx inventory tuple interface,
        TODO: move to class interface if it becomes public (#173)
    """
    transposed = {}
    for type_, items in inv.items():
        if not type_.startswith("py:"):
            continue
        for item, info in items.items():
            location = (
                info.uri if not use_tuple and sphinx_version >= (8, 2) else info[2]
            )
            if not location.startswith("http"):
                location = str(Path(location).relative_to(relative_to))
            transposed[item] = location
    return transposed
