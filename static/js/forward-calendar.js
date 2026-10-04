// Forward Calendar tab: the next weeks of NIFTY sessions with their sky events (/api/engine/calendar).
(function () {
  const el = (id) => document.getElementById(id);
  const form = el("calendar-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const num = (x) => (x == null ? "–" : Number(x).toLocaleString("en-IN", { maximumFractionDigits: 0 }));
  const band = (b) => (b ? `${num(b[0])} – ${num(b[1])}` : "–");
  const arrow = (v) => (v > 0 ? "▲" : v < 0 ? "▼" : "·");

  function setStatus(msg, isErr) {
    const s = el("calendar-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function weeks(c) {
    const rows = c.weeks.map((w) => `
      <tr><td>${esc(w.start)} → ${esc(w.end)}</td><td class="num">${w.sessions}</td>
        <td class="num">${band(w.band_68)}</td><td class="num">${w.events}</td></tr>`).join("");
    return `
      <div class="analog-table-wrap">
        <table class="analog-table">
          <caption>${window.SBCFreshness ? SBCFreshness.badge(c.freshness, "NIFTY") + " " : ""}Weekly 68% range (VIX ${c.vix == null ? "–" : c.vix.toFixed(2)}, from the ${esc(c.data_as_of)} close of ${num(c.entry_close)})</caption>
          <thead><tr><th scope="col">Week</th><th scope="col">Sessions</th><th scope="col">68% range at week end</th>
            <th scope="col">Sky events</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function days(c) {
    const rows = c.days.map((d) => {
      const events = d.events.map(esc).join("<br>") || "";
      if (!d.trading) {
        return `<tr class="cal-closed"><td>${esc(d.date)} ${esc(d.weekday)}</td><td colspan="4">${esc(d.holiday || "closed")}</td>
          <td class="cal-events">${events}</td></tr>`;
      }
      const a = d.analogs;
      return `
        <tr>
          <td>${esc(d.date)} ${esc(d.weekday)}</td>
          <td>${esc(d.moon)}<br><span class="muted">${esc(d.tithi)}</span></td>
          <td class="num">${d.rules.up}▲ ${d.rules.down}▼</td>
          <td>O${arrow(a.overall)} S${arrow(a.slow)} M${arrow(a.medium)} F${arrow(a.fast)}</td>
          <td>${esc(d.flags.map((f) => f.replace(/_volatility$/, "")).join(", ")) || "–"}</td>
          <td class="cal-events">${events}</td>
        </tr>`;
    }).join("");
    return `
      <div class="analog-table-wrap">
        <table class="analog-table cal-days">
          <caption>Day by day. Rules: directional rules and factors leaning up / down. Analogs: whole-sky, slow, medium, fast.</caption>
          <thead><tr><th scope="col">Day</th><th scope="col">Moon · tithi</th><th scope="col">Rules</th>
            <th scope="col">Analogs</th><th scope="col">Volatility flags</th><th scope="col">Sky events</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  async function stored() {
    try {
      const r = await fetch("/api/engine/calendar/reports");
      const d = await r.json();
      const list = (d.reports || []).slice(0, 8).map((x) =>
        `<a href="/api/engine/calendar/reports/${encodeURIComponent(x.html)}" target="_blank" rel="noopener">${esc(x.key)}</a>`);
      el("calendar-stored").innerHTML = list.length
        ? `Weekly copies: ${list.join(" · ")}`
        : "No weekly copy yet. The server writes one every Saturday from 08:00 IST.";
    } catch (err) {
      el("calendar-stored").textContent = "";
    }
  }

  async function run() {
    const params = new URLSearchParams({ weeks: el("calendar-weeks").value });
    if (el("calendar-start").value) params.set("start", el("calendar-start").value);
    el("calendar-open-html").href = `/api/engine/calendar?${params}&format=html`;
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    setStatus("Building calendar…");
    try {
      const r = await fetch(`/api/engine/calendar?${params}`);
      const c = await r.json().catch(() => ({}));
      if (!r.ok || c.error) throw new Error(c.error || `HTTP ${r.status}`);
      el("calendar-results").innerHTML = weeks(c) + days(c);
      setStatus(`${c.start} → ${c.end} · generated ${c.generated_at}`);
    } catch (err) {
      setStatus(`Could not build the calendar: ${err.message}`, true);
    } finally {
      btn.disabled = false;
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  document.querySelector('[data-tab="tab-calendar"]')?.addEventListener("click", () => {
    if (!el("calendar-results").innerHTML.trim()) { run(); stored(); }
  });
  if (window.location.hash === "#tab-calendar") { run(); stored(); }
})();
