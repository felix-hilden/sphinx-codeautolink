from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Cache external pages for the duration of the runtime,
# so that we don't request them multiple times needlessly
sess = requests.Session()
external_site_ids = {}


def check_link_targets(root: Path) -> int:
    """Validate links in HTML site at root, return number of links found."""
    site_docs = {
        p: BeautifulSoup(p.read_text("utf-8"), "html.parser")
        for p in root.glob("**/*.html")
    }
    site_ids = {k: gather_ids(v) for k, v in site_docs.items()}

    total = 0
    for doc, soup in site_docs.items():
        for link in soup.find_all("a", attrs={"class": "sphinx-codeautolink-a"}):
            base, id_ = link["href"].split("#")
            if any(base.startswith(s) for s in ("http://", "https://")):
                if base not in external_site_ids:
                    sub_soup = BeautifulSoup(sess.get(base).text, "html.parser")
                    external_site_ids[base] = gather_ids(sub_soup)
                ids = external_site_ids[base]
            else:
                target_path = (doc.parent / base).resolve()
                if target_path.is_dir():
                    target_path /= "index.html"
                assert target_path.exists(), (
                    f"Target path {target_path!s} not found while validating"
                    f" link for `{link.string}` in {doc.relative_to(root)!s}!"
                )
                ids = site_ids[target_path]

            assert id_ in ids, (
                f"ID {id_} not found in {base} while validating link"
                f" for `{link.string}` in {doc.relative_to(root)!s}!"
            )
            total += 1
    return total


def check_reference_targets_exist(root: Path):
    site_docs = {
        p: BeautifulSoup(p.read_text("utf-8"), "html.parser")
        for p in root.glob("**/*.html")
    }
    for doc, soup in site_docs.items():
        for link in soup.find_all("a", attrs={"class": "reference internal"}):
            base = link["href"].split("#")[0]
            if any(base.startswith(s) for s in ("http://", "https://")):
                continue
            target_path = doc if base == "" else (doc.parent / base).resolve()
            if target_path.is_dir():
                target_path /= "index.html"
            assert target_path.exists(), (
                f"Target path {target_path!s} not found while validating"
                f" link for `{link.string}` in {doc.relative_to(root)!s}!"
            )


def gather_ids(soup: BeautifulSoup) -> set:
    """Gather all HTML IDs from a given page."""
    return {tag["id"] for tag in soup.find_all(id=True)}
