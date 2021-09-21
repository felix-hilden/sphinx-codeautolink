.. _about:

About
=====
Here's some additional information about sphinx-codeautolink!

Caveats
-------
- **Only works with HTML documentation**, disabled otherwise. If the extension
  is off, it silently removes directives that would produce output.
- **Doesn't run code or follow assignments and type hints**. Therefore all
  possible resolvable names are not found, and the runtime correctness of code
  cannot be validated. For example, assigning :code:`cal = sphinx_codeautolink`
  and using its attributes like :code:`cal.setup()` does not produce a link.
  Likewise, nonsensical operations that would result in errors at runtime are
  possible. Some of this may change when the extension is developed further.
- **Only processes literal blocks, not inline code**. Sphinx has great tools
  for linking definitions inline, and longer code should be in a block anyway.

Clean Sphinx build
------------------
A JSON file is used to track code references, which allows access to the
reference information for pages in partial builds.
The file shouldn't become outdated, but a clean build can be achieved
by deleting the reference file and the entire build directory.
