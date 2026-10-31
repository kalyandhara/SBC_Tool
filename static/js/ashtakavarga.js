// Ashtakavarga tab (spec .internal/specs/2026-10-31-ashtakavarga-design.md). Live view of
// GET /api/ashtakavarga: an anchor's natal BAV/SAV and the signs the planets transit at
// 09:15 IST. Descriptive, not validated. Every data value is set with textContent, never as markup.

const AV_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"];
const AV_MODES = [["auto", "Auto"], ["classical", "Classical (with Lagna)"], ["seven", "7 planets (no Lagna)"]];
const AV_STATE = { anchor: "nifty", lagna_mode: "auto", date: "", dateTouched: false };
let AV_SEQ = 0;

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

function avSelect(label, options, value, onChange) {
  const select = avEl("select", { "aria-label": label });
  for (const [v, text] of options) {
    const opt = avEl("option", { value: v, text });
    if (v === value) opt.selected = true;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => onChange(select.value));
  return avEl("label", {}, [avEl("span", { text: `${label} ` }), select]);
}

function avDateInput(value) {
  const input = avEl("input", { type: "date", min: "1900-01-01", max: "2100-12-31", "aria-label": "Transit date" });
  input.value = value;
  input.addEventListener("change", () => {
    if (input.value) { AV_STATE.date = input.value; AV_STATE.dateTouched = true; avLoad(); }
  });
  return avEl("label", {}, [avEl("span", { text: "Transit date " }), input]);
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
  const head = avEl("tr", {}, [avEl("th", { text: `Planet (/${n.max_per_sign})` })]);
  data.signs.forEach((s) => head.appendChild(avEl("th", { text: s.slice(0, 3), title: s })));
  const body = avEl("tbody");
  for (const p of AV_PLANETS) {
    const row = avEl("tr", {}, [avEl("th", { text: p })]);
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
  const savRow = avEl("tr", { class: "av-sav" }, [avEl("th", { text: "SAV" })]);
  for (const v of n.sav) {
    const cell = avEl("td", { text: String(v) });
    cell.style.setProperty("--av-heat", (hi === lo ? 0.5 : (v - lo) / (hi - lo)).toFixed(2));
    savRow.appendChild(cell);
  }
  body.appendChild(savRow);
  return avEl("table", { class: "data-table av-grid" }, [avEl("thead", {}, [head]), body]);
}

function avTransitTable(data) {
  const cols = ["Planet", "Sign", `BAV (/${data.natal.max_per_sign})`, "SAV"];
  const head = avEl("tr", {}, cols.map((t) => avEl("th", { text: t })));
  const body = avEl("tbody");
  for (const p of AV_PLANETS) {
    const t = data.transit[p];
    body.appendChild(avEl("tr", {}, [p, t.sign, String(t.bav_points), String(t.sav_points)]
      .map((x) => avEl("td", { text: x }))));
  }
  return avEl("div", {}, [
    avEl("h3", { text: `Transits on ${data.date}, as of ${data.transit_time}` }),
    avEl("table", { class: "data-table av-transit-table" }, [avEl("thead", {}, [head]), body]),
  ]);
}

function avRender(data) {
  document.getElementById("av-root").replaceChildren(
    avEl("div", { class: "av-controls" }, [
      avSelect("Anchor", data.anchors.map((a) => [a, a]), data.anchor, (v) => { AV_STATE.anchor = v; avLoad(); }),
      avSelect("Lagna", AV_MODES, AV_STATE.lagna_mode, (v) => { AV_STATE.lagna_mode = v; avLoad(); }),
      avDateInput(data.date),
    ]),
    avEl("p", { class: "panel-sub", text: `${data.anchor_name}: ${data.anchor_note}` }),
    avBanner(data),
    avGrid(data),
    avTransitTable(data),
  );
}

async function avLoad() {
  const status = document.getElementById("av-status");
  if (!AV_STATE.date) AV_STATE.date = document.getElementById("date")?.value || "";
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
  } catch (err) {
    if (seq === AV_SEQ) status.textContent = `Could not load Ashtakavarga (${err.message}).`;
  }
}

(function avInit() {
  document.querySelector('[data-tab="tab-ashtakavarga"]')?.addEventListener("click", avLoad);
  // Follow the header session date until the tab's own date picker is used.
  document.getElementById("date")?.addEventListener("change", (e) => {
    if (AV_STATE.dateTouched || !e.target.value) return;
    AV_STATE.date = e.target.value;
    if (document.getElementById("tab-ashtakavarga")?.classList.contains("active")) avLoad();
  });
  if (window.location.hash === "#tab-ashtakavarga") avLoad();
})();
