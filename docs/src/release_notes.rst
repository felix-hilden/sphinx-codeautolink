.. _release-notes:

Release notes
=============

These release notes are based on
`Keep a Changelog <https://keepachangelog.com>`_.
sphinx-codeautolink adheres to
`Semantic Versioning <https://semver.org>`_.

Unreleased
----------
This release changes an internal API.
Please delete the cache file before building documentation.

- Link import statements (:issue:`42`)
- Enable configurations without autodoc (:issue:`48`)
- Fix crash on annotation-only assignment (:issue:`50`)

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
