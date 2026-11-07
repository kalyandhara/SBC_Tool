// AstroTrade Navigator tab. Shows a weighted score, its lineage and the walk-forward backtest.
// Every data value is set with textContent. Birth data is never read back: the profile list
// carries id, label and is_sample only. The add form sends birth data once, as a JSON POST
// body, then resets; nothing from it is kept in storage or the DOM.

const NAV_POLL_MS = 3000;
const NAV_TIMEOUT_MS = 20000;
// Mirrors sbc.navigator.scoring.ACTIONS, highest band first; a test pins the two together.
const NAV_BANDS = [
  ["Exceptional Setup", "Trade Aggressively"],
  ["High Probability", "Trade Normally"],
  ["Normal", "Reduce Position Size"],
  ["Very Defensive", "Stay Cash"],
  ["No Trading", "Avoid Market Entirely"],
];
const NAV_NO_EDGE = "no demonstrated edge";
const NAV_STRENGTH_NOTE = "Planet Strength is a partial index: no Shadbala/Avastha yet.";
const NAV_ACTIVE = ["queued", "running"];

const NAV = {
  open: false, booted: false, profiles: [], profileId: null,
  loadSeq: 0, pollSeq: 0, timer: null, ctl: null, runId: null,
};

function navId(id) { return document.getElementById(id); }

function navEl(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function navClear(node) { node.replaceChildren(); }
function navShown(x) { return x === null || x === undefined ? "n/a" : String(x); }
function navNum(x, digits = 2) { return typeof x === "number" ? x.toFixed(digits) : "n/a"; }
function navPct(x, digits = 2) { return typeof x === "number" ? `${(x * 100).toFixed(digits)}%` : "n/a"; }
function navSigned(x) { return typeof x === "number" ? `${x > 0 ? "+" : ""}${x.toFixed(2)}` : "n/a"; }
function navRank(x) { return typeof x === "number" ? x.toFixed(1) : "n/a (too few placebos)"; }

function navMessage(id, text, isError = false) {
  const node = navId(id);
  node.textContent = text;
  node.classList.toggle("nav-error", isError);
}

function navToken() {
  try { return localStorage.getItem("sbcApiToken"); } catch (e) { return null; }
}

// api-token.js covers writes only, and the navigator guard covers reads too.
async function navFetch(url, init = {}, ctl = new AbortController()) {
  const headers = new Headers(init.headers || {});
  const token = navToken();
  if (token) headers.set("X-API-Token", token);
  let timedOut = false;
  const limit = setTimeout(() => { timedOut = true; ctl.abort(); }, NAV_TIMEOUT_MS);
  try {
    const res = await fetch(url, { ...init, headers, signal: ctl.signal });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error((body && body.error) || `The server returned HTTP ${res.status}.`);
    if (body === null) throw new Error("The server sent an unreadable response.");
    return body;
  } catch (err) {
    if (timedOut) throw new Error("The server did not respond in time. Try again.");
    if (err instanceof TypeError) throw new Error("Could not reach the server.");
    throw err;
  } finally {
    clearTimeout(limit);
  }
}

function navTable(caption, heads, rows) {
  const table = navEl("table", { class: "nav-table" });
  if (caption) table.appendChild(navEl("caption", { text: caption }));
  table.appendChild(navEl("thead", {}, [navEl("tr", {}, heads.map((h) => navEl("th", { text: h, scope: "col" })))]));
  table.appendChild(navEl("tbody", {}, rows.map((row) => navEl("tr", {}, row.map((cell) => navEl("td", { text: navShown(cell) }))))));
  return navEl("div", { class: "nav-scroll" }, [table]);
}

function navHeading(text) { return navEl("h3", { class: "nav-heading", text }); }
function navSubheading(text) { return navEl("h4", { class: "nav-subheading", text }); }
function navNote(text) { return navEl("p", { class: "nav-note", text }); }

function navRenderChart(data) {
  const out = navId("nav-chart");
  navClear(out);
  out.appendChild(navHeading(`Chart: ${data.label}`));
  out.appendChild(navTable("", ["Point", "Sign", "Degree in sign", "Nakshatra", "Pada"],
    (data.points || []).map((p) => [p.name, p.sign, navNum(p.degree), p.nakshatra, p.pada])));
}

function navMoves(title, moves) {
  const box = navEl("div", {}, [navSubheading(title)]);
  if (!moves.length) box.appendChild(navNote("None for this day."));
  else box.appendChild(navEl("ul", { class: "nav-list" },
    moves.map((m) => navEl("li", { text: `${m.label}: ${navSigned(m.delta)} points` }))));
  return box;
}

function navFactorRows(line) {
  const rows = [["Neutral baseline", navNum(line.baseline), ""]];
  for (const f of line.factors) {
    const flags = [f.neutral ? "neutral" : "", f.note || ""].filter(Boolean).join("; ");
    rows.push([f.label, navSigned(f.contribution), flags]);
  }
  return rows;
}

function navVolNote(data) {
  if (!data.vol_neutral) return null;
  if (data.future) {
    return `Volatility is neutral: ${data.day} is after the last market session in the data `
      + `(${data.data_asof}), so its prior India VIX close does not exist yet. A neutral term `
      + "adds its baseline and no information.";
  }
  return "Volatility is neutral: the prior session's India VIX close is missing, or there is "
    + "too little VIX history before it. A neutral term adds its baseline and no information.";
}

function navRenderLineage(data) {
  const out = navId("nav-lineage");
  const lines = data.lineage.contributions;
  const sum = lines.reduce((total, c) => total + Math.round(c.contribution * 100), 0) / 100;
  navClear(out);
  out.appendChild(navHeading("Score lineage"));
  out.appendChild(navEl("div", { class: "nav-moves" }, [
    navMoves("Raised the score", data.lineage.raised),
    navMoves("Lowered the score", data.lineage.lowered),
  ]));
  const rows = lines.map((c) => [c.label, navNum(c.weight), navNum(c.raw), navNum(c.contribution)]);
  rows.push(["Sum of contributions", "", "", navNum(sum)]);
  out.appendChild(navTable("Weighted contributions", ["Term", "Weight", "Term value", "Points"], rows));
  for (const line of lines) {
    if (line.adjustment || !line.factors) continue;
    out.appendChild(navEl("details", { class: "nav-details" }, [
      navEl("summary", { text: `${line.label}: ${navNum(line.contribution)} points` }),
      navTable("", ["Factor", "Points", "Flags"], navFactorRows(line)),
    ]));
  }
}

function navRenderScore(data) {
  const out = navId("nav-score");
  navClear(out);
  out.appendChild(navHeading(`Weighted score for ${data.day}`));
  out.appendChild(navEl("div", { class: "nav-score-row" }, [
    navEl("span", { class: "nav-score-value", text: navShown(data.score) }),
    navEl("div", {}, [
      navEl("div", { class: "nav-band", text: data.band }),
      navEl("div", {}, [
        navEl("strong", { text: `Action label: ${data.action}` }),
        navEl("span", { class: "nav-tag", text: data.status }),
      ]),
    ]),
  ]));
  out.appendChild(navNote(`${data.label}. Weights ${data.weights_version}. Market data through ${data.data_asof}.`));
  out.appendChild(navNote(data.disclaimer));
  if (data.future) {
    out.appendChild(navNote(`${data.day} has no finished session yet, so this is a forward score: market inputs stop at ${data.data_asof}.`));
  }
  const vol = navVolNote(data);
  if (vol) out.appendChild(navNote(vol));
  out.appendChild(navNote(NAV_STRENGTH_NOTE));
  navRenderLineage(data);
}

function navBandRow(results, name) { return (results.bands || {})[name] || {}; }
function navEventWord(insufficient) { return insufficient === false ? "enough events" : "insufficient events"; }

function navVerdictText(results) {
  if (results.verdict === NAV_NO_EDGE) {
    return `Verdict: ${NAV_NO_EDGE}. This run does not support acting on the action labels.`;
  }
  return `Verdict: ${results.verdict}. Bands: ${(results.candidate_bands || []).join(", ")}. `
    + "This is research evidence on hand-set weights, not validation.";
}

// Every band gets a row, so an empty extreme band reads as 0 days rather than disappearing.
function navOccupancy(results) {
  const minimum = (results.params || {}).min_events;
  const rows = NAV_BANDS.map(([name, action]) => {
    const band = navBandRow(results, name);
    const days = (band.session_stats || {}).days || 0;
    return [name, action, `${days} days`, band.events || 0,
      navEventWord(days ? band.insufficient : true), band.verdict || NAV_NO_EDGE];
  });
  return navTable(`Band occupancy, beside action labels. Bands are not rescaled. Minimum ${navShown(minimum)} events; each band's event count comes from its strongest horizon.`,
    ["Band", "Action label", "Days", "Events", "Event count", "Verdict"], rows);
}

function navSessions(results) {
  const horizons = (results.params || {}).horizons || [];
  const horizon = (navBandRow(results, NAV_BANDS[0][0]).session_stats || {}).horizon;
  const rows = NAV_BANDS.map(([name]) => {
    const band = navBandRow(results, name);
    const s = band.session_stats || {};
    return [name, s.days || 0, navPct(s.vol), navPct(s.max_dd), navPct(s.hit, 1), navPct(s.win, 1),
      navNum(s.sharpe), navPct(band.mean_oc), ...horizons.map((h) => navPct(band[`mean_oo_${h}`]))];
  });
  return navTable(`session_stats at the ${navShown(horizon)}-session horizon, net of cost`,
    ["Band", "Days", "Vol", "Max drawdown", "Hit", "Win", "Sharpe", "Mean open to close",
      ...horizons.map((h) => `Mean open to open, ${h} sessions`)], rows);
}

function navHorizons(results) {
  const rows = [];
  for (const [name] of NAV_BANDS) {
    for (const [horizon, e] of Object.entries(navBandRow(results, name).by_horizon || {})) {
      rows.push([name, horizon, e.events, navEventWord(e.insufficient), navPct(e.excess),
        navPct(e.excess_vs_control), e.beats_control ? "yes" : "no", navNum(e.p, 3), navNum(e.q, 3),
        e.active_folds, navPct(e.fold_pos, 0), navRank(e.full_pct), navRank(e.natal_pct),
        e.natal_band_days, e.verdict]);
    }
  }
  return navTable("Per-horizon results and decile-matched controls",
    ["Band", "Horizon", "Events", "Event count", "Net excess", "Excess vs control", "Beats control",
      "p", "q", "Active folds", "Positive folds", "Full percentile", "Natal percentile",
      "Natal band days", "Verdict"], rows);
}

function navFolds(run) {
  const horizons = (run.results.params || {}).horizons || [];
  const rows = (run.folds || []).map((fold) => [fold.year, fold.sessions, ...NAV_BANDS.map(([name]) => {
    const band = (fold.bands || {})[name] || {};
    return [`${band.days || 0} days`, ...horizons.map((h) => `${h}: ${navPct(band[`excess_${h}`])}`)].join(" / ");
  })]);
  if (!rows.length) return navNote("No fold results: too few scored sessions.");
  return navTable("Walk-forward folds: days in band, then net excess by horizon",
    ["Test year", "Sessions", ...NAV_BANDS.map(([name]) => name)], rows);
}

function navPlacebo(results) {
  const p = results.placebo || {};
  const box = navEl("div", {}, [navSubheading("Placebo charts")]);
  box.appendChild(navNote(`${navShown(p.n)} of ${navShown(p.requested)} random charts ran in ${navNum(p.seconds, 0)} seconds, seed ${navShown(p.seed)}.`));
  if (p.reduced) box.appendChild(navNote("The placebo count was reduced to fit the time limit."));
  box.appendChild(navNote(`Top band ${navShown(p.top_band)} at the ${navShown(p.horizon)}-session horizon: full-score percentile ${navRank(p.full_pct)}, natal-only percentile ${navRank(p.natal_pct)}.`));
  const rows = [];
  for (const [name] of NAV_BANDS) {
    for (const [horizon, pct] of Object.entries((p.by_band || {})[name] || {})) {
      rows.push([name, horizon, navRank(pct.full), navRank(pct.natal)]);
    }
  }
  box.appendChild(navTable("", ["Band", "Horizon", "Full-score percentile", "Natal-only percentile"], rows));
  return box;
}

function navCandidates(results) {
  const list = results.candidates || [];
  if (!list.length) return navNote("Candidates: none. No band and horizon met every condition.");
  return navEl("ul", { class: "nav-list" }, list.map((c) => navEl("li", {
    text: `Candidate: ${c.band}, ${c.horizon}-session horizon, q ${navNum(c.q, 3)}`,
  })));
}

function navRenderRun(run) {
  const out = navId("nav-backtest-out");
  const results = run.results;
  const params = results.params || {};
  navClear(out);
  out.appendChild(run.is_sample
    ? navEl("p", { class: "nav-banner", text: "Sample chart: pipeline check only. A sample chart can never qualify as an edge." })
    : navNote(run.label));
  const edge = results.verdict !== NAV_NO_EDGE;
  out.appendChild(navEl("p", { class: edge ? "nav-verdict nav-verdict-edge" : "nav-verdict", text: navVerdictText(results) }));
  out.appendChild(navNote(run.disclaimer));
  out.appendChild(navNote(`${navShown(run.instrument)}, ${navShown(results.sessions_scored)} sessions scored, data through ${navShown(run.data_asof)}, weights ${navShown(run.weights_version)}, cost ${navShown(params.cost_bps)} bps, ${navShown(results.vol_neutral_days)} sessions with neutral Volatility.`));
  out.append(navOccupancy(results), navSessions(results), navHorizons(results), navFolds(run),
    navPlacebo(results), navCandidates(results), navSubheading("Notes"),
    navEl("ul", { class: "nav-list" }, (results.notes || []).map((n) => navEl("li", { text: n }))));
}

function navStopPolling() {
  NAV.pollSeq += 1;
  clearTimeout(NAV.timer);
  NAV.timer = null;
  if (NAV.ctl) NAV.ctl.abort();
  NAV.ctl = null;
}

function navEndRun(message, isError) {
  navStopPolling();
  NAV.runId = null;
  navId("nav-run").disabled = false;
  navMessage("nav-backtest-status", message, isError);
}

function navHandleRun(run) {
  if (NAV_ACTIVE.includes(run.status)) {
    navMessage("nav-backtest-status", `Backtest ${run.id} is ${run.status}. Checking every 3 seconds; a full run can take about 10 minutes.`);
    NAV.timer = setTimeout(navPoll, NAV_POLL_MS);
  } else if (run.status === "done" && run.results) {
    navEndRun(`Backtest ${run.id} finished.`, false);
    try {
      navRenderRun(run);
    } catch (err) {
      navMessage("nav-backtest-status", "The backtest finished, but its results could not be displayed.", true);
    }
  } else if (run.status === "done") {
    navEndRun(`Backtest ${run.id} finished with no results.`, true);
  } else {
    navEndRun(run.error || "The backtest failed.", true);
  }
}

// The next timer is set only after this response lands, so one request is in flight at a time.
async function navPoll() {
  const seq = NAV.pollSeq;
  const ctl = new AbortController();
  NAV.ctl = ctl;
  try {
    const run = await navFetch(`/api/navigator/backtest/${NAV.runId}`, {}, ctl);
    if (seq === NAV.pollSeq) navHandleRun(run);
  } catch (err) {
    if (seq === NAV.pollSeq) navEndRun(err.message, true);
  }
}

async function navStartRun() {
  const seq = NAV.loadSeq;
  navStopPolling();
  navId("nav-run").disabled = true;
  navClear(navId("nav-backtest-out"));
  navMessage("nav-backtest-status", "Starting the backtest.");
  try {
    const started = await navFetch("/api/navigator/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: NAV.profileId }),
    });
    if (seq !== NAV.loadSeq) return;
    NAV.runId = started.run_id;
    if (NAV.open) navPoll();
  } catch (err) {
    if (seq === NAV.loadSeq) navEndRun(err.message, true);
  }
}

function navSectionError(id, title, err) {
  const out = navId(id);
  navClear(out);
  out.append(navHeading(title), navEl("p", { class: "nav-error", text: err.message }));
}

async function navLoadProfile() {
  const seq = ++NAV.loadSeq;
  const id = NAV.profileId;
  const profile = NAV.profiles.find((p) => p.id === id);
  navStopPolling();
  NAV.runId = null;
  navId("nav-run").disabled = false;
  navId("nav-sample-banner").hidden = !(profile && profile.is_sample);
  navClear(navId("nav-lineage"));
  navClear(navId("nav-backtest-out"));
  navMessage("nav-backtest-status", "");
  navId("nav-chart").textContent = "Loading chart.";
  navId("nav-score").textContent = "Loading score.";
  const load = async (url, render, target, title) => {
    try {
      const data = await navFetch(url);
      if (seq === NAV.loadSeq) render(data);
    } catch (err) {
      if (seq === NAV.loadSeq) navSectionError(target, title, err);
    }
  };
  await Promise.all([
    load(`/api/navigator/chart?profile_id=${id}`, navRenderChart, "nav-chart", "Chart"),
    load(`/api/navigator/score?profile_id=${id}`, navRenderScore, "nav-score", "Weighted score"),
    navLoadLatest(seq, id),
  ]);
}

// A 404 means no run exists for this profile yet, so any failure just leaves the section empty.
async function navLoadLatest(seq, id) {
  let run;
  try {
    run = await navFetch(`/api/navigator/backtest/latest?profile_id=${id}`);
  } catch (err) {
    return;
  }
  if (seq !== NAV.loadSeq || NAV.runId !== null) return;
  if (NAV_ACTIVE.includes(run.status)) {
    NAV.runId = run.id;
    navId("nav-run").disabled = true;
    if (NAV.open) navHandleRun(run);
  } else if (run.status === "done" && run.results) {
    navMessage("nav-backtest-status", `Latest saved backtest: run ${run.id}, market data through ${navShown(run.data_asof)}. Run again to refresh it.`);
    try {
      navRenderRun(run);
    } catch (err) {
      navMessage("nav-backtest-status", "The saved backtest could not be displayed.", true);
    }
  } else {
    navMessage("nav-backtest-status", `Latest saved backtest: run ${run.id} ${run.status}, market data through ${navShown(run.data_asof)}.`, run.status === "failed");
  }
}

// Values are read by input type, sent once in the body, and the form is then reset.
function navFormBody(form) {
  const body = {};
  for (const input of form.querySelectorAll("input[name]")) {
    const value = input.value.trim();
    if (input.type === "number") body[input.name] = value === "" ? null : Number(value);
    else if (input.type === "time") body[input.name] = /^\d\d:\d\d$/.test(value) ? `${value}:00` : value;
    else if (value !== "" || input.required) body[input.name] = value;
  }
  return body;
}

async function navSubmitProfile(event) {
  event.preventDefault();
  const form = event.target;
  const save = navId("nav-f-save");
  save.disabled = true;
  navMessage("nav-form-status", "Saving the chart.");
  try {
    const created = await navFetch("/api/navigator/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(navFormBody(form)),
    });
    form.reset();
    NAV.profiles.push({ id: created.id, label: created.label, is_sample: false });
    const select = navId("nav-profile");
    select.appendChild(navEl("option", { value: String(created.id), text: created.label }));
    select.value = String(created.id);
    NAV.profileId = created.id;
    navMessage("nav-form-status", `Saved as profile ${created.id} and selected. It has no backtest yet.`);
    await navLoadProfile();
  } catch (err) {
    navMessage("nav-form-status", err.message, true);
  } finally {
    save.disabled = false;
  }
}

async function navBoot() {
  navMessage("nav-status", "Loading profiles.");
  navId("nav-run").disabled = true;
  try {
    const data = await navFetch("/api/navigator/profile");
    NAV.profiles = data.profiles || [];
    if (!NAV.profiles.length) throw new Error("No profiles are saved.");
    const select = navId("nav-profile");
    navClear(select);
    for (const p of NAV.profiles) {
      select.appendChild(navEl("option", { value: String(p.id), text: p.is_sample ? `${p.label} (sample)` : p.label }));
    }
    NAV.profileId = NAV.profiles[0].id;
    navMessage("nav-status", "");
    await navLoadProfile();
  } catch (err) {
    NAV.booted = false;  // the next visit to the tab retries
    navMessage("nav-status", err.message, true);
  }
}

function navSync() {
  const open = navId("tab-navigator").classList.contains("active");
  if (open === NAV.open) return;
  NAV.open = open;
  if (!open) { navStopPolling(); return; }
  if (!NAV.booted) { NAV.booted = true; navBoot(); return; }
  if (NAV.runId !== null) navPoll();
}

(function navInit() {
  const pane = navId("tab-navigator");
  if (!pane) return;
  new MutationObserver(navSync).observe(pane, { attributes: true, attributeFilter: ["class"] });
  navId("nav-run").addEventListener("click", navStartRun);
  navId("nav-profile-form").addEventListener("submit", navSubmitProfile);
  navId("nav-profile").addEventListener("change", (e) => {
    NAV.profileId = Number(e.target.value);
    navLoadProfile();
  });
  navSync();
})();
