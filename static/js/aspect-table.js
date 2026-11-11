// Aspect Table panel: exact-time geocentric sidereal aspects with Moon included (B-43).
// Shown as a planet-pair by day timeline, with the full table one click below it.
// Traditional timing, untested. Not a forecast.
(function () {
  const el = (id) => document.getElementById(id);
  const form = el("at-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

  const PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
    "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"];
  const ASPECT_NAMES = {
    0: "Conjunction", 30: "Semi-sextile", 45: "Semi-square", 60: "Sextile", 90: "Square",
    120: "Trine", 135: "Sesquiquadrate", 150: "Inconjunct", 180: "Opposition",
  };
  const FAMILY = { 0: "conj", 45: "tense", 90: "tense", 135: "tense", 180: "tense",
    30: "easy", 60: "easy", 120: "easy", 150: "inconj" };
  const ROW_H = 17;
  const GROUP_H = 22;
  const AXIS_H = 26;
  const LABEL_W = 128;
  const DAY_MS = 86400000;

  // Filled by run(); the toggles redraw from this without another fetch.
  const state = { rows: [], start: "", end: "", planet: "", showMoon: false, showKetu: false, marks: [] };

  function setStatus(msg, isErr) {
    const s = el("at-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  const isEntry = (a) => a.aspect === "KSc" || a.aspect === "KSp";
  const hasMoon = (a) => a.pl1 === "Moon" || a.pl2 === "Moon";
  const hasKetu = (a) => a.pl1 === "Ketu" || a.pl2 === "Ketu";

  function aspectLabel(a) {
    const named = `${ASPECT_NAMES[a.target_angle]} (${a.target_angle}°)`;
    return isEntry(a) ? `${a.aspect}: orb entry for ${named}` : named;
  }

  // IST wall-clock strings are compared as if UTC, so no local timezone leaks in.
  const toMs = (stamp) => Date.parse(`${stamp.replace(" ", "T")}:00Z`);
  const stampOf = (a) => `${a.date} ${a.time}`;

  function shortStamp(stamp) {
    if (!stamp) return "none found";
    const d = new Date(toMs(stamp));
    const day = d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
    return `${day} ${stamp.slice(11)} IST`;
  }

  function markText(a) {
    const head = `${a.pl1} ${isEntry(a) ? a.aspect : `${a.target_angle}°`} ${a.pl2}`;
    const when = shortStamp(stampOf(a));
    const pairTime = isEntry(a)
      ? `Exact ${a.target_angle}°: ${a.exact_at ? shortStamp(a.exact_at) : "not reached inside the orb"}`
      : `Orb entry (${a.target_angle === 0 ? "KSp" : "KSc"}): ${shortStamp(a.orb_entry)}`;
    return { head: `${head} · ${when}`, sub: `${aspectLabel(a)} · ${pairTime}` };
  }

  function visibleRows() {
    const moon = state.showMoon || state.planet === "Moon";
    const ketu = state.showKetu || state.planet === "Ketu";
    return state.rows.filter((a) => (moon || !hasMoon(a)) && (ketu || !hasKetu(a)));
  }

  function shapeFor(family, x, y) {
    if (family === "conj") return `<circle cx="${x}" cy="${y}" r="4.5"/>`;
    if (family === "tense") return `<path d="M${x} ${y - 5.5}l5 5.5-5 5.5-5-5.5z"/>`;
    if (family === "easy") return `<path d="M${x} ${y - 5}l5 9h-10z"/>`;
    return `<rect x="${x - 3.5}" y="${y - 3.5}" width="7" height="7"/>`;
  }

  function dayTicks(startMs, days, pxPerDay) {
    const every = pxPerDay >= 26 ? 1 : pxPerDay >= 13 ? 2 : pxPerDay >= 4 ? 7 : 30;
    const out = [];
    for (let i = 0; i < days; i += every) out.push(i);
    return { every, indices: out, startMs };
  }

  function renderChart() {
    const box = el("at-chart");
    const rows = visibleRows();
    state.marks = [];
    if (!rows.length) {
      box.innerHTML = `<p class="analog-note">${state.rows.length
        ? "Every aspect in this range is hidden. Turn on Moon or Ketu mirrors above."
        : "No aspects found for the selected range and filters."}</p>`;
      return;
    }

    const startMs = toMs(`${state.start} 00:00`);
    const endMs = toMs(`${state.end} 00:00`) + DAY_MS;
    const days = Math.round((endMs - startMs) / DAY_MS);
    const width = Math.max(box.clientWidth || 0, 640);
    const plotW = width - LABEL_W - 8;
    const pxPerDay = plotW / days;
    const x = (ms) => +(LABEL_W + ((Math.min(Math.max(ms, startMs), endMs) - startMs) / DAY_MS) * pxPerDay).toFixed(1);

    // Rows: planet pairs in planet order, the Moon's pairs in their own block.
    const order = (a) => PLANETS.indexOf(a.pl1) * 20 + PLANETS.indexOf(a.pl2);
    const pairs = new Map();
    rows.slice().sort((p, q) => order(p) - order(q)).forEach((a) => {
      const key = `${a.pl1}|${a.pl2}`;
      if (!pairs.has(key)) pairs.set(key, { a, items: [] });
      pairs.get(key).items.push(a);
    });
    const groups = [
      ["Planets", [...pairs.values()].filter((p) => !hasMoon(p.a))],
      ["Moon", [...pairs.values()].filter((p) => hasMoon(p.a))],
    ].filter(([, list]) => list.length);

    const total = AXIS_H + groups.reduce((n, [, list]) => n + GROUP_H + list.length * ROW_H, 0) + 4;
    const parts = [];

    // Day columns behind everything: weekends shaded, then labels.
    const ticks = dayTicks(startMs, days, pxPerDay);
    for (let i = 0; i < days; i += 1) {
      const dow = new Date(startMs + i * DAY_MS).getUTCDay();
      if ((dow === 0 || dow === 6) && pxPerDay >= 4) {
        parts.push(`<rect class="at-weekend" x="${x(startMs + i * DAY_MS)}" y="${AXIS_H}" width="${pxPerDay.toFixed(1)}" height="${total - AXIS_H}"/>`);
      }
    }
    ticks.indices.forEach((i) => {
      const ms = startMs + i * DAY_MS;
      const d = new Date(ms);
      const newMonth = i === 0 || d.getUTCDate() === 1;
      const text = newMonth
        ? d.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })
        : String(d.getUTCDate());
      parts.push(`<line class="at-grid" x1="${x(ms)}" x2="${x(ms)}" y1="${AXIS_H}" y2="${total}"/>`);
      parts.push(`<text class="at-tick" x="${x(ms) + 2}" y="${AXIS_H - 8}">${esc(text)}</text>`);
    });

    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const nowMs = toMs(`${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`);
    if (nowMs >= startMs && nowMs < endMs) {
      parts.push(`<line class="at-now" x1="${x(nowMs)}" x2="${x(nowMs)}" y1="${AXIS_H - 4}" y2="${total}"/>`);
    }

    let y = AXIS_H;
    groups.forEach(([name, list]) => {
      parts.push(`<text class="at-group" x="0" y="${y + 15}">${esc(name)}</text>`);
      y += GROUP_H;
      list.forEach((pair) => {
        const cy = y + ROW_H / 2;
        const drawn = new Set();
        parts.push(`<line class="at-row" x1="${LABEL_W}" x2="${width - 8}" y1="${cy}" y2="${cy}"/>`);
        parts.push(`<text class="at-pair" x="${LABEL_W - 8}" y="${cy + 4}">${esc(pair.a.pl1)} – ${esc(pair.a.pl2)}</text>`);

        // Orb windows first, so marks sit on top of them.
        pair.items.forEach((a) => {
          const from = isEntry(a) ? stampOf(a) : a.orb_entry;
          const to = isEntry(a) ? a.exact_at : stampOf(a);
          const key = `${a.target_angle}|${from}`;
          if (!from || !to || drawn.has(key)) return;
          drawn.add(key);
          const x1 = x(toMs(from));
          const x2 = x(toMs(to));
          const family = FAMILY[a.target_angle];
          parts.push(`<rect class="at-orb at-${family}" x="${x1}" y="${cy - 1.5}" width="${Math.max(x2 - x1, 1).toFixed(1)}" height="3" rx="1.5"/>`);
        });

        pair.items.forEach((a) => {
          const ms = toMs(stampOf(a));
          const mx = x(ms);
          const family = FAMILY[a.target_angle];
          const index = state.marks.push(a) - 1;
          const label = `${markText(a).head}. ${markText(a).sub}`;
          const body = isEntry(a)
            ? `<line class="at-entry" x1="${mx}" x2="${mx}" y1="${cy - 5}" y2="${cy + 5}"/>`
            : shapeFor(family, mx, cy);
          const angle = !isEntry(a) && !hasMoon(a) && pxPerDay >= 18
            ? `<text class="at-angle" x="${mx + 7}" y="${cy - 2}">${a.target_angle}</text>` : "";
          parts.push(`<g class="at-mark at-${family}" data-i="${index}" tabindex="0" role="button" aria-label="${esc(label)}">` +
            `<rect class="at-hit" x="${mx - 8}" y="${cy - ROW_H / 2}" width="16" height="${ROW_H}"/>${body}${angle}</g>`);
        });
        y += ROW_H;
      });
    });

    box.innerHTML = `<svg class="at-svg" width="${width}" height="${total}" viewBox="0 0 ${width} ${total}" ` +
      `role="group" aria-label="Aspect timeline by planet pair and day">${parts.join("")}</svg>`;
    box.dataset.width = String(box.clientWidth);
  }

  function renderDetail(a) {
    const { head, sub } = markText(a);
    const flags = [a.combust ? "Combust" : "", a.retro ? "Retrograde involved" : ""].filter(Boolean).join(" · ");
    el("at-detail").innerHTML = `<strong>${esc(head)}</strong><br>${esc(sub)}<br>` +
      `Rashis ${esc(a.rashis)} · Relations ${esc(a.relations)} · Winner ${esc(a.winner)}` +
      ` · Muhurta ${esc(a.muhurta || "–")}${flags ? ` · ${esc(flags)}` : ""}`;
  }

  function renderTable(aspects) {
    const summary = el("at-table-summary");
    summary.textContent = `Full table (${aspects.length} row${aspects.length === 1 ? "" : "s"}, including anything hidden in the timeline)`;
    if (!aspects.length) {
      el("at-results").innerHTML = "";
      return;
    }
    const rows = aspects.map((a) => {
      const rowClass = a.target_angle === 0 ? "cal-conj" : "";
      const combustBadge = a.combust ? ' <span class="badge badge-warn">Combust</span>' : "";
      const retroBadge = a.retro ? ' <span class="badge badge-info">Retro</span>' : "";
      const muhurtaBadge = a.muhurta ? ` <span class="badge badge-note">${esc(a.muhurta)}</span>` : "";
      return `
        <tr class="${rowClass}">
          <td>${esc(a.date)}</td>
          <td>${esc(a.weekday)}</td>
          <td class="num">${esc(a.time)}</td>
          <td>${esc(a.pl1)}</td>
          <td>${esc(aspectLabel(a))}</td>
          <td>${esc(a.pl2)}</td>
          <td>${esc(a.rashis)}</td>
          <td class="num">${esc(a.relations)}</td>
          <td>${esc(a.winner)}${combustBadge}${retroBadge}</td>
          <td>${muhurtaBadge || "–"}</td>
        </tr>`;
    }).join("");

    el("at-results").innerHTML = `
      <div class="analog-table-wrap">
        <table class="analog-table at-table">
          <caption>${aspects.length} rows. KSc/KSp mark orb-entry events (when planets enter the aspect tolerance). Highlighted rows are conjunctions.</caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Day</th>
              <th scope="col">Time (IST)</th>
              <th scope="col">Planet 1</th>
              <th scope="col">Aspect</th>
              <th scope="col">Planet 2</th>
              <th scope="col">Rashis</th>
              <th scope="col">Relations</th>
              <th scope="col">Winner</th>
              <th scope="col">Muhurta</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function syncToggles() {
    [["at-toggle-moon", "showMoon", hasMoon, "Moon", "Moon"],
     ["at-toggle-ketu", "showKetu", hasKetu, "Ketu mirrors", "Ketu"]].forEach(([id, key, test, label, planet]) => {
      const b = el(id);
      const forced = state.planet === planet;
      b.textContent = `${label} (${state.rows.filter(test).length})`;
      b.setAttribute("aria-pressed", String(state[key] || forced));
      b.disabled = forced;
    });
  }

  async function run() {
    const start = el("at-start").value;
    const end = el("at-end").value;
    const planet = el("at-planet").value;
    const aspect = el("at-aspect").value;

    if (!start || !end) {
      setStatus("Start and end dates are required", true);
      return;
    }

    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    setStatus("Loading aspects…");

    try {
      const r = await fetch(`/api/engine/aspect_table?${new URLSearchParams({ start, end })}`);
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);

      let filtered = d.aspects || [];
      if (planet) filtered = filtered.filter((a) => a.pl1 === planet || a.pl2 === planet);
      if (aspect) filtered = filtered.filter((a) => String(a.aspect) === aspect);

      Object.assign(state, { rows: filtered, start: d.start, end: d.end, planet });
      syncToggles();
      renderChart();
      renderTable(filtered);
      el("at-detail").textContent = "Hover a mark for its exact time. Click or press Enter to keep the full details here.";
      setStatus(`${d.start} → ${d.end} · ${filtered.length} aspect event${filtered.length === 1 ? "" : "s"}`);
    } catch (err) {
      setStatus(`Could not load aspects: ${err.message}`, true);
      el("at-chart").innerHTML = "";
      el("at-results").innerHTML = "";
    } finally {
      btn.disabled = false;
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });

  ["moon", "ketu"].forEach((name) => {
    el(`at-toggle-${name}`).addEventListener("click", () => {
      const key = name === "moon" ? "showMoon" : "showKetu";
      state[key] = !state[key];
      syncToggles();
      renderChart();
    });
  });

  // One tooltip and one set of handlers for all the marks.
  const chart = el("at-chart");
  const tip = el("at-tip");
  const markAt = (target) => {
    const g = target.closest && target.closest(".at-mark");
    return g ? { g, row: state.marks[Number(g.dataset.i)] } : null;
  };
  function showTip(hit) {
    const { head, sub } = markText(hit.row);
    tip.innerHTML = `<strong>${esc(head)}</strong><br>${esc(sub)}`;
    tip.hidden = false;
    const r = hit.g.getBoundingClientRect();
    const left = Math.min(r.left + r.width / 2 + 10, window.innerWidth - tip.offsetWidth - 8);
    const top = r.top - tip.offsetHeight - 6;
    tip.style.left = `${Math.max(8, left)}px`;
    tip.style.top = `${top < 8 ? r.bottom + 6 : top}px`;
  }
  const hideTip = () => { tip.hidden = true; };
  chart.addEventListener("pointerover", (e) => { const h = markAt(e.target); if (h) showTip(h); else hideTip(); });
  chart.addEventListener("pointerleave", hideTip);
  chart.addEventListener("focusin", (e) => { const h = markAt(e.target); if (h) showTip(h); });
  chart.addEventListener("focusout", hideTip);
  chart.addEventListener("click", (e) => { const h = markAt(e.target); if (h) renderDetail(h.row); });
  chart.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const h = markAt(e.target);
    if (h) { e.preventDefault(); renderDetail(h.row); }
  });

  // The panel sits in a hidden tab at first, so redraw once it has a real width.
  new ResizeObserver(() => {
    if (state.start && chart.clientWidth && String(chart.clientWidth) !== chart.dataset.width) renderChart();
  }).observe(chart);

  // Default range: the current month, in local dates.
  const today = new Date();
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  el("at-start").value = iso(new Date(today.getFullYear(), today.getMonth(), 1));
  el("at-end").value = iso(new Date(today.getFullYear(), today.getMonth() + 1, 0));

  // Auto-load when tab opens if not already loaded
  document.querySelector('[data-tab="tab-calendar"]')?.addEventListener("click", () => {
    if (!state.start) run();
  });
})();
