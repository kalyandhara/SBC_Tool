// Bullion Week tab (/api/engine/bullion-week), B-56: MCX gold and silver, Monday to Friday.
(function () {
  const el = (id) => document.getElementById(id);
  const form = el("bw-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const STAR_LORD = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"];
  const STARS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya",
    "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "P.Ashadha", "U.Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "P.Bhadrapada",
    "U.Bhadrapada", "Revati"];
  const lordOf = (n) => STAR_LORD[STARS.indexOf(n) % 9] || "";
  const ARROW = { up: "↑", down: "↓", volatile: "⇄", stable: "→", none: "–" };
  const dlabel = (iso, opt) => new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-GB", { timeZone: "UTC", ...opt });
  const t12 = (hm) => {
    let [h, m] = hm.split(":").map(Number);
    const ap = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")} ${ap}`;
  };
  let W = null;
  let current = 0;

  function setStatus(msg, isErr) {
    const s = el("bw-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function clip(subs, [s0, s1]) {
    return subs.map((s) => ({ ...s, ca: Math.max(s.a, s0), cb: Math.min(s.b, s1) })).filter((s) => s.cb > s.ca);
  }

  function week() {
    el("bw-week").innerHTML = W.days.map((d, i) => {
      const sess = d.session || W.session;
      const [s0, s1] = sess;
      const bar = clip(d.subs, sess).map((s) =>
        `<i class="bw-${s.tone}" style="width:${((s.cb - s.ca) / (s1 - s0)) * 100}%" title="${esc(s.from)}–${esc(s.to)} ${esc(s.lord)}"></i>`).join("");
      const enters = d.padas.find((p) => p.enters && p.time > d.sunrise);
      const econ = W.econ.filter((e) => e.date === d.date);
      return `<button type="button" class="bw-daycard" data-i="${i}" aria-pressed="${i === current}">
        <span class="bw-dayname"><b>${esc(d.weekday.slice(0, 3))} ${esc(dlabel(d.date, { day: "numeric" }))}</b><span class="muted">${esc(d.tithi)}</span></span>
        <span class="bw-line">Moon in <b>${esc(d.moon_nakshatra)}</b>${enters ? ` → <b>${esc(enters.nakshatra)}</b> ${esc(enters.time)}` : ""}</span>
        <span class="bw-line">Rahu Kaal <b class="num">${esc(d.rahu_kaal.from)}–${esc(d.rahu_kaal.to)}</b></span>
        <span class="bw-bar" aria-hidden="true">${bar}</span>
        <span class="bw-ticks muted"><span>09:00</span><span>16:00</span><span>${esc((d.session_label || "09:00–23:30").slice(-5))}</span></span>
        ${econ.length ? `<span class="bw-line bw-econ">US data: ${econ.map((e) => esc(e.name.replace(/^US /, ""))).join(", ")}</span>` : ""}
      </button>`;
    }).join("") + `<div class="ta-legend bw-legend" aria-hidden="true">
      <span><i class="bw-up"></i>Positive direction</span><span><i class="bw-down"></i>Pressure</span>
      <span><i class="bw-volatile"></i>Volatility</span><span><i class="bw-stable"></i>Stability / range</span>
      <span><i class="bw-none"></i>No rule</span><span>Bar: MCX session (09:00 to 23:30 IST, 23:55 when the US is on standard time), by the Moon's KP sub-lord</span></div>`;
  }

  function record(naks) {
    const parts = ["gold", "silver"].map((asset) => {
      const t = W.track[asset];
      if (!t || !t.available) return `<p class="muted">No ${asset} history found in data/${asset}_ohlc.csv.</p>`;
      const rows = naks.map((n) => {
        const r = t.by_nakshatra[n];
        if (!r || !r.sessions) return `<tr><td>${esc(n)}</td><td colspan="3" class="muted">no sessions</td></tr>`;
        const sig = r.p_value < 0.05;
        return `<tr><td>${esc(n)} <span class="muted">(${esc(lordOf(n))})</span></td>
          <td class="num">${r.up} up · ${r.down} down</td><td class="num">${Math.round(r.up_rate * 100)}%</td>
          <td class="num${sig ? " bw-sig" : ""}">${r.p_value.toFixed(2)}</td></tr>`;
      }).join("");
      const lagDays = Math.round((new Date(`${W.week_of}T00:00:00Z`) - new Date(`${t.as_of}T00:00:00Z`)) / 864e5);
      const stale = lagDays > 7
        ? `<p class="bw-stale">${asset[0].toUpperCase() + asset.slice(1)} prices end ${esc(t.as_of)}, ${lagDays} days before this week. Refresh data/${asset}_ohlc.csv for a current record.</p>`
        : "";
      return stale + `<table class="analog-table bw-track">
        <caption>${asset[0].toUpperCase() + asset.slice(1)}: last 50 sessions per nakshatra to ${esc(t.as_of)}. Base rate ${Math.round(t.base_up_rate * 100)}% up.</caption>
        <thead><tr><th scope="col">Nakshatra</th><th scope="col">Closes</th><th scope="col">Up</th><th scope="col">p vs base</th></tr></thead>
        <tbody>${rows}</tbody></table>`;
    });
    return parts.join("") + `<p class="muted">Session nakshatra is the Moon's at 09:15 IST. p is a two-sided binomial test against the base rate, uncorrected; with 27 nakshatras, one in twenty will show p &lt; 0.05 by chance.</p>`;
  }

  function day(i) {
    current = i;
    el("bw-week").querySelectorAll(".bw-daycard").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.i === i)));
    const d = W.days[i];
    const [s0, s1] = d.session || W.session;
    const horas = ["Jupiter", "Venus", "Mercury", "Saturn"].map((lord) => {
      const h = d.horas.filter((x) => x.lord === lord && x.b > s0 && x.a < s1);
      return h.length ? `<dt>${lord} hora</dt><dd class="num">${h.map((x) => `${esc(x.from)}–${esc(x.to)}`).join("<br>")}</dd>` : "";
    }).join("");
    const moon = `<dt>At sunrise</dt><dd>${esc(d.moon_nakshatra)} · ${esc(d.moon_sign)}</dd>` +
      d.padas.map((p) => `<dt class="num">${esc(p.time)}</dt><dd>${p.enters ? `<b>Enters ${esc(p.nakshatra)}</b>` : esc(p.nakshatra)} pada ${p.pada}</dd>`).join("");
    const naks = [...new Set([d.session_nakshatra, d.moon_nakshatra, ...d.padas.map((p) => p.nakshatra)])];
    const econ = W.econ.filter((e) => e.date === d.date);
    const rows = d.subs.map((s) => {
      const off = s.b <= s0 || s.a >= s1;
      const rk = !off && s.a < d.rahu_kaal.b && s.b > d.rahu_kaal.a;
      return `<tr class="${off ? "bw-off" : ""}"><td class="num">${t12(s.from)} – ${t12(s.to)}</td>
        <td><b>${esc(s.lord)}</b></td>
        <td class="bw-t-${s.tone}">${ARROW[s.tone]} ${esc(s.reading)}</td>
        <td>${esc(s.guidance)}${rk ? ' · <span class="bw-t-down">overlaps Rahu Kaal</span>' : ""}${off ? " · outside session" : ""}</td></tr>`;
    }).concat(econ.map((e) => `<tr><td class="num">${t12(e.time)}</td><td><b>US data</b></td>
      <td class="bw-t-volatile">⚑ ${esc(e.name)}</td><td>Event risk; spreads often widen</td></tr>`)).join("");
    el("bw-day").innerHTML = `
      <div class="bw-dayhead"><h3>${esc(dlabel(d.date, { weekday: "long", day: "numeric", month: "long", year: "numeric" }))}</h3>
        <span class="muted">Sunrise ${esc(d.sunrise)} · Sunset ${esc(d.sunset)} · ${esc(d.tithi)} · session nakshatra ${esc(d.session_nakshatra)}</span></div>
      <div class="bw-cols">
        <div class="bw-box"><h4>Important timings</h4><dl class="bw-kv"><dt>Rahu Kaal</dt><dd class="num bw-t-down"><b>${esc(d.rahu_kaal.from)}–${esc(d.rahu_kaal.to)}</b></dd>${horas}</dl></div>
        <div class="bw-box"><h4>Moon transit</h4><dl class="bw-kv">${moon}</dl></div>
        <div class="bw-box"><h4>Nakshatra record</h4>${record(naks)}</div>
      </div>
      <div class="analog-table-wrap">
        <table class="analog-table bw-timeline">
          <caption>Intraday timeline by the Moon's KP sub-lord. Readings are the source sheet's rules, untested.</caption>
          <thead><tr><th scope="col">Time (IST)</th><th scope="col">Sub-lord</th><th scope="col">Traditional reading</th><th scope="col">Guidance</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function context() {
    const all = W.events.map((e) => ({ ...e })).concat(W.econ.map((e) => ({ date: e.date, time: e.time, text: e.name })))
      .sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
    const ev = all.map((e) => `<tr><td class="num">${esc(dlabel(e.date, { weekday: "short", day: "numeric", month: "short" }))} ${esc(e.time)}</td><td>${esc(e.text)}</td></tr>`).join("");
    const pos = W.positions.map((p) => `<span class="bw-pos"><span class="muted">${esc(p.name)}</span> ${esc(p.sign)} ${p.degree}°${p.retrograde ? " ℞" : ""}</span>`).join("");
    el("bw-context").innerHTML = `
      <div class="analog-table-wrap"><table class="analog-table"><caption>This week's events (IST)</caption>
        <thead><tr><th scope="col">When</th><th scope="col">Event</th></tr></thead><tbody>${ev || '<tr><td colspan="2">None</td></tr>'}</tbody></table></div>
      <div><p class="muted bw-poshead">Planets at Monday sunrise (sidereal, Lahiri)</p><div class="bw-positions">${pos}</div>
        <p class="muted">US releases come from data/econ_events.json. Add each week's dates there with times in IST.</p></div>`;
  }

  async function run() {
    const start = el("bw-start").value;
    setStatus("Building the week…");
    try {
      const r = await fetch(`/api/engine/bullion-week${start ? `?start=${encodeURIComponent(start)}` : ""}`);
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
      W = d;
      el("bw-start").value = d.week_of;
      const today = new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 10);
      current = Math.max(0, d.days.findIndex((x) => x.date === today));
      week();
      day(current);
      context();
      setStatus(`${d.week_of} → ${d.end} · ${d.location} · ${d.zodiac}`);
    } catch (err) {
      setStatus(`Could not build the week: ${err.message}`, true);
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  el("bw-week").addEventListener("click", (e) => {
    const b = e.target.closest(".bw-daycard");
    if (b) day(+b.dataset.i);
  });
  document.querySelector('[data-tab="tab-bullion"]')?.addEventListener("click", () => { if (!W) run(); });
  if (window.location.hash === "#tab-bullion") run();
})();
