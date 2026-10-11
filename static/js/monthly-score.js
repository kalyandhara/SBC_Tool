// Monthly Score panel (Forward Calendar tab, B-41): the SBC composite score for each
// calendar day beside the NIFTY closes so far. Data: /api/engine/monthly_projection.
// Hypothetical and unvalidated. Plotly is loaded on first use, not with the page.
(function () {
  "use strict";
  const PLOTLY_SRC = "/static/vendor/plotly-basic-4.1.1.min.js";
  const el = (id) => document.getElementById(id);
  const form = el("ms-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
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
    const s = el("ms-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function renderMeta(d) {
    const freshness = window.SBCFreshness ? SBCFreshness.badge(d.freshness, "NIFTY") : "";
    const live = d.live_hit_rate_5h == null
      ? "no live 5-session hit rate yet"
      : `live 5-session hit rate ${pct(d.live_hit_rate_5h)}`;
    el("ms-meta").innerHTML = `${freshness} <span class="asof-badge stale">${esc(d.disclaimer)}</span> ` +
      `${esc(live)} · source: ${esc(d.source)}`;
  }

  function renderChart(Plotly, d) {
    const text = css("--text", "#e2e8f0");
    const grid = css("--line", "#1f2c47");
    const dates = d.days.map((x) => x.date);
    // Non-trading days get hollow markers, so the weekends and holidays stand out.
    const score = {
      type: "scatter", mode: "lines+markers", name: "Score", x: dates, y: d.days.map((x) => x.score),
      line: { color: "#38bdf8", width: 1.5 },
      marker: { size: 6, color: d.days.map((x) => (x.trading ? "#38bdf8" : "rgba(0,0,0,0)")),
        line: { color: "#38bdf8", width: 1 } },
      text: d.days.map((x) => (x.trading ? "trading day" : "non-trading day")),
      hovertemplate: "Score %{y:.2f} · %{text}<extra>%{x}</extra>",
    };
    // Closes exist only up to today; the server sends null for later days.
    const close = {
      type: "scatter", mode: "lines+markers", name: "NIFTY close", x: dates,
      y: d.days.map((x) => x.nifty_close), yaxis: "y2", connectgaps: false,
      line: { color: "#f59e0b", width: 1.5 }, marker: { size: 5, color: "#f59e0b" },
      hovertemplate: "NIFTY %{y:,.0f}<extra>%{x}</extra>",
    };
    Plotly.react(el("ms-chart"), [score, close], {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", autosize: true,
      font: { color: text, size: 12 }, margin: { l: 56, r: 56, t: 30, b: 40 },
      hovermode: "x unified", legend: { orientation: "h", y: 1.1, x: 0, font: { size: 11 } },
      xaxis: { type: "date", gridcolor: grid },
      yaxis: { title: { text: "Score (SBC classical net)" }, gridcolor: grid, zeroline: true, zerolinecolor: grid },
      yaxis2: { title: { text: "NIFTY close" }, overlaying: "y", side: "right", showgrid: false },
    }, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
  }

  async function getJson(url) {
    const r = await fetch(url);
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
  }

  async function run() {
    const month = el("ms-month").value;
    if (!month) { setStatus("Pick a month.", true); return; }
    setStatus("Loading…");
    try {
      const [d, Plotly] = await Promise.all([
        getJson(`/api/engine/monthly_projection?month=${encodeURIComponent(month)}`),
        loadPlotly(),
      ]);
      renderMeta(d);
      renderChart(Plotly, d);
      const trading = d.days.filter((x) => x.trading).length;
      setStatus(`${d.days.length} calendar days, ${trading} trading days.`);
    } catch (err) {
      setStatus(`Could not load the monthly score: ${err.message}`, true);
    }
  }

  const now = new Date();
  el("ms-month").value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });

  // Draw when the tab is first opened (Plotly needs a visible box to size itself).
  let drawn = false;
  const tab = document.querySelector('[data-tab="tab-calendar"]');
  const firstDraw = () => { if (!drawn) { drawn = true; run(); } };
  if (tab) tab.addEventListener("click", () => setTimeout(firstDraw, 0));
  if (el("tab-calendar")?.classList.contains("active")) firstDraw();
})();
