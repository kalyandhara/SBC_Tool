"""Headless UI smoke test (backlog B-03/B-09): open every tab, click every visible button,
and fail on any uncaught JavaScript error.

Needs Playwright and Chromium, so it is skipped unless they are installed:
    pip install -e ".[ui]" && playwright install chromium
CI runs it in the "UI smoke" job.

Failed API calls are not failures here (the panels handle them and some routes
download market data); uncaught exceptions and unhandled promise rejections are.
"""

import threading

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

# Buttons that leave the page or wait on long external downloads.
SKIP_BUTTON_TEXT = ("download", "export", "docx", "print")


@pytest.fixture(scope="module")
def base_url():
    from werkzeug.serving import make_server

    from app import app
    app.testing = True  # skips the per-IP rate limit; this test fires many requests
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="module")
def page(base_url):
    with sync_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(accept_downloads=True, viewport={"width": 1400, "height": 900})
        context.on("page", lambda p: p.close() if p != context.pages[0] else None)  # window.open
        pg = context.new_page()
        pg.errors = []
        pg.on("pageerror", lambda exc: pg.errors.append(str(exc)))
        pg.on("dialog", lambda d: d.dismiss())  # alert()/confirm()
        pg.goto(base_url + "/", wait_until="load")
        pg.wait_for_timeout(3000)
        yield pg
        browser.close()


def _tabs(page):
    page.evaluate("document.querySelector('.advanced-workspaces')?.setAttribute('open', '')")
    return page.eval_on_selector_all(".nav-tab[data-tab]", "els => els.map(e => e.dataset.tab)")


def test_page_loads_without_errors(page):
    assert page.errors == []


def test_every_tab_and_button(page):
    errors = {}
    for tab in _tabs(page):
        page.evaluate("document.querySelector('.advanced-workspaces')?.setAttribute('open', '')")
        page.click(f".nav-tab[data-tab='{tab}']")
        page.wait_for_timeout(500)
        buttons = page.locator(f"#{tab} button:visible")
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            try:
                label = (btn.inner_text(timeout=1000) or "").strip().lower()
                if btn.is_disabled() or any(s in label for s in SKIP_BUTTON_TEXT):
                    continue
                before = len(page.errors)
                btn.click(timeout=2000)
                page.wait_for_timeout(300)
                if len(page.errors) > before:
                    errors[f"{tab} / {label or i}"] = page.errors[before:]
            except sync_api.Error:
                continue  # re-rendered or hidden by an earlier click
        page.keyboard.press("Escape")
    page.wait_for_timeout(2000)  # let in-flight requests settle and report
    assert errors == {}, errors
    assert page.errors == [], page.errors
