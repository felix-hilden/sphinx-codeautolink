.. _about:

About
=====
Here's some additional information about sphinx-codeautolink!

Caveats
-------
- **Only works with HTML documentation**, disabled otherwise. If the extension
  is off, it silently removes directives that would produce output.
- **Only processes literal blocks, not inline code**. Sphinx has great tools
  for linking definitions inline, and longer code should be in a block anyway.
- **Doesn't run example code**. Therefore all possible resolvable types are not found,
  and the runtime correctness of code cannot be validated.
  Nonsensical operations that would result in errors at runtime are possible.
  However, syntax errors are caught while parsing!
- **Parsing and type hint resolving is incomplete**. While all Python syntax is
  supported, some ambiguous cases might produce unintuitive results or even
  incorrect results when compared to runtime behavior. We try to err on the
  side of caution, but here are some examples of compromises and limitations:

  - Only simple assignments of names, attributes and calls to a single name
    are tracked and used to resolve later values.
  - Only simple return type hints that consists of a single resolved type
    (not a string) are tracked through call and attribute access chains.
  - Type hints of intersphinx-linked definitions are not available.
  - Deleting or assigning to a global variable from an inner scope is
    not recognised in outer scopes. This is because the value depends on when
    the function is called, which is not tracked. Additionally, variable values
    are assumed to be static after leaving an inner scope, i.e. a function
    referencing a global variable. This is not the case in Python: values may
    change after the definition and impact the function.
    Encountering this should be unlikely, because it only occurs in practice
    when a variable shadows or overwrites an imported module or its part.

  These cases are subject to change when the library matures. For more details
  on the expected failures, see our test suite on `GitHub <https://github.com
  /felix-hilden/sphinx-codeautolink>`_. Please report any unexpected failures!

Clean Sphinx build
------------------
A JSON file is used to track code references, which allows access to the
reference information for pages in partial builds.
The file shouldn't become outdated, but a clean build can be achieved
by deleting the reference file and the entire build directory.
