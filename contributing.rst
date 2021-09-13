Contributing
============
|issues_open| |issue_resolution|

Thank you for considering contributing to sphinx-codeautolink!
If you've found a bug or would like to propose a feature,
please submit an `issue <https://github.com/felix-hilden/sphinx-codeautolink/issues>`_.

If you'd like to get more involved,
`here's how <https://opensource.guide/how-to-contribute/>`_.
There are many valuable contributions in addition to contributing code!
If you're so inclined, triaging issues, improving documentation,
helping other users and reviewing existing code and PRs is equally appreciated!

The rest of this guide focuses on development and code contributions.

Installation
------------
Start by cloning the most recent version, either from the main repository
or a fork you created, and installing the source as an editable package.
Using a virtual environment of your choice for the installation is recommended.

.. code:: sh

    $ git clone https://github.com/felix-hilden/sphinx-codeautolink.git
    $ cd sphinx-codeautolink
    $ pip install -e .[dev]

The last command installs all the necessary extra dependencies for development.

If you forked, consider adding the upstream repository as a remote to easily
update your main branch with the latest upstream changes.
For tips and tricks on contributing, see `how to submit a contribution
<https://opensource.guide/how-to-contribute/#how-to-submit-a-contribution>`_,
specifically `opening a pull request
<https://opensource.guide/how-to-contribute/#opening-a-pull-request>`_.

Testing
-------
The install can be verified, and any changes tested by running tox.

.. code:: sh

    $ tox

Now tests and static checks have been run.
A list of all individual tasks can be viewed with their descriptions.

.. code:: sh

    $ tox -a -v

Test suite
**********
The repository contains a suite of test cases
which can be studied and run to ensure the package works as intended.

.. code:: sh

    $ pytest

For tox, this is the default command when running e.g. ``tox -e py``.
To measure test coverage and view uncovered lines or branches run ``coverage``.

.. code:: sh

    $ coverage run
    $ coverage report

This can be achieved with tox by running ``tox -e coverage``.

Documentation
*************
Documentation can be built locally with Sphinx.

.. code:: sh

    $ cd docs
    $ make html

The main page ``index.html`` can be found in ``build/html``.

Code style
**********
A set of style rules is followed using a variety of tools,
which check code, docstrings and documentation files.
To run all style checks use ``tox -e lint``.

Releasing
---------
Before releasing, make sure the version number is incremented
and the release notes reference the new release.
Running tests once more is also good practice.
The following commands build source and wheel distributions
to a clean directory, and publish them on PyPI
according to the project name specified in the project metadata.

.. code:: sh

    $ rm -r dist
    $ python -m build
    $ twine check --strict dist/*
    $ twine upload dist/*

If you'd like to test the upload and the resulting package,
use `TestPyPI <https://test.pypi.org>`_ instead.

.. code:: sh

    $ twine upload --repository testpypi dist/*
    $ pip install --index-url https://test.pypi.org/simple/ sphinx-codeautolink

.. |issue_resolution| image:: http://isitmaintained.com/badge/resolution/felix-hilden/sphinx-codeautolink.svg
   :target: https://isitmaintained.com/project/felix-hilden/sphinx-codeautolink
   :alt: issue resolution time

.. |issues_open| image:: http://isitmaintained.com/badge/open/felix-hilden/sphinx-codeautolink.svg
   :target: https://isitmaintained.com/project/felix-hilden/sphinx-codeautolink
   :alt: open issues
