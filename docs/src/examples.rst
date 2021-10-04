.. _examples:

Examples
========

Short examples about how to achieve certain tasks with sphinx-codeautolink.

Basic use
---------
Once sphinx-codeautolink has been enabled, code in all Python code blocks will
be analysed and linked to known reference documentation entries.

.. code:: python

   import sphinx_codeautolink

   sphinx_codeautolink.setup()
   names = sphinx_codeautolink.parse.parse_names([
       sphinx_codeautolink.parse.Name("setup")
   ])

Different import styles are supported, along with all Python syntax.
Star imports might be particularly handy in code examples.
Python console blocks using :code:`.. code:: pycon` work too.

.. code:: pycon

   >>> from sphinx_codeautolink.parse import *
   >>> def foo() -> Name:
   ...     return Name("setup")
   >>> foo()
   Name("setup")

A list of all code examples where a particular definition is used is handy
particularly in the reference documentation itself:

.. code-refs:: sphinx_codeautolink.setup
   :type: func

Such a table is generated with::

   .. code-refs:: sphinx_codeautolink.setup
      :type: func

Implicit imports
----------------
When writing lots of small snippets of code, having the same import at the
beginning of every example becomes quite repetitive.
The import can be hidden instead.

.. implicit-import:: import sphinx_codeautolink
.. code:: python

  sphinx_codeautolink.setup()

The previous block is produced with::

   .. implicit-import:: import sphinx_codeautolink
   .. code:: python

      sphinx_codeautolink.setup()

Multiple implicit imports can be stacked::

   .. implicit-import:: import sphinx_codeautolink
   .. implicit-import:: from sphinx_codeautolink import parse as p
   .. code:: python

      sphinx_codeautolink.setup()
      names = p.parse_names([p.Name("setup")])

.. implicit-import:: import sphinx_codeautolink
.. implicit-import:: from sphinx_codeautolink import parse as p
.. code:: python

   sphinx_codeautolink.setup()
   names = p.parse_names([p.Name("setup")])

Default import statements can be set in :ref:`configuration`
to avoid writing the same imports repeatedly.

Concatenating examples
----------------------
Examples interlaced with explanations can make for more comprehensible docs.

.. concat-blocks:: section
.. code:: python

   import sphinx_codeautolink

   sphinx_codeautolink.setup()

After explaining some details, the following block may continue where
the previous left off.

.. code:: python

   sphinx_codeautolink.parse.parse_names()

This was achieved with::

   .. concat-blocks:: section
   .. code:: python

      import sphinx_codeautolink

   .. code:: python

      sphinx_codeautolink.setup()

Now all Python code blocks within the same section will be concatenated.
See :ref:`reference` for more information on the exact behavior and options.

Skipping blocks
---------------
If needed, Python blocks can be skipped, resulting in no links for that block
and preventing it from being included in further sources with concatenation.

.. autolink-skip::
.. code:: python

   import sphinx_codeautolink

   sphinx_codeautolink.setup()

Which is done via::

   .. autolink-skip::
   .. code:: python

      import sphinx_codeautolink

      sphinx_codeautolink.setup()

Skipping is supported for single blocks, sections and entire files.
See :ref:`reference` for more information on the exact behavior and options.

Autodoc integration
-------------------
A backreference table of the code examples that use a definition is handy
for example in reference documentation.
sphinx-codeautolink provides an autodoc integration for that purpose,
which is also enabled by default.

.. autofunction:: sphinx_codeautolink.setup
   :noindex:

If you'd like to place the directive manually, disable the integration
and implement a `Sphinx extension <https://www.sphinx-doc.org/en/master/
extdev/index.html>`_ with a listener for the ``autodoc-process-docstring``
`event <https://www.sphinx-doc.org/en/master/usage/
extensions/autodoc.htm#event-autodoc-process-docstring>`_.
An object type "class" seems to work for other types as well.

.. code:: python

   codeautolink_autodoc_inject = False

   def process_docstring(app, what, name, obj, options, lines):
       lines.append(f".. code-refs:: {name}")
       lines.append(f"   :type: class")
       lines.append(f"   :collapse:")

   def setup(app):
       app.connect("autodoc-process-docstring", process_docstring)
       return {"version": "0.1.0"}

Intersphinx integration
-----------------------
When writing documentation that references other libraries, `intersphinx
<https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`_
is a great extension to use. It enables links to documentation on other sites.
sphinx-codeautolink integrates this functionality seamlessly,
linking objects as long as the correct ``intersphinx_mapping`` is defined.

.. code:: python

   import numpy as np
   from matplotlib import pyplot as plt

   x = np.linspace(0, 2 * np.pi, 100)
   plt.plot(x, np.sin(x))
   plt.show()

Reference tables across intersphinx work too:

.. code-refs:: numpy.linspace
   :type: func

Example Python objects
----------------------
This section contains parts of the inner API of sphinx-codeautolink.
Note that they are not a part of the public API.
Objects are presented here only for demonstration purposes,
and their use in examples does not represent their correct usage.

sphinx-codeautolink
*******************
.. autofunction:: sphinx_codeautolink.setup

sphinx-codeautolink.parse
*************************
.. autoclass:: sphinx_codeautolink.parse.Name
.. autofunction:: sphinx_codeautolink.parse.parse_names
