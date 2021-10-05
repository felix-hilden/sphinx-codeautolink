.. _reference:

Reference
=========
The public API of sphinx-codeautolink consists only of the configuration
and directives made available to Sphinx.
The extension is enabled with the name ``sphinx_codeautolink``.
During the build phase, a cache containing code example information is saved
to the Sphinx doctree directory to track references during partial builds.

.. _configuration:

Configuration
-------------
Available configuration values in ``conf.py``:

- :code:`codeautolink_autodoc_inject: bool`: Inject a :code:`autolink-examples`
  table to the end of all autodoc definitions. Defaults to :code:`True`.
- :code:`codeautolink_global_preface: str`: Preface code to include before
  all parsed code blocks. When other prefaces or concatenated sources are used
  in a block, the global preface is included first and only once.

Directives
----------
rST directives available in Sphinx documentation:

- :code:`.. autolink-examples:: object`: Insert a table containing links to
  sections that reference ``object`` in their code examples.
  The table is removed if it would have no entries or a non-HTML builder is
  used. Options:

  - ``:type: type``: the object's reference type as used in other roles,
    e.g. "func" (``:func:`foo```). ``type`` is "class" by default,
    which seems to work for as a default for other types as well.
  - ``:collapse:``: make the table collapsible (using a "details" HTML tag)

- :code:`.. autolink-concat:: [mode]`: Toggle literal block concatenation.
  Concatenated code blocks are treated as a continuous source,
  so that imports and statements in previous blocks affect later blocks.
  Concatenation is begun at the directive, not applied retroactively.
  The directive also resets concatenation state.
  ``mode``, if specified, must be one of:

  - "on" - concatenate all blocks in the current file (default value)
  - "off" - no concatenation (default behavior until a :code:`concat-blocks`
    directive is encountered)
  - "section" - concatenate blocks until the next title

- :code:`.. autolink-preface:: code`: Include a hidden preface in the next
  code block. The next block consumes this directive even if it is not
  processed (e.g. non-Python blocks) to avoid placement confusion.
  Multiple prefaces before a single block are combined.
  Prefaces are included in block concatenation.
- :code:`.. autolink-skip:: [level]`: Skip sphinx-codeautolink functionality.
  ``level``, if specified, must be one of:

  - "next" - next block (default)
  - "section" - blocks until the next title
  - "file" - all blocks in the current file
  - "off" - turn skipping off

  If "next" was specified, the following block consumes this directive even if
  it is not processed (e.g. non-Python blocks) to avoid placement confusion.
  Skipped blocks are ignored in block concatenation as well, and concatenation
  is resumed without breaks after skipping is over.
