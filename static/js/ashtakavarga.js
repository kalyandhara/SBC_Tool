// Ashtakavarga tab (spec .internal/specs/2026-10-31-ashtakavarga-design.md). Live view of
// GET /api/ashtakavarga: an anchor's natal BAV/SAV and the signs the planets transit at
// 09:15 IST. Descriptive, not validated. Every data value is set with textContent, never as markup.

const AV_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"];
const AV_MODES = [["auto", "Auto"], ["classical", "Classical (with Lagna)"], ["seven", "7 planets (no Lagna)"]];
const AV_MIN_DATE = "1900-01-01";
const AV_MAX_DATE = "2100-12-31";
const AV_STATE = { anchor: "nifty", lagna_mode: "auto", date: "", dateTouched: false };
const AV_UI = { controls: null, anchor: null, anchorList: "", lagna: null, date: null, note: null, data: null };
let AV_SEQ = 0;
let AV_LAST_KEY = ""; // params of the last successfully rendered view

function avEl(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function avSelectField(label, onChange) {
  const select = avEl("select", { "aria-label": label });
  select.addEventListener("change", () => onChange(select.value));
  return { select, field: avEl("label", {}, [avEl("span", { text: `${label} ` }), select]) };
}

function avFillOptions(select, options, value) {
  select.replaceChildren(...options.map(([v, text]) => avEl("option", { value: v, text })));
  select.value = value;
}

function avValidDate(v) {
  return /^\d{4}-\d{2}-\d{2}$/.test(v) && v >= AV_MIN_DATE && v <= AV_MAX_DATE;
}

// The date the next request will use: the header's, until the tab's own picker is used.
function avEffectiveDate() {
  return AV_STATE.dateTouched ? AV_STATE.date : (document.getElementById("date")?.value || "");
}

function avKey() {
  return [AV_STATE.anchor, AV_STATE.lagna_mode, avEffectiveDate()].join("|");
}

// Build the controls once; they keep their DOM nodes (and focus) across reloads.
function avEnsureUi() {
  if (AV_UI.controls) return;
  const anchor = avSelectField("Anchor", (v) => { AV_STATE.anchor = v; avLoad(true); });
  const lagna = avSelectField("Lagna", (v) => { AV_STATE.lagna_mode = v; avLoad(true); });
  avFillOptions(lagna.select, AV_MODES, AV_STATE.lagna_mode);
  const input = avEl("input", { type: "date", min: AV_MIN_DATE, max: AV_MAX_DATE, "aria-label": "Transit date" });
  input.addEventListener("change", () => {
    if (!avValidDate(input.value)) {
      input.value = avEffectiveDate();
      document.getElementById("av-status").textContent =
        `Transit date must be between ${AV_MIN_DATE} and ${AV_MAX_DATE}.`;
      return;
    }
    AV_STATE.date = input.value;
    AV_STATE.dateTouched = true;
    avLoad(true);
  });
  AV_UI.anchor = anchor.select;
  AV_UI.lagna = lagna.select;
  AV_UI.date = input;
  AV_UI.controls = avEl("div", { class: "av-controls" }, [
    anchor.field, lagna.field, avEl("label", {}, [avEl("span", { text: "Transit date " }), input]),
  ]);
  AV_UI.note = avEl("p", { class: "panel-sub" });
  AV_UI.data = avEl("div", { class: "av-data" });
  document.getElementById("av-root").replaceChildren(AV_UI.controls, AV_UI.note, AV_UI.data);
}

// Only repopulate the anchor options when the list changed; otherwise just reflect the state.
function avSyncControls(anchors) {
  const list = anchors.join(",");
  if (list !== AV_UI.anchorList) {
    avFillOptions(AV_UI.anchor, anchors.map((a) => [a, a]), AV_STATE.anchor);
    AV_UI.anchorList = list;
  } else if (AV_UI.anchor.value !== AV_STATE.anchor) {
    AV_UI.anchor.value = AV_STATE.anchor;
  }
  AV_UI.lagna.value = AV_STATE.lagna_mode;
  const date = avEffectiveDate();
  if (AV_UI.date.value !== date) AV_UI.date.value = date;
}

function avBanner(data) {
  const lines = [];
  if (data.mode === "seven") {
    lines.push(data.lagna_reliable ? "Lagna excluded by choice." : `Lagna excluded: ${data.lagna_reason}.`);
  } else if (!data.lagna_reliable) {
    lines.push(`Lagna included by choice, but it is unreliable: ${data.lagna_reason}.`);
  }
  for (const [planet, signs] of Object.entries(data.ambiguous_contributors)) {
    lines.push(`${planet} changes sign during the birth day (${signs.join("/")}); its points may be misplaced.`);
  }
  const box = avEl("div", { class: "analog-banner", role: "note" },
    [avEl("strong", { text: "Experimental · descriptive. No validated market edge." })]);
  for (const line of lines) box.appendChild(avEl("p", { text: line }));
  return box;
}

function avGrid(data) {
  const n = data.natal;
  const head = avEl("tr", {}, [avEl("th", { text: `Planet (/${n.max_per_sign})`, scope: "col" })]);
  data.signs.forEach((s) => head.appendChild(avEl("th", { text: s.slice(0, 3), title: s, scope: "col" })));
  const body = avEl("tbody");
  for (const p of AV_PLANETS) {
    const row = avEl("tr", {}, [avEl("th", { text: p, scope: "row" })]);
    n.bav[p].forEach((v, i) => {
      const cell = avEl("td", { text: String(v) });
      if (data.transit[p] && data.transit[p].sign_index === i) {
        cell.classList.add("av-transit");
        cell.title = `${p} transits ${data.signs[i]}`;
      }
      row.appendChild(cell);
    });
    body.appendChild(row);
  }
  const hi = Math.max(...n.sav);
  const lo = Math.min(...n.sav);
  const savRow = avEl("tr", { class: "av-sav" }, [avEl("th", { text: "SAV", scope: "row" })]);
  for (const v of n.sav) {
    const cell = avEl("td", { text: String(v) });
    cell.style.setProperty("--av-heat", (hi === lo ? 0.5 : (v - lo) / (hi - lo)).toFixed(2));
    savRow.appendChild(cell);
  }
  body.appendChild(savRow);
  const caption = avEl("caption", { class: "av-caption", text: "Bindus by sign (BAV per planet, SAV total)" });
  return avEl("table", { class: "data-table av-grid" }, [caption, avEl("thead", {}, [head]), body]);
}

function avTransitTable(data) {
  const cols = ["Planet", "Sign", `BAV (/${data.natal.max_per_sign})`, "SAV"];
  const head = avEl("tr", {}, cols.map((t) => avEl("th", { text: t, scope: "col" })));
  const body = avEl("tbody");
  for (const p of AV_PLANETS) {
    const t = data.transit[p];
    body.appendChild(avEl("tr", {}, [p, t.sign, String(t.bav_points), String(t.sav_points)]
      .map((x, i) => (i === 0 ? avEl("th", { text: x, scope: "row" }) : avEl("td", { text: x })))));
  }
  return avEl("div", {}, [
    avEl("h3", { text: `Transits on ${data.date}, as of ${data.transit_time}` }),
    avEl("table", { class: "data-table av-transit-table" }, [
      avEl("caption", { class: "av-caption", text: "Transit bindus" }), avEl("thead", {}, [head]), body]),
  ]);
}

function avRender(data) {
  avEnsureUi();
  avSyncControls(data.anchors);
  AV_UI.note.textContent = `${data.anchor_name}: ${data.anchor_note}`;
  AV_UI.data.replaceChildren(avBanner(data), avGrid(data), avTransitTable(data));
}

// force=true: an explicit control change always fetches. Otherwise skip when nothing changed.
async function avLoad(force = false) {
  const status = document.getElementById("av-status");
  avEnsureUi();
  if (!AV_STATE.dateTouched) AV_STATE.date = document.getElementById("date")?.value || "";
  const key = avKey();
  if (force !== true && key === AV_LAST_KEY) return;
  const params = new URLSearchParams({ anchor: AV_STATE.anchor, lagna_mode: AV_STATE.lagna_mode });
  if (AV_STATE.date) params.set("date", AV_STATE.date);
  const seq = ++AV_SEQ;
  status.textContent = "Loading…";
  try {
    const r = await fetch(`/api/ashtakavarga?${params}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    if (seq !== AV_SEQ) return; // a newer request superseded this one
    status.textContent = "";
    avRender(data);
    AV_LAST_KEY = key;
  } catch (err) {
    if (seq !== AV_SEQ) return;
    AV_LAST_KEY = "";
    AV_UI.data.replaceChildren(); // never leave old data under controls that no longer match it
    AV_UI.note.textContent = "";
    avSyncControls(AV_UI.anchorList ? AV_UI.anchorList.split(",") : [AV_STATE.anchor]);
    status.textContent = `Could not load Ashtakavarga (${err.message}).`;
  }
}

(function avInit() {
  const isActive = () => document.getElementById("tab-ashtakavarga")?.classList.contains("active");
  const refresh = () => { if (isActive()) avLoad(); };
  document.querySelector('[data-tab="tab-ashtakavarga"]')?.addEventListener("click", () => avLoad());
  // Follow the header session date until the tab's own picker is used. Programmatic header
  // moves (the next-session default) fire no change event, so also watch the value cheaply.
  const header = document.getElementById("date");
  header?.addEventListener("change", refresh);
  let lastHeader = header?.value || "";
  setInterval(() => {
    const v = header?.value || "";
    if (v !== lastHeader) { lastHeader = v; refresh(); }
  }, 1000);
  // A deep link loads after DOMContentLoaded, once app.js has set the header date.
  const deepLink = () => { if (window.location.hash === "#tab-ashtakavarga") avLoad(); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", deepLink);
  else deepLink();
})();
