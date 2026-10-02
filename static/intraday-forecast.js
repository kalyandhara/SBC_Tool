// Forward intraday forecast (SBC + KP confluence) drawn with Plotly.
// Data: /api/engine/intraday_forecast (+ /actual, /ledger). Plotly (1.2 MB)
// is loaded on first use, not with the page.
(function () {
  const PLOTLY_SRC = "/static/vendor/plotly-basic-4.1.1.min.js";
  const el = (id) => document.getElementById(id);
  if (!el("intraday-forecast")) return;

  let plotlyPromise = null;
  function loadPlotly() {
    if (window.Plotly) return Promise.resolve(window.Plotly);
    if (!plotlyPromise) {
      plotlyPromise = new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = PLOTLY_SRC;
        s.onload = () => resolve(window.Plotly);
        s.onerror = () => reject(new Error("could not load Plotly"));
        document.head.appendChild(s);
      });
    }
    return plotlyPromise;
  }

  const css = (name, fallback) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  const escHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

  function setStatus(msg, isErr) {
    const s = el("ifc-status");
    if (!s) return;
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  // Default day: today if NSE trades and it's before the close, else the next
  // trading day (IST), skipping weekends and the NSE holidays in `closed`.
  const isoOf = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  function defaultDay(closed) {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
    const d = new Date(now);
    const afterClose = now.getHours() * 60 + now.getMinutes() > 15 * 60 + 30;
    if (afterClose) d.setDate(d.getDate() + 1);
    while (d.getDay() === 0 || d.getDay() === 6 || closed.has(isoOf(d))) d.setDate(d.getDate() + 1);
    return isoOf(d);
  }

  async function holidaySet() {
    const year = new Date().getFullYear();
    const sets = await Promise.all([year, year + 1].map((y) =>
      getJSON(`/api/market/holidays?year=${y}`).then((r) => r.holidays).catch(() => [])));
    return new Set(sets.flat().filter((h) => h.type === "holiday").map((h) => h.date));
  }

  async function getJSON(url) {
    const r = await fetch(url);
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.error) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }

  const COMP_LABEL = {
    hora: "Hora", asc_sub: "Asc sub-lord", moon_sub: "Moon sub-lord",
    impulse_moon: "Moon transition", impulse_asc: "Asc transition", sbc: "SBC vedha",
  };

  function bucketHover(b) {
    const parts = Object.entries(b.components)
      .filter(([, v]) => v !== 0)
      .map(([k, v]) => `${COMP_LABEL[k] || k}: ${v > 0 ? "+" : ""}${v}`);
    const flags = [b.dl_hora && "DL-hora", b.chand_vat && "Chand/Vat", b.dahan && "Dahan"].filter(Boolean);
    return [
      `<b>${b.time}</b> score ${b.score > 0 ? "+" : ""}${b.score} · path ${b.cumulative}`,
      `Hora ${escHtml(b.hora_lord || "-")} · Asc sub ${escHtml(b.asc_sublord)} · Moon sub ${escHtml(b.moon_sublord)}`,
      parts.join("<br>") || "no active components",
      flags.length ? `Flags: ${flags.join(", ")}` : "",
      ...(b.events || []).map((e) => `⟶ ${escHtml(e)}`),
    ].filter(Boolean).join("<br>");
  }

  function render(Plotly, f, actual) {
    const day = f.date;
    const X = (t) => `${day} ${t}`;
    const text = css("--text", "#e2e8f0");
    const muted = css("--muted", "#94a3b8");
    const grid = css("--line", "#1f2c47");
    const green = css("--green", "#34d399");
    const red = css("--red", "#f87171");
    const accent = css("--accent", "#fbbf24");

    const b = f.buckets;
    const traces = [{
      x: b.map((k) => X(k.time)), y: b.map((k) => k.cumulative),
      type: "scatter", mode: "lines", name: "Forecast path",
      line: { color: "#3b82f6", width: 2.5, shape: "spline", smoothing: 0.6 },
      fill: "tozeroy", fillcolor: "rgba(59,130,246,0.12)",
      hovertext: b.map(bucketHover), hoverinfo: "text", xaxis: "x", yaxis: "y",
    }];

    // Moon sub-lord changes: labelled dots. Asc changes: small, hover only.
    const pathAt = (t) => {
      let v = 0;
      for (const k of b) { if (k.time <= t) v = k.cumulative; else break; }
      return v;
    };
    for (const [body, size, labelled] of [["Moon", 13, true], ["Ascendant", 6, false]]) {
      const tr = f.transitions.filter((t) => t.body === body);
      if (!tr.length) continue;
      traces.push({
        x: tr.map((t) => X(t.time)), y: tr.map((t) => pathAt(t.time)),
        type: "scatter", mode: labelled ? "markers+text" : "markers",
        name: `${body === "Moon" ? "Moon" : "Asc"} sub-lord change`,
        text: labelled ? tr.map((t) => t.time) : undefined, textposition: "top center",
        textfont: { color: accent, size: 11 },
        marker: {
          size, line: { width: 1, color: "#0b1120" },
          color: tr.map((t) => t.direction === "Bullish" ? green : t.direction === "Bearish" ? red : accent),
        },
        hovertext: tr.map((t) => `<b>${escHtml(t.time)}</b> ${body} sub ${escHtml(t.old_sublord)} → ${escHtml(t.new_sublord)}<br>` +
          `star ${escHtml(t.star)} · houses ${escHtml(t.houses.join(","))} · strength ${Number(t.strength)}<br>${escHtml(t.direction)}`),
        hoverinfo: "text", xaxis: "x", yaxis: "y",
      });
    }

    // Actual NIFTY (5-min closes) on a secondary axis once traded.
    const bars = (actual && actual.bars) || [];
    if (bars.length) {
      traces.push({
        x: bars.map((k) => X(k.time)), y: bars.map((k) => k.close),
        type: "scatter", mode: "lines", name: `Actual NIFTY${actual.settled ? "" : " (live)"}`,
        line: { color: muted, width: 1.5, dash: "dot" },
        hovertemplate: "%{x|%H:%M} NIFTY %{y:.2f}<extra></extra>", xaxis: "x", yaxis: "y3",
      });
    }

    traces.push({
      x: b.map((k) => X(k.time)), y: b.map((k) => k.score), type: "bar", name: "Bucket score",
      marker: {
        color: b.map((k) => k.score >= 0 ? green : red),
        opacity: b.map((k) => k.chand_vat ? 1 : k.dahan ? 0.35 : 0.75),
      },
      hovertext: b.map(bucketHover), hoverinfo: "text", xaxis: "x2", yaxis: "y2",
    });

    // Hora bands: dotted boundaries, gold = DL-hora, grey = Dahan, green = Chand/Vat.
    const shapes = [], annotations = [];
    for (const h of f.horas) {
      const fill = h.dl_hora ? "rgba(251,191,36,0.18)" : h.dahan ? "rgba(148,163,184,0.16)"
        : h.chand_vat ? "rgba(52,211,153,0.10)" : null;
      for (const [xref, yref] of [["x", "y domain"], ["x2", "y2 domain"]]) {
        if (fill) shapes.push({ type: "rect", xref, yref, x0: X(h.start), x1: X(h.end), y0: 0, y1: 1,
          fillcolor: fill, line: { width: 0 }, layer: "below" });
        shapes.push({ type: "line", xref, yref, x0: X(h.start), x1: X(h.start), y0: 0, y1: 1,
          line: { color: muted, width: 1, dash: "dot" }, layer: "below" });
      }
      // Label horas long enough to hold one (the session's first/last can be minutes long).
      const mins = (t) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
      if (mins(h.end) - mins(h.start) >= 20) {
        annotations.push({ xref: "x", yref: "y domain", x: X(h.start), y: 0.02, xanchor: "left",
          text: ` ${escHtml(h.lord)}`, showarrow: false, font: { size: 10, color: muted } });
      }
    }
    shapes.push({ type: "line", xref: "x domain", yref: "y", x0: 0, x1: 1, y0: 0, y1: 0,
      line: { color: grid, width: 1 } });

    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      autosize: true, font: { color: text, size: 12 }, margin: { l: 56, r: bars.length ? 64 : 20, t: 30, b: 40 },
      hovermode: "closest", hoverlabel: { align: "left" }, bargap: 0.15,
      legend: { orientation: "h", y: 1.07, x: 0, font: { size: 11 } },
      grid: { rows: 2, columns: 1, pattern: "independent" },
      xaxis: { domain: [0, 1], anchor: "y", type: "date", tickformat: "%H:%M", gridcolor: grid,
        matches: "x2", showticklabels: false },
      yaxis: { domain: [0.38, 1], title: { text: "Forecast path" }, gridcolor: grid, zeroline: false },
      xaxis2: { domain: [0, 1], anchor: "y2", type: "date", tickformat: "%H:%M", gridcolor: grid },
      yaxis2: { domain: [0, 0.3], title: { text: `${f.step_minutes}-min score` }, gridcolor: grid },
      yaxis3: { overlaying: "y", side: "right", showgrid: false, title: { text: "NIFTY" },
        tickformat: ",.0f", visible: bars.length > 0 },
      shapes, annotations,
    };
    const node = el("ifc-chart");
    Plotly.react(node, traces, layout,
      { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] })
      .then(() => resizeSoon());
  }

  function renderFrozen(f) {
    const node = el("ifc-frozen");
    if (!node) return;
    const fr = f.frozen;
    if (!fr) { node.textContent = "Not frozen yet (today's forecast freezes automatically before 09:15 IST)."; return; }
    const when = fr.frozen_at.replace("T", " ").slice(0, 16);
    const kind = { live: "frozen before the open ✓", late: "frozen after the open", backfill: "back-test" }[fr.kind] || fr.kind;
    node.textContent = `Ledger: ${kind} · ${when} IST · model ${fr.model_version}${fr.stale_model ? " (weights changed since)" : ""}`;
  }

  function renderLedger(s) {
    const node = el("ifc-ledger");
    if (!node) return;
    const row = (label, g) => {
      if (!g) return `<tr><td>${label}</td><td colspan="5">no scored days yet</td></tr>`;
      const hr = g.hit_rate == null ? "-" : `${(g.hit_rate * 100).toFixed(1)}%`;
      const bl = g.baseline == null ? "-" : `${(g.baseline * 100).toFixed(1)}%`;
      const cls = g.hit_rate != null && g.baseline != null ? (g.hit_rate > g.baseline ? "beats" : "lags") : "";
      return `<tr><td>${label}</td><td>${Number(g.days)}</td><td>${Number(g.buckets)}</td>` +
        `<td class="${cls}">${hr}</td><td>${bl}</td><td>${escHtml(g.day_direction)}</td></tr>`;
    };
    node.innerHTML = `<strong>Forecast record (last ${s.window_days} days)</strong>` +
      `<table><thead><tr><th></th><th>Days</th><th>Buckets</th><th>Hit rate</th>` +
      `<th>Baseline</th><th>Day direction</th></tr></thead><tbody>` +
      row("Forward (frozen on the day)", s.groups.forward) +
      row("Back-test (backfilled)", s.groups.backfill) +
      `</tbody></table><div>Baseline = majority-class rate on the same bars; a hit rate below it means no skill.</div>`;
  }

  let loadSeq = 0;  // only the latest request may draw (tab auto-load vs. a click)

  async function load() {
    const seq = ++loadSeq;
    const day = el("ifc-date").value;
    const step = el("ifc-step").value;
    if (!day) { setStatus("Pick a trading day.", true); return; }
    setStatus(`Computing forecast for ${day}…`);
    try {
      const [Plotly, f] = await Promise.all([
        loadPlotly(), getJSON(`/api/engine/intraday_forecast?date=${day}&step=${step}`)]);
      let actual = null;
      try { actual = await getJSON(`/api/engine/intraday_forecast/actual?date=${day}`); } catch (e) { actual = null; }
      if (seq !== loadSeq) return;  // a newer request superseded this one
      render(Plotly, f, actual);
      renderFrozen(f);
      const moonCount = f.transitions.filter((t) => t.body === "Moon").length;
      const last = f.buckets[f.buckets.length - 1];
      setStatus(`${f.buckets.length} buckets · ${moonCount} Moon / ${f.transitions.length - moonCount} Asc sub-lord changes · ` +
        `day lord ${f.day_lord} · Moon in ${f.moon.star} (${f.moon.sign}) · path ends ${last ? last.cumulative : "-"}` +
        (actual && actual.bars && actual.bars.length ? ` · ${actual.bars.length} actual bars` : ""));
    } catch (e) {
      if (seq === loadSeq) setStatus(`Forecast unavailable: ${e.message}`, true);
    }
    getJSON("/api/engine/intraday_forecast/ledger?days=60").then(renderLedger).catch(() => {});
  }

  // Plotly measures its container when drawing; a hidden tab measures as the
  // 700px fallback, so re-measure once the panel is actually visible.
  function resizeSoon() {
    const node = el("ifc-chart");
    if (!window.Plotly || !node || !node.data) return;
    requestAnimationFrame(() => { if (node.offsetWidth > 0) window.Plotly.Plots.resize(node); });
  }

  if (window.ResizeObserver) {
    let lastW = 0;
    new ResizeObserver((entries) => {
      const w = Math.round(entries[0].contentRect.width);
      if (w > 0 && w !== lastW) { lastW = w; resizeSoon(); }
    }).observe(el("ifc-chart"));
  }

  let userPicked = false;  // never override a date the user chose
  el("ifc-date").value = defaultDay(new Set());
  const ready = holidaySet().then((closed) => {
    if (!userPicked) el("ifc-date").value = defaultDay(closed);
  });
  el("ifc-load").addEventListener("click", load);
  el("ifc-date").addEventListener("change", () => { userPicked = true; drawn = true; load(); });
  el("ifc-step").addEventListener("change", () => { drawn = true; load(); });
  // Draw on first visit to the KP tab rather than on page load.
  let drawn = false;
  const tabBtn = document.querySelector('[data-tab="tab-kp"]');
  const maybeDraw = () => {
    if (!drawn) { drawn = true; ready.then(load); } else { setTimeout(resizeSoon, 50); }
  };
  if (tabBtn) tabBtn.addEventListener("click", maybeDraw);
  if (location.hash === "#tab-kp") maybeDraw();
})();
