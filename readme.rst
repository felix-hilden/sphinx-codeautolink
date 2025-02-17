sphinx-codeautolink
===================
|license| |readthedocs| |build|

sphinx-codeautolink makes code examples clickable by inserting links
from individual code elements to the corresponding reference documentation.
We aim for a minimal setup assuming your examples are already valid Python.

For a live demo, see our online documentation on
`Read The Docs <https://sphinx-codeautolink.rtfd.org>`_.

sphinx-codeautolink elsewhere:

- Package on `PyPI <https://pypi.org/project/sphinx-codeautolink>`_
- How to contribute on `GitHub <https://github.com/felix-hilden/
  sphinx-codeautolink/blob/master/contributing.rst>`_

Installation
------------
|pypi| |conda-forge|

sphinx-codeautolink can be installed from the following sources:

.. code:: sh

    $ pip install sphinx-codeautolink
    $ conda install -c conda-forge sphinx-codeautolink

To enable sphinx-codeautolink, modify the extension list in ``conf.py``.
Note that the extension name uses an underscore rather than a hyphen.

.. code:: python

   extensions = [
       ...,
       "sphinx_codeautolink",
   ]

That's it! Now your code examples are linked.
For ways of concatenating examples, setting default import statements,
or customising link style among other things,
see the `online documentation <https://sphinx-codeautolink.rtfd.org>`_.

.. |pypi| image:: https://img.shields.io/pypi/v/sphinx-codeautolink.svg
   :target: https://pypi.org/project/sphinx-codeautolink
   :alt: PyPI package

.. |conda-forge| image:: https://anaconda.org/conda-forge/sphinx-codeautolink/badges/version.svg
   :target: https://anaconda.org/conda-forge/sphinx-codeautolink
   :alt: Conda-Forge package

.. |license| image:: https://img.shields.io/badge/License-MIT-blue.svg
   :target: https://choosealicense.com/licenses/mit
   :alt: License: MIT

.. |readthedocs| image:: https://rtfd.org/projects/sphinx-codeautolink/badge/?version=latest
   :target: https://sphinx-codeautolink.rtfd.org/en/latest/
   :alt: documentation

.. |build| image:: https://github.com/felix-hilden/sphinx-codeautolink/workflows/CI/badge.svg
   :target: https://github.com/felix-hilden/sphinx-codeautolink/actions
   :alt: build status
