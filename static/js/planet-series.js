// Planet Motion panel (Forward Calendar tab): exact stations and a Plotly chart of
// declination / ecliptic latitude / speed (B-42, B-45). Data: /api/engine/stations
// and /api/engine/planet_series. Plotly is loaded on first use, not with the page.
(function () {
  const PLOTLY_SRC = "/static/vendor/plotly-basic-4.1.1.min.js";
  const el = (id) => document.getElementById(id);
  const form = el("pm-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const css = (name, fallback) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  const isoOf = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  // One colour per body (Plotly's default cycle repeats after ten).
  const COLORS = { Sun: "#f59e0b", Moon: "#94a3b8", Mercury: "#22c55e", Venus: "#ec4899", Mars: "#ef4444",
    Jupiter: "#eab308", Saturn: "#3b82f6", Uranus: "#06b6d4", Neptune: "#6366f1", Pluto: "#a16207",
    Rahu: "#a855f7", Ketu: "#f97316" };
  const TITLES = { declination: "Declination (°)", latitude: "Ecliptic latitude (°)", speed: "Speed (°/day)" };

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
    const s = el("pm-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function renderStations(d) {
    const rows = d.stations.map((s) => `
      <tr><td>${esc(s.time.replace("T", " "))}</td><td>${esc(s.planet)}${s.planet === "Rahu" ? " (true node)" : ""}</td>
        <td>${esc(s.direction)}</td></tr>`).join("");
    el("pm-stations").innerHTML = `
      <div class="analog-table-wrap">
        <table class="analog-table">
          <caption>Stations, IST, ${esc(d.zodiac)}: ${d.count} between ${esc(d.start)} and ${esc(d.end)}</caption>
          <thead><tr><th scope="col">Time (IST)</th><th scope="col">Planet</th><th scope="col">Turns</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="3">No stations in this range.</td></tr>`}</tbody>
        </table>
      </div>`;
  }

  function renderChart(Plotly, d) {
    const text = css("--text", "#e2e8f0");
    const grid = css("--line", "#1f2c47");
    const muted = css("--muted", "#94a3b8");
    const traces = d.planets.map((p) => ({
      type: "scatter", mode: "lines", name: p, x: d.dates, y: d.series[p], line: { color: COLORS[p], width: 1.5 },
      hovertemplate: `${p} %{y:.3f}<extra>%{x}</extra>`,
      // The Moon swamps the speed chart (~13°/day); start it hidden there.
      visible: d.metric === "speed" && p === "Moon" ? "legendonly" : true,
    }));
    const shapes = d.reference.values.map((v) => ({
      type: "line", xref: "paper", x0: 0, x1: 1, y0: v, y1: v,
      line: { color: v === 0 ? grid : muted, width: 1, dash: v === 0 ? "solid" : "dash" },
    }));
    const annotations = d.reference.values.filter((v) => v !== 0).map((v) => ({
      xref: "paper", x: 1, y: v, xanchor: "right", yanchor: v > 0 ? "bottom" : "top",
      text: `${d.reference.label} ${v > 0 ? "+" : ""}${v}°`, showarrow: false, font: { size: 10, color: muted },
    }));
    Plotly.react(el("pm-chart"), traces, {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", autosize: true,
      font: { color: text, size: 12 }, margin: { l: 56, r: 20, t: 30, b: 40 },
      hovermode: "x unified", legend: { orientation: "h", y: 1.1, x: 0, font: { size: 11 } },
      xaxis: { type: "date", gridcolor: grid },
      yaxis: { title: { text: TITLES[d.metric] }, gridcolor: grid, zeroline: false },
      shapes, annotations,
    }, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
  }

  async function getJson(url) {
    const r = await fetch(url);
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
  }

  async function run() {
    const params = new URLSearchParams({ start: el("pm-start").value, end: el("pm-end").value });
    setStatus("Loading…");
    try {
      const [st, series, Plotly] = await Promise.all([
        getJson(`/api/engine/stations?${params}`),
        getJson(`/api/engine/planet_series?${params}&metric=${encodeURIComponent(el("pm-metric").value)}`),
        loadPlotly(),
      ]);
      renderStations(st);
      renderChart(Plotly, series);
      setStatus(series.note);
    } catch (err) {
      setStatus(`Could not load planet motion: ${err.message}`, true);
    }
  }

  const now = new Date();
  el("pm-start").value = isoOf(new Date(now.getFullYear(), now.getMonth(), 1));
  el("pm-end").value = isoOf(new Date(now.getFullYear(), now.getMonth() + 1, 4));
  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  el("pm-metric").addEventListener("change", run);

  // Draw when the tab is first opened (Plotly needs a visible box to size itself).
  let drawn = false;
  const tab = document.querySelector('[data-tab="tab-calendar"]');
  const firstDraw = () => { if (!drawn) { drawn = true; run(); } };
  if (tab) tab.addEventListener("click", () => setTimeout(firstDraw, 0));
  if (el("tab-calendar")?.classList.contains("active")) firstDraw();
})();
