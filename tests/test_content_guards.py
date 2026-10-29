"""Backlog tests (B-03, B-10): no placeholder output and no hard-coded dates in the page."""

import ast
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTE_FILES = [ROOT / "app.py", ROOT / "sbc" / "app_factory.py", *(ROOT / "sbc" / "api").rglob("*.py")]


def test_no_route_module_returns_placeholder_text():
    hits = []
    for f in ROUTE_FILES:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and re.search(r"placeholder|lorem ipsum|\bTODO\b|demo data", node.value, re.I)):
                hits.append(f"{f.relative_to(ROOT)}:{node.lineno}: {node.value[:60]!r}")
    assert hits == []


class _TextDates(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hits: list[str] = []

    def handle_data(self, data):
        for m in re.findall(r"\b20\d\d-\d\d-\d\d\b", data):
            self.hits.append(f"line {self.getpos()[0]}: {m}")

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == "value" and value and re.fullmatch(r"20\d\d-\d\d-\d\d.*", value):
                self.hits.append(f"line {self.getpos()[0]}: <{tag} value={value}>")


def test_index_has_no_hardcoded_dates():
    """Dates come from the API or today's date, never from the markup."""
    p = _TextDates()
    p.feed((ROOT / "templates" / "index.html").read_text(encoding="utf-8"))
    assert p.hits == []
