sphinx-codeautolink
===================
|pyversions| |downloads| |license| |readthedocs|

sphinx-codeautolink makes code examples clickable by inserting links
from individual code elements to the corresponding reference documentation.
We aim for a minimal setup assuming your examples are already valid Python.

For a live demo, see our online documentation on
`Read The Docs <https://sphinx-codeautolink.rtfd.org>`_.

Installation
------------
sphinx-codeautolink can be installed from the following sources:

.. code:: sh

    $ pip install sphinx-codeautolink
    $ conda install -c conda-forge sphinx-codeautolink

Note that the library is in early development, so version pinning is advised.
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

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/sphinx-codeautolink
   :alt: Python versions

.. |downloads| image:: https://img.shields.io/pypi/dm/sphinx-codeautolink
   :alt: Monthly downloads

.. |license| image:: https://img.shields.io/badge/License-MIT-blue.svg
   :target: https://choosealicense.com/licenses/mit
   :alt: License: MIT

.. |readthedocs| image:: https://rtfd.org/projects/sphinx-codeautolink/badge/?version=stable
   :target: https://sphinx-codeautolink.rtfd.org/en/stable/
   :alt: Documentation
