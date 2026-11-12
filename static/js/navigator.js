// AstroTrade Navigator tab. Shows a weighted score, its lineage and the walk-forward backtest.
// Every data value is set with textContent. Birth data is never read back: the profile list
// carries id, label and is_sample only. The add form sends birth data once, as a JSON POST
// body, then resets; nothing from it is kept in storage or the DOM.

const NAV_POLL_MS = 3000;
const NAV_TIMEOUT_MS = 20000;
// A cold similar-dates run takes several seconds; the server's own lock answers 202 {busy: true} if busy.
const NAV_ANALOG_TIMEOUT_MS = 120000;
const NAV_NEXT5 = "open to open, 5 sessions, as in the backtest";
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
  analogSeq: 0, analogCtl: null, analogFor: null,
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
async function navFetch(url, init = {}, ctl = new AbortController(), timeoutMs = NAV_TIMEOUT_MS) {
  const headers = new Headers(init.headers || {});
  const token = navToken();
  if (token) headers.set("X-API-Token", token);
  let timedOut = false;
  const limit = setTimeout(() => { timedOut = true; ctl.abort(); }, timeoutMs);
  try {
    const res = await fetch(url, { ...init, headers, signal: ctl.signal });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const err = new Error((body && body.error) || `The server returned HTTP ${res.status}.`);
      err.status = res.status;
      throw err;
    }
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
        navEl("span", { class: "nav-tag", text: (data.latest_verdict || {}).text || "verdict unavailable" }),
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
    const occ = band.occupancy || {};
    return [name, action, `${days} days`, occ.events || 0,
      navEventWord(days ? occ.insufficient : true), band.verdict || NAV_NO_EDGE];
  });
  return navTable(`Band occupancy, beside action labels. Bands are not rescaled. Minimum ${navShown(minimum)} events; event counts are for the first horizon; per-horizon counts are in the horizon table.`,
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

// ---- Similar past dates ----------------------------------------------------------------

function navShare(x) { return typeof x === "number" ? `${(x * 100).toFixed(1)}%` : null; }

function navRandomSentence(prefix, n, share) {
  const pct = navShare(share);
  if (pct === null) return `${prefix}: n/a.`;
  return `${prefix}: random sets of ${n} did at least this well ${pct} of the time.`;
}

function navBaselineText(title, b) {
  if (!b) return `${title}: n/a.`;
  return `${title}: ${navShown(b.n)} sessions, win ratio ${navPct(b.win_ratio, 1)}, average next-5 ${navPct(b.mean_next5)}.`;
}

function navSectors(o) {
  const top = (o.sectors_top5 || []).map((x) => `${x.symbol} ${navPct(x.return)}`).join(", ");
  return top || "n/a";
}

function navAnalogTable(rows) {
  return navTable(`Analogs. Next-5 is ${NAV_NEXT5}.`,
    ["Date", "Age (years)", "Similarity", "Natal", "Sky", "Nifty day", "Bank Nifty day",
      "India VIX change", "Top 5 sectors", "Sectors missing", `Next-5 (${NAV_NEXT5})`, "Max drawdown"],
    rows.map((r) => {
      const o = r.outcomes || {};
      return [r.date, navNum(r.age_years, 1), navNum(r.similarity, 4), navNum(r.natal, 4), navNum(r.sky, 4),
        navPct(o.nifty_day), navPct(o.bank_day),
        typeof o.vix_change_pct === "number" ? `${o.vix_change_pct.toFixed(2)}%` : "n/a",
        navSectors(o), (o.sectors_missing || []).join(", ") || "none",
        navPct(o.next5), navPct(o.drawdown)];
    }));
}

function navSummaryLines(s) {
  const era = s.era_window || {};
  return [
    `${s.label}.`,
    `Analogs: ${navShown(s.n)}, ${navShown(s.n_with_outcome)} with a next-5 outcome.`,
    `Win ratio: ${navPct(s.win_ratio, 1)}. Average next-5: ${navPct(s.mean_next5)}. Median next-5: ${navPct(s.median_next5)}. Average drawdown: ${navPct(s.mean_drawdown)}.`,
    navBaselineText("All-eras baseline", s.baseline),
    `${navRandomSentence("All eras", s.n_with_outcome, s.random_share)}${s.random_note ? ` ${s.random_note}` : ""}`,
    `Era window: ${navShown(era.start)} to ${navShown(era.end)}.`,
    navBaselineText("Era-matched baseline", s.era_baseline),
    `${navRandomSentence("Era-matched", s.n_with_outcome, s.era_random_share)}${s.era_random_note ? ` ${s.era_random_note}` : ""}`,
    s.era_note ? `Era note: ${s.era_note}` : "Era note: n/a.",
    `Median analog age: ${typeof s.median_age_years === "number" ? `${s.median_age_years.toFixed(1)} years` : "n/a"}.`,
  ];
}

function navAnalogTarget(t) {
  const rows = t.analogs || [];
  const s = t.summary;
  const head = `${t.date}: score ${navShown(t.score)}, ${navShown(t.band)}, ${rows.length} analogs`;
  const box = navEl("details", { class: "nav-analog-target" }, [navEl("summary", { text: head })]);
  if (s) {
    box.appendChild(navEl("ul", { class: "nav-analog-summary" }, navSummaryLines(s).map((line) => navEl("li", { text: line }))));
  } else {
    box.appendChild(navNote("Too few analogs: no summary for this date."));
  }
  if (t.note) box.appendChild(navNote(`Note: ${t.note}`));
  if (rows.length) box.appendChild(navAnalogTable(rows));
  return box;
}

function navRenderAnalogs(data) {
  const out = navId("nav-analogs-out");
  navClear(out);
  const w = data.window || {};
  if (data.is_sample) out.appendChild(navEl("p", { class: "nav-banner", text: "Sample chart: pipeline check only." }));
  out.appendChild(navNote(`${data.status}. Next ${navShown(w.sessions)} sessions, ${navShown(w.start)} to ${navShown(w.end)}. Market data through ${navShown(data.data_asof)}. Similarity ${navShown(data.version)}.`));
  out.appendChild(navEl("p", { class: "nav-band", text: data.mode === "high_scoring"
    ? "High-scoring dates in this window"
    : "no high-scoring date in this window: showing the top-scoring dates instead" }));
  const targets = data.targets || [];
  if (!targets.length) out.appendChild(navNote("No target dates in this window."));
  for (const t of targets) out.appendChild(navAnalogTarget(t));
  out.append(navSubheading("Data caveats and notes"),
    navEl("ul", { class: "nav-list" }, (data.notes || []).map((n) => navEl("li", { text: n }))));
}

function navStopAnalogs() {
  NAV.analogSeq += 1;
  if (NAV.analogCtl) NAV.analogCtl.abort();
  NAV.analogCtl = null;
}

// Fired without await, so the score never waits on it. A new call aborts the old request,
// so one is in flight at a time, and the sequence check drops a stale render.
const NAV_ANALOG_TRIES = 3;
const NAV_ANALOG_WAITS_MS = [5000, 10000];

// A busy server answers 202 with busy: true while another chart's computation runs: retry after 5, then 10
// seconds (3 tries in all). The sequence check after every await drops a cancelled chain.
async function navLoadAnalogs(id) {
  navStopAnalogs();
  const seq = NAV.analogSeq;
  const ctl = new AbortController();
  NAV.analogCtl = ctl;
  NAV.analogFor = null;
  navClear(navId("nav-analogs-out"));
  navMessage("nav-analogs-status", "Loading similar past dates. A first run takes several seconds.");
  for (let attempt = 1; attempt <= NAV_ANALOG_TRIES; attempt += 1) {
    try {
      const data = await navFetch(`/api/navigator/analogs?profile_id=${id}&days=30`, {}, ctl, NAV_ANALOG_TIMEOUT_MS);
      if (seq !== NAV.analogSeq) return;
      if (data.busy) {
        if (attempt < NAV_ANALOG_TRIES) {
          navMessage("nav-analogs-status", "Similar past dates are being computed for another chart; retrying…");
          await new Promise((resolve) => setTimeout(resolve, NAV_ANALOG_WAITS_MS[attempt - 1]));
          if (seq !== NAV.analogSeq) return;
          continue;
        }
        NAV.analogCtl = null;
        navMessage("nav-analogs-status", data.error || "Similar past dates are still being computed. Try again shortly.", true);
        return;
      }
      NAV.analogCtl = null;
      navMessage("nav-analogs-status", "");
      try {
        navRenderAnalogs(data);
        NAV.analogFor = id;
      } catch (err) {
        navMessage("nav-analogs-status", "Similar past dates loaded, but could not be displayed.", true);
      }
      return;
    } catch (err) {
      if (seq !== NAV.analogSeq) return;
      NAV.analogCtl = null;
      navMessage("nav-analogs-status", err.message, true);
      return;
    }
  }
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
  navStopAnalogs();
  NAV.analogFor = null;
  if (NAV.open) navLoadAnalogs(id);
  navLoadForecast(id);
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

// A null run means no saved backtest yet, so any failure just leaves the section empty.
async function navLoadLatest(seq, id) {
  let run;
  try {
    run = await navFetch(`/api/navigator/backtest/latest?profile_id=${id}`);
  } catch (err) {
    return;
  }
  if (seq !== NAV.loadSeq || NAV.runId !== null) return;
  if (run.run === null) return;  // no saved backtest yet
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

// Degrees, minutes and seconds to a decimal. The sign comes from the degree text,
// and "neg" keeps the hemisphere when the degree is zero (a number field shows -0 as 0).
// Any blank part of an entered degree counts as 0; a blank degree gives null.
function navDmsToDecimal(deg, min, sec, neg) {
  const d = String(deg ?? "").trim();
  if (d === "") return null;
  const whole = Math.abs(Number(d));
  const m = Number(String(min ?? "").trim() || 0);
  const s = Number(String(sec ?? "").trim() || 0);
  if (![whole, m, s].every(Number.isFinite)) return null;
  if (m < 0 || m >= 60 || s < 0 || s >= 60) return null;
  const negative = d.startsWith("-") || (whole === 0 && Boolean(neg));
  const value = whole + m / 60 + s / 3600;
  return negative ? -value : value;
}

function navCoord(prefix) {
  const deg = navId(`${prefix}-deg`);
  return navDmsToDecimal(deg.value, navId(`${prefix}-min`).value, navId(`${prefix}-sec`).value,
    deg.dataset.neg === "1");
}

// Keeps the hemisphere of a source value whose degree is zero.
function navMarkHemisphere(prefix, negative) {
  const deg = navId(`${prefix}-deg`);
  if (negative) deg.dataset.neg = "1";
  else delete deg.dataset.neg;
}

// Named inputs are read by type; coordinates come from the degree fields.
// Everything is sent once in the body, and the form is then reset.
function navFormBody(form) {
  const body = {};
  for (const input of form.querySelectorAll("input[name]")) {
    const value = input.value.trim();
    if (input.type === "time") body[input.name] = /^\d\d:\d\d$/.test(value) ? `${value}:00` : value;
    else if (value !== "" || input.required) body[input.name] = value;
  }
  body.lat = navCoord("nav-bd-lat");
  body.lon = navCoord("nav-bd-lon");
  return body;
}

// The IANA name for a place. Coordinates are rounded to 0.01 degree before they
// go in the query string, which is enough to pick a time zone.
async function navTzFromCoords(lat, lon) {
  if (lat === null || lon === null) return;
  const q = `lat=${lat.toFixed(2)}&lon=${lon.toFixed(2)}`;
  try {
    const data = await navFetch(`/api/tz/from_coords?${q}`);
    if (data.timezone) navId("nav-bd-tz").value = data.timezone;
  } catch (err) {
    navMessage("nav-form-status", "The time zone name could not be found. Type it in.", true);
  }
}

const NAV_BIRTH = { profiles: [] };

async function navLoadBirthProfiles() {
  const select = navId("nav-bd-profile-select");
  try {
    const list = await navFetch("/api/astro/profile?user_key=default");
    NAV_BIRTH.profiles = Array.isArray(list) ? list : [];
  } catch (err) {
    NAV_BIRTH.profiles = [];
  }
  navClear(select);
  select.appendChild(navEl("option", { value: "", text: "-- Select saved profile --" }));
  for (const p of NAV_BIRTH.profiles) {
    const d = p.data || {};
    const text = `${p.name ? p.name + ": " : ""}${d.date || "?"} ${d.city || ""} ${p.created_at || ""}`.trim();
    select.appendChild(navEl("option", { value: String(p.id), text: text + (p.is_default ? " ★" : "") }));
  }
}

function navSetDms(prefix, part) {
  const v = (x) => (x === null || x === undefined ? "" : String(x));
  navId(`${prefix}-deg`).value = v(part.deg);
  navId(`${prefix}-min`).value = v(part.min);
  navId(`${prefix}-sec`).value = v(part.sec);
  navMarkHemisphere(prefix, v(part.deg).trim().startsWith("-"));
}

function navClearDms(prefix) {
  navSetDms(prefix, { deg: "", min: "", sec: "" });
}

// The newest saved profile by creation time, then id; the list order puts the default first.
function navNewestProfile(list) {
  let best;
  for (const p of list) {
    if (!best) { best = p; continue; }
    const a = String(p.created_at || ""), b = String(best.created_at || "");
    if (a > b || (a === b && p.id > best.id)) best = p;
  }
  return best;
}

async function navFillFromProfile(p) {
  if (!p) { navMessage("nav-form-status", "No saved profile was found.", true); return; }
  const d = p.data || {};
  const set = (id, x) => { navId(id).value = x === null || x === undefined ? "" : String(x); };
  set("nav-bd-date", d.date);
  set("nav-bd-time", d.time);
  set("nav-bd-city", d.city);
  set("nav-bd-tz-hours", d.tz_hours);
  set("nav-bd-tz-mins", d.tz_mins);
  set("nav-bd-tz", "");
  if (d.lat) navSetDms("nav-bd-lat", d.lat);
  else navClearDms("nav-bd-lat");
  if (d.lon) navSetDms("nav-bd-lon", d.lon);
  else navClearDms("nav-bd-lon");
  navMessage("nav-form-status", "Profile loaded. Check the time zone name, then create the chart.");
  await navTzFromCoords(navCoord("nav-bd-lat"), navCoord("nav-bd-lon"));
}

function navInitBirthForm() {
  if (typeof window.initBirthCity === "function") {
    window.initBirthCity({
      cityInput: "nav-bd-city", status: "nav-bd-city-status", list: "nav-bd-city-results",
      lonDeg: "nav-bd-lon-deg", lonMin: "nav-bd-lon-min", lonSec: "nav-bd-lon-sec",
      latDeg: "nav-bd-lat-deg", latMin: "nav-bd-lat-min", latSec: "nav-bd-lat-sec",
      buttons: "#nav-profile-form .city-buttons button",
      onSelect: (city) => {
        navMarkHemisphere("nav-bd-lat", city.lat < 0);
        navMarkHemisphere("nav-bd-lon", city.lon < 0);
        if (city.timezone) navId("nav-bd-tz").value = city.timezone;
        else navTzFromCoords(city.lat, city.lon);
      },
    });
  }
  for (const prefix of ["nav-bd-lat", "nav-bd-lon"]) {  // a typed degree carries its own sign
    navId(`${prefix}-deg`).addEventListener("input", () => navMarkHemisphere(prefix, false));
  }
  navId("nav-bd-profile-load").addEventListener("click", () => {
    const id = navId("nav-bd-profile-select").value;
    if (!id) { navMessage("nav-form-status", "Choose a saved profile first.", true); return; }
    navFillFromProfile(NAV_BIRTH.profiles.find((p) => String(p.id) === id));
  });
  navId("nav-bd-load-latest").addEventListener("click", async () => {
    await navLoadBirthProfiles();
    navFillFromProfile(navNewestProfile(NAV_BIRTH.profiles));
  });
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
    navMarkHemisphere("nav-bd-lat", false);
    navMarkHemisphere("nav-bd-lon", false);
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
    navLoadBirthProfiles();
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
  if (!open) {
    navStopPolling();
    if (NAV.analogCtl) {  // left mid-load: cancel, and reload on the next visit
      navStopAnalogs();
      NAV.analogFor = null;
      navMessage("nav-analogs-status", "");
    }
    return;
  }
  if (!NAV.booted) { NAV.booted = true; navBoot(); return; }
  if (NAV.profileId !== null && NAV.analogFor !== NAV.profileId && !NAV.analogCtl) navLoadAnalogs(NAV.profileId);
  if (NAV.runId !== null) navPoll();
}

(function navInit() {
  const pane = navId("tab-navigator");
  if (!pane) return;
  new MutationObserver(navSync).observe(pane, { attributes: true, attributeFilter: ["class"] });
  navId("nav-run").addEventListener("click", navStartRun);
  navId("nav-profile-form").addEventListener("submit", navSubmitProfile);
  navInitBirthForm();
  navId("nav-profile").addEventListener("change", (e) => {
    NAV.profileId = Number(e.target.value);
    navLoadProfile();
  });
  navSync();
})();


// ---- Phase 3: forecast calendar ----
const NAV_FC = { window: 30, data: null, seq: 0, show: new Set(NAV_BANDS.map((b) => b[0])), zoom: null };
const NAV_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function navBandIndex(band) { return NAV_BANDS.findIndex((b) => b[0] === band); }

function navForecastRows(list) {
  return (list || []).map((r) => [r.date, r.score, r.band, r.action]);
}

function navMonthBlock(year, month, byDate, zoomed) {
  const grid = navEl("div", { class: "nav-month-grid" });
  const first = new Date(Date.UTC(year, month, 1));
  const lead = (first.getUTCDay() + 6) % 7;            // Monday first
  for (let i = 0; i < lead; i += 1) grid.appendChild(navEl("span", { class: "nav-day dim", "aria-hidden": "true" }));
  const days = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  for (let d = 1; d <= days; d += 1) {
    const iso = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const row = byDate.get(iso);
    let cls = "nav-day";
    let label = `${iso}: no session`;
    if (row) {
      const k = navBandIndex(row.band);
      cls += NAV_FC.show.has(row.band) ? ` nav-b${k}` : " dim";
      label = `${iso}: score ${row.score}, ${row.band}, ${row.action}`;
    } else {
      cls += " dim";
    }
    grid.appendChild(navEl("span", { class: cls, title: label, "aria-label": label, text: zoomed && row ? `${d} · ${row.score}` : String(d) }));
  }
  const name = `${NAV_MONTHS[month]} ${year}`;
  const head = navEl("button", { type: "button", class: "btn btn-secondary nav-month-btn", text: zoomed ? `${name} (back to all months)` : name, "aria-label": zoomed ? "Show all months" : `Zoom into ${name}` });
  head.addEventListener("click", () => { NAV_FC.zoom = zoomed ? null : `${year}-${month}`; navRenderForecast(); });
  return navEl("div", { class: "nav-month" }, [head, grid]);
}

function navRenderForecast() {
  const out = navId("nav-forecast-out");
  if (!out) return;
  navClear(out);
  const data = NAV_FC.data;
  if (!data) return;
  const byDate = new Map((data.sessions || []).map((r) => [r.date, r]));
  const counts = data.band_counts || {};
  out.appendChild(navNote(`${(data.sessions || []).length} sessions in the next ${data.window_days} days. Market data through ${data.data_asof}. `
    + NAV_BANDS.map((b) => `${b[0]} ${counts[b[0]] || 0}`).join(", ") + "."));
  const months = [];
  for (const r of data.sessions || []) {
    const key = r.date.slice(0, 7);
    if (!months.includes(key)) months.push(key);
  }
  const cal = navEl("div", { class: NAV_FC.zoom ? "nav-cal zoomed" : "nav-cal" });
  for (const key of months) {
    const [y, m] = key.split("-").map(Number);
    if (NAV_FC.zoom && NAV_FC.zoom !== `${y}-${m - 1}`) continue;
    cal.appendChild(navMonthBlock(y, m - 1, byDate, Boolean(NAV_FC.zoom)));
  }
  out.appendChild(cal);
  const keep = (rows) => (rows || []).filter((r) => NAV_FC.show.has(r.band));
  out.appendChild(navTable("Top 20 trading dates (highest scores)", ["Date", "Score", "Band", "Action label"], navForecastRows(keep(data.top))));
  out.appendChild(navTable("Top 20 stay-away dates (lowest scores)", ["Date", "Score", "Band", "Action label"], navForecastRows(keep(data.stay_away))));
  for (const n of data.notes || []) out.appendChild(navNote(n));
}

async function navLoadForecast(id) {
  const seq = ++NAV_FC.seq;
  NAV_FC.data = null;
  NAV_FC.zoom = null;
  navRenderForecast();
  navMessage("nav-forecast-status", "Loading forecast.");
  try {
    const data = await navFetch(`/api/navigator/forecast?profile_id=${encodeURIComponent(id)}&window=${NAV_FC.window}`);
    if (seq !== NAV_FC.seq) return;
    NAV_FC.data = data;
    navMessage("nav-forecast-status", "");
    navRenderForecast();
  } catch (err) {
    if (seq === NAV_FC.seq) navMessage("nav-forecast-status", (err && err.message) || "Forecast could not be loaded.", true);
  }
}

(function navForecastInit() {
  const filter = document.querySelector("#nav-forecast .nav-band-filter");
  if (filter) {
    NAV_BANDS.forEach(([band], k) => {
      const box = navEl("input", { type: "checkbox", checked: "checked", "aria-label": `Show ${band}` });
      box.addEventListener("change", () => {
        if (box.checked) NAV_FC.show.add(band); else NAV_FC.show.delete(band);
        navRenderForecast();
      });
      filter.appendChild(navEl("label", {}, [box, navEl("span", { class: `nav-swatch nav-b${k}` }), navEl("span", { text: band })]));
    });
  }
  document.querySelectorAll("#nav-forecast .nav-window").forEach((btn) => {
    btn.addEventListener("click", () => {
      NAV_FC.window = Number(btn.dataset.window);
      document.querySelectorAll("#nav-forecast .nav-window").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      if (NAV.profileId) navLoadForecast(NAV.profileId);
    });
  });
})();
