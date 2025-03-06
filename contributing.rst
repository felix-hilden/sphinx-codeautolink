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
    $ pip install -e .
    $ pip install -r requirements/dev

The last command installs all the necessary tools for development
as well as all optional dependencies.

If you forked, consider adding the upstream repository as a remote to easily
update your main branch with the latest upstream changes.
For tips and tricks on contributing, see `how to submit a contribution
<https://opensource.guide/how-to-contribute/#how-to-submit-a-contribution>`_,
specifically `opening a pull request
<https://opensource.guide/how-to-contribute/#opening-a-pull-request>`_.

If you want to contribute to someone else's fork and find yourself forgetting
how to do it every time, here's the runbook:

.. code:: sh

   git remote add [name] git@github.com:[name]/sphinx-codeautolink.git
   git fetch [name]
   git switch -c branch [name]/branch
   git remote rm [name]

Testing
-------
The installation can be verified, and any changes tested by running tox.

.. code:: sh

    $ tox

Developing
----------
A number of tools are used to automate development tasks.
They are available through tox labels.

.. code:: sh

    $ coverage run && coverage report  # execute test suite
    $ tox -m docs  # build documentation to docs/build/html/index.html
    $ tox -m lint  # check code style
    $ tox -m format  # autoformat code
    $ tox -m build  # packaging dry run

Releasing
---------
Before releasing, make sure the version number is incremented
and the release notes reference the new release.

.. note::

    With sphinx-codeautolink specifically, if Sphinx's environment data
    structure was modified, increment the environment version number before
    releasing a new version.

Running tests once more is also good practice.
Tox is used to build the appropriate distributions and publish them on PyPI.

.. code:: sh

    $ tox -m publish

If you'd like to test the upload and the resulting package,
upload manually to `TestPyPI <https://test.pypi.org>`_ instead.

.. code:: sh

    $ python -m build
    $ twine upload --repository testpypi dist/*
    $ pip install --index-url https://test.pypi.org/simple/ sphinx-codeautolink

Translations
------------
You are also welcome to contribute translations!
Use the following Babel commands to add new translations and locales.

.. code:: sh

    $ cd src/sphinx_codeautolink
    $ pybabel init --input-file=locale/sphinx-codeautolink.pot --domain=sphinx-codeautolink --output-dir=locale --locale=fi_FI
    $ pybabel update --input-file=locale/sphinx-codeautolink.pot --domain=sphinx-codeautolink --output-dir=locale
    $ pybabel compile --directory=locale --domain=sphinx-codeautolink

.. |issue_resolution| image:: http://isitmaintained.com/badge/resolution/felix-hilden/sphinx-codeautolink.svg
   :target: https://isitmaintained.com/project/felix-hilden/sphinx-codeautolink
   :alt: issue resolution time

.. |issues_open| image:: http://isitmaintained.com/badge/open/felix-hilden/sphinx-codeautolink.svg
   :target: https://isitmaintained.com/project/felix-hilden/sphinx-codeautolink
   :alt: open issues
