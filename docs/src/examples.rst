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
`Doctest <https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html
#doctest-blocks>`_ and console blocks using :code:`.. code:: pycon` work too.

.. code:: pycon

   >>> from lib import *
   >>> def visit_town(time_spent: int, budget: int) -> Shrubbery:
   ...     return Shrubbery(time_spent > 20, budget > 300)
   >>> visit_town(35, 200)
   Shrubbery(looks_nice=True, too_expensive=False)

A list of all code examples where a particular definition is used is handy
particularly in the reference documentation itself:

.. autolink-examples:: lib.Knight

Such a table is generated with :rst:dir:`autolink-examples`::

   .. autolink-examples:: lib.Knight

Invisible imports
-----------------
When writing lots of small snippets of code, having the same import at the
beginning of every example becomes quite repetitive.
The import can be hidden instead.

.. autolink-preface:: import lib
.. code:: python

  lib.Knight().taunt()

The previous block is produced with :rst:dir:`autolink-preface`::

   .. autolink-preface:: import lib
   .. code:: python

        lib.Knight().taunt()

A multiline preface can be written in the content portion of the directive::

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

This was achieved with :rst:dir:`autolink-concat`::

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

Which is done via :rst:dir:`autolink-skip`::

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
which is also enabled by default.

.. autofunction:: lib.Knight.scratch
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
       lines.append("")
       lines.append(".. autolink-examples:: " + name)
       lines.append("   :type: class")
       lines.append("   :collapse:")

   def setup(app):
       app.connect("autodoc-process-docstring", process_docstring)

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

.. autolink-examples:: numpy.linspace
   :type: func

It seems that the reference type information is more important
for Sphinx when dealing with external modules,
likely because the references cannot be resolved dynamically.
Please specify a ``type`` in :rst:dir:`autolink-examples`::

   .. autolink-examples:: numpy.linspace
      :type: func
