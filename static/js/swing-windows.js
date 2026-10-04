// Swing Windows tab (B-39): heliocentric aspect ENTRY -> technical-confluence EXIT (/api/engine/swing_windows).
(function () {
  const el = (id) => document.getElementById(id);
  const form = el("swing-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const pct = (x, d = 1) => (x == null || !isFinite(x) ? "–" : `${(x * 100).toFixed(d)}%`);
  const signed = (x, d = 2) => (x == null || !isFinite(x) ? "–" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`);
  const bps = (x) => (x == null || !isFinite(x) ? "–" : `${x >= 0 ? "+" : ""}${(x * 1e4).toFixed(1)} bps`);
  const cls = (x) => (x == null || !isFinite(x) || x === 0 ? "" : x > 0 ? "pos" : "neg");
  let chart = null;
  let observer = null;

  function setStatus(msg, isErr) {
    const s = el("swing-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function verdict(v) {
    if (!v) return `<p class="analog-note">No validation report yet. Run <code>scripts/validate_swing.py</code>.</p>`;
    const m = v.model || {};
    const rows = Object.entries(v.baselines || {}).map(([k, s]) =>
      `<tr><td>${esc(k)}</td><td class="num">${s.n}</td><td class="num">${pct(s.mean_return, 2)}</td>
        <td class="num">${pct(s.win_rate, 0)}</td><td class="num">${bps(s.mean_excess)}</td>
        <td class="num">${s.mean_bars == null ? "–" : s.mean_bars.toFixed(1)}</td></tr>`).join("");
    return `
      <div class="analog-card">
        <h3>Back-test 2008 onward: <strong>${esc(v.verdict)}</strong></h3>
        <p class="analog-note">Entry timing: ${v.entry_edges} of ${v.entry_tests} tests found an edge.
          Random entries with the same exit: p = ${v.random && v.random.p_value != null ? v.random.p_value.toFixed(3) : "–"}
          (${esc(v.report)}).</p>
        <div class="analog-table-wrap">
          <table class="analog-table">
            <thead><tr><th scope="col">Exit on the same entries</th><th scope="col">Trades</th><th scope="col">Mean</th>
              <th scope="col">Win</th><th scope="col">Excess over drift</th><th scope="col">Bars</th></tr></thead>
            <tbody>
              <tr><td><strong>Model (confluence)</strong></td><td class="num">${m.n ?? "–"}</td><td class="num">${pct(m.mean_return, 2)}</td>
                <td class="num">${pct(m.win_rate, 0)}</td><td class="num">${bps(m.mean_excess)}</td>
                <td class="num">${m.mean_bars == null ? "–" : m.mean_bars.toFixed(1)}</td></tr>
              ${rows}
            </tbody>
          </table>
        </div>
      </div>`;
  }

  function payloads(d) {
    const entries = JSON.stringify(d.entries);
    const exits = JSON.stringify(d.exits);
    return `
      <div class="analog-card">
        <h3>TradingView payloads</h3>
        <p class="analog-note">Paste into the inputs of <code>tools/tradingview/astro_swing_windows.pine</code>.</p>
        <label class="swing-payload">ENTRY <textarea readonly rows="3">${esc(entries)}</textarea></label>
        <label class="swing-payload">EXIT <textarea readonly rows="3">${esc(exits)}</textarea></label>
      </div>`;
  }

  function table(d) {
    if (!d.swings.length) return `<p class="analog-note">No swing windows in this range.</p>`;
    const rows = d.swings.map((s) => {
      const trig = Object.entries(s.triggers || {}).map(([k, v]) =>
        `${esc(k)}: ${esc([...new Set(v)].slice(0, 3).join(", "))}`).join("<br>");
      return `
        <tr>
          <td>${esc(s.pair)} ${esc(s.aspect)}<br><span class="muted">${esc(s.window_entry)} → ${esc(s.window_exit)}</span></td>
          <td>${esc(s.entry_session)}</td>
          <td>${s.direction > 0 ? "▲ long" : "▼ short"}</td>
          <td>${esc(s.exit_session)}</td>
          <td>${esc(s.exit_reason)}</td>
          <td class="num">${s.bars}</td>
          <td class="num ${cls(s.return)}">${signed(s.return)}</td>
          <td class="num">${signed(s.mae)}</td>
          <td class="swing-trig">${trig || "–"}</td>
        </tr>`;
    }).join("");
    return `
      <div class="analog-table-wrap">
        <table class="analog-table swing-table">
          <caption>Hypothetical swing windows, oldest first</caption>
          <thead><tr><th scope="col">Window</th><th scope="col">Entry</th><th scope="col">Side</th><th scope="col">Exit</th>
            <th scope="col">Reason</th><th scope="col">Bars</th><th scope="col">Return</th><th scope="col">Worst</th>
            <th scope="col">Exit triggers</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function draw(d) {
    const box = el("swing-chart");
    if (chart) { try { chart.remove(); } catch (e) { /* already gone */ } chart = null; }
    if (!window.LightweightCharts || !d.bars.length) { box.textContent = ""; return; }
    const css = getComputedStyle(document.body);
    chart = LightweightCharts.createChart(box, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: css.getPropertyValue("--muted") || "#94a3b8", fontSize: 11 },
      grid: { vertLines: { visible: false }, horzLines: { color: "rgba(148,163,184,.15)" } },
      timeScale: { timeVisible: false },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#22c55e", downColor: "#ef4444", wickUpColor: "#22c55e", wickDownColor: "#ef4444", borderVisible: false,
    });
    series.setData(d.bars.map((b) => ({ time: b.date, open: b.open, high: b.high, low: b.low, close: b.close })));
    const inRange = new Set(d.bars.map((b) => b.date));
    const markers = [];
    for (const s of d.swings) {
      if (inRange.has(s.entry_session)) {
        markers.push({ time: s.entry_session, position: s.direction > 0 ? "belowBar" : "aboveBar",
          color: "#14b8a6", shape: s.direction > 0 ? "arrowUp" : "arrowDown", text: `${s.aspect}` });
      }
      if (s.exit_reason !== "open" && inRange.has(s.exit_session)) {
        markers.push({ time: s.exit_session, position: s.direction > 0 ? "aboveBar" : "belowBar",
          color: "#f97316", shape: "circle", text: s.exit_reason === "confluence" ? "EXIT" : s.exit_reason });
      }
    }
    markers.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    series.setMarkers(markers);
    // Lightweight Charts keeps its bar spacing on resize; refit whenever the box changes width.
    const fit = () => chart && chart.timeScale().fitContent();
    fit();
    if (observer) observer.disconnect();
    if (window.ResizeObserver) {
      observer = new ResizeObserver(() => requestAnimationFrame(fit));
      observer.observe(box);
    }
  }

  async function run() {
    const params = new URLSearchParams({ confluence: el("swing-confluence").value });
    for (const [key, id] of [["start", "swing-start"], ["end", "swing-end"], ["planet", "swing-planet"], ["aspect", "swing-aspect"]]) {
      if (el(id).value) params.set(key, el(id).value);
    }
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    setStatus("Scanning aspects and simulating exits…");
    try {
      const r = await fetch(`/api/engine/swing_windows?${params}`);
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
      const s = d.summary;
      el("swing-results").innerHTML = `
        <div class="analog-grid">
          <div class="analog-card">
            <h3>${d.windows.length} aspect windows · ${d.swings.length} swing windows</h3>
            <dl class="analog-stats">
              <div><dt>Closed trades</dt><dd>${s.trades}</dd></div>
              <div><dt>Mean return</dt><dd class="${cls(s.mean_return)}">${signed(s.mean_return)}</dd></div>
              <div><dt>Win rate</dt><dd>${pct(s.win_rate, 0)}</dd></div>
              <div><dt>Confluence exits</dt><dd>${s.confluence_exits}</dd></div>
              <div><dt>Median bars</dt><dd>${s.median_bars ?? "–"}</dd></div>
            </dl>
            <p class="analog-note">${window.SBCFreshness ? SBCFreshness.badge(d.freshness, "NIFTY") : "NIFTY data as of " + esc(d.data_as_of)}. ${esc(d.caveat)}</p>
          </div>
          ${verdict(d.validation)}
        </div>
        ${payloads(d)}
        ${table(d)}`;
      draw(d);
      setStatus("");
    } catch (err) {
      setStatus(`Could not build swing windows: ${err.message}`, true);
    } finally {
      btn.disabled = false;
    }
  }

  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
  const yearAgo = new Date(Date.now() - 365 * 86400000).toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
  el("swing-start").value = yearAgo;
  el("swing-end").value = today;
  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  document.querySelector('[data-tab="tab-swing"]')?.addEventListener("click", () => {
    if (!el("swing-results").innerHTML.trim()) run();
  });
  if (window.location.hash === "#tab-swing") run();
})();
