"""
Basic extension tests.

The tests are structured as .txt files, parsed and executed here.
The structure of the file is::

   number of expected autolinks
   # split
   lines to add to the default conf.py
   # split
   index.html content
"""
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

txt_tests = list(Path(__file__).parent.glob('*.txt'))


@pytest.mark.parametrize('file', txt_tests)
def test_extension(file: Path, tmp_path: Path):
    n_links, conf, index = file.read_text('utf-8').split('# split')
    src_dir = tmp_path / 'src'
    src_dir.mkdir()
    (src_dir / 'conf.py').write_text(default_conf + conf, 'utf-8')
    (src_dir / 'index.rst').write_text(index, 'utf-8')

    build_dir = tmp_path / 'build'
    sphinx_main(['-M', 'html', str(src_dir), str(build_dir)])

    index_html = build_dir / 'html' / 'index.html'
    text = index_html.read_text('utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    blocks = soup.find_all('a', attrs={'class': 'sphinx-codeautolink-a'})
    assert len(blocks) == int(n_links.strip())
