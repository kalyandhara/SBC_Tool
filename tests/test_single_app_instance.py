"""B-15: running `python app.py` must create exactly one Flask app."""

import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

PROBE = r"""
import runpy, sys, flask
created = []
_init = flask.Flask.__init__
def counting_init(self, *a, **k):
    created.append(a[0] if a else k.get("import_name"))
    _init(self, *a, **k)
flask.Flask.__init__ = counting_init
flask.Flask.run = lambda self, *a, **k: None   # don't start a server
g = runpy.run_path("app.py", run_name="__main__")
# Blueprints import the engine lazily, at request time, so make requests too.
c = g["app"].test_client()
for url in ("/api/presets", "/api/prediction?date=2026-10-05",
            "/api/prediction_series?start=2026-10-05&end=2026-10-06&anchor=nifty",
            "/api/astro/personal?date=2026-10-05"):
    assert c.get(url).status_code < 500, url
print("FLASK_APPS", len(created))
print("APP_MODULE_LOADED", "app" in sys.modules)
"""


def test_running_app_py_as_main_creates_one_flask_app(tmp_path):
    env = {"SBC_SERIES_CACHE_DB": str(tmp_path / "s.db"),
           "SBC_PROFILES_DB": str(tmp_path / "p.db"),
           "SBC_FORECAST_DB": str(tmp_path / "f.db")}
    import os
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, capture_output=True,
                         text=True, timeout=180, env={**os.environ, **env})
    assert out.returncode == 0, out.stderr[-2000:]
    assert "FLASK_APPS 1" in out.stdout, out.stdout
    assert "APP_MODULE_LOADED False" in out.stdout, out.stdout


def test_no_first_party_module_imports_app():
    offenders = []
    for base in ("sbc", "research"):
        for p in (ROOT / base).rglob("*.py"):
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names = [node.module]
                elif isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                if any(n == "app" or n.startswith("app.") for n in names):
                    offenders.append(f"{p.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []


def test_app_still_reexports_the_engine():
    import app
    from sbc import engine
    assert app.build_response is engine.build_response
    assert app.ANCHORS is engine.ANCHORS
    assert app._utc_from_local is engine._utc_from_local
