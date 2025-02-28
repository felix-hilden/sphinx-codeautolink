.. _examples:

Examples
========

Short examples about how to achieve certain tasks with sphinx-codeautolink.

Basic use
---------
Once sphinx-codeautolink has been enabled, code in all Python code blocks will
be analysed and linked to known reference documentation entries.

.. code:: python

   import lib

   knight = lib.Knight()
   while knight.limbs >= 0:
       print(knight.taunt())
       knight.scratch()

Different import styles are supported, along with all Python syntax.
Star imports might be particularly handy in code examples.

A number of other types of blocks are also supported
along with standard Sphinx configuration, like:

- Literal blocks, the ``.. highlight::`` directive
  and ``highlight_language`` configuration
- `Doctest blocks <https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#doctest-blocks>`_
- Console blocks using :code:`.. code:: pycon`
- Including code via :rst:dir:`literalinclude`, but requires using one of the
  `Python Lexers <https://pygments.org/docs/lexers/#pygments.lexers.python.PythonLexer>`_

.. code:: pycon

   >>> from lib import *
   >>> def visit_town(time_spent: int, budget: int) -> Shrubbery:
   ...     return Shrubbery(time_spent > 20, budget > 300)
   >>> visit_town(35, 200)
   Shrubbery(looks_nice=True, too_expensive=False)

A list of all code examples where a particular definition is used is handy
particularly in the reference documentation itself:

.. autolink-examples:: lib.Knight

Such a table is generated with :rst:dir:`autolink-examples`:

.. code-block:: rst

   .. autolink-examples:: lib.Knight

Invisible imports
-----------------
When writing lots of small snippets of code, having the same import at the
beginning of every example becomes quite repetitive.
The import can be hidden instead.

.. autolink-preface:: import lib
.. code:: python

  lib.Knight().taunt()

The previous block is produced with :rst:dir:`autolink-preface`:

.. code-block:: rst

   .. autolink-preface:: import lib
   .. code:: python

        lib.Knight().taunt()

A multiline preface can be written in the content portion of the directive:

.. code-block:: rst

   .. autolink-preface::

      import lib
      from lib import Knight

A global preface can be set in :confval:`codeautolink_global_preface`
to avoid writing the same imports repeatedly.

Concatenating examples
----------------------
Examples interlaced with explanations can make for more comprehensible docs.

.. autolink-concat:: section
.. code:: python

   import lib
   knight = lib.Knight()

After explaining some details, the following block may continue where
the previous left off.

.. code:: python

   while knight.limbs >= 0:
       print(knight.taunt())
       knight.scratch()

This was achieved with :rst:dir:`autolink-concat`:

.. code-block:: rst

   .. autolink-concat:: section
   .. code:: python

      import lib
      knight = lib.Knight()

   .. code:: python

      while knight.limbs >= 0:
          print(knight.taunt())
          knight.scratch()

Now all Python code blocks within the same section will be concatenated.
See :rst:dir:`autolink-concat` for more information and options.

Skipping blocks
---------------
If needed, Python blocks can be skipped, resulting in no links for that block
and preventing it from being included in further sources with concatenation.

.. autolink-skip::
.. code:: python

   import lib
   lib.Knight()

Which is done via :rst:dir:`autolink-skip`:

.. code-block:: rst

   .. autolink-skip::
   .. code:: python

      import lib
      lib.Knight()

Skipping is supported for single blocks, sections and entire files.
See :rst:dir:`autolink-skip` for more information and options.

Autodoc integration
-------------------
A backreference table of the code examples that use a definition is handy
for example in reference documentation.
sphinx-codeautolink provides an autodoc integration for that purpose,
which injects the appropriate table to each autodoc entry.

.. autofunction:: lib.Knight.scratch
   :noindex:

To enable the integration, set :confval:`codeautolink_autodoc_inject`.
If you'd like to place the directive manually, implement a small
`Sphinx extension <https://www.sphinx-doc.org/en/master/extdev/index.html>`_
with a listener for the ``autodoc-process-docstring``
`event <https://www.sphinx-doc.org/en/master/usage/
extensions/autodoc.htm#event-autodoc-process-docstring>`_.
An object type "class" seems to work for other types as well.

.. code:: python

   def process_docstring(app, what, name, obj, options, lines):
       lines.append("")
       lines.append(".. autolink-examples:: " + name)
       lines.append("   :type: class")
       lines.append("   :collapse:")

   def setup(app):
       app.connect("autodoc-process-docstring", process_docstring)

Intersphinx integration
-----------------------
When writing code examples that use builtins or other libraries, `intersphinx
<https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`_
can be used to enable links to documentation on other Sphinx-generated sites.
Intersphinx is integrated seamlessly, linking objects as long as the correct
``intersphinx_mapping`` is defined.

.. code:: python

   if __debug__:
       print(...)
   else:
       raise RuntimeError(f"Could not debug!")

.. code:: python

   import numpy as np
   from matplotlib import pyplot as plt

   x = np.linspace(0, 2 * np.pi, 100)
   plt.plot(x, np.sin(x))
   plt.show()

Reference tables across intersphinx work too:

.. autolink-examples:: numpy.linspace
   :type: func

It seems that the reference type information is more important
for Sphinx when dealing with external modules,
likely because the references cannot be resolved dynamically.
Please specify a ``type`` in :rst:dir:`autolink-examples`:

.. code-block:: rst

   .. autolink-examples:: numpy.linspace
      :type: func

Doctest code blocks
-------------------
Using the ``sphinx.ext.doctest`` extension for code examples only requires
activating the extension::

   extensions = [
       ...,
       "sphinx.ext.doctest",
   ]

``doctest`` and ``testcode`` blocks now work as expected.
Code in :rst:dir:`testsetup` is considered to be the first block
:rst:dir:`autolink-preface` before each matching test group.
However, `skipif` is not supported.

.. doctest::

   >>> import lib
   >>> lib.Knight()

IPython blocks and notebooks
----------------------------
Code blocks using ``ipython`` or ``ipython3`` lexers are supported by default.
The function :func:`~sphinx_codeautolink.clean_ipython` is used to handle
IPython-specific syntax like `magic functions`_ and console prefixes.

.. _magic functions: https://ipython.readthedocs.io/en/stable/
   interactive/tutorial.html#magic-functions

.. code:: ipython3

   %reset
   import lib
   lib.Knight().taunt()

IPython's ``.. ipython::`` `directive <https://ipython.readthedocs.io/en/
stable/sphinxext.html#>`_ is also supported:

.. ipython::

   In [1]: import lib

   In [2]: lib.Knight().taunt()
   Out[2]: -taunt here-

They are also useful for integrating Jupyter notebooks and similar source code,
which is possible with separate Sphinx extensions like nbsphinx_ or MyST-NB_.
Enabling :confval:`codeautolink_concat_default` with notebooks is recommended.
IPython processing is enabled if the ``ipython`` library is installed.
It is also included in the ``ipython`` extra of sphinx-codeautolink.

.. code:: sh

   pip install sphinx-codeautolink[ipython]

.. _nbsphinx: https://nbsphinx.readthedocs.io/
.. _MyST-NB: https://myst-nb.readthedocs.io/

Third-party code blocks
-----------------------
Third-party code blocks that use the basic Pygments lexers for Python
are supported out of the box.
The example below uses matplotlib's :mod:`~matplotlib.sphinxext.plot_directive`
to automatically run the code and include a plot in the documentation:

.. plot::

   import numpy as np
   from matplotlib import pyplot as plt

   x = np.linspace(0, 2 * np.pi, 100)
   plt.plot(x, np.cos(x))

Code blocks with special highlighting or syntax are supported
with custom transformer functions in :confval:`codeautolink_custom_blocks`.
For example, a transformer could be implemented as follows:

.. code:: python

   def transform(source):
       """Ignore lines starting with `!--`."""
       lines = []
       for line in source.split("\n"):
           if line.strip().startswith("!--"):
               line = ""
           lines.append(line)
       return source, "\n".join(lines)

   codeautolink_custom_blocks = {"python": transform}

Sometimes links with third-party code blocks are broken.
See :ref:`about` for a potential solution.

.. _examples-css:

Custom link styles
------------------
If you want a specific style to be applied to code block links,
you may add your own CSS file to the Sphinx build.

.. code:: python

   # conf.py
   html_static_path = ['static']
   html_css_files = ['custom.css']

To include only in specific documents, see the ``html-page-context`` event
and the :meth:`Sphinx.add_css_file` function.
For example, you can add similar underlines as this documentation
and change the hover colour:

.. code:: css

   /* static/custom.css */
   .sphinx-codeautolink-a{
       border-bottom-color: #ccc;
       border-bottom-style: solid;
       border-bottom-width: 1px;
   }
   .sphinx-codeautolink-a:hover{
       color: rgb(255, 139, 139);
   }
