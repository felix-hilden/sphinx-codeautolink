.. _about:

About
=====
sphinx-codeautolink is built with a few major components: code analysis,
import and type hint resolving, and HTML injection.
Code analysis is performed with the builtin ``ast`` parsing tool to generate
a set of reference chains to imported modules.
That information is fed to the name resolver, which attempts to match a series
of attributes and calls to the concrete type in question by following
type hints and other information accessible via imports of the library.
If a match is found, a link to the correct reference documentation entry
is injected after the ordinary Sphinx build is finished.

.. _caveats:

Caveats
-------
- **Only works with HTML or DIRHTML documentation**, disabled otherwise. If the
  extension is off, it silently removes directives that would produce output.
- **Only processes blocks, not inline code**. Sphinx has great tools
  for linking definitions inline, and longer code should be in a block anyway.
- **Doesn't run example code**. Therefore all possible resolvable types are not
  found, and the runtime correctness of code cannot be validated.
  Nonsensical operations that would result in errors at runtime are possible.
  However, syntax errors are caught while parsing!
- **Parsing and type hint resolving is incomplete**. While all Python syntax is
  supported, some ambiguous cases might produce unintuitive results or even
  incorrect results when compared to runtime behavior. We try to err on the
  side of caution, but here are some of the compromises and limitations:

  - Only simple assignments of names, attributes and calls to a single name
    are tracked and used to resolve later values.
  - Only simple return type hints that consist of a single, possibly optional
    type are tracked through call and attribute access chains.
  - Type hints of intersphinx-linked definitions are not necessarily available.
    Resolving names using type hints is only possible if the package is
    installed, but simple usage can be tracked via documentation entries alone.
  - Deleting or assigning to a global variable from an inner scope is
    not recognised in outer scopes. This is because the value depends on when
    the function is called, which is not tracked. Additionally, variable values
    are assumed to be static after leaving an inner scope, i.e. a function
    referencing a global variable. This is not the case in Python: values may
    change after the definition and impact the function.
    Encountering this should be unlikely, because it only occurs in practice
    when a variable shadows or overwrites an imported module or its part.

  These cases are subject to change when the library matures. For more details
  on the expected failures, see our `test suite on GitHub <https://github.com
  /felix-hilden/sphinx-codeautolink>`_. Please report any unexpected failures!

Sphinx semantics
----------------
Warnings
********
For an easier time with debugging, we recommend enabling all warnings,
treating them as errors with ``-W`` and only ignoring specific warning types
with :confval:`suppress_warnings`. This is also easier if
:confval:`show_warning_types` is set.

Clean build
***********
For correct partial builds, code reference information is saved to a file
which is updated when parsing new or outdated files.
It shouldn't become outdated, but a clean build can be achieved with
`sphinx-build -E <https://www.sphinx-doc.org/en/master/man/sphinx-build.html
#cmdoption-sphinx-build-E>`_ or by deleting the build directory.

Sphinx cache
************
A function specified in :confval:`codeautolink_custom_blocks` prevents Sphinx
from caching documentation results. Consider using an importable instead.
For more information, see the discussion in :issue:`76`.
You can also suppress the warning.

Parallel build and custom parsers
*********************************
Locally defined custom block parsers in :confval:`codeautolink_custom_blocks`
cannot be passed to Pickle, which prevents parallel Sphinx builds.
Please consider using an importable function instead.

Priority
********
The extension parses code blocks in the ``doctree-read`` Sphinx event.
The priority is set to 490 to catch nodes removed by ``sphinx.ext.doctest``
(priority 500). In other cases the priority of the extension is default.

Copying code blocks
-------------------
If you feel like code links make copying code a bit more difficult,
`sphinx-copybutton <https://sphinx-copybutton.readthedocs.io>`_
is a fantastic extension to use.
It adds a button to copy an entire code block to the clipboard.
So give it a go, perhaps even if you don't think links make copying harder!

Matching failures
-----------------
Matching can fail on two levels, for a whole code example or a specific line.
Firstly, failing to match an entire code example is almost always considered
a bug, which you can report on `GitHub
<https://github.com/felix-hilden/sphinx-codeautolink/issues>`_.
If third-party code blocks are in use, matching may fail because of
inconsistent or unrecognised CSS classes. The class related to the block lexer
name is automatically added to the list of CSS classes that are searched when
matching code examples as ``highlight-{lexer}``.
If the class has another value, :confval:`codeautolink_search_css_classes`
can be used to extend the search. To find out which classes should be added,
build your documentation, locate the code example and use the class of the
outermost ``div`` tag. For example:

.. code:: python

   codeautolink_search_css_classes = ["highlight-default"]

Secondly, matching can fail on a specific line or range of lines.
This is often a bug, but the known expected failure cases are presented here
(none currently).

Debugging missing links
-----------------------
There are multiple potential reasons for missing links.
Here are some common causes and ways to debug and resolve the issue.
First, please enable all warning messages found in :ref:`configuration`
to see information about known link misses.

Missing Sphinx inventory entry
******************************
Links cannot be resolved, because the documentation entry for a particular
object cannot be found in the Sphinx inventory. Likely causes:

- The autodoc (or equivalent) entry is missing entirely. To resolve, add the
  corresponding entry to your documentation.
- The object has been relocated and is documented elsewhere, i.e. the
  ``__module__`` attribute and Sphinx location are out of sync. To resolve,
  provide the correct location in :confval:`codeautolink_inventory_map`.

Failed link resolving
*********************
Determining the canonical location of an object failed. Likely causes:

- Missing type hints in function returns or class attributes. To resolve,
  add appropriate type hints. See :ref:`caveats` for limitations.
- Highly dynamic or runtime-dependent code which is not possible to parse only
  via imports. To resolve, consider simplifying or filing an issue.
