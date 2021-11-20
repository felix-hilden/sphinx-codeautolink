.. _release-notes:

Release notes
=============

These release notes are based on
`Keep a Changelog <https://keepachangelog.com>`_.
sphinx-codeautolink adheres to
`Semantic Versioning <https://semver.org>`_.

Unreleased
----------
- Avoid index error when handling syntax errors (:issue:`60`)
- Construct fully-qualified names more strictly to avoid hiding other issues
  (:issue:`61`)
- Correctly ensure that return annotations are valid types (:issue:`63`)

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
