"""B-25: error responses must not carry exception text."""

import ast
import logging
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SECRET = r"C:\secret\path.db: no such table: profiles"


def boom(*_a, **_k):
    raise RuntimeError(SECRET)


def assert_generic_500(resp):
    assert resp.status_code == 500
    body = resp.get_data(as_text=True)
    assert "secret" not in body and "no such table" not in body
    assert resp.get_json()["error"]


def test_app_route_failure_is_generic(client, monkeypatch, caplog):
    import app
    monkeypatch.setattr(app.profiles_db, "connect", boom)
    with caplog.at_level(logging.ERROR):
        resp = client.get("/api/habits/summary?user_key=default")
    assert_generic_500(resp)
    assert SECRET in caplog.text  # the traceback still reaches the server log


def test_blueprint_route_failure_is_generic(client, monkeypatch):
    import sbc.monthly_heatmap
    monkeypatch.setattr(sbc.monthly_heatmap, "monthly_heatmap", boom)
    assert_generic_500(client.get("/api/monthly_heatmap?date=2026-10-05&days=3"))


def test_astro_personal_failure_is_generic(client, monkeypatch):
    import sbc.engine
    monkeypatch.setattr(sbc.engine, "build_response", boom)
    assert_generic_500(client.get("/api/astro/personal?date=2026-10-05"))


def test_unhandled_exception_is_generic(client, monkeypatch):
    """Routes without their own try/except fall through to the global handler."""
    import app
    monkeypatch.setattr(app, "build_response", boom)
    monkeypatch.setattr(app, "_contra_cache", {}, raising=False)
    resp = client.get("/api/contra_signals?start=2026-10-05")
    assert_generic_500(resp)


@pytest.mark.parametrize("url", [
    "/api/tz/offset?tz=Not/AZone&date=2026-10-05",
    "/api/tz/offset?tz=Asia/Kolkata&date=2026-13-45",
    "/api/tz/from_coords?lat=north&lon=88",
])
def test_bad_timezone_input_is_400(client, url):
    assert client.get(url).status_code == 400


def test_no_handler_returns_exception_text_with_a_500():
    """Static guard: `except Exception as e: return jsonify({"error": str(e)}), 500` must not return."""
    offenders = []
    for f in [ROOT / "app.py", *(ROOT / "sbc" / "api").rglob("*.py")]:
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for h in ast.walk(tree):
            if not (isinstance(h, ast.ExceptHandler) and h.name):
                continue
            for r in (n for n in ast.walk(h) if isinstance(n, ast.Return) and n.value is not None):
                src = ast.unparse(r.value).replace(" ", "")
                if f"str({h.name})" in src and src.endswith(",500)"):
                    offenders.append(f"{f.relative_to(ROOT)}:{r.lineno}")
    assert offenders == []
