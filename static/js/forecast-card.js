// Evidence card on the Executive Overview: the next session's NIFTY forecast (/api/engine/forecast/card).
(function () {
  const box = document.getElementById("forecast-evidence-body");
  if (!box) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const pct = (x, d = 1) => (x == null || !isFinite(x) ? "–" : `${(x * 100).toFixed(d)}%`);
  const num = (x) => (x == null ? "–" : Number(x).toLocaleString("en-IN", { maximumFractionDigits: 0 }));
  const band = (b) => (b ? `${num(b[0])} – ${num(b[1])}` : "–");
  const lean = (c) => {
    if (c.kind === "event") return c.flag ? "flag on" : "–";
    return c.lean > 0 ? "▲ up" : c.lean < 0 ? "▼ down" : "· none";
  };

  function record(tr) {
    if (!tr || !tr.scored) return `${tr ? tr.frozen : 0} frozen, none scored yet`;
    const better = tr.brier < tr.base_brier;
    return `${tr.scored} scored · Brier ${tr.brier.toFixed(3)} vs ${tr.base_brier.toFixed(3)} base ` +
      `<span class="${better ? "pos" : "neg"}">(${better ? "better" : "worse"})</span>`;
  }

  function tiles(d) {
    return ["1", "5", "20"].map((h) => {
      const x = d.horizons[h];
      const moved = Math.abs(x.probability_up - x.base_up) > 1e-4;
      return `
        <div class="fe-tile">
          <span class="fe-label">${h} session${h === "1" ? "" : "s"}</span>
          <strong class="fe-prob">${pct(x.probability_up)} <small>chance up</small></strong>
          <span class="fe-sub">${moved ? `base rate ${pct(x.base_up)}` : "= historical base rate"}</span>
          <span class="fe-sub">68% range ${band(x.band_68)}</span>
          <span class="fe-sub">95% range ${band(x.band_95)}</span>
          <span class="fe-sub">Live record: ${record(x.track_record)}</span>
        </div>`;
    }).join("");
  }

  function evidence(d) {
    const rows = d.components.map((c) => `
      <tr>
        <td title="${esc(c.description)}">${esc(c.name)}</td>
        <td>${lean(c)}</td>
        <td>${esc(c.verdict || "–")}</td>
        <td>${esc(c.beyond_market || "–")}</td>
        <td>${c.validated ? "yes" : "no"}</td>
      </tr>`).join("");
    return `
      <details class="fe-details">
        <summary>Evidence: what each rule and analog set says (${d.components_horizon}-session tests)</summary>
        <div class="analog-table-wrap">
          <table class="analog-table">
            <thead><tr><th scope="col">Component</th><th scope="col">Today</th><th scope="col">Historical test</th>
              <th scope="col">Beyond market conditions</th><th scope="col">Counts?</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </details>`;
  }

  function sky(s) {
    const parts = [`Moon ${esc(s.moon)}`, esc(s.tithi)];
    if (s.retrograde.length) parts.push(`retrograde: ${esc(s.retrograde.join(", "))}`);
    if (s.exact_aspects.length) parts.push(esc(s.exact_aspects.slice(0, 3).join("; ")));
    if (s.eclipse) parts.push(esc(s.eclipse));
    if (s.bhadra_at_open) parts.push("Bhadra at the open");
    return parts.join(" · ");
  }

  function render(d) {
    const v = Object.values(d.validation || {});
    const passed = v.reduce((a, x) => a + x.passed, 0);
    const tests = v.reduce((a, x) => a + x.tests, 0);
    document.getElementById("forecast-evidence-date").textContent = d.date;
    box.innerHTML = `
      <div class="fe-tiles">${tiles(d)}</div>
      <p class="fe-note"><strong>${passed} of ${tests}</strong> astro tests have passed so far, so the chance shown is the
        historical base rate. The range comes from India VIX (${d.vix == null ? "–" : d.vix.toFixed(2)}) and NIFTY's close of ${num(d.entry_close)}
        on ${esc(d.entry_date)}. ${window.SBCFreshness ? SBCFreshness.badge(d.freshness, "NIFTY") : "Data as of " + esc(d.data_as_of)}</p>
      <p class="fe-note">Sky: ${sky(d.sky)}</p>
      ${evidence(d)}
      <p class="fe-note">${esc(d.caveat)}</p>`;
  }

  async function load() {
    try {
      const r = await fetch("/api/engine/forecast/card");
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
      render(d);
    } catch (err) {
      box.innerHTML = `<p class="fe-note error">Forecast unavailable: ${esc(err.message)}</p>`;
    }
  }

  document.getElementById("forecast-evidence-calendar")?.addEventListener("click", () => {
    document.querySelector('[data-tab="tab-calendar"]')?.click();
  });
  load();
})();
