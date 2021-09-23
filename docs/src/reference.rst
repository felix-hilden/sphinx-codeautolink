.. _reference:

Reference
=========
The public API of sphinx-codeautolink consists only of the configuration
and directives made available to Sphinx.
The extension is enabled with the name ``sphinx_codeautolink``.
During the build phase, a JSON file called ``sphinx-codeautolink-refs.json``
is saved to the source folder to track code references during partial builds.

Configuration
-------------
Available configuration values in ``conf.py``:

- :code:`codeautolink_autodoc_inject: bool`: Inject a :code:`code-refs` table
  to the end of all autodoc definitions. Defaults to :code:`True`.

Directives
----------
rST directives available in Sphinx documentation:

- :code:`.. code-refs:: object [type]`: Insert a table containing links to
  sections that reference ``object`` in their code examples. ``type`` is the
  object's type as used in other Sphinx roles like "func" (``:func:`foo```).
  ``type`` is "class" by default, which seems to work for other types as well.
  The table is removed if it would have no entries or a non-HTML builder is
  used.
- :code:`.. concat-blocks:: [mode]`: Toggle literal block concatenation.
  Concatenated code blocks are treated as a continuous source,
  so that imports and statements in previous blocks affect later blocks.
  Concatenation is begun at the directive, not applied retroactively.
  The directive also resets concatenation state.
  ``mode``, if specified, must be one of:

  - "on" - concatenate all blocks in the current file (default value)
  - "off" - no concatenation (default behavior until a :code:`concat-blocks`
    directive is encountered)
  - "section" - concatenate blocks until the next title

- :code:`.. implicit-import:: code`: Include an implicit import in the next
  code block. The next block consumes this directive even if it is not
  processed (e.g. non-Python blocks) to avoid placement confusion.
  Multiple directives can be combined for more imports in the following block.
  Implicit imports are included in block concatenation.
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
