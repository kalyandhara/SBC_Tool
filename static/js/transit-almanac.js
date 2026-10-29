// Transit Almanac section of the Forward Calendar tab (/api/engine/transit-almanac), B-55.
(function () {
  const el = (id) => document.getElementById(id);
  const form = el("ta-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
  const ELEM = ["fire", "earth", "air", "water"];
  const MEAN = {
    Mercury: "communication, travel, contracts, news and decision-making",
    Venus: "money, relationships, values and what people buy",
    Mars: "action, energy, aggression, conflict and risk-taking",
    Jupiter: "growth, optimism, expansion, luck and excess",
    Saturn: "limits, discipline, delays, structure and hard lessons",
    Uranus: "sudden change, surprises, technology and rebellion",
    Neptune: "dreams, confusion, illusion, speculation and inspiration",
    Pluto: "power, transformation, deep hidden forces and crises",
    Nodes: "collective direction and turning points",
  };
  const FLAVOUR = {
    Aries: "bold, impulsive and pioneering", Taurus: "slow, steady and money-minded",
    Gemini: "talkative, curious and scattered", Cancer: "protective, emotional and home-focused",
    Leo: "confident, dramatic and proud", Virgo: "careful, analytical and practical",
    Libra: "balanced, diplomatic and partnership-minded", Scorpio: "intense, secretive and probing",
    Sagittarius: "expansive, optimistic and restless", Capricorn: "disciplined, ambitious and cautious",
    Aquarius: "independent, unconventional and collective", Pisces: "dreamy, sensitive and diffuse",
  };
  const ASPECT = {
    conjunction: ["merge: their themes fuse and intensify", "conj"],
    sextile: ["cooperate easily: mild opportunities and a helpful flow", "easy"],
    trine: ["flow together smoothly: ease, support and good luck", "easy"],
    square: ["clash: tension, friction and pressure that forces action", "tense"],
    opposition: ["pull against each other: tug-of-war and showdowns", "tense"],
  };
  const FAST = new Set(["Venus", "Mercury"]);
  const FAST_ROWS = new Set(["Mars", "Venus", "Mercury"]);
  let data = null;
  let filter = "all";

  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const dm = (d) => `${d.slice(8)}-${d.slice(5, 7)}`;
  const shown = (e) => e.type !== "aspect" || el("ta-fast").checked || !FAST.has(e.body);

  function setStatus(msg, isErr) {
    const s = el("ta-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function short(e) {
    if (e.type === "station") return e.kind;
    if (e.type === "ingress") return e.back && e.body !== "Nodes" ? `back to ${e.sign}` : `→ ${e.sign}`;
    if (e.type === "aspect") return `${e.aspect} ${e.other}`;
    return `${e.kind} eclipse`;
  }

  function title(e) {
    if (e.type === "station") return `${e.body} ${e.kind.toLowerCase() === "retrograde" ? "turns retrograde" : "turns direct"}`;
    if (e.type === "ingress") {
      if (e.body === "Nodes") return `Nodes enter ${e.sign}/${SIGNS[(SIGNS.indexOf(e.sign) + 6) % 12]}`;
      return `${e.body} ${e.back ? "re-enters" : "enters"} ${e.sign}`;
    }
    if (e.type === "aspect") return `${e.body} ${e.aspect} ${e.other}`;
    return `${e.kind} eclipse in ${e.sign}`;
  }

  function meaning(e) {
    if (e.type === "station") {
      return e.kind === "Retrograde"
        ? `${e.body} stations retrograde at ${e.degree}° ${e.sign}. Until it turns direct, ${MEAN[e.body]} tend to slow down, get delayed or revisited.`
        : `${e.body} stations direct at ${e.degree}° ${e.sign}. Delays around ${MEAN[e.body]} start to clear.`;
    }
    if (e.type === "ingress") {
      if (e.body === "Nodes") return `The nodes move into the ${e.sign} axis. For about 18 months eclipses fall in these signs.`;
      return `${e.body} ${e.back ? "slips back into" : "enters"} ${e.sign}. While it stays, ${MEAN[e.body]} take on a ${FLAVOUR[e.sign]} flavour.`;
    }
    if (e.type === "aspect") {
      return `Exact at ${e.degree}° ${e.sign}${e.other_retro ? `, ${e.other} retrograde` : ""}. The two ${ASPECT[e.aspect][0]}. Mixes ${MEAN[e.body]} with ${MEAN[e.other]}.`;
    }
    return e.kind === "Solar"
      ? `New Moon on the nodes at ${e.degree}° ${e.sign}. Traditionally a reset: beginnings, endings, sudden news.`
      : `Full Moon on the nodes at ${e.degree}° ${e.sign}. Traditionally a peak: things come to a head or are revealed.`;
  }

  function tone(e) {
    if (e.type === "aspect") return ASPECT[e.aspect][1];
    if (e.type === "station") return e.kind === "Retrograde" ? "tense" : "easy";
    if (e.type === "eclipse") return e.kind === "Solar" ? "conj" : "tense";
    return null;
  }

  function draw() {
    if (!data) return;
    const B = data.bodies;
    const W = 1400, L = 140, R = 100, top = 40, row = 92, H = top + row * B.length + 26;
    const X = (t) => L + t * (W - L - R);
    const c = {
      fire: css("--ta-fire"), earth: css("--ta-earth"), air: css("--ta-air"), water: css("--ta-water"),
      tense: css("--ta-fire"), easy: css("--ta-water"), conj: css("--ta-air"),
      text: css("--text"), muted: css("--muted"), line: css("--line"), panel: css("--panel"), accent: css("--accent"),
    };
    const y0 = Date.UTC(data.year, 0, 1), y1 = Date.UTC(data.year + 1, 0, 1);
    let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Transit timeline ${data.year}">`;
    for (let m = 0; m <= 12; m++) {
      const x = X((Date.UTC(data.year, m, 1) - y0) / (y1 - y0));
      s += `<line x1="${x}" x2="${x}" y1="${top - 12}" y2="${H - 20}" stroke="${c.line}"/>`;
      if (m < 12) s += `<text x="${x + 4}" y="${top - 18}" font-size="11" fill="${c.muted}">${new Date(Date.UTC(2000, m, 1)).toLocaleString("en", { month: "short", timeZone: "UTC" })}</text>`;
    }
    const now = new Date();
    if (now.getFullYear() === data.year) {
      const x = X((now - y0) / (y1 - y0));
      s += `<line x1="${x}" x2="${x}" y1="${top - 12}" y2="${H - 20}" stroke="${c.accent}" stroke-dasharray="3 3"/>
        <text x="${x}" y="${H - 6}" text-anchor="middle" font-size="11" fill="${c.accent}">today</text>`;
    }
    B.forEach((b, i) => {
      const y = top + i * row + row * 0.62;
      s += `<text x="${L - 12}" y="${y + 1}" text-anchor="end" font-size="14" font-weight="600" fill="${c.text}">${esc(b.name)}</text>
        <text x="${L - 12}" y="${y + 16}" text-anchor="end" font-size="10.5" fill="${c.muted}">${esc(b.start)}</text>
        <text x="${W - R + 8}" y="${y + 4}" font-size="10.5" fill="${c.muted}">${esc(b.end)}</text>`;
      b.segments.forEach((g) => {
        s += `<line x1="${X(g.a)}" x2="${X(g.b)}" y1="${y}" y2="${y}" stroke="${c[ELEM[g.sign % 4]]}" stroke-width="${g.retro ? 4 : 5}"${g.retro ? ' stroke-dasharray="2 5" stroke-linecap="round"' : ""}><title>${SIGNS[g.sign]}${g.retro ? " (retrograde)" : ""}</title></line>`;
      });
      const lanes = [];
      b.events.filter(shown).forEach((e) => {
        const x = X(e.t);
        const tip = `<title>${esc(dm(e.date))} · ${esc(title(e))}. ${esc(meaning(e))}</title>`;
        if (e.type === "ingress") {
          s += `<g>${tip}<line x1="${x}" x2="${x}" y1="${y - 7}" y2="${y + 7}" stroke="${c.text}" stroke-width="2"/>
            <text x="${x}" y="${y + 20}" text-anchor="middle" font-size="10" fill="${c[ELEM[SIGNS.indexOf(e.sign) % 4]]}">${esc(short(e))}</text>
            <text x="${x}" y="${y + 31}" text-anchor="middle" font-size="9.5" fill="${c.muted}">${dm(e.date)}</text></g>`;
          return;
        }
        let mark;
        if (e.type === "station") mark = `<rect x="${x - 5}" y="${y - 5}" width="10" height="10" transform="rotate(45 ${x} ${y})" fill="${c[tone(e)]}" stroke="${c.panel}"/>`;
        else if (e.type === "aspect") mark = `<path d="M${x - 6} ${y + 2} L${x} ${y - 9} L${x + 6} ${y + 2}Z" fill="${c[tone(e)]}" stroke="${c.panel}"/>`;
        else mark = `<circle cx="${x}" cy="${y}" r="6" fill="${c[tone(e)]}" stroke="${c.panel}" stroke-width="1.5"/>`;
        let lane = 0;
        if (!(e.type === "aspect" && FAST_ROWS.has(b.name))) {
          while (lanes[lane] !== undefined && x - lanes[lane] < 70) lane++;
          lanes[lane] = x;
        }
        const ly = y - 15 - lane * 20;
        // B-74: fast planets have many aspects; show their marker only (details in the
        // tooltip and the ledger) so the Mars, Venus and Mercury rows stay readable.
        const quiet = e.type === "aspect" && FAST_ROWS.has(b.name);
        if (lane < 3 && !quiet) {
          s += `<line x1="${x}" x2="${x}" y1="${ly + 3}" y2="${y - 8}" stroke="${c.line}"/>
            <text x="${x}" y="${ly - 7}" text-anchor="middle" font-size="10" fill="${c.text}">${esc(short(e))}</text>
            <text x="${x}" y="${ly + 2}" text-anchor="middle" font-size="9.5" fill="${c.muted}">${dm(e.date)}</text>`;
        }
        s += `<g class="ta-mark">${tip}${mark}</g>`;
      });
    });
    el("ta-chart").innerHTML = s + "</svg>";
  }

  function ledger() {
    if (!data) return;
    const today = new Date().toISOString().slice(0, 10);
    const rows = data.bodies.flatMap((b) => b.events.map((e) => ({ ...e, body: e.body || "Nodes" })))
      .filter(shown).filter((e) => filter === "all" || e.type === filter)
      .sort((a, b) => a.t - b.t);
    let marked = false;
    const html = rows.map((e) => {
      let cls = e.date < today ? "ta-past" : "";
      if (!marked && e.date >= today && String(data.year) === today.slice(0, 4)) { cls = "ta-next"; marked = true; }
      const t = tone(e);
      return `<tr class="${cls}"><td class="num">${esc(dm(e.date))}-${esc(e.date.slice(0, 4))}</td>
        <td>${esc(title(e))}${t ? ` <span class="ta-pill ta-${t}">${t === "conj" ? "merge" : t}</span>` : ""}</td>
        <td class="ta-meaning">${esc(meaning(e))}</td></tr>`;
    }).join("");
    el("ta-ledger").innerHTML = `
      <div class="analog-table-wrap">
        <table class="analog-table ta-table">
          <caption>${esc(data.year)} · ${esc(data.zodiac_label)} · mean node · ${rows.length} events</caption>
          <thead><tr><th scope="col">Date</th><th scope="col">Event</th><th scope="col">Traditional meaning</th></tr></thead>
          <tbody>${html || '<tr><td colspan="3">No events of this kind.</td></tr>'}</tbody>
        </table>
      </div>`;
  }

  async function run() {
    const year = el("ta-year").value || new Date().getFullYear();
    el("ta-year").value = year;
    setStatus("Computing the year…");
    try {
      const r = await fetch(`/api/engine/transit-almanac?year=${encodeURIComponent(year)}&zodiac=${encodeURIComponent(el("ta-zodiac").value)}`);
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);
      data = d;
      draw();
      ledger();
      setStatus(`${d.year} · ${d.zodiac_label}. Hover a marker for its meaning.`);
    } catch (err) {
      setStatus(`Could not build the almanac: ${err.message}`, true);
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  el("ta-fast").addEventListener("change", () => { draw(); ledger(); });
  el("ta-filter").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-f]");
    if (!b) return;
    filter = b.dataset.f;
    el("ta-filter").querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    ledger();
  });
  new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  document.querySelector('[data-tab="tab-calendar"]')?.addEventListener("click", () => { if (!data) run(); });
  if (window.location.hash === "#tab-calendar") run();
})();
