import re
import sys
import pytest

from unittest.mock import patch
from typing import Dict
from pathlib import Path
from bs4 import BeautifulSoup
from sphinx.cmd.build import main as sphinx_main

from ._check import check_link_targets

# Insert test package root to path for all tests
sys.path.insert(0, str(Path(__file__).parent / "src"))

default_conf = """
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_codeautolink",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
}
"""

any_whitespace = re.compile(r'\s*')
ref_tests = list(Path(__file__).with_name('ref').glob('*.txt'))
ref_xfails = {
    'ref_fluent_attrs.txt': sys.version_info < (3, 8),
    'ref_fluent_call.txt': sys.version_info < (3, 8),
    'ref_import_from_complex.txt': sys.version_info < (3, 8),
}


def assert_links(file: Path, links: list):
    text = file.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = list(soup.find_all('a', attrs={'class': 'sphinx-codeautolink-a'}))
    strings = [any_whitespace.sub('', ''.join(b.strings)) for b in blocks]

    assert len(strings) == len(links)
    for s, link in zip(strings, links):
        assert s == link


@pytest.mark.parametrize('file', ref_tests)
def test_references(file: Path, tmp_path: Path):
    """
    Basic extension tests for reference building.

    The tests are structured as .txt files, parsed and executed here.
    The structure of the file is::

        expected
        autolink
        link.targets
        # split
        lines to add to the default conf.py
        # split
        index.html content
    """
    if ref_xfails.get(file.name, False):
        pytest.xfail('Expected to fail.')

    links, conf, index = file.read_text('utf-8').split('# split')
    links = links.strip().split('\n')
    if len(links) == 1 and not links[0]:
        links = []

    files = {'conf.py': default_conf + conf, 'index.rst': index}
    result_dir = _sphinx_build(tmp_path, 'html', files)

    assert_links(result_dir / 'index.html', links)
    assert check_link_targets(result_dir) == len(links)


table_tests = list(Path(__file__).with_name('table').glob('*.txt'))


@pytest.mark.parametrize('file', table_tests)
def test_tables(file: Path, tmp_path: Path):
    """
    Tests for backreference tables.

    The tests are structured as .txt files, parsed and executed here.
    The structure of the file is::

        expected
        table
        link.targets
        # split
        lines to add to the default conf.py
        # split
        index.html content

    Note that the header of the table is also considered a link target.
    However, if the table is collapsible, the header is not a part of
    the table, so it should be omitted from the expected links.
    The processing also removes any whitespace, which should be taken into account.
    """
    links, conf, index = file.read_text('utf-8').split('# split')
    links = links.strip().split('\n')
    if len(links) == 1 and not links[0]:
        links = []

    files = {'conf.py': default_conf + conf, 'index.rst': index}
    result_dir = _sphinx_build(tmp_path, 'html', files)

    index_html = result_dir / 'index.html'
    text = index_html.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = list(soup.select('table a'))
    strings = [any_whitespace.sub('', ''.join(b.strings)) for b in blocks]

    assert len(strings) == len(links)
    for s, link in zip(strings, links):
        assert s == link


fail_tests = list(Path(__file__).with_name('fail').glob('*.txt'))


@pytest.mark.parametrize('file', fail_tests)
def test_fails(file: Path, tmp_path: Path):
    """
    Tests for failing builds.

    The tests are structured as .txt files, parsed and executed here.
    The structure of the file is::

        lines to add to the default conf.py
        # split
        index.html content
    """
    conf, index = file.read_text('utf-8').split('# split')
    files = {'conf.py': default_conf + conf, 'index.rst': index}
    with pytest.raises(RuntimeError):
        _sphinx_build(tmp_path, 'html', files)


def test_non_html_build(tmp_path: Path):
    index = """
Test project
------------

.. code:: python

   import test_project
   test_project.bar()

.. automodule:: test_project
.. autolink-examples:: test_project.bar
"""
    files = {'conf.py': default_conf, 'index.rst': index}
    _sphinx_build(tmp_path, 'man', files)


def test_build_twice_and_modify_one_file(tmp_path: Path):
    index = """
Test project
------------

.. code:: python

   import test_project
   test_project.bar()

.. automodule:: test_project

.. toctree::

   another
"""
    another = """
Another
-------
.. autolink-examples:: test_package.bar
"""
    another2 = """
Another
-------
But edited.

.. autolink-examples:: test_package.bar
"""
    files = {'conf.py': default_conf, 'index.rst': index, 'another.rst': another}
    _sphinx_build(tmp_path, 'html', files)
    _sphinx_build(tmp_path, 'html', {'another.rst': another2})


def test_build_twice_and_delete_one_file(tmp_path: Path):
    index = """
Test project
------------

.. code:: python

   import test_project
   test_project.bar()

.. automodule:: test_project

.. toctree::

   another
"""
    another = """
Another
-------
.. autolink-examples:: test_project.bar
"""

    files = {'conf.py': default_conf, 'index.rst': index, 'another.rst': another}
    _sphinx_build(tmp_path, 'html', files)
    (tmp_path / 'src' / 'another.rst').unlink()
    _sphinx_build(tmp_path, 'html', {})


def test_raise_unexpected(tmp_path: Path):
    index = """
Test project
------------

.. code:: python

   import test_project
   test_project.bar()

.. automodule:: test_project
"""
    files = {'conf.py': default_conf, 'index.rst': index}

    def raise_msg(*args, **kwargs):
        raise ValueError('ValueError')

    def raise_nomsg(*args, **kwargs):
        raise ValueError()

    target = 'sphinx_codeautolink.extension.CodeBlockAnalyser'
    with pytest.raises(RuntimeError), patch(target, raise_msg):
        _sphinx_build(tmp_path, 'html', files)

    with pytest.raises(RuntimeError), patch(target, raise_nomsg):
        _sphinx_build(tmp_path, 'html', files)


def test_parallel_build(tmp_path: Path):
    index = """
Test project
------------
.. automodule:: test_project
.. toctree::
"""
    template = """
{header}
---
.. code:: python

   import test_project
   test_project.bar()
"""
    links = ['test_project', 'test_project.bar']

    n_subfiles = 20
    subfiles = {
        name: template.format(header=name)
        for name in map(lambda x: f'F{x}', range(n_subfiles))
    }
    index = index + '\n   '.join([''] + list(subfiles))
    files = {'conf.py': default_conf, 'index.rst': index}
    files.update({k + '.rst': v for k, v in subfiles.items()})
    result_dir = _sphinx_build(tmp_path, 'html', files, n_processes=4)

    for file in subfiles:
        assert_links(result_dir / (file + '.html'), links)
    assert check_link_targets(result_dir) == n_subfiles * len(links)


def _sphinx_build(
    folder: Path, builder: str, files: Dict[str, str], n_processes: int = None
) -> Path:
    """Build Sphinx documentation and return result folder."""
    src_dir = folder / 'src'
    src_dir.mkdir(exist_ok=True)
    for name, content in files.items():
        (src_dir / name).write_text(content, 'utf-8')

    build_dir = folder / 'build'
    args = ['-M', builder, str(src_dir), str(build_dir), '-W']
    if n_processes:
        args.extend(['-j', str(n_processes)])
    ret_val = sphinx_main(args)
    if ret_val:
        raise RuntimeError('Sphinx build failed!')
    return build_dir / builder
