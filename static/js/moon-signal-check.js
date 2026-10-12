// Moon Signal Check (Trading Signals panel): the Moon-sign bullish/bearish call scored against
// the next session's close, next to the base rate. Data: /api/signals/moon-check.
// Plotly is loaded on first use, not with the page.
(function () {
  "use strict";
  const PLOTLY_SRC = "/static/vendor/plotly-basic-4.1.1.min.js";
  const el = (id) => document.getElementById(id);
  const form = el("msc-form");
  if (!form) return;

  const escH = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const css = (name, fallback) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  const pct = (x) => (x == null || !isFinite(x) ? "–" : `${(x * 100).toFixed(1)}%`);

  let plotlyPromise = null;
  function loadPlotly() {
    if (window.Plotly) return Promise.resolve(window.Plotly);
    if (!plotlyPromise) {
      plotlyPromise = new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = PLOTLY_SRC;
        s.onload = () => resolve(window.Plotly);
        s.onerror = () => { plotlyPromise = null; reject(new Error("could not load Plotly")); };
        document.head.appendChild(s);
      });
    }
    return plotlyPromise;
  }

  function setStatus(msg, isErr) {
    const s = el("msc-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  let last = null;

  function renderScore(d) {
    const s = d.summary || {};
    const g = d.gap_control || {};
    const gapOn = el("msc-gap").checked;
    const edge = s.hit_rate != null && s.base_rate != null ? (s.hit_rate - s.base_rate) * 100 : null;
    const cls = s.p_value != null && s.p_value < 0.05 && edge > 0 ? "good" : "flat";
    const p = s.p_value == null ? "–" : s.p_value < 0.001 ? "<0.001" : s.p_value.toFixed(3);
    el("msc-score").innerHTML = `
      <div class="msc-stat"><span>Hit rate</span><b>${pct(s.hit_rate)}</b><small>${s.hits ?? 0} of ${s.samples ?? 0} calls</small></div>
      <div class="msc-stat"><span>Base rate</span><b>${pct(s.base_rate)}</b><small>always calling the commoner direction</small></div>
      <div class="msc-stat"><span>Edge</span><b class="${cls}">${edge == null ? "–" : (edge >= 0 ? "+" : "") + edge.toFixed(1) + " pts"}</b><small>p = ${p} (binomial vs base)</small></div>
      ${gapOn ? `<div class="msc-stat warn"><span>Gap alone</span><b>${pct(g.hit_rate)}</b><small>${escH(g.note)}</small></div>` : ""}
      <p class="msc-verdict">${escH(s.verdict)}</p>
      <p class="msc-meta">${escH(d.name)} · ${escH(d.start)} to ${escH(d.end)} · ${escH(d.source)}</p>`;
  }

  async function renderChart(d) {
    const Plotly = await loadPlotly();
    const up = css("--green", "#34d399"), down = css("--red", "#f87171");
    const text = css("--text", "#e2e8f0"), muted = css("--muted", "#94a3b8");
    const line = css("--line", "#1f2c47"), accent = css("--accent", "#fbbf24");
    const closeBy = new Map(d.bars.map((b) => [b.date, b.close]));

    // Background bands: one rectangle per run of identical calls (call made on `date`, scored on `scored`).
    const shapes = [];
    let run = null;
    for (const r of d.rows) {
      if (run && run.call === r.expected) { run.x1 = r.scored; continue; }
      if (run) shapes.push(run);
      run = { call: r.expected, x0: r.date, x1: r.scored };
    }
    if (run) shapes.push(run);
    const bandShapes = shapes.map((s) => ({
      type: "rect", xref: "x", yref: "y domain", x0: s.x0, x1: s.x1, y0: 0, y1: 1,
      fillcolor: s.call === "bullish" ? up : down, opacity: 0.09, line: { width: 0 }, layer: "below",
    }));

    const hits = d.rows.filter((r) => r.match), misses = d.rows.filter((r) => !r.match);
    const marker = (rows, name, color, symbol) => ({
      type: "scatter", mode: "markers", name, xaxis: "x", yaxis: "y",
      x: rows.map((r) => r.scored), y: rows.map((r) => closeBy.get(r.scored)),
      marker: { color, size: 5, symbol },
      customdata: rows.map((r) => [r.sign, r.expected, r.actual]),
      hovertemplate: "%{x}<br>Moon in %{customdata[0]}: called %{customdata[1]}<br>Close went %{customdata[2]}<extra>" + name + "</extra>",
    });
    const base = d.summary.base_rate;
    const traces = [
      { type: "scatter", mode: "lines", name: "Close", x: d.bars.map((b) => b.date), y: d.bars.map((b) => b.close),
        line: { color: text, width: 1.3 }, hovertemplate: "%{x}<br>%{y:,.2f}<extra></extra>" },
      marker(hits, "Hit", up, "circle"),
      marker(misses, "Miss", down, "x"),
      { type: "scatter", mode: "lines", name: `Rolling ${d.rolling_window}-call hit rate`, xaxis: "x", yaxis: "y2",
        x: d.rolling.map((r) => r.date), y: d.rolling.map((r) => r.hit_rate),
        line: { color: accent, width: 1.6 }, hovertemplate: "%{x}<br>%{y:.1%}<extra></extra>" },
    ];
    if (base != null && d.rolling.length) {
      traces.push({ type: "scatter", mode: "lines", name: "Base rate", xaxis: "x", yaxis: "y2",
        x: [d.rolling[0].date, d.rolling[d.rolling.length - 1].date], y: [base, base],
        line: { color: muted, width: 1, dash: "dash" }, hovertemplate: `Base rate ${pct(base)}<extra></extra>` });
    }
    const axis = { gridcolor: line, zerolinecolor: line, color: muted };
    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { color: text, size: 11 },
      margin: { l: 56, r: 12, t: 8, b: 32 }, height: 460, hovermode: "closest", shapes: bandShapes,
      legend: { orientation: "h", y: 1.06, x: 0, font: { size: 10 } },
      xaxis: Object.assign({ type: "date", anchor: "y2" }, axis),
      yaxis: Object.assign({ domain: [0.34, 1], title: { text: "Close", font: { size: 10 } } }, axis),
      yaxis2: Object.assign({ domain: [0, 0.26], range: [0, 1], tickformat: ".0%", title: { text: "Hit rate", font: { size: 10 } } }, axis),
    };
    Plotly.react(el("msc-chart"), traces, layout, { responsive: true, displaylogo: false });
  }

  function exportCsv() {
    if (!last) return;
    const head = "signal_date,scored_date,moon_sign,call,actual,hit,gap_direction";
    const body = last.rows.map((r) => [r.date, r.scored, r.sign, r.expected, r.actual, r.match ? 1 : 0, r.gap ?? ""].join(","));
    const blob = new Blob([[head, ...body].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `moon-signal-${last.symbol}-${last.start}-${last.end}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  async function run(ev) {
    if (ev) ev.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    const q = new URLSearchParams({
      symbol: el("msc-symbol").value, years: el("msc-years").value,
      multi_tf: el("msc-multi").checked, regime: el("msc-regime").checked, gap: el("msc-gap").checked,
    });
    if (btn) btn.disabled = true;
    setStatus("Scoring the signal…");
    try {
      const res = await fetch(`/api/signals/moon-check?${q}`);
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.error || `request failed (${res.status})`);
      last = d;
      renderScore(d);
      await renderChart(d);
      el("msc-csv").disabled = !d.rows.length;
      setStatus(`${d.summary.samples} scored sessions. Shaded bands show the call; markers show hits and misses.`);
    } catch (e) {
      setStatus(`Couldn't run the check: ${e.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  form.addEventListener("submit", run);
  el("msc-csv").addEventListener("click", exportCsv);

  // Run once when the section first scrolls into view, so the page load stays light.
  const target = el("moon-signal-check");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { io.disconnect(); run(); }
    });
    io.observe(target);
  } else {
    run();
  }
})();
