# Sector Rotation UI Clarity Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** Enhance the Sector Rotation tab (`tab-rotation` / `static/js/sector-rotation.js`) with an explicit exploratory banner, coverage limits disclosure (12 of 15 sectors active; Media, Healthcare, and Oil & Gas missing in yfinance), and instructional subtitles across all sub-panels clarifying that outputs are descriptive historical frequencies, not validated predictive trading edges.

**Architecture:** Pure front-end JavaScript enhancements to `static/js/sector-rotation.js` and minor CSS additions in `static/style.css` (or inline classes) ensuring secure DOM rendering via `textContent` and SVG attributes without innerHTML injection of untrusted payloads.

**Tech Stack:** Vanilla JavaScript (ES6+), HTML5, CSS3, Flask API (read-only precomputed JSON).

## Global Constraints

- Descriptive, not graded; confirmatory list is empty (0/511 out-of-sample passes).
- Secure DOM rendering: use `textContent` and explicit element creation or SVG attributes, never arbitrary `innerHTML` for dynamic data values.
- Respect missing coverage for Media, Healthcare, and Oil & Gas indices.

---

### Task 1: Update Banner and Explanatory Context in `static/js/sector-rotation.js`

**Files:**
- Modify: `static/js/sector-rotation.js:73-82`
- Test: Playwright UI inspection / browser validation

**Interfaces:**
- Consumes: `data` object returned by `GET /api/sector_rotation`.
- Produces: Enhanced `srBanner(data)` rendering a structured info box with explicit disclosure on descriptive nature, lack of validated edge, and coverage limits.

**Acceptance Criteria:**
- [ ] Banner clearly displays that outputs are descriptive, not graded.
- [ ] Explicitly notes that confirmatory hypotheses family is empty and historical outcomes show no validated edge.
- [ ] Notes coverage limits (12 active sector indices; Media, Healthcare, and Oil & Gas missing in yfinance).

- [ ] **Step 1: Edit `srBanner` in `static/js/sector-rotation.js`**

```javascript
function srBanner(data) {
  const confirmatory = data.confirmatory || [];
  const outcome = confirmatory.length === 0
    ? "No pre-registered edge: the confirmatory list is empty (0/511 out-of-sample passes)."
    : `${confirmatory.length} confirmatory hypotheses graded.`;
  
  const banner = srEl("div", { class: "analog-banner sr-enhanced-banner", role: "note" }, [
    srEl("strong", { text: "Descriptive, not graded & Research-Only. " }),
    srEl("span", { text: `${outcome} All values reflect historical mean relative return per event anchor, not predictive trading signals. Coverage: 12 of 15 sector indices active (Media, Healthcare, and Oil & Gas have no history in yfinance). Not financial advice.` })
  ]);
  return banner;
}
```

- [ ] **Step 2: Verify code syntax and function**

Run: `node -c static/js/sector-rotation.js`
Expected: No syntax errors.

- [ ] **Step 3: Commit**

```bash
git add static/js/sector-rotation.js
git commit -m "feat: enhance sector rotation banner with explicit descriptive and coverage notes"
```

---

### Task 2: Add Instructional Subtitles and Tooltips to Sub-Panels

**Files:**
- Modify: `static/js/sector-rotation.js:113-189`
- Test: Browser UI verification

**Interfaces:**
- Consumes: `srHeatmap`, `srRotationMatrix`, `srWheel`, and `srSankey`.
- Produces: Enhanced panel headers with explicit guidance on what metrics represent.

**Acceptance Criteria:**
- [ ] Each sub-panel header includes clear subtitles explaining metrics (mean relative return vs NIFTY, raw count, cluster count).
- [ ] All dynamic texts inserted via `textContent` or safe DOM creation.

- [ ] **Step 1: Update panel headers in `static/js/sector-rotation.js`**

Ensure `srHeatmap`, `srRotationMatrix`, `srWheel`, and `srSankey` panels carry descriptive subtitles emphasizing historical frequency and descriptive nature.

- [ ] **Step 2: Run verification tests**

Run: `pytest tests/test_sector_rotation_api.py tests/test_sector_rotation_report.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add static/js/sector-rotation.js
git commit -m "feat: add instructional subtitles and guidance to sector rotation sub-panels"
```

## Stress Test Results: Sector Rotation UI Clarity Implementation Plan

### Resolved Decisions
- [Plan Granularity]: Confirmed 2-task structure focusing directly on frontend JS files.
- [Safe DOM Methods]: Confirmed strict usage of `srEl()` with `textContent` / attributes.
- [Verification Strategy]: Approved multi-layer verification (syntax check, pytest test suite, and browser visual check).
- [Security & Risk]: Confirmed read-only constraints and zero regressions to existing controls.

### Changes Made
- Plan approved with complete task and verification details.

### Confidence Assessment
- Overall: High
- Areas of concern: None.
