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
- **Doesn't run code or follow importable type hints**. Therefore all
  possible resolvable names are not found, and the runtime correctness of code
  cannot be validated. Nonsensical operations that would result in errors at
  runtime are possible. However, syntax errors are caught while parsing!
- **Parsing is incomplete and performed top-down**. While all Python syntax is
  supported, some cases are ambiguous and produce unintuitive results or even
  incorrect results when compared to runtime behavior. Firstly, assignments
  are not followed. For example, assigning :code:`cal = sphinx_codeautolink`
  and using its attributes like :code:`cal.setup()` does not produce a link.
  Deleting or assigning to a global variable from an inner scope is
  not recognised in outer scopes. This is because the value depends on when
  the function is called, which is not tracked. Additionally, variable values
  are assumed to be static after leaving an inner scope, i.e. a function
  referencing a global variable. This is not the case in Python: values may
  change after the definition and impact the function. For more details on the
  expected failures, see our test suite on `GitHub <https://github.com/
  felix-hilden/sphinx-codeautolink>`_. Please report any unexpected failures!
  Because the library's purpose is to highlight the definitions used from
  imported modules, these shortcomings are likely minor, and only occur in
  practice when a variable shadows or overwrites an imported module.

Clean Sphinx build
------------------
A JSON file is used to track code references, which allows access to the
reference information for pages in partial builds.
The file shouldn't become outdated, but a clean build can be achieved
by deleting the reference file and the entire build directory.
