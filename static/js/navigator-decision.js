// Navigator decision panel: Today card, 10-session timeline and the rule-1 backtest.
// Uses navigator.js helpers. Values via textContent only. The card will not render
// without its disclaimer and evidence line: research output is never shown unlabelled.

const NAV_DIR = { up: "↑", down: "↓", neutral: "→" };
const NAV_RULE = { seq: 0, timer: null, runId: null };
const NAV_RULE_LABEL = "Run rule backtest";

function navBadge(text) { return navEl("span", { class: "nav-tag nav-badge", text }); }

function navWindowList(title, list) {
  return navEl("div", {}, [navSubheading(title), navEl("ul", { class: "nav-list" },
    (list || []).map((w) => navEl("li", { text: `${w.start} to ${w.end} (score ${w.score})` })))]);
}

function navRenderToday(data) {
  if (!data || !data.disclaimer || !data.evidence || !data.evidence.text) {
    throw new Error("The decision card is missing its disclaimer or evidence line.");
  }
  const out = navId("nav-today");
  navClear(out);
  out.appendChild(navHeading(`Today: ${data.day}`));
  const card = navEl("div", { class: "nav-card" });
  if (data.label) card.appendChild(navNote(data.label));
  const s = data.stance;
  if (!data.covered || !s) {
    card.appendChild(navEl("p", { class: "nav-error", text: data.coverage_note || "No stance for this date." }));
  } else {
    card.appendChild(navEl("div", { class: "nav-stance", text: s.stance }));
    card.appendChild(navEl("p", { text: `Size ${s.multiplier}× · band ${s.band} (score ${data.score}) · trend ${s.trend} · VIX ${s.vix} · ${s.rule_version}` }));
  }
  card.appendChild(navEl("p", { class: "nav-strong" }, [navEl("span", { text: data.evidence.text }), navBadge("unvalidated")]));
  if (data.stale) card.appendChild(navEl("p", { class: "nav-error", text: `Data stale: last close ${navShown(data.t_minus_1)}. Stance is provisional.` }));
  card.appendChild(navNote(`Inputs as of the ${navShown(data.t_minus_1)} close.`));
  if (data.side === "short") card.appendChild(navNote(data.short_cost_note));
  card.appendChild(navEl("p", { class: "nav-disclaimer", text: data.disclaimer }));
  out.appendChild(card);
  const w = data.windows || {};
  const win = navEl("div", { class: "nav-card" }, [navSubheading("Time windows"), navBadge("experimental")]);
  if (!w.available) win.appendChild(navNote(w.text || "windows unavailable"));
  else win.append(navWindowList("Best", w.best), navWindowList("Worst", w.worst), navNote(w.notice || ""));
  out.appendChild(win);
  out.appendChild(navTable("Confluence", ["", "Signal", "Reading", "Role", "Evidence"],
    (data.confluence || []).map((i) => [NAV_DIR[i.direction] || "→", i.label, i.detail,
      i.in_rule ? "in the rule" : "context only", i.badge])));
}

function navRenderTimeline(data) {
  if (!data || !data.disclaimer) throw new Error("The timeline is missing its disclaimer.");
  const out = navId("nav-timeline");
  navClear(out);
  out.appendChild(navEl("div", {}, [navHeading("Next 10 sessions"), navBadge("unvalidated")]));
  out.appendChild(navNote(`Stances are provisional: trend and VIX frozen at the ${navShown(data.frozen_asof)} close. Volatility is neutral on future days.`));
  out.appendChild(navTable("", ["Date", "Score", "Band", "Stance (provisional)", "Events"],
    (data.rows || []).map((r) => [r.covered ? r.date : `${r.date} (${r.coverage_note})`, r.score, r.band,
      `${r.stance} ${r.multiplier}×`, (r.events || []).join("; ") || "none"])));
  out.appendChild(navEl("p", { class: "nav-disclaimer", text: data.disclaimer }));
}

function navRuleRows(results) {
  return ["long", "short"].map((side) => {
    const s = (results.sides || {})[side] || {};
    const best = (s.by_horizon || {})[s.best_horizon] || {};
    return [side, navShown(s.verdict), navShown(s.best_horizon), navShown(best.events), navShown(best.closed_events),
      navPct(best.excess, 3), navPct(best.sized_excess, 3), navNum(best.q, 3), navShown(best.pct)];
  });
}

function navRenderRule(run) {
  const out = navId("nav-rule-out");
  navClear(out);
  if (!run || run.run === null) { out.appendChild(navNote("No rule backtest yet.")); return; }
  if (run.status === "failed") { out.appendChild(navEl("p", { class: "nav-error", text: run.error || "The rule backtest failed." })); return; }
  if (run.status !== "done" || !run.results) { out.appendChild(navNote(`Rule backtest ${run.status}.`)); return; }
  out.appendChild(navNote(`${run.results.label || run.label}. Run ${run.id}, data through ${navShown(run.data_asof)}.`));
  out.appendChild(navTable("rule-1 against trend-only, net of costs",
    ["Side", "Verdict", "Horizon", "Events", "Gate-closed events", "Excess / day (1 unit)", "Sized excess (descriptive)", "q", "Placebo pct"],
    navRuleRows(run.results)));
  for (const note of run.results.notes || []) out.appendChild(navNote(note));
}

function navRuleIdle() {
  const button = navId("nav-rule-run");
  button.disabled = false;
  button.textContent = NAV_RULE_LABEL;
}

async function navPollRule(seq) {
  if (seq !== NAV_RULE.seq || NAV_RULE.runId === null) return;
  try {
    const run = await navFetch(`/api/navigator/rule-backtest/${NAV_RULE.runId}`);
    if (seq !== NAV_RULE.seq) return;
    navRenderRule(run);
    if (NAV_ACTIVE.includes(run.status)) NAV_RULE.timer = setTimeout(() => navPollRule(seq), NAV_POLL_MS);
    else { NAV_RULE.runId = null; navRuleIdle(); }
  } catch (err) {
    if (seq === NAV_RULE.seq) { navMessage("nav-rule-status", err.message, true); navRuleIdle(); }
  }
}

async function navStartRule() {
  const seq = ++NAV_RULE.seq;
  navId("nav-rule-run").disabled = true;
  navMessage("nav-rule-status", "");
  try {
    const body = await navFetch("/api/navigator/rule-backtest", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: NAV.profileId }) });
    if (seq !== NAV_RULE.seq) return;
    NAV_RULE.runId = body.run_id;
    navPollRule(seq);
  } catch (err) {
    if (seq !== NAV_RULE.seq) return;
    navMessage("nav-rule-status", err.message, true);
    navRuleIdle();
  }
}

async function navLoadLatestRule(ruleSeq, id) {
  try {
    const run = await navFetch(`/api/navigator/rule-backtest/latest?profile_id=${id}`);
    if (ruleSeq !== NAV_RULE.seq) return;
    navRenderRule(run);
    if (run && NAV_ACTIVE.includes(run.status)) {
      NAV_RULE.runId = run.id;
      navId("nav-rule-run").disabled = true;
      navPollRule(ruleSeq);
    }
  } catch (err) {
    if (ruleSeq === NAV_RULE.seq) navMessage("nav-rule-status", err.message, true);
  }
}

async function navLoadDecision(seq, id) {
  clearTimeout(NAV_RULE.timer);
  const ruleSeq = ++NAV_RULE.seq;
  NAV_RULE.runId = null;
  navRuleIdle();
  navId("nav-today").textContent = "Loading today's card.";
  navClear(navId("nav-timeline"));
  navLoadLatestRule(ruleSeq, id);
  try {
    const today = await navFetch(`/api/navigator/decision?profile_id=${id}`);
    if (seq === NAV.loadSeq) navRenderToday(today);
  } catch (err) {
    if (seq === NAV.loadSeq) navSectionError("nav-today", "Today", err);
  }
  if (seq === NAV.loadSeq) {
    navId("nav-timeline").textContent = "Loading the next 10 sessions.";
    try {
      const tl = await navFetch(`/api/navigator/timeline?profile_id=${id}`);
      if (seq === NAV.loadSeq) navRenderTimeline(tl);
    } catch (err) {
      if (seq === NAV.loadSeq) navSectionError("nav-timeline", "Next 10 sessions", err);
    }
  }
}

(function navDecisionInit() {
  const button = navId("nav-rule-run");
  if (button) button.addEventListener("click", navStartRule);
})();
