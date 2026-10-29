// Sector Rotation tab (SBC_Tool-5fy.9). Read-only view of reports/sector_rotation_*.json
// via GET /api/sector_rotation. Descriptive, not graded: the pre-registered confirmatory list
// is empty. Every data value is set with textContent or as an SVG attribute, never innerHTML.

const SR_EVENT_LABEL = {
  MERCURY_RETROGRADE_START: "Mercury retrograde",
  SOLAR_ECLIPSE: "Solar eclipse",
  LUNAR_ECLIPSE: "Lunar eclipse",
  JUPITER_INGRESS: "Jupiter ingress",
  SATURN_INGRESS: "Saturn ingress",
};
const SR_RADAR_AXES = [
  ["return", "Return"],
  ["volatility", "Volatility"],
  ["win_rate", "Win rate"],
  ["sharpe", "Sharpe"],
  ["participation", "Participation"],
];
const SR_HEAT_LABEL = {
  dark_green: "Strong outperformance",
  light_green: "Mild outperformance",
  yellow: "Neutral",
  orange: "Mild underperformance",
  dark_red: "Strong underperformance",
};

let SR_DATA = null;
let SR_H = "5";

function srEl(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function srPct(x, digits = 2) {
  return x == null ? "–" : `${(x * 100).toFixed(digits)}%`;
}

function srNum(x, digits = 2) {
  return x == null ? "–" : x.toFixed(digits);
}

function srEventName(key) {
  return SR_EVENT_LABEL[key] || key;
}

function srBanner(data) {
  const confirmatory = data.confirmatory || [];
  const outcome = confirmatory.length === 0
    ? "No pre-registered edge: the confirmatory list is empty."
    : `${confirmatory.length} confirmatory hypotheses graded.`;
  return srEl("div", { class: "analog-banner", role: "note" }, [
    srEl("strong", { text: "Descriptive, not graded. " }),
    srEl("span", { text: `${outcome} Not trading advice. Breadth is not computed (phase 2).` }),
  ]);
}

function srHorizonPicker(onChange) {
  const select = srEl("select", { id: "sr-horizon", "aria-label": "Horizon in sessions" });
  for (const h of ["5", "10", "20"]) {
    const opt = srEl("option", { value: h, text: `T+${h}` });
    if (h === SR_H) opt.setAttribute("selected", "selected");
    select.appendChild(opt);
  }
  select.addEventListener("change", () => { SR_H = select.value; onChange(); });
  return srEl("label", {}, [srEl("span", { text: "Horizon " }), select]);
}

function srHeatmap(data) {
  const events = Object.keys(data.descriptive);
  const sectors = data.descriptive[events[0]][SR_H].map((r) => r.sector);
  const head = srEl("tr", {}, [srEl("th", { text: "Sector" }),
    ...events.map((ev) => srEl("th", { scope: "col", text: srEventName(ev) }))]);
  const body = sectors.map((sector) => srEl("tr", {}, [
    srEl("th", { scope: "row", text: sector }),
    ...events.map((ev) => {
      const cell = data.descriptive[ev][SR_H].find((r) => r.sector === sector);
      if (!cell) return srEl("td", { text: "–" });
      const label = cell.heat ? SR_HEAT_LABEL[cell.heat] : "No colour";
      return srEl("td", {
        class: `sr-heat sr-heat-${cell.heat || "none"}`,
        title: `${label}. Raw ${cell.n_raw}, clusters ${cell.n_clusters}`,
        text: `${srPct(cell.mean_relative)} (${cell.n_raw})`,
      });
    }),
  ]));
  return srEl("section", { class: "panel" }, [
    srEl("div", { class: "panel-head" }, [
      srEl("h2", { text: `Sector heatmap, T+${SR_H}` }),
      srEl("span", { class: "panel-sub", text: "Mean sector return minus NIFTY, per event. Count in brackets. Descriptive, not graded." }),
    ]),
    srEl("div", { class: "sr-scroll" }, [srEl("table", { class: "sr-table" }, [srEl("thead", {}, [head]), srEl("tbody", {}, body)])]),
    srEl("p", { class: "sr-legend", text: "Colours: " + Object.values(SR_HEAT_LABEL).join(" · ") + "." }),
  ]);
}

function srRotationMatrix(data) {
  const rows = Object.keys(data.rotation).map((ev) => {
    const sectors = data.descriptive[ev][SR_H];
    const strongest = sectors[0] ? sectors[0].sector : "–";
    const weakest = sectors.length ? sectors[sectors.length - 1].sector : "–";
    const block = data.rotation[ev][SR_H];
    const labels = Object.entries(block.labels).map(([k, v]) => `${k} ${v}`).join(", ") || "–";
    return srEl("tr", {}, [
      srEl("th", { scope: "row", text: srEventName(ev) }),
      srEl("td", { text: strongest }),
      srEl("td", { text: weakest }),
      srEl("td", { text: labels }),
      srEl("td", { text: String(block.occurrences) }),
    ]);
  });
  return srEl("section", { class: "panel" }, [
    srEl("div", { class: "panel-head" }, [
      srEl("h2", { text: `Rotation matrix, T+${SR_H}` }),
      srEl("span", { class: "panel-sub", text: "Strongest and weakest sector by mean relative return; pattern labels over the top five. Descriptive, not graded." }),
    ]),
    srEl("div", { class: "sr-scroll" }, [srEl("table", { class: "sr-table" }, [
      srEl("thead", {}, [srEl("tr", {}, ["Event", "Strongest", "Weakest", "Pattern labels", "Occurrences"].map((t) => srEl("th", { scope: "col", text: t })))]),
      srEl("tbody", {}, rows),
    ])]),
  ]);
}

function srRadar(data) {
  const events = Object.keys(data.event_summary);
  const size = 260, cx = size / 2, cy = size / 2, radius = 100;
  const axes = SR_RADAR_AXES;
  // Each axis is scaled 0..1 across events, so the shape compares events against each other.
  const scaled = {};
  for (const [key] of axes) {
    const values = events.map((ev) => data.event_summary[ev][SR_H][key]);
    const finite = values.filter((v) => v != null);
    const lo = finite.length ? Math.min(...finite) : 0;
    const hi = finite.length ? Math.max(...finite) : 1;
    events.forEach((ev, i) => {
      const v = values[i];
      scaled[ev] = scaled[ev] || {};
      scaled[ev][key] = v == null || hi === lo ? 0.5 : (v - lo) / (hi - lo);
    });
  }
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
  svg.setAttribute("class", "sr-radar");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `Radar chart of ${axes.length} dimensions, one polygon per event, scaled across events`);
  const point = (i, frac) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / axes.length;
    return [cx + radius * frac * Math.cos(angle), cy + radius * frac * Math.sin(angle)];
  };
  const svgEl = (tag, attrs) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    return node;
  };
  [0.5, 1].forEach((f) => svg.appendChild(svgEl("polygon", {
    points: axes.map((_, i) => point(i, f).join(",")).join(" "), class: "sr-grid",
  })));
  axes.forEach(([, label], i) => {
    const [x, y] = point(i, 1);
    svg.appendChild(svgEl("line", { x1: cx, y1: cy, x2: x, y2: y, class: "sr-grid" }));
    const t = svgEl("text", { x: point(i, 1.18)[0], y: point(i, 1.18)[1], class: "sr-axis", "text-anchor": "middle" });
    t.textContent = label;
    svg.appendChild(t);
  });
  events.forEach((ev, idx) => {
    const pts = axes.map(([key], i) => point(i, scaled[ev][key]).join(",")).join(" ");
    const poly = svgEl("polygon", { points: pts, class: `sr-shape sr-shape-${idx % 4}` });
    const title = svgEl("title", {});
    title.textContent = srEventName(ev);
    poly.appendChild(title);
    svg.appendChild(poly);
  });
  const table = srEl("table", { class: "sr-table" }, [
    srEl("thead", {}, [srEl("tr", {}, [srEl("th", { text: "Event" }), ...axes.map(([, l]) => srEl("th", { text: l }))])]),
    srEl("tbody", {}, events.map((ev) => {
      const s = data.event_summary[ev][SR_H];
      return srEl("tr", {}, [
        srEl("th", { scope: "row", text: srEventName(ev) }),
        srEl("td", { text: srPct(s.return) }),
        srEl("td", { text: srPct(s.volatility) }),
        srEl("td", { text: srPct(s.win_rate, 0) }),
        srEl("td", { text: srNum(s.sharpe) }),
        srEl("td", { text: srPct(s.participation, 0) }),
      ]);
    })),
  ]);
  return srEl("section", { class: "panel" }, [
    srEl("div", { class: "panel-head" }, [
      srEl("h2", { text: `Event radar, T+${SR_H}` }),
      srEl("span", { class: "panel-sub", text: "Five dimensions: return, volatility, win rate, Sharpe, participation. Breadth is not computed. Axes are scaled across events; values in the table." }),
    ]),
    srEl("div", { class: "sr-radar-wrap" }, [svg, srEl("div", { class: "sr-scroll" }, [table])]),
  ]);
}

function srNotes(data) {
  const short = Object.entries(data.coverage).filter(([, c]) => c.short_history).map(([k]) => k);
  const coverage = Object.entries(data.coverage).map(([k, c]) => `${k} ${c.first || "–"} to ${c.last || "–"} (${c.sessions})`);
  return srEl("section", { class: "panel" }, [
    srEl("div", { class: "panel-head" }, [srEl("h2", { text: "Coverage and inputs" })]),
    srEl("p", { text: `Out-of-sample era from ${data.era_boundary}. Short-history sectors: ${short.length ? short.join(", ") : "none"}.` }),
    srEl("p", { text: `Price rows SHA-256: ${data.input.price_sha256}` }),
    srEl("ul", { class: "sr-coverage" }, coverage.map((line) => srEl("li", { text: line }))),
  ]);
}

function srRender() {
  const root = document.getElementById("sr-root");
  if (!root || !SR_DATA) return;
  const data = SR_DATA;
  root.replaceChildren(
    srBanner(data),
    srEl("div", { class: "sr-controls" }, [srHorizonPicker(srRender)]),
    srHeatmap(data),
    srRotationMatrix(data),
    srRadar(data),
    srNotes(data),
  );
}

async function srLoad() {
  const status = document.getElementById("sr-status");
  if (SR_DATA) return;
  status.textContent = "Loading sector rotation report…";
  try {
    const r = await fetch("/api/sector_rotation");
    if (r.status === 404) {
      status.textContent = "No sector rotation report yet. The report is not run until the sector set is decided.";
      return;
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    SR_DATA = (await r.json()).data;
    status.textContent = "";
    srRender();
  } catch (err) {
    status.textContent = `Could not load the sector rotation report (${err.message}).`;
  }
}

(function srInit() {
  document.querySelector('[data-tab="tab-rotation"]')?.addEventListener("click", srLoad);
  if (window.location.hash === "#tab-rotation") srLoad();
})();
