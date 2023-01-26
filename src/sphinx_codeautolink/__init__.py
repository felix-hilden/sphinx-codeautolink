"""Sphinx extension for linking code examples to reference documentation."""
from sphinx.application import Sphinx

from .extension import SphinxCodeAutoLink, backref, directive
from .extension.block import clean_ipython, clean_pycon  # NOQA

__version__ = "0.13.2"


def setup(app: Sphinx):
    """Set up extension, directives and events."""
    state = SphinxCodeAutoLink()
    app.setup_extension("sphinx.ext.autodoc")
    app.add_css_file("sphinx-codeautolink.css")
    app.add_config_value("codeautolink_autodoc_inject", False, "html", types=[bool])
    app.add_config_value("codeautolink_global_preface", "", "html", types=[str])
    app.add_config_value("codeautolink_custom_blocks", {}, "html", types=[dict])
    app.add_config_value("codeautolink_concat_default", False, "html", types=[bool])
    app.add_config_value("codeautolink_search_css_classes", [], "html", types=[list])
    app.add_config_value(
        "codeautolink_warn_on_missing_inventory", False, "html", types=[bool]
    )
    app.add_config_value(
        "codeautolink_warn_on_failed_resolve", False, "html", types=[bool]
    )

    app.add_directive("autolink-concat", directive.Concat)
    app.add_directive("autolink-examples", directive.Examples)
    app.add_directive("autolink-preface", directive.Preface)
    app.add_directive("autolink-skip", directive.Skip)

    app.connect("builder-inited", state.build_inited)
    app.connect("autodoc-process-docstring", state.autodoc_process_docstring)
    app.connect("doctree-read", state.parse_blocks)
    app.connect("env-merge-info", state.merge_environments)
    app.connect("env-purge-doc", state.purge_doc_from_environment)
    app.connect("env-updated", state.create_references)
    app.connect("doctree-resolved", state.generate_backref_tables)
    app.connect("build-finished", state.apply_links)

    app.add_node(
        backref.DetailsNode, html=(backref.visit_details, backref.depart_details)
    )
    app.add_node(
        backref.SummaryNode, html=(backref.visit_summary, backref.depart_summary)
    )
    return {"version": __version__, "env_version": 1, "parallel_read_safe": True}
