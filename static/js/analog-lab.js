// Analog Lab: past NIFTY sessions with the most similar sky (/api/engine/analogs).
(function () {
  const el = (id) => document.getElementById(id);
  const form = el("analog-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const pct = (x, d = 1) => (x == null || !isFinite(x) ? "–" : `${(x * 100).toFixed(d)}%`);
  const signed = (x, d = 2) => (x == null || !isFinite(x) ? "–" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`);
  const cls = (x) => (x == null || !isFinite(x) || x === 0 ? "" : x > 0 ? "pos" : "neg");
  const todayIST = () => new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

  function setStatus(msg, isErr) {
    const s = el("analog-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function trackRecord(tr, horizon) {
    if (!tr) return `<p class="analog-note">No walk-forward report found. Run <code>scripts/validate_analogs.py</code>.</p>`;
    const eras = Object.entries(tr.eras || {}).map(([k, v]) => `${esc(k)}: ${signed(v, 2)}`).join(" · ");
    return `
      <div class="analog-card">
        <h3>Track record of this setting (${horizon}-session horizon)</h3>
        <dl class="analog-stats">
          <div><dt>Verdict</dt><dd><strong>${esc(tr.verdict)}</strong></dd></div>
          <div><dt>Hit rate</dt><dd>${pct(tr.hit_rate)} <span class="muted">vs ${pct(tr.baseline)} by chance</span></dd></div>
          <div><dt>Excess per call</dt><dd class="${cls(tr.excess)}">${signed(tr.excess, 2)}</dd></div>
          <div><dt>q-value</dt><dd>${tr.q == null ? "–" : tr.q.toFixed(3)}</dd></div>
          <div><dt>By era</dt><dd>${eras}</dd></div>
          <div><dt>Years ahead</dt><dd>${tr.years_right}/${tr.years}</dd></div>
        </dl>
        <p class="analog-note">Walk-forward ${esc(tr.sample.first)} → ${esc(tr.sample.last)} (${esc(tr.report)}).</p>
      </div>`;
  }

  function summary(d) {
    const s = d.summary;
    if (!s) return `<p class="analog-note">No eligible history before this date.</p>`;
    const lean = s.lean > 0 ? "above" : s.lean < 0 ? "below" : "in line with";
    return `
      <div class="analog-card">
        <h3>What followed the ${s.n} analogs over ${d.horizon} session${d.horizon > 1 ? "s" : ""}</h3>
        <dl class="analog-stats">
          <div><dt>Average</dt><dd class="${cls(s.mean)}">${signed(s.mean)}</dd></div>
          <div><dt>Median</dt><dd class="${cls(s.median)}">${signed(s.median)}</dd></div>
          <div><dt>Middle half</dt><dd>${signed(s.q25)} to ${signed(s.q75)}</dd></div>
          <div><dt>Up share</dt><dd>${pct(s.up_share, 0)} <span class="muted">vs ${pct(s.base_up_share, 0)} for all sessions</span></dd></div>
          <div><dt>Versus all sessions</dt><dd class="${cls(s.excess)}">${signed(s.excess)} (${lean} the usual ${signed(s.base_mean)})</dd></div>
          <div><dt>Best match</dt><dd>${pct(d.best_similarity, 0)} similar</dd></div>
        </dl>
        <p class="analog-note">${d.mode === "threshold" ? "All sessions above the similarity threshold." : `The ${s.n} most similar sessions, at least 5 sessions apart.`}
          Searched ${d.pool.toLocaleString()} sessions whose outcome was known before ${esc(d.target)}. ${window.SBCFreshness ? SBCFreshness.badge(d.freshness, "Market") : "Market data as of " + esc(d.data_as_of)}</p>
      </div>`;
  }

  function table(d) {
    const hs = ["1", "5", "20"];
    const rows = d.analogs.map((a) => `
      <tr>
        <td>${esc(a.date)}</td>
        <td class="num">${a.age_years}</td>
        <td class="num">${pct(a.similarity, 0)}</td>
        <td class="num">${pct(a.tiers.slow, 0)}</td>
        <td class="num">${pct(a.tiers.medium, 0)}</td>
        <td class="num">${pct(a.tiers.fast, 0)}</td>
        <td>${esc(a.same_sign.join(", ")) || "–"}</td>
        ${hs.map((h) => `<td class="num ${cls(a.forward[h])}">${signed(a.forward[h])}</td>`).join("")}
      </tr>`).join("");
    return `
      <div class="analog-table-wrap">
        <table class="analog-table">
          <caption>Analogs of ${esc(d.target)}, most similar first</caption>
          <thead><tr>
            <th scope="col">Date</th><th scope="col">Years ago</th><th scope="col">Similar</th>
            <th scope="col">Slow</th><th scope="col">Medium</th><th scope="col">Fast</th>
            <th scope="col">Same sign</th><th scope="col">+1</th><th scope="col">+5</th><th scope="col">+20</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  async function run() {
    const params = new URLSearchParams({
      date: el("analog-date").value,
      horizon: el("analog-horizon").value,
      variant: el("analog-variant").value,
      k: el("analog-k").value,
    });
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    setStatus("Searching history…");
    try {
      const r = await fetch(`/api/engine/analogs?${params}`);
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
      el("analog-results").innerHTML =
        `<div class="analog-grid">${summary(d)}${trackRecord(d.track_record, d.horizon)}</div>${table(d)}`;
      setStatus("");
    } catch (err) {
      setStatus(`Could not load analogs: ${err.message}`, true);
    } finally {
      btn.disabled = false;
    }
  }

  el("analog-date").value = todayIST();
  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  document.querySelector('[data-tab="tab-analogs"]')?.addEventListener("click", () => {
    if (!el("analog-results").innerHTML.trim()) run();
  });
  if (window.location.hash === "#tab-analogs") run();
})();
