// Aspect Table tab: exact-time geocentric sidereal aspects with Moon included (B-43).
(function () {
  const el = (id) => document.getElementById(id);
  const form = el("at-form");
  if (!form) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));

  function setStatus(msg, isErr) {
    const s = el("at-status");
    s.textContent = msg;
    s.classList.toggle("error", !!isErr);
  }

  function aspectLabel(code) {
    if (code === "KSc") return "KSc (orb entry)";
    if (code === "KSp") return "KSp (conj. orb entry)";
    if (typeof code === "number") {
      const labels = {
        0: "Conjunction (0°)",
        30: "Sextile (30°)",
        45: "Semi-square (45°)",
        60: "Sextile (60°)",
        90: "Square (90°)",
        120: "Trine (120°)",
        135: "Sesquiquadrate (135°)",
        150: "Inconjunct (150°)",
        180: "Opposition (180°)",
      };
      return labels[code] || `${code}°`;
    }
    return code;
  }

  function renderTable(aspects) {
    if (!aspects || aspects.length === 0) {
      return `<p class="analog-note">No aspects found for the selected range and filters.</p>`;
    }

    const rows = aspects.map((a) => {
      const isConj = a.aspect === 0 || a.aspect === "KSp";
      const rowClass = isConj ? "cal-conj" : "";
      const combustBadge = a.combust ? ' <span class="badge badge-warn">Combust</span>' : "";
      const retroBadge = a.retro ? ' <span class="badge badge-info">Retro</span>' : "";
      const muhurtaBadge = a.muhurta ? ` <span class="badge badge-note">${esc(a.muhurta)}</span>` : "";

      return `
        <tr class="${rowClass}">
          <td>${esc(a.date)}</td>
          <td>${esc(a.weekday)}</td>
          <td class="num">${esc(a.time)}</td>
          <td>${esc(a.pl1)}</td>
          <td>${aspectLabel(a.aspect)}</td>
          <td>${esc(a.pl2)}</td>
          <td>${esc(a.rashis)}</td>
          <td class="num">${esc(a.relations)}</td>
          <td>${esc(a.winner)}${combustBadge}${retroBadge}</td>
          <td>${muhurtaBadge || "–"}</td>
        </tr>`;
    }).join("");

    return `
      <div class="analog-table-wrap">
        <table class="analog-table at-table">
          <caption>${aspects.length} aspects. KSc/KSp mark orb-entry events (when planets enter the aspect tolerance). Highlighted rows are conjunctions.</caption>
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

  async function run() {
    const start = el("at-start").value;
    const end = el("at-end").value;
    const planet = el("at-planet").value;
    const aspect = el("at-aspect").value;

    if (!start || !end) {
      setStatus("Start and end dates are required", true);
      return;
    }

    const params = new URLSearchParams({ start, end });
    if (planet) params.set("planet", planet);
    if (aspect) params.set("aspect", aspect);

    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    setStatus("Loading aspects…");

    try {
      const r = await fetch(`/api/engine/aspect_table?${params}`);
      const d = await r.json().catch(() => ({}));
      if (!r.ok || d.error) throw new Error(d.error || `HTTP ${r.status}`);

      // Filter on client side if API doesn't support it
      let filtered = d.aspects || [];
      if (planet) {
        filtered = filtered.filter((a) => a.pl1 === planet || a.pl2 === planet);
      }
      if (aspect) {
        filtered = filtered.filter((a) => String(a.aspect) === aspect);
      }

      el("at-results").innerHTML = renderTable(filtered);
      setStatus(`${d.start} → ${d.end} · ${filtered.length} aspects shown`);
    } catch (err) {
      setStatus(`Could not load aspects: ${err.message}`, true);
      el("at-results").innerHTML = "";
    } finally {
      btn.disabled = false;
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); run(); });

  // Set default date range (current month)
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
  const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  el("at-start").value = firstDay.toISOString().split("T")[0];
  el("at-end").value = lastDay.toISOString().split("T")[0];

  // Auto-load when tab opens if not already loaded
  document.querySelector('[data-tab="tab-calendar"]')?.addEventListener("click", () => {
    if (!el("at-results").innerHTML.trim()) {
      run();
    }
  });
})();
