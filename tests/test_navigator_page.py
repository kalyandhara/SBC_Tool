"""Navigator tab: markup served by the app, and source checks that need no JS runtime."""
import re
from pathlib import Path

import pytest

from sbc.navigator import scoring as S
from sbc.navigator.backtest import NO_EDGE

ROOT = Path(__file__).resolve().parent.parent
JS = ROOT / "static" / "js" / "navigator.js"


@pytest.fixture(scope="module")
def html():
    from sbc.app_factory import create_app
    return create_app().test_client().get("/").get_data(as_text=True)


@pytest.fixture(scope="module")
def js():
    return JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def code(js):
    """Comments removed, so a banned word in prose cannot satisfy or fail a check."""
    return re.sub(r"^\s*//.*$", "", js, flags=re.M)


def test_tab_present(html):
    assert 'data-tab="tab-navigator"' in html and "navigator.js" in html
    assert "unvalidated research output" in html


def test_pane_has_every_section(html):
    pane = html[html.index('id="tab-navigator"', html.index('class="tab-pane')):]
    for node in ("nav-sample-banner", "nav-profile", "nav-status", "nav-chart", "nav-score",
                 "nav-lineage", "nav-backtest", "nav-run", "nav-backtest-status", "nav-backtest-out"):
        assert f'id="{node}"' in pane, node


def test_sample_banner_starts_hidden_and_says_pipeline_check(html):
    banner = re.search(r'<div id="nav-sample-banner"[^>]*>([^<]*)<', html)
    assert banner and " hidden" in banner.group(0).split(">")[0]
    assert "pipeline check" in banner.group(1)


def test_disclaimer_is_static_markup_not_left_to_a_successful_fetch(html):
    assert re.search(r'class="nav-disclaimer"[^>]*>[^<]*not personal financial advice', html)


def test_script_and_stylesheet_are_cache_busted(html):
    assert re.search(r'src="/static/js/navigator\.js\?v=\d+"', html)
    assert 'href="/static/style.css?v=36"' not in html


def test_no_html_sinks(code):
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert sink not in code, sink


def test_no_external_dependency_or_embedded_secret(code):
    assert "http://" not in code and "https://" not in code and "import " not in code
    assert not re.search(r"X-API-Token['\"]\s*:\s*['\"]", code)


def test_every_route_is_called_by_its_literal_path(code):
    for path in ("/api/navigator/profile", "/api/navigator/chart", "/api/navigator/score",
                 "/api/navigator/backtest"):
        assert path in code, path


def test_uses_the_pages_token_mechanism_for_reads(code):
    """api-token.js only covers writes, and the navigator guard covers reads too."""
    assert 'localStorage.getItem("sbcApiToken")' in code and '"X-API-Token"' in code


def test_birth_fields_never_reach_a_request(code):
    for field in ("birth_date", "birth_time", "\"lat\"", "\"lon\""):  # only via FormData names
        assert field not in code, field
    urls = re.findall(r"/api/navigator/[^\"'`]*", code)
    assert all("label" not in u and "tz" not in u for u in urls), urls


def test_polling_chains_a_timer_so_only_one_request_is_in_flight(code):
    assert "setInterval" not in code
    assert re.search(r"NAV_POLL_MS\s*=\s*3000", code)
    assert "AbortController" in code, "a request with no timeout could hang the tab"
    assert "MutationObserver" in code, "polling must stop on tab leave, however the tab changes"


def test_bands_and_actions_match_the_engine(code):
    for _, band in S.BANDS:
        assert f'"{band}"' in code, band
    for band, action in S.ACTIONS.items():
        assert re.search(rf'"{band}"\s*,\s*"{action}"', code) or f'"{band}": "{action}"' in code


def test_required_honest_wording(code):
    for phrase in ("insufficient events", "pipeline check only", NO_EDGE, "no Shadbala/Avastha",
                   "session_stats", "neutral"):
        assert phrase in code, phrase


def test_no_mystical_wording(js):
    for word in ("auspicious", "destiny", "cosmic", "mystical", "divine", "blessed"):
        assert word not in js.lower(), word


# ---- page fixes: birth form, latest run, duplicate text, tab bar ----------------
@pytest.fixture(scope="module")
def form(html):
    match = re.search(r'<form id="nav-profile-form".*?</form>', html, flags=re.S)
    assert match, "the birth data form is missing"
    return match.group(0)


def test_birth_form_has_every_field_and_autocomplete_off(form):
    assert re.search(r'<form id="nav-profile-form"[^>]*autocomplete="off"', form)
    for name, kind in (("label", "text"), ("birth_date", "date"), ("birth_time", "time"),
                       ("tz", "text"), ("lat", "number"), ("lon", "number")):
        tag = re.search(rf'<input[^>]*id="nav-f-{name}"[^>]*>', form)
        assert tag, name
        assert f'type="{kind}"' in tag.group(0) and 'autocomplete="off"' in tag.group(0), name
    assert 'step="1"' in re.search(r'<input[^>]*id="nav-f-birth_time"[^>]*>', form).group(0)
    assert "method=\"post\"" in form.lower() and "action=" not in form.lower()


def test_birth_form_wording(html, form):
    assert "cannot be entered on this page" not in html
    for phrase in ("local database", "unencrypted", "Phase 1", "new backtest"):
        assert phrase in form, phrase


def test_birth_form_posts_json_and_never_persists_values(code):
    submit = code[code.index("async function navSubmitProfile"):]
    submit = submit[:submit.index("\n}\n")]
    assert 'method: "POST"' in submit and "JSON.stringify" in submit
    assert '"Content-Type": "application/json"' in submit
    assert "form.reset()" in submit and "navLoadProfile" in submit
    assert "localStorage.setItem" not in code and "sessionStorage" not in code
    assert re.search(r'navFetch\("/api/navigator/profile",\s*\{', submit), "no values in the URL"


def test_latest_run_is_loaded_and_labelled_with_its_data_date(code):
    assert "/api/navigator/backtest/latest?profile_id=" in code
    assert "Latest saved backtest" in code and "data_asof" in code


def test_disclaimer_is_not_repeated_in_the_backtest(code):
    render = code[code.index("function navRenderRun"):]
    render = render[:render.index("\n}\n")]
    assert "status_note" not in render and render.count("run.disclaimer") == 1


def test_tab_bar_wraps_at_desktop_width():
    css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    block = re.search(r"@media \(min-width: 761px\) \{[^{]*?\.nav-tabs \{([^}]*)\}", css)
    assert block and "flex-wrap: wrap" in block.group(1)


def test_score_card_shows_the_latest_verdict_beside_the_action_label(code):
    render = code[code.index("function navRenderScore"):]
    render = render[:render.index("\n}\n")]
    action = render.index("Action label:")
    assert "latest_verdict" in render[action:action + 400]


def test_occupancy_label_names_the_first_horizon(code):
    occ = code[code.index("function navOccupancy"):]
    occ = occ[:occ.index("\n}\n")]
    assert "band.occupancy" in occ and "first horizon" in occ and "strongest horizon" not in occ


# --- Phase 4: similar past dates -------------------------------------------------------

def test_similar_dates_section_sits_between_score_and_backtest(html):
    pane = html[html.index('id="tab-navigator"', html.index('class="tab-pane')):]
    for node in ("nav-analogs", "nav-analogs-status", "nav-analogs-out"):
        assert f'id="{node}"' in pane, node
    assert pane.index('id="nav-score"') < pane.index('id="nav-analogs"') < pane.index('id="nav-backtest"')
    section = pane[pane.index('id="nav-analogs"'):pane.index('id="nav-backtest"')]
    assert "Similar past dates" in section
    assert re.search(r'id="nav-analogs-status"[^>]*role="status"', section)


def test_similar_dates_caveats_are_static_markup(html):
    section = html[html.index('id="nav-analogs"'):html.index('id="nav-backtest"')]
    assert "not a tested signal" in section
    assert "open to open, 5 sessions, as in the backtest" in section
    assert "n/a" in section


def test_similar_dates_calls_the_api_with_profile_and_days(code):
    assert "/api/navigator/analogs?profile_id=${" in code
    assert "&days=30" in code


def test_similar_dates_labels(code):
    for label in ("open to open, 5 sessions, as in the backtest", "random sets of ",
                  "did at least this well", "of the time", "Era window", "Era-matched baseline",
                  "All-eras baseline", "Median analog age", "Average drawdown", "Median next-5",
                  "Average next-5", "Win ratio", "Loading similar past dates",
                  "no high-scoring date in this window", "High-scoring dates"):
        assert label in code, label
    for field in ("nifty_day", "bank_day", "vix_change_pct", "sectors_top5", "sectors_missing",
                  "next5", "drawdown", "age_years", "similarity", "natal", "sky",
                  "era_note", "era_window", "era_random_share", "era_baseline", "median_age_years",
                  "random_share", "label"):
        assert f".{field}" in code, field


def test_similar_dates_cancel_stale_renders_and_one_request(code):
    assert "analogSeq" in code
    body = code[code.index("async function navLoadAnalogs"):]
    body = body[:body.index("\n}\n")]
    assert body.count("seq !== NAV.analogSeq") >= 2 and "NAV.analogCtl = ctl" in body
    stop = code[code.index("function navStopAnalogs"):]
    assert ".abort()" in stop[:stop.index("\n}\n")]
    load = code[code.index("async function navLoadProfile"):]
    assert "navStopAnalogs" in load[:load.index("\n}\n")]


def test_similar_dates_is_lazy_and_does_not_block_the_score(code):
    load = code[code.index("async function navLoadProfile"):]
    load = load[:load.index("\n}\n")]
    # Fired without await, outside the Promise.all that renders the score.
    assert "navLoadAnalogs(" in load
    assert "await navLoadAnalogs" not in load
    assert "navLoadAnalogs" not in load[load.index("Promise.all"):]
    sync = code[code.index("function navSync"):]
    assert "navStopAnalogs" in sync[:sync.index("\n}\n")]


def test_navigator_script_version_bumped(html):
    assert re.search(r'navigator\.js\?v=([3-9]|\d\d+)"', html)
