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
.. confval:: codeautolink_autodoc_inject

   Type: ``bool``. Inject a :rst:dir:`autolink-examples` table
   to the end of all autodoc definitions. Defaults to :code:`True`.

.. confval:: codeautolink_global_preface

   Type: ``str``. Include a :rst:dir:`autolink-preface` before all blocks.
   When other prefaces or concatenated sources are used in a block,
   the global preface is included first and only once.

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

   Toggle literal block concatenation.
   Concatenated code blocks are treated as a continuous source,
   so that imports and statements in previous blocks affect later blocks.
   Concatenation is begun at the directive, not applied retroactively.
   The directive also resets concatenation state.
   ``mode``, if specified, must be one of:

   - "on" - concatenate all blocks in the current file (default value)
   - "off" - no concatenation (default behavior until a :code:`concat-blocks`
     directive is encountered)
   - "section" - concatenate blocks until the next title

.. rst:directive:: .. autolink-preface:: [code]

   Include a hidden preface in the next code block.
   The next block consumes this directive even if it is not
   processed (e.g. non-Python blocks) to avoid placement confusion.
   A multiline preface can be written in the content portion of the directive.
   Prefaces are included in block concatenation.

.. rst:directive:: .. autolink-skip:: [level]

   Skip sphinx-codeautolink functionality.
   ``level``, if specified, must be one of:

   - "next" - next block (default)
   - "section" - blocks until the next title
   - "file" - all blocks in the current file
   - "off" - turn skipping off

   If "next" was specified, the following block consumes this directive even if
   it is not processed (e.g. non-Python blocks) to avoid placement confusion.
   Skipped blocks are ignored in block concatenation as well, and concatenation
   is resumed without breaks after skipping is over.
