"""B-17: index.html is markup only; scripts live in static/ where they can be cached and linted."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_no_inline_script_blocks():
    inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", HTML)
    assert inline == [], f"move inline scripts to static/js/: {inline}"


def test_no_inline_event_handlers():
    assert re.findall(r"\son[a-z]+\s*=", HTML) == []


def test_every_referenced_script_exists():
    for src in re.findall(r'<script src="/static/([^"?]+)', HTML):
        assert (ROOT / "static" / src).is_file(), src


@pytest.mark.parametrize("name", ["birth-city", "profiles-habits", "trading-signals", "rahu-ketu-trap", "sector-rotation"])
def test_extracted_scripts_parse(name):
    try:
        out = subprocess.run(["node", "--check", str(ROOT / "static" / "js" / f"{name}.js")],
                             capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        pytest.skip("node not installed")
    assert out.returncode == 0, out.stderr
