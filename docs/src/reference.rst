.. _reference:

Reference
=========
The public API of sphinx-codeautolink consists only of the configuration
and directives made available to Sphinx.
The extension is enabled with the name ``sphinx_codeautolink``.

Configuration
-------------
- :code:`codeautolink_concat_blocks`: Default behavior for code example
  concatenation. Concatenated code blocks are treated as a continuous source,
  so that imports and statements in previous blocks affect later blocks.
  Value must be one of:

  - "none" - no concatenation
  - "section" - blocks between titles
  - "file" - all blocks in the current file

Directives
----------
- :code:`.. code-refs:: object`: Insert a table containing links to sections
  that reference ``object`` in their code examples.
- :code:`.. concat-blocks:: level`: Toggle literal block concatenation.
  Concatenation is begun at the directive, not applied retroactively.
  The directive also resets concatenation state.
  ``level`` must be one of:

  - "none" - no concatenation
  - "section" - blocks between titles
  - "file" - all blocks in the current file
  - "reset" - behavior reset to the value set in configuration

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
  - "none" - turn skipping off

  If "next" was specified, the following block consumes this directive even if
  it is not processed (e.g. non-Python blocks) to avoid placement confusion.
  Skipped blocks are ignored in block concatenation as well, and concatenation
  is resumed without breaks after skipping is over.
