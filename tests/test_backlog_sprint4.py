"""Backlog sprint 4: B-08 lock file, B-27 template cache, B-32 line endings."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _names(lines):
    out = set()
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(re.split(r"[<>=!~\[ ;]", line, maxsplit=1)[0].lower().replace("_", "-"))
    return out


def test_lock_pins_every_runtime_requirement():
    """B-08: Docker and CI install requirements.lock, so it must cover requirements.txt."""
    wanted = _names((ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines())
    lock_lines = (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
    pinned = [ln.split("#", 1)[0].strip() for ln in lock_lines if ln.split("#", 1)[0].strip()]
    assert all("==" in ln for ln in pinned), "every lock line is an exact pin"
    assert wanted <= _names(pinned), f"missing from lock: {wanted - _names(pinned)}"


def test_docker_and_ci_install_the_lock():
    assert "-r requirements.lock" in (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pip install -r requirements.txt" not in ci
    assert "pip install -r requirements.lock" in ci


def test_template_reload_follows_debug(app):
    """B-27: templates are cached in production and reloaded only under debug."""
    assert app.config.get("TEMPLATES_AUTO_RELOAD") is None
    debug = app.debug
    try:
        app.debug = False
        assert app.jinja_env.auto_reload is False
        app.debug = True
        assert app.jinja_env.auto_reload is True
    finally:
        app.debug = debug


def test_gitattributes_normalises_line_endings():
    """B-32."""
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in text
