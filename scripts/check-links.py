#!/usr/bin/env python3
"""Check that every internal link and asset in a static site points to a file that exists.

Usage: python3 scripts/check-links.py <site folder> [<site folder> ...]

External links (http, https, mailto, tel, data, javascript) are skipped: they are not
under our control and would make CI flaky. Root-relative links (/en/) resolve against the
site folder. A link to a folder needs an index.html in it; a link without an extension may
also point to <name>.html (Netlify pretty URLs). Exit code 1 when anything is missing.
"""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:", "javascript:", "sms:")
LINK_ATTRS = {"href", "src", "srcset", "poster", "data-src"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name not in LINK_ATTRS or not value:
                continue
            if tag == "link" and dict(attrs).get("rel") in ("preconnect", "dns-prefetch", "canonical", "alternate"):
                continue
            if name == "srcset":
                for part in value.split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.found.append(url)
            else:
                self.found.append(value)


def redirect_rules(root: Path) -> list[str]:
    """Source paths from a Netlify _redirects file. A catch-all ("/*") is ignored: it would
    hide every broken link."""
    rules = []
    file = root / "_redirects"
    if file.is_file():
        for line in file.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts and parts[0].startswith("/") and parts[0] != "/*":
                rules.append(parts[0])
    return rules


def redirected(path: str, rules: list[str]) -> bool:
    for rule in rules:
        if rule.endswith("*") and path.startswith(rule[:-1]):
            return True
        if path.rstrip("/") == rule.rstrip("/"):
            return True
    return False


def exists(root: Path, page: Path, url: str, rules: list[str]) -> bool:
    path = unquote(urlsplit(url).path)
    if not path:
        return True  # "#anchor" or "?query" on the same page
    if path.startswith("/") and redirected(path, rules):
        return True
    target = (root / path.lstrip("/")) if path.startswith("/") else (page.parent / path)
    if target.is_file():
        return True
    if target.is_dir():
        return (target / "index.html").is_file()
    return not target.suffix and target.with_suffix(".html").is_file()


def check(root: Path) -> list[str]:
    problems = []
    rules = redirect_rules(root)
    for page in sorted(root.rglob("*.html")):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        for url in parser.found:
            if url.lower().startswith(SKIP_SCHEMES) or url.startswith("//") or "{{" in url:
                continue
            if not exists(root, page, url, rules):
                problems.append(f"{page.relative_to(root)}: {url}")
    return problems


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    problems = []
    for folder in sys.argv[1:]:
        root = Path(folder)
        if not root.is_dir():
            print(f"Not a folder: {folder}")
            return 2
        problems += [f"{folder}/{p}" for p in check(root)]
    for p in problems:
        print(f"Missing: {p}")
    print(f"{len(problems)} broken internal link(s)" if problems else "All internal links resolve")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
