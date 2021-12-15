import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Cache external pages for the duration of the runtime,
# so that we don't request them multiple times needlessly
sess = requests.Session()
external_site_ids = {}


def check_link_targets(root: Path) -> int:
    """Validate links in HTML site at root, return number of links found."""
    site_docs = {
        p.relative_to(root): BeautifulSoup(p.read_text('utf-8'), 'html.parser')
        for p in root.glob('**/*.html')
    }
    site_ids = {k: gather_ids(v) for k, v in site_docs.items()}

    total = 0
    for doc, soup in site_docs.items():
        doc = str(doc)
        for link in soup.find_all('a', attrs={'class': 'sphinx-codeautolink-a'}):
            base, id_ = link['href'].split('#')
            if any(base.startswith(s) for s in ('http://', 'https://')):
                if base not in external_site_ids:
                    soup = BeautifulSoup(sess.get(base).text, 'html.parser')
                    external_site_ids[base] = gather_ids(soup)
                ids = external_site_ids[base]
            else:
                ids = site_ids[Path(base)]
            assert id_ in ids, (
                f'ID {id_} not found in {base}'
                f' while validating link for `{link.string}` in {doc}!'
            )
            total += 1
    return total


def gather_ids(soup: BeautifulSoup) -> set:
    """Gather all HTML IDs from a given page."""
    return set(tag['id'] for tag in soup.find_all(id=True))
