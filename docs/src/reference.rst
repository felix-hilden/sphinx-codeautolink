.. _reference:

Reference
=========
The public API of sphinx-codeautolink consists mostly of the configuration
and directives made available to Sphinx.
The extension is enabled with the name ``sphinx_codeautolink``.
During the build phase, a cache containing code example information is saved
to the Sphinx doctree directory to track references during partial builds.

.. _configuration:

Configuration
-------------
.. confval:: codeautolink_autodoc_inject

   Type: ``bool``. Inject an :rst:dir:`autolink-examples` table
   to the end of all autodoc definitions. Defaults to :code:`False`.

.. confval:: codeautolink_global_preface

   Type: ``str``. Include an :rst:dir:`autolink-preface` before all blocks.
   When other prefaces or concatenated sources are used in a block,
   the global preface is included first and only once.

.. confval:: codeautolink_concat_default

   Type: ``bool``. Default behavior for code block concatenation (see
   :rst:dir:`autolink-concat`). Value corresponds to the "on" and "off"
   settings in the directive. Defaults to :code:`False`.

.. confval:: codeautolink_custom_blocks

   Type: ``Dict[str, None | str | Callable[[str], Tuple[str, str]]]``.
   Register custom parsers for lexers of unknown types of code blocks.
   They are registered as a dict mapping a block lexer name to a function
   possibly cleaning up the block content to valid Python syntax.
   If none is specified, no transformations are applied.
   A string is interpreted as an importable transformer function.
   The transformer must return two strings: the code appearing in documentation
   (often just the original source) and the cleaned Python source code.
   The transformer must preserve line numbers for correct matching.
   The transformer may raise a syntax error, which is caught automatically and
   a corresponding Sphinx warning using subtype "parsing_error" is issued.

.. confval:: codeautolink_search_css_classes

   Type: ``List[str]``. Extra CSS classes used to search for code examples
   when matching the final HTML. May contain multiple values separated by
   spaces as they would be passed to :code:`bs4.BeautifulSoup.find_all`.

.. confval:: codeautolink_inventory_map

   Type: ``Dict[str, str]``. Remap the final location of any inventory entry.
   Useful when objects are imported and documented somewhere else than their
   original location as advertised by ``__module__``.

.. confval:: codeautolink_warn_on_missing_inventory

   Type: ``bool``. Warn when an object cannot be found in
   the inventory (autodoc or intersphinx). Defaults to :code:`False`.

.. confval:: codeautolink_warn_on_failed_resolve

   Type: ``bool``. Warn when failing to resolve the canonical location
   of an object that a code element references. Defaults to :code:`False`.

.. confval:: codeautolink_warn_on_no_backreference

   Type: ``bool``. Warn when no backreference could be found
   from reference documentation using the :rst:dir:`autolink-examples` table.
   This highlights objects for which no tutorial, example or how-to exists.
   Defaults to :code:`False`.

.. confval:: codeautolink_warn_on_default_parse_fail

   Type: ``bool``. Warn when a code block using the ``default`` lexer
   cannot be parsed as Python. By default these cases are ignored by the
   syntax highlighter, so we match the behavior. Defaults to :code:`False`.

Directives
----------
.. rst:directive:: .. autolink-examples:: object

   Insert a table containing links to sections
   that reference ``object`` in their code examples.
   The table is removed if it would be empty.

   .. rubric:: Options

   .. rst:directive:option:: type
      :type: object's reference type, single value

      The object's reference type as used in other RST roles,
      e.g. ``:func:`function```. ``type`` is "class" by default,
      which seems to work for other types as well.

   .. rst:directive:option:: collapse
      :type: no value

      Make the table collapsible (using a "details" HTML tag).

.. rst:directive:: .. autolink-concat:: [mode]

   Toggle block concatenation.
   Concatenated code blocks are treated as a continuous source,
   so that imports and statements in previous blocks affect later blocks.
   Concatenation is begun at the directive, not applied retroactively.
   The directive also resets concatenation state. Until this directive is
   encountered, :confval:`codeautolink_concat_default` is used as the default
   behavior. ``mode``, if specified, must be one of:

   - "on" - concatenate all blocks in the current file (default value)
   - "off" - stop concatenation
   - "section" - concatenate until the next title, then reset to the previous
     value ("on" or "off") also resetting concatenation state

.. rst:directive:: .. autolink-preface:: [code]

   Include a hidden preface before a code block.
   A multiline preface can be written in the content portion of the directive.
   Prefaces are preserved in block concatenation, and are added to the source
   in the following order: :confval:`codeautolink_global_preface` > file preface
   > :rst:dir:`autolink-concat` sources (with their block prefaces)
   > block prefaces > block source.

   .. rubric:: Options

   .. rst:directive:option:: level
      :type: preface level

      - "next" - add preface only to the next block (default).
        Multiple prefaces are combined, and the next block consumes this
        directive even if it's not processed (e.g. non-Python blocks)
        to avoid placement confusion.
      - "file" - set a preface for all blocks in the current file, placed
        after  but before block-level
        prefaces.

.. rst:directive:: .. autolink-skip:: [level]

   Skip sphinx-codeautolink functionality.
   ``level``, if specified, must be one of:

   - "next" - next encountered block (default)
   - "section" - blocks until the next title
   - "file" - all blocks in the current file
   - "off" - turn skipping off

   If "next" was specified, the following block consumes this directive even if
   it is not processed (e.g. non-Python blocks) to avoid placement confusion.
   Skipped blocks are ignored in block concatenation as well, and concatenation
   is resumed without breaks after skipping is over.
   "Next" doesn't need to be specified right before the block that would consume
   it. For e.g. literal blocks the skip directive would be inserted before the
   preceding paragraph.

CSS class
---------
The CSS class used in all code block links is ``sphinx-codeautolink-a``.
By default, the links only have a light blue hover colour.
The style has been made more obvious in the documentation for demonstration.
See :ref:`examples-css` for more information.

Cleanup functions
-----------------
The functions below are usable for cleaning
``pycon`` and ``ipython`` code blocks.
They are intended to be used with :confval:`codeautolink_custom_blocks`.

.. autofunction:: sphinx_codeautolink.clean_pycon

.. autofunction:: sphinx_codeautolink.clean_ipython

Warning types
-------------
Sphinx logging machinery is used to issue warnings during documentation builds.
All warning subtypes below are in the ``codeautolink.*`` namespace
and can be ignored with configuring ``suppress_warnings``.

- ``invalid_argument``: issued when a directive is used incorrectly
- ``clean_block``: issued when cleaning a block fails with a ``SyntaxError``
- ``parse_block``: issued when parsing a block fails with a ``SyntaxError``
- ``import_star``: issued when a library cannot be imported to determine
  the names that an ``import *`` would introduce
- ``match_block``: issued when a block cannot be matched
- ``match_name``: issued when a code snippet cannot be matched

The following warnings are only issued depending on configuration:

- ``missing_inventory``: issued when an object cannot be found in the inventory
- ``failed_resolve``: issued when an object's canonical location in a module
  cannot be determined
