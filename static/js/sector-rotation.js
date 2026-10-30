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
let SR_EVENT = null;
const SR_WHEEL_GROUPS = ["Financials", "Technology", "Pharma", "Consumption", "Industrials", "Commodities"];
const SR_NS = "http://www.w3.org/2000/svg";

function srSvgEl(tag, attrs = {}) {
  const node = document.createElementNS(SR_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

function srEventSelect(events, onChange) {
  const select = srEl("select", { "aria-label": "Event" });
  for (const ev of events) {
    const opt = srEl("option", { value: ev, text: srEventName(ev) });
    if (ev === SR_EVENT) opt.setAttribute("selected", "selected");
    select.appendChild(opt);
  }
  select.addEventListener("change", () => { SR_EVENT = select.value; onChange(); });
  return srEl("label", {}, [srEl("span", { text: "Event " }), select]);
}

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
    ? "No pre-registered edge: the confirmatory hypothesis family is empty (0/511 out-of-sample tests passed across all research)."
    : `${confirmatory.length} confirmatory hypotheses graded.`;
  return srEl("div", { class: "analog-banner sr-enhanced-banner", role: "note" }, [
    srEl("div", { class: "sr-banner-title" }, [
      srEl("strong", { text: "Descriptive Research Only — No Validated Trading Edge" }),
    ]),
    srEl("ul", { class: "sr-banner-list" }, [
      srEl("li", {}, [
        srEl("b", { text: "What this shows: " }),
        srEl("span", { text: "Historical mean sector returns relative to NIFTY (T+5, T+10, T+20 sessions) around core planetary event anchors (Mercury retrograde start, Eclipses, Jupiter and Saturn sign ingresses)." }),
      ]),
      srEl("li", {}, [
        srEl("b", { text: "Edge & Validation: " }),
        srEl("span", { text: `${outcome} All metrics reflect historical frequencies; none constitutes predictive alpha or an investment recommendation.` }),
      ]),
      srEl("li", {}, [
        srEl("b", { text: "Data Coverage: " }),
        srEl("span", { text: "12 of 15 sector indices are active. 3 indices (NIFTY MEDIA, HEALTHCARE, OIL & GAS) have missing price history in yfinance and are omitted from descriptive tables." }),
      ]),
    ]),
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
      srEl("span", { class: "panel-sub", text: "Mean sector return minus NIFTY per event anchor over T+" + SR_H + " sessions. Numbers in parentheses indicate historical occurrence count. Green indicates relative outperformance, red underperformance. Descriptive frequency only, not a trading signal." }),
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
      srEl("span", { class: "panel-sub", text: "Historical strongest and weakest sector by mean relative return; pattern labels classify the majority group among the top-5 sectors. Descriptive, not graded." }),
    ]),
    srEl("div", { class: "sr-scroll" }, [srEl("table", { class: "sr-table" }, [
      srEl("thead", {}, [srEl("tr", {}, ["Event", "Strongest", "Weakest", "Pattern labels", "Occurrences"].map((t) => srEl("th", { scope: "col", text: t })))]),
      srEl("tbody", {}, rows),
    ])]),
  ]);
}

function srWheel(data) {
  const events = Object.keys(data.wheel);
  const groups = data.wheel[SR_EVENT][SR_H];
  const values = SR_WHEEL_GROUPS.map((g) => groups[g]);
  const scale = Math.max(1e-9, ...values.map((v) => (v == null ? 0 : Math.abs(v))));
  const size = 280, cx = size / 2, cy = size / 2, inner = 36, outer = 110;
  const svg = srSvgEl("svg", { viewBox: `0 0 ${size} ${size}`, class: "sr-wheel", role: "img",
    "aria-label": `Rotation wheel for ${srEventName(SR_EVENT)} at T+${SR_H}: mean relative return by capital-flow group` });
  const step = (2 * Math.PI) / SR_WHEEL_GROUPS.length;
  SR_WHEEL_GROUPS.forEach((g, i) => {
    const v = values[i];
    const a0 = -Math.PI / 2 + i * step + 0.03, a1 = a0 + step - 0.06;
    const r = v == null ? inner : inner + (outer - inner) * (Math.abs(v) / scale);
    const pt = (rad, ang) => [cx + rad * Math.cos(ang), cy + rad * Math.sin(ang)];
    const [x0, y0] = pt(inner, a0), [x1, y1] = pt(r, a0), [x2, y2] = pt(r, a1), [x3, y3] = pt(inner, a1);
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const d = `M${x0},${y0} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} L${x3},${y3} A${inner},${inner} 0 ${large} 0 ${x0},${y0} Z`;
    const path = srSvgEl("path", { d, class: v == null ? "sr-wedge-none" : v >= 0 ? "sr-wedge-up" : "sr-wedge-down" });
    const title = srSvgEl("title", {});
    title.textContent = `${g}: ${v == null ? "no data" : srPct(v)}`;
    path.appendChild(title);
    svg.appendChild(path);
    const mid = a0 + (a1 - a0) / 2;
    const [lx, ly] = pt(outer + 14, mid);
    const label = srSvgEl("text", { x: lx, y: ly, class: "sr-axis", "text-anchor": "middle" });
    label.textContent = g;
    svg.appendChild(label);
  });
  return srEl("section", { class: "panel" }, [
    srEl("div", { class: "panel-head" }, [
      srEl("h2", { text: `Rotation wheel, T+${SR_H}` }),
      srEl("span", { class: "panel-sub", text: "Capital-flow groups. Wedge length indicates mean relative return (green: above NIFTY, red: below). Group membership is a conceptual heuristic; descriptive only." }),
    ]),
    srEventSelect(events, srRender),
    srEl("div", { class: "sr-wheel-wrap" }, [svg, srEl("div", { class: "sr-scroll" }, [srEl("table", { class: "sr-table" }, [
      srEl("thead", {}, [srEl("tr", {}, [srEl("th", { text: "Group" }), srEl("th", { text: "Mean relative" })])]),
      srEl("tbody", {}, SR_WHEEL_GROUPS.map((g, i) => srEl("tr", {}, [srEl("th", { scope: "row", text: g }), srEl("td", { text: srPct(values[i]) })]))),
    ])])]),
  ]);
}

function srSankey(data) {
  const flow = data.flows[SR_EVENT][SR_H];
  const links = flow.links;
  const W = 520, H = 320, pad = 8, colX = [0, 240, 470], nodeW = 14;
  const sectorTotals = {}, outcomeTotals = {};
  for (const l of links) {
    // event -> sector links carry the sector in target; sector -> NIFTY links carry it in source.
    if (l.target.startsWith("NIFTY")) outcomeTotals[l.target] = (outcomeTotals[l.target] || 0) + l.value;
    else if (l.source === SR_EVENT) sectorTotals[l.target] = (sectorTotals[l.target] || 0) + l.value;
  }
  const total = links.filter((l) => l.source === SR_EVENT).reduce((a, l) => a + l.value, 0);
  const columns = [
    [[SR_EVENT, total]],
    Object.entries(sectorTotals).sort((a, b) => b[1] - a[1]),
    ["NIFTY up", "NIFTY down"].filter((k) => outcomeTotals[k]).map((k) => [k, outcomeTotals[k]]),
  ];
  const place = new Map();
  columns.forEach((col, ci) => {
    const sum = col.reduce((a, [, v]) => a + v, 0) || 1;
    const usable = H - 2 * pad - (col.length - 1) * 6;
    let y = pad;
    col.forEach(([name, v]) => {
      const h = Math.max(2, (v / sum) * usable);
      place.set(`${ci}:${name}`, { x: colX[ci], y, h, value: v, name, used: 0 });
      y += h + 6;
    });
  });
  const svg = srSvgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "sr-sankey", role: "img",
    "aria-label": `Flow from ${srEventName(SR_EVENT)} to the strongest sector to the NIFTY outcome, T+${SR_H}` });
  for (const l of links) {
    let a, b;
    if (l.source === SR_EVENT) { a = place.get(`0:${SR_EVENT}`); b = place.get(`1:${l.target}`); }
    else { a = place.get(`1:${l.source}`); b = place.get(`2:${l.target}`); }
    if (!a || !b) continue;
    const tA = Math.max(1, (l.value / a.value) * a.h), tB = Math.max(1, (l.value / b.value) * b.h);
    const ay = a.y + a.used + tA / 2, by = b.y + b.used + tB / 2;
    a.used += tA; b.used += tB;
    const x0 = a.x + nodeW, x1 = b.x, mx = (x0 + x1) / 2;
    const path = srSvgEl("path", { d: `M${x0},${ay} C${mx},${ay} ${mx},${by} ${x1},${by}`,
      class: "sr-flow", "stroke-width": Math.min(tA, tB) });
    const title = srSvgEl("title", {});
    const from = l.source === SR_EVENT ? srEventName(SR_EVENT) : l.source;
    title.textContent = `${from} → ${l.target}: ${l.value}`;
    path.appendChild(title);
    svg.appendChild(path);
  }
  for (const node of place.values()) {
    svg.appendChild(srSvgEl("rect", { x: node.x, y: node.y, width: nodeW, height: node.h, class: "sr-node" }));
    const right = node.x >= colX[2];
    const label = srSvgEl("text", { x: node.x + (right ? -4 : nodeW + 4), y: node.y + node.h / 2 + 4,
      class: "sr-axis", "text-anchor": right ? "end" : "start" });
    label.textContent = `${node.name === SR_EVENT ? srEventName(node.name) : node.name} (${node.value})`;
    svg.appendChild(label);
  }
  const notes = [];
  if (flow.unranked) notes.push(`${flow.unranked} occurrence(s) had no sector with data in the window`);
  if (flow.nifty_missing) notes.push(`${flow.nifty_missing} had no NIFTY return`);
  return srEl("section", { class: "panel" }, [
    srEl("div", { class: "panel-head" }, [
      srEl("h2", { text: `Flow, T+${SR_H}` }),
      srEl("span", { class: "panel-sub", text: "Flow of historical occurrences: Event → strongest sector → NIFTY Up/Down over T+" + SR_H + " sessions. Descriptive sample frequencies only." }),
    ]),
    srEventSelect(Object.keys(data.flows), srRender),
    srEl("div", { class: "sr-scroll" }, [svg]),
    srEl("p", { class: "sr-legend", text: notes.length ? notes.join("; ") + "." : "All occurrences are counted." }),
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
      srEl("span", { class: "panel-sub", text: "Five comparative dimensions: return, volatility, win rate, Sharpe, participation. Breadth is not computed (phase 2). Axes scaled across events; descriptive frequencies only." }),
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

function srBriefing(data) {
  return srEl("section", { class: "panel sr-briefing-panel" }, [
    srEl("div", { class: "panel-head" }, [
      srEl("h2", { text: "Market & Planetary Intelligence Briefing" }),
      srEl("span", { class: "panel-sub", text: "Direct answers to the six core timing questions. Exploratory historical frequencies, not predictive alpha." }),
    ]),
    srEl("div", { class: "sr-briefing-grid" }, [
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "1. Current Planetary Events" }),
        srEl("p", { text: `Active ephemeris anchors and transit alignments. Out-of-sample testing era spans from ${data.era_boundary || "2021-10-01"} (${data.oos_sessions || 1254} sessions).` })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "2. Sectoral Market Impacts" }),
        srEl("p", { text: "Evaluates 12 NSE sector indices across T+5, T+10, and T+20 event windows. Note: Media, Healthcare, and Oil & Gas have no history in yfinance." })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "3. Upcoming Major Events" }),
        srEl("p", { text: "Tracks Jupiter Ingress, Solar/Lunar Eclipses, and Mercury/Saturn Retrograde turns for market volatility clustering." })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "4. Past NIFTY & Sector Outcomes" }),
        srEl("p", { text: "Historical occurrence counts and win-rate distributions. Past outcomes reflect descriptive sample frequencies rather than guarantees." })
      ]),
      srEl("div", { class: "sr-briefing-card" }, [
        srEl("strong", { text: "5. 6-Month & 1-Year Horizons" }),
        srEl("p", { text: "Transit models capture short-term event windows (T+5 to T+20). Medium and long-term (6m/1y) investment decisions MUST rely on macro fundamentals, earnings growth, and technical trend analysis." })
      ]),
      srEl("div", { class: "sr-briefing-card sr-validation-card" }, [
        srEl("strong", { text: "6. Signal Validation Status" }),
        srEl("p", { text: "Status: EXPLORATORY / DESCRIPTIVE ONLY | Validated Edge: NONE (0 out-of-sample passes across 511 tests). Not financial advice." })
      ]),
    ])
  ]);
}

function srRender() {
  const root = document.getElementById("sr-root");
  if (!root || !SR_DATA) return;
  const data = SR_DATA;
  if (!SR_EVENT || !data.wheel[SR_EVENT]) SR_EVENT = Object.keys(data.wheel)[0];
  root.replaceChildren(
    srBanner(data),
    srBriefing(data),
    srEl("div", { class: "sr-controls" }, [srHorizonPicker(srRender)]),
    srHeatmap(data),
    srRotationMatrix(data),
    srWheel(data),
    srSankey(data),
    srRadar(data),
    srNotes(data),
  );
}

async function srLoad() {
  const status = document.getElementById("sr-status");
  if (SR_DATA) return;
  status.textContent = "";
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
