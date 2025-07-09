.. _release-notes:

Release notes
=============

These release notes are based on
`Keep a Changelog <https://keepachangelog.com>`_.
sphinx-codeautolink adheres to
`Semantic Versioning <https://semver.org>`_.

0.17.5 (2025-07-09)
-------------------
- Add ``Python`` to default lexers (:issue:`194`)

0.17.4 (2025-03-07)
-------------------
- Fix backreference links using relative URIs (:issue:`190`)

0.17.3 (2025-03-06)
-------------------
- Fix Sphinx InventoryItem deprecation warning (:issue:`173`)
- Add support for the DIRHTML Sphinx builder (:issue:`188`)

0.17.2 (2025-03-02)
-------------------
- Support :rst:dir:`testsetup` from ``sphinx.ext.doctest`` as another
  type of preface (:issue:`186`)

0.17.1 (2025-02-24)
-------------------
- Add translations via i18n (:issue:`164`)
- Fix attribute and call after walrus leading parser error (:issue:`174`)
- Fix parsing error in doctest blocks with empty lines (:issue:`176`)
- Improve error message on uncaught parsing errors (:issue:`177`)
- Add ``level`` argument to :rst:dir:`autolink-preface` to support
  file-level prefaces (:issue:`180`)

0.17.0 (2025-02-18)
-------------------
Added
*****
- Add more Pygments lexer aliases in code blocks (:issue:`160`)
- Introduce :confval:`codeautolink_warn_on_no_backreference` to highlight
  where reference documentation does not appear to have
  a corresponding tutorial or how-to (:issue:`161`)
- Support the ``default`` lexer, literal blocks, ``.. highlight::`` directive
  and ``highlight_language`` configuration (:issue:`166`)
- Add :confval:`codeautolink_warn_on_default_parse_fail` to warn about
  failing to link code blocks without a language parameter (:issue:`166`)
- Detect and implicitly use ``pycon`` lexer for blocks that look like
  console code (:issue:`168`)

Fixed
*****
- Fix undocumented class attribute leading to a crash (:issue:`165`)
- Fix skipping blocks with identical content to linked ones (:issue:`172`)

0.16.2 (2025-01-16)
-------------------
- Fix regression in not handling malformed return types (:issue:`159`)

0.16.1 (2025-01-15)
-------------------
- Fix regression in not handling invalid return type hints (:issue:`158`)

0.16.0 (2025-01-11)
-------------------
- Declare support for Python 3.12 and 3.13 (:issue:`150`)
- Remove support for Python 3.7-3.9 (:issue:`150`, :issue:`157`)
- Fix changed whitespace handling in Pygments 2.19 (:issue:`152`)
- Improve support for future and string annotations (:issue:`155`)

0.15.2 (2024-06-03)
-------------------
- Fix matching of ``import a, b`` (:issue:`142`)

0.15.1 (2024-04-17)
-------------------
- Fix linking blocks with line numbers (:issue:`137`)
- Use safer version of ``mro`` to support ``type`` (:issue:`120`)

0.15.0 (2023-02-05)
-------------------
- Fix handling of syntax errors in parsed blocks (:issue:`135`)
- Differentiate warning types of block cleaning and parsing (:issue:`136`)

0.14.1 (2023-01-30)
-------------------
- Fix added debug info on failed resolving crashing the build (:issue:`134`)

0.14.0 (2023-01-28)
-------------------
- Add configuration for mapping inventory locations
  (:confval:`codeautolink_inventory_map`) (:issue:`131`)
- Improve warning messages to include debugging hints (:issue:`131`)
- Fix AnnAssigns with no links not overwriting values (:issue:`133`)

0.13.2 (2023-01-26)
-------------------
- Fix parsing IPython blocks that had a leading comment (:issue:`130`)

0.13.1 (2023-01-16)
-------------------
- Fix IPython block parsing where output is not prefixed with `Out`
  (:issue:`129`)

0.13.0 (2023-01-08)
-------------------
- Declare support for Python 3.11 (:issue:`122`)
- Remove support for Python 3.6 (:issue:`123`)
- Disallow faulty IPython version 8.7.0 (:issue:`124`)
- Correctly require Beautiful Soup version 4.8.1 (:issue:`128`)

0.12.1 (2022-11-05)
-------------------
- Created an Anaconda (Conda-Forge) binary (:issue:`111`)
- Fix IPython parsing on multiline output and empty input (:issue:`119`)

0.12.0 (2022-09-14)
-------------------
- Link assignment targets, bare names and annotated function arguments
  (:issue:`109`)
- Initial support for match statement (:issue:`110`)
- Fix links when assigning walrus statement result (:issue:`112`)
- Fix links in multi-assignments when one target is unlinkable (:issue:`113`)

0.11.0 (2022-06-08)
-------------------
- Support Python 3.10 (:issue:`33`)
- Include the expected location of a type in
  :confval:`codeautolink_warn_on_failed_resolve` for debugging (:issue:`106`)
- Define extension environment version for Sphinx (:issue:`107`)
- Merge environments only when the extension is active (:issue:`107`)
- Link arguments and annotated assignment with type hints (:issue:`108`)

0.10.0 (2022-01-25)
-------------------
- Don't try to link empty name between two subsequent calls (:issue:`96`)
- Introduce :confval:`codeautolink_warn_on_missing_inventory` and
  :confval:`codeautolink_warn_on_failed_resolve` to issue additional warnings
  when linking or resolving an object fails (:issue:`97`)
- Support callable classes (:issue:`98`)

0.9.0 (2022-01-13)
------------------
- Use Sphinx logging instead of raising exceptions (:issue:`86`)
- Link builtins if visible to intersphinx (:issue:`87`)
- Use Sphinx logging instead of the builtin ``warnings`` to warn
  (:issue:`89`, :issue:`94`)
- Support IPython's ``.. ipython::`` directive (:issue:`91`)

0.8.0 (2021-12-16)
------------------
- Correctly test for optional types in annotations (:issue:`72`)
- Don't check for ``notranslate`` CSS class, allowing for additional classes
  (:issue:`75`)
- Allow to specify block parsers as importable references (:issue:`76`)
- Allow parallel builds (:issue:`77`)
- Automatic support for ``ipython3`` code blocks (:issue:`79`)
- Correctly produce links for ``py`` code blocks (:issue:`81`)

0.7.0 (2021-11-28)
------------------
- Declare CSS class as public API (:issue:`3`)
- Add ability to link to subclass documentation (:issue:`68`)
- Append a newline to error messages with source code (:issue:`70`)
- Fix unpacking starred assignment (:issue:`71`)
- Improve errors with information about the current document (:issue:`71`)

0.6.0 (2021-11-21)
------------------
- Remove text decoration from produced links (:issue:`3`)
- Turn autodoc integration off by default (:issue:`58`)
- Avoid index error when handling syntax errors (:issue:`60`)
- Construct fully-qualified names more strictly to avoid hiding other issues
  (:issue:`61`)
- Resolve string annotations in the module scope (:issue:`62`)
- Correctly ensure that return annotations are valid types (:issue:`63`)
- Resolve imported functions to their original location if a documentation
  entry is not found in the used location (:issue:`64`)
- Fix multi-target assignment and unpacked assignment (:issue:`66`)
- Correctly accept ``None`` as a custom block transformer (:issue:`67`)
- Document support for ``sphinx.ext.doctest`` blocks (:issue:`67`)

0.5.1 (2021-11-20)
------------------
- Fix intersphinx links in documents inside folders (:issue:`56`)

0.5.0 (2021-11-07)
------------------
This release changes an internal API.
Please delete the cache file before building documentation.

- Link import statements (:issue:`42`)
- Gracefully handle functions that don't have an annotations dict (:issue:`47`)
- Enable configurations without autodoc (:issue:`48`)
- Support custom code block syntax (:issue:`49`)
- Fix crash on annotation-only assignment (:issue:`50`)
- Fix issue with filenames that have dots (:issue:`52`)
- Correctly remove extension when building non-HTML documentation (:issue:`53`)
- Support searching extra CSS classes for code example matching (:issue:`54`)
- Add configuration for global default concatenation state (:issue:`55`)

0.4.0 (2021-10-08)
------------------
- Support fluent interfaces (:issue:`37`)
- Fix links for names that shadow builtins (:issue:`38`)
- Support doctest blocks (:issue:`39`)

0.3.0 (2021-10-05)
------------------
- Treat optional types as their underlying type (:issue:`21`)
- Improve ``autolink-examples`` argument structure and
  provide an option making a collapsible table (:issue:`25`)
- Rename directives for consistency (:issue:`27`)
- Correctly link decorators (:issue:`28`)
- Move cache to Sphinx doctree directory (:issue:`29`)
- Support Python console blocks (:issue:`30`)
- Add configuration for default import statements (:issue:`31`)
- Support star imports (:issue:`32`)
- Accept multiline prefaces (:issue:`35`)
- Fix autodoc injection on one-line docstrings (:issue:`36`)

0.2.1 (2021-10-01)
------------------
- Fix type resolving for class instances (:issue:`24`)

0.2.0 (2021-10-01)
------------------
- Improve code analysis and follow simple type hints (:issue:`5`)
- Improve directive arguments and behavior (:issue:`16`)
- Correctly consume :code:`autolink-skip:: next` (:issue:`17`)
- Find type hints via imports, fix links in partial builds (:issue:`18`)

0.1.1 (2021-09-22)
------------------
- Correctly filter out names from concatenated sources (:issue:`14`)
- Fix links in documents inside folder (:issue:`15`)

0.1.0 (2021-09-22)
------------------
Initial release
