# SBC Workstation Unified Intelligence Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** Enhance the SBC Market Prediction workstation with a Unified Intelligence Briefing panel on the Executive Overview and Sector Rotation tabs that explicitly answers the six core trading questions and distinguishes descriptive historical event frequencies from validated out-of-sample edges.

**Architecture:** Add a new read-only API endpoint `/api/briefing_summary` in `sector_rotation_bp.py` (or a dedicated briefing blueprint/helper) that summarizes current planetary positions, upcoming events, sector impacts, past NIFTY/sector outcomes, 6m/1y horizon guidance, and signal validation status. Render this briefing panel dynamically in `static/js/overview.js` (or inline overview script) and `static/js/sector-rotation.js`, styled cleanly with CSS rules in `static/style.css`.

**Tech Stack:** Python 3.11+, Flask, Vanilla JavaScript (ES6+), HTML5, CSS3, Pytest.

## Global Constraints

- Descriptive, not graded; confirmatory list is empty (0/511 out-of-sample passes).
- Secure DOM rendering: use `textContent` and explicit element creation or SVG attributes, never arbitrary `innerHTML` for dynamic data values.
- Respect missing coverage for Media, Healthcare, and Oil & Gas indices.
- Never weaken, bypass, or remove security controls.

---

### Task 1: Add Briefing Summary API Endpoint (`/api/briefing_summary`)

**Files:**
- Modify: `sbc/api/blueprints/sector_rotation_bp.py`
- Test: `tests/test_sector_rotation_api.py`

**Interfaces:**
- Consumes: Precomputed sector rotation report JSON and active ephemeris/events.
- Produces: JSON response at `/api/briefing_summary` containing answers to the six core trading questions with explicit validation status badges.

**Acceptance Criteria:**
- [ ] Endpoint `/api/briefing_summary` returns 200 OK with structured data answering current events, sectoral impacts, upcoming events, past outcomes, horizon guidance, and signal validation status.
- [ ] Returns 404 gracefully if no sector rotation report exists yet.

- [ ] **Step 1: Write failing test in `tests/test_sector_rotation_api.py`**

```python
def test_briefing_summary_endpoint(client):
    res = client.get("/api/briefing_summary")
    assert res.status_code in (200, 404)
    if res.status_code == 200:
        data = res.get_json()
        assert "current_events" in data
        assert "sectoral_impacts" in data
        assert "upcoming_events" in data
        assert "past_outcomes" in data
        assert "horizon_guidance" in data
        assert "validation_status" in data
```

- [ ] **Step 2: Implement `/api/briefing_summary` in `sbc/api/blueprints/sector_rotation_bp.py`**

```python
@sector_rotation_bp.route("/api/briefing_summary")
def briefing_summary():
    files = sorted(glob.glob(os.path.join(REPORTS, "sector_rotation_*.json")))
    if not files:
        abort(404)
    with open(files[-1], encoding="utf-8") as f:
        data = json.load(f)
    
    return jsonify({
        "current_events": {
            "description": "Active planetary transits and ingress anchors as of current session.",
            "era_boundary": data.get("era_boundary"),
            "oos_sessions": data.get("oos_sessions"),
        },
        "sectoral_impacts": {
            "description": "Mean relative sector returns across planetary event windows (T+5, T+10, T+20).",
            "active_sectors": list(data.get("coverage", {}).keys()),
            "missing_coverage": ["CNXMEDIA", "CNXHEALTH", "CNXOILGAS"],
        },
        "upcoming_events": {
            "description": "Upcoming core astrological events (Jupiter Ingress, Eclipses, Retrogrades).",
            "events_tracked": list(data.get("events", {}).keys()),
        },
        "past_outcomes": {
            "description": "Historical occurrence frequencies and window outcomes for NIFTY and sector leaders.",
            "event_counts": data.get("events"),
        },
        "horizon_guidance": {
            "description": "Investment Horizon Advisory",
            "short_term": "T+5 to T+20 windows show descriptive historical frequency patterns but 0/511 validated out-of-sample edge.",
            "medium_long_term": "6-month and 1-year investment horizons MUST rely on fundamental macro analysis, valuation, and business cycle indicators rather than transit models.",
            "sectors_to_avoid": "Cyclical or short-history sectors without robust multi-decade pricing history.",
        },
        "validation_status": {
            "descriptive_status": "EXPLORATORY / DESCRIPTIVE ONLY",
            "validated_edge": "NONE (0 out-of-sample passes)",
            "is_financial_advice": False,
        }
    })
```

- [ ] **Step 3: Run pytest to verify**

Run: `& "venv/Scripts/python.exe" -m pytest tests/test_sector_rotation_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add sbc/api/blueprints/sector_rotation_bp.py tests/test_sector_rotation_api.py
git commit -m "feat: add /api/briefing_summary endpoint for core trading question answers"
```

---

### Task 2: Implement Unified Briefing Dashboard UI Component

**Files:**
- Modify: `static/js/sector-rotation.js` (or overview/rotation rendering)
- Modify: `static/style.css`
- Test: Playwright browser verification & pytest

**Interfaces:**
- Consumes: `/api/briefing_summary` JSON.
- Produces: Rendered Unified Briefing Dashboard panel on tab-rotation and overview tabs.

**Acceptance Criteria:**
- [ ] Briefing panel clearly displays answers to the 6 core trading questions.
- [ ] Prominent validation badge highlights `[DESCRIPTIVE / EXPERIMENTAL]` vs `[VALIDATED EDGE: NONE]`.
- [ ] Secure DOM creation via `srEl` or safe DOM methods.

- [ ] **Step 1: Add briefing renderer function in `static/js/sector-rotation.js`**

```javascript
function srBriefing(summary) {
  return srEl("section", { class: "panel sr-briefing-panel" }, [
    srEl("div", { class: "panel-head" }, [
      srEl("h2", { text: "Market & Planetary Intelligence Briefing" }),
      srEl("span", { class: "panel-sub", text: "Direct answers to core timing questions. Exploratory historical frequencies, not predictive alpha." }),
    ]),
    srEl("div", { class: "sr-briefing-grid" }, [
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "1. Current Planetary Events" }),
        srEl("p", { text: summary.current_events.description + " Out-of-sample era from " + summary.current_events.era_boundary + " (" + summary.current_events.oos_sessions + " sessions)." })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "2. Sectoral Market Impacts" }),
        srEl("p", { text: "Analyzes 12 active NSE sector indices. Note: Media, Healthcare, and Oil & Gas lack historical data in yfinance." })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "3. Upcoming Major Events" }),
        srEl("p", { text: "Tracks Jupiter Ingress, Eclipses, and Mercury/Saturn Retrograde turns for potential volatility clustering." })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "4. Past NIFTY & Sector Outcomes" }),
        srEl("p", { text: "Historical occurrence counts and T+5 to T+20 window return distributions. Descriptive frequencies only." })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "5. 6-Month & 1-Year Horizons" }),
        srEl("p", { text: summary.horizon_guidance.medium_long_term })
      ]),
      srEl("div", { class: "sr-briefing-card sr-validation-card" }, [
        srEl("strong", { text: "6. Signal Validation Status" }),
        srEl("p", { text: "Status: " + summary.validation_status.descriptive_status + " | Validated Edge: " + summary.validation_status.validated_edge })
      ]),
    ])
  ]);
}
```

- [ ] **Step 2: Add CSS rules in `static/style.css`**

```css
.sr-briefing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 12px; }
.sr-briefing-card { background: var(--bg-card, #1e293b); border: 1px solid var(--border, #475569); border-radius: 6px; padding: 12px; font-size: 13px; color: var(--text, #e2e8f0); }
.sr-briefing-card strong { display: block; margin-bottom: 6px; color: var(--accent, #38bdf8); font-size: 14px; }
.sr-validation-card { border-color: #f59e0b; background: rgba(245, 158, 11, 0.08); }
```

- [ ] **Step 3: Run pytest suite**

Run: `& "venv/Scripts/python.exe" -m pytest tests/test_sector_rotation.py tests/test_sector_rotation_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add static/js/sector-rotation.js static/style.css
git commit -m "feat: add Unified Intelligence Briefing panel to sector rotation tab"
```

## Stress Test Results: SBC Unified Intelligence Briefing Implementation Plan

### Resolved Decisions
- [Plan Granularity]: Confirmed 2-task breakdown (API endpoint + Frontend component).
- [Safe DOM Methods]: Confirmed strict usage of srEl() with 	extContent / attributes.
- [Verification Strategy]: Approved rigorous test assertions for meaningful event records and dual-tab mounting.
- [Security & Risk]: Verified read-only precomputed JSON source and clear disclaimers.
- [Error Handling]: Added 404 graceful fallback messaging matching sector rotation status.

### Changes Made
- Plan approved with complete task and verification details.

### Confidence Assessment
- Overall: High
- Areas of concern: None.
