import re
import sys
import pytest

from pathlib import Path
from bs4 import BeautifulSoup
from sphinx.cmd.build import main as sphinx_main

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

    src_dir = tmp_path / 'src'
    src_dir.mkdir()
    (src_dir / 'conf.py').write_text(default_conf + conf, 'utf-8')
    (src_dir / 'index.rst').write_text(index, 'utf-8')

    build_dir = tmp_path / 'build'
    sphinx_main(['-M', 'html', str(src_dir), str(build_dir)])

    index_html = build_dir / 'html' / 'index.html'
    text = index_html.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = list(soup.find_all('a', attrs={'class': 'sphinx-codeautolink-a'}))

    assert len(blocks) == len(links)
    for block, link in zip(blocks, links):
        assert any_whitespace.sub('', ''.join(block.strings)) == link


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

    src_dir = tmp_path / 'src'
    src_dir.mkdir()
    (src_dir / 'conf.py').write_text(default_conf + conf, 'utf-8')
    (src_dir / 'index.rst').write_text(index, 'utf-8')

    build_dir = tmp_path / 'build'
    sphinx_main(['-M', 'html', str(src_dir), str(build_dir)])

    index_html = build_dir / 'html' / 'index.html'
    text = index_html.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = list(soup.select('table a'))

    assert len(blocks) == len(links)
    for block, link in zip(blocks, links):
        assert any_whitespace.sub('', ''.join(block.strings)) == link
