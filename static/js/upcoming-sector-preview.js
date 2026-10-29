// Forward Calendar: upcoming core planetary events with the historical sector pattern after each
// (/api/sector_rotation/upcoming). Descriptive, not graded: no pre-registered edge yet.
// Every value is set with textContent, never innerHTML.
(function () {
  const box = document.getElementById("upcoming-sector-preview");
  if (!box) return;

  const HEAT_LABEL = {
    dark_green: "Strong outperformance", light_green: "Mild outperformance", yellow: "Neutral",
    orange: "Mild underperformance", dark_red: "Strong underperformance",
  };
  const SECTOR_NAME = {
    CNXBANK: "Bank", CNXFIN: "Fin Service", CNXIT: "IT", CNXPHARMA: "Pharma", CNXAUTO: "Auto",
    CNXFMCG: "FMCG", CNXMETAL: "Metal", CNXENERGY: "Energy", CNXREALTY: "Realty",
    CNXPSUBANK: "PSU Bank", CNXINFRA: "Infrastructure", CNXCONSUM: "Consumer Durables",
  };
  const HORIZONS = ["5", "10", "20"];

  const el = (id) => document.getElementById(id);
  const pct = (x) => (x == null ? "–" : `${(x * 100).toFixed(2)}%`);
  const node = (tag, props = {}, children = []) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === "text") n.textContent = v;
      else if (k === "class") n.className = v;
      else n.setAttribute(k, v);
    }
    for (const c of children) n.appendChild(c);
    return n;
  };

  function chip(row) {
    const name = SECTOR_NAME[row.sector] || row.sector;
    const label = row.heat ? HEAT_LABEL[row.heat] : "No colour";
    return node("span", {
      class: `sr-chip sr-heat sr-heat-${row.heat || "none"}`,
      title: `${label}. ${row.n_raw} occurrences in ${row.n_clusters} independent clusters.`,
      text: `${name} ${pct(row.mean_relative)} (${row.n_raw})`,
    });
  }

  function chips(rows) {
    if (!rows || !rows.length) return node("span", { class: "muted", text: "–" });
    return node("span", { class: "sr-chips" }, rows.map(chip));
  }

  function outlookTable(outlook) {
    const body = HORIZONS.filter((h) => outlook[h]).map((h) => node("tr", {}, [
      node("th", { scope: "row", text: `T+${h}` }),
      node("td", {}, [chips(outlook[h].strongest)]),
      node("td", {}, [chips(outlook[h].weakest)]),
    ]));
    return node("div", { class: "sr-scroll" }, [node("table", { class: "sr-table" }, [
      node("thead", {}, [node("tr", {}, [
        node("th", { scope: "col", text: "Horizon" }),
        node("th", { scope: "col", text: "Strongest vs NIFTY" }),
        node("th", { scope: "col", text: "Weakest vs NIFTY" }),
      ])]),
      node("tbody", {}, body),
    ])]);
  }

  function eventCard(ev) {
    const until = ev.window_end ? ` · Mercury retrograde window to ${ev.window_end}` : "";
    return node("article", { class: "usp-card" }, [
      node("h3", { text: `${ev.date} · ${ev.label}` }),
      node("p", { class: "analog-note", text: `Past occurrences: ${ev.raw} in ${ev.clusters} independent clusters${until}.` }),
      outlookTable(ev.outlook),
    ]);
  }

  function render(d) {
    el("usp-results").replaceChildren(...(d.events.length
      ? d.events.map(eventCard)
      : [node("p", { class: "analog-note", text: `No core planetary event in the next ${d.days} days.` })]));
    el("usp-status").textContent = `As of ${d.as_of}; NIFTY data to ${d.last_session}. ${d.caveat}`;
  }

  async function load() {
    const status = el("usp-status");
    const days = el("usp-days").value;
    status.textContent = "Loading upcoming events…";
    try {
      const r = await fetch(`/api/sector_rotation/upcoming?days=${encodeURIComponent(days)}`);
      if (r.status === 404) {
        status.textContent = "No sector rotation report yet, so no historical pattern to show.";
        el("usp-results").replaceChildren();
        return;
      }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      render(await r.json());
    } catch (err) {
      status.textContent = `Could not load upcoming events (${err.message}).`;
    }
  }

  el("usp-days").addEventListener("change", load);
  load();
})();
