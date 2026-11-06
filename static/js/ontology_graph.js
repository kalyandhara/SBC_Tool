// static/js/ontology_graph.js
// 3D Impact Lineage Ontology Graph — Plotly scatter3d + lines
// Research-grade only. No validated edge. Dasha layer deferred to Phase 2.
(function () {
  "use strict";

  // plotly-basic (used elsewhere in the app) has no scatter3d, so this chart
  // uses its own gl3d bundle, kept off window.Plotly so other modules are unaffected.
  const PLOTLY_SRC = "/static/vendor/plotly-gl3d-3.0.1.min.js";

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const el = (id) => document.getElementById(id);
  const qsa = (sel) => Array.from(document.querySelectorAll(sel));

  // ── Lazy Plotly loader (same pattern as monthly-score.js) ─────────────────
  let plotlyPromise = null;
  let Plotly3d = null;
  function loadPlotly() {
    if (Plotly3d) return Promise.resolve(Plotly3d);
    if (!plotlyPromise) {
      plotlyPromise = new Promise((resolve, reject) => {
        const prior = window.Plotly;
        const restore = () => {
          if (prior) window.Plotly = prior;
          else delete window.Plotly;
        };
        const s = document.createElement("script");
        s.src = PLOTLY_SRC;
        s.onload = () => {
          Plotly3d = window.Plotly;
          restore();
          resolve(Plotly3d);
        };
        s.onerror = () => {
          plotlyPromise = null;
          restore();
          reject(new Error("Could not load Plotly from " + PLOTLY_SRC));
        };
        document.head.appendChild(s);
      });
    }
    return plotlyPromise;
  }

  // ── State ─────────────────────────────────────────────────────────────────
  let _graphData = null;         // last fetched API response
  let _activeSentiment = "all";  // "all" | "bullish" | "bearish"
  let _view = "radial";          // "radial" | "layered"
  let _focusId = null;           // centred node in the cards view
  let _visibleLayers = new Set(["planet", "sector", "stock"]);

  // ── Fetch graph data ──────────────────────────────────────────────────────
  function fetchGraph(date, time, tz) {
    const container = el("og-container");
    if (!container) return Promise.reject(new Error("og-container not found"));
    if (Plotly3d) Plotly3d.purge(container);
    container.innerHTML = '<p class="og-note og-loading">Loading graph…</p>';
    const params = new URLSearchParams({ date, time: time || "09:15", tz: tz || "Asia/Kolkata" });
    return fetch("/api/ontology/graph?" + params.toString())
      .then((r) => {
        if (!r.ok) return r.json().then((e) => Promise.reject(new Error(e.error || r.statusText)));
        return r.json();
      });
  }

  // ── Build Plotly traces ───────────────────────────────────────────────────
  function buildTraces(graphData, visibleLayers, activeSentiment) {
    const nodes = graphData.nodes;
    const edges = graphData.edges;

    // Group nodes by type
    const byType = {};
    for (const n of nodes) {
      (byType[n.type] = byType[n.type] || []).push(n);
    }

    const NODE_COLORS = {
      planet: "#818cf8", rasi: "#22d3ee", nakshatra: "#fb923c",
      aspect: "#c084fc", theme: "#fbbf24", sector: "#60a5fa", stock: "#4ade80",
    };
    const NODE_SIZES = {
      planet: 16, rasi: 10, nakshatra: 10, aspect: 12, theme: 10, sector: 14, stock: 8,
    };

    const traces = [];

    // --- Node traces (one scatter3d per layer type) ---
    for (const [type, nlist] of Object.entries(byType)) {
      const visible = visibleLayers.has(type);
      const xs = [], ys = [], zs = [], texts = [], hovers = [];
      for (const n of nlist) {
        // Sentiment filter applies to nodes: hide if not matching
        if (activeSentiment !== "all" && n.sentiment !== activeSentiment) continue;
        xs.push(n.x); ys.push(n.y); zs.push(n.z);
        texts.push(n.label);
        const detail = n.detail || {};
        const isUnconfigured = detail.unconfigured;
        let hoverLines = ["<b>" + n.label + "</b> (" + type + ")"];
        if (isUnconfigured) hoverLines.push("⚠ Stock list not yet configured for this sector");
        for (const [k, v] of Object.entries(detail)) {
          if (typeof v !== "object" && k !== "breakdown") {
            hoverLines.push(k + ": " + v);
          }
        }
        if (n.score !== 0) hoverLines.push("score: " + n.score);
        hovers.push(hoverLines.join("<br>"));
      }
      traces.push({
        type: "scatter3d",
        mode: "markers+text",
        name: type.charAt(0).toUpperCase() + type.slice(1),
        x: xs, y: ys, z: zs,
        text: texts,
        textposition: "top center",
        textfont: { size: 9 },
        hovertemplate: "%{customdata}<extra></extra>",
        customdata: hovers,
        marker: {
          size: NODE_SIZES[type] || 10,
          color: NODE_COLORS[type] || "#94a3b8",
          line: { width: 0.5, color: "#1e293b" },
        },
        visible: visible,
      });
    }

    // --- Edge traces (one scatter3d per sentiment colour group) ---
    const edgesBySentiment = {};
    for (const e of edges) {
      if (activeSentiment !== "all" && e.sentiment !== activeSentiment) continue;
      // Check both connected nodes are in visible layers
      const fromNode = nodes.find((n) => n.id === e.from);
      const toNode = nodes.find((n) => n.id === e.to);
      if (!fromNode || !toNode) continue;
      if (!visibleLayers.has(fromNode.type) || !visibleLayers.has(toNode.type)) continue;
      const color = e.color || "#94a3b8";
      (edgesBySentiment[color] = edgesBySentiment[color] || []).push({ e, fromNode, toNode });
    }

    for (const [color, group] of Object.entries(edgesBySentiment)) {
      const xs = [], ys = [], zs = [];
      for (const { fromNode, toNode } of group) {
        xs.push(fromNode.x, toNode.x, null);
        ys.push(fromNode.y, toNode.y, null);
        zs.push(fromNode.z, toNode.z, null);
      }
      const sentimentLabel = color === "#22c55e" ? "Bullish edges"
        : color === "#f87171" ? "Bearish edges" : "Volatile edges";
      traces.push({
        type: "scatter3d",
        mode: "lines",
        name: sentimentLabel,
        x: xs, y: ys, z: zs,
        line: { color: color, width: 2 },
        hoverinfo: "none",
        showlegend: true,
      });
    }

    return traces;
  }

  // ── Radial overview: Root → Planet → Sector group → Stock ─────────────────
  function buildRadialTraces(radial, activeSentiment) {
    const COLORS = { bullish: "#34d399", bearish: "#f87171", volatile: "#fbbf24", neutral: "#1e293b" };
    const SIZES = { root: 26, planet: 15, group: 13, stock: 6 };
    const shown = radial.nodes.filter((n) =>
      activeSentiment === "all" || n.type === "root" || n.type === "planet" || n.sentiment === activeSentiment);
    const byId = new Map(shown.map((n) => [n.id, n]));
    const xs = [], ys = [], zs = [];
    for (const e of radial.edges) {
      const a = byId.get(e.from), b = byId.get(e.to);
      if (!a || !b) continue;
      xs.push(a.x, b.x, null); ys.push(a.y, b.y, null); zs.push(a.z, b.z, null);
    }
    return [
      { type: "scatter3d", mode: "lines", x: xs, y: ys, z: zs, hoverinfo: "none",
        line: { color: "#cbd5e1", width: 2 }, showlegend: false },
      { type: "scatter3d", mode: "markers+text", showlegend: false,
        x: shown.map((n) => n.x), y: shown.map((n) => n.y), z: shown.map((n) => n.z),
        text: shown.map((n) => n.label), textposition: "top center", textfont: { size: 11 },
        hovertemplate: "%{customdata}<extra></extra>",
        customdata: shown.map((n) => {
          const lines = ["<b>" + n.label + "</b>"];
          if (n.detail.unconfigured) lines.push("⚠ Stock list not yet configured for this sector");
          for (const [k, v] of Object.entries(n.detail)) {
            if (k !== "unconfigured") lines.push(k + ": " + v);
          }
          if (n.score) lines.push("score: " + n.score);
          return lines.join("<br>");
        }),
        marker: { size: shown.map((n) => SIZES[n.type] || 8),
                  color: shown.map((n) => COLORS[n.sentiment] || COLORS.neutral),
                  line: { width: 1, color: "#e2e8f0" }, opacity: 1 } },
    ];
  }

  // ── Cards view: one focused node, what feeds it left, what it leads to right ─
  const CARD_HEADINGS = {
    occupies: ["Planets here", "Occupies"],
    in: ["Planets here", "In nakshatra"],
    implies: ["Implied by", "Implies"],
    drives: ["Driven by theme", "Drives"],
    contains: ["In sector", "Representative stocks"],
    influences: ["Influenced by", "Influences sectors"],
  };
  const CARD_COLORS = { bullish: "#22c55e", bearish: "#f87171", volatile: "#fbbf24", neutral: "#94a3b8" };

  function cardLinks(graphData) {
    const byId = new Map(graphData.nodes.map((n) => [n.id, n]));
    const links = graphData.edges.filter((e) => byId.has(e.from) && byId.has(e.to));
    // Scoring links are not graph edges, so derive them from each sector's planets.
    for (const n of graphData.nodes) {
      if (n.type !== "sector") continue;
      for (const name of n.detail.planets || []) {
        const from = "planet_" + name;
        if (byId.has(from)) links.push({ from, to: n.id, label: "influences", sentiment: n.sentiment });
      }
    }
    return { byId, links };
  }

  function defaultFocus(graphData) {
    const sectors = graphData.nodes.filter((n) => n.type === "sector");
    sectors.sort((a, b) => Math.abs(b.score) - Math.abs(a.score));
    return (sectors[0] || graphData.nodes[0]).id;
  }

  function cardSubtitle(n) {
    const d = n.detail || {};
    if (d.unconfigured) return "Stock list not yet configured for this sector";
    if (n.type === "planet") return d.rasi + " · " + d.nakshatra + (d.retrograde ? " · retrograde" : "");
    if (n.type === "aspect") return d.aspect_name + " · orb " + d.orb_diff + "°";
    if (n.type === "rasi") return d.element + " · " + d.modality;
    if (n.type === "nakshatra") return d.is_sensitive ? "Sensitive star" : "Nakshatra";
    if (n.type === "sector") return "Score " + n.score;
    if (n.type === "stock") return d.sector;
    return "";
  }

  function makeCard(n, side) {
    const card = document.createElement(side === "focus" ? "div" : "button");
    card.className = "og-card" + (side === "focus" ? " og-card-focus" : "");
    if (side !== "focus") {
      card.type = "button";
      card.addEventListener("click", () => {
        _focusId = n.id;
        renderGraph(_graphData);
      });
    }
    card.dataset.side = side;
    card.style.setProperty("--og-accent", CARD_COLORS[n.sentiment] || CARD_COLORS.neutral);
    const kind = document.createElement("span");
    kind.className = "og-card-kind";
    kind.textContent = n.type;
    const title = document.createElement("strong");
    title.textContent = n.label;
    card.append(kind, title);
    const subtitle = cardSubtitle(n);
    if (subtitle) {
      const sub = document.createElement("span");
      sub.className = "og-card-sub";
      sub.textContent = subtitle;
      card.append(sub);
    }
    return card;
  }

  function makeColumn(items, side) {
    const col = document.createElement("div");
    col.className = "og-card-col";
    const groups = new Map();
    for (const it of items) {
      const pair = CARD_HEADINGS[it.label];
      const heading = pair ? pair[side === "left" ? 0 : 1] : "Aspect: " + it.label;
      if (!groups.has(heading)) groups.set(heading, []);
      groups.get(heading).push(it.node);
    }
    for (const [heading, list] of groups) {
      const h = document.createElement("p");
      h.className = "og-card-heading";
      h.textContent = heading;
      col.append(h, ...list.map((n) => makeCard(n, side)));
    }
    return col;
  }

  function drawConnectors(wrap, focus) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "og-card-lines");
    svg.setAttribute("width", wrap.scrollWidth);
    svg.setAttribute("height", wrap.scrollHeight);
    const box = wrap.getBoundingClientRect();
    const f = focus.getBoundingClientRect();
    const fy = f.top - box.top + f.height / 2;
    wrap.querySelectorAll(".og-card[data-side='left'], .og-card[data-side='right']").forEach((c) => {
      const r = c.getBoundingClientRect();
      const y = r.top - box.top + r.height / 2;
      const left = c.dataset.side === "left";
      const x1 = left ? r.right - box.left : f.right - box.left;
      const y1 = left ? y : fy;
      const x2 = left ? f.left - box.left : r.left - box.left;
      const y2 = left ? fy : y;
      const mid = (x1 + x2) / 2;
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "M" + x1 + " " + y1 + " C" + mid + " " + y1 + " " + mid + " " + y2 + " " + x2 + " " + y2);
      path.setAttribute("stroke", getComputedStyle(c).getPropertyValue("--og-accent"));
      svg.append(path);
    });
    wrap.prepend(svg);
  }

  function renderCards(graphData, container) {
    const { byId, links } = cardLinks(graphData);
    if (!_focusId || !byId.has(_focusId)) _focusId = defaultFocus(graphData);
    const focusNode = byId.get(_focusId);
    const keep = (it) => _activeSentiment === "all" || it.node.sentiment === _activeSentiment;
    const seen = new Set();
    const once = (it) => {
      const key = it.label + it.node.id;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    };
    const left = links.filter((e) => e.to === _focusId)
      .map((e) => ({ label: e.label, node: byId.get(e.from) })).filter(keep).filter(once);
    const right = links.filter((e) => e.from === _focusId)
      .map((e) => ({ label: e.label, node: byId.get(e.to) })).filter(keep).filter(once);

    const picker = document.createElement("select");
    picker.className = "og-card-picker";
    picker.setAttribute("aria-label", "Focus node");
    for (const n of graphData.nodes) {
      if (n.type !== "planet" && n.type !== "sector") continue;
      picker.add(new Option(n.type + ": " + n.label, n.id, false, n.id === _focusId));
    }
    picker.addEventListener("change", () => {
      _focusId = picker.value;
      renderGraph(_graphData);
    });

    const wrap = document.createElement("div");
    wrap.className = "og-card-map";
    const focusCard = makeCard(focusNode, "focus");
    const middle = document.createElement("div");
    middle.className = "og-card-mid";
    middle.append(focusCard);
    wrap.append(makeColumn(left, "left"), middle, makeColumn(right, "right"));
    container.style.minHeight = "";
    container.append(picker, wrap);
    drawConnectors(wrap, focusCard);
  }

  // ── Render chart ──────────────────────────────────────────────────────────
  function renderGraph(graphData) {
    const container = el("og-container");
    if (!container) return;
    if (_view === "cards") {
      if (Plotly3d && container._fullLayout) Plotly3d.purge(container);
      container.replaceChildren();
      renderCards(graphData, container);
      return;
    }
    const radial = _view === "radial";
    const traces = radial
      ? buildRadialTraces(graphData.radial, _activeSentiment)
      : buildTraces(graphData, _visibleLayers, _activeSentiment);
    const theme = document.documentElement.dataset.theme;
    const isDark = theme ? theme === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    const bg = isDark ? "#0f172a" : "#f8fafc";
    const textColor = isDark ? "#e2e8f0" : "#1e293b";
    const layout = {
      paper_bgcolor: bg,
      plot_bgcolor: bg,
      font: { color: textColor, size: 10 },
      margin: { l: 0, r: 0, t: 40, b: 0 },
      title: {
        text: "Impact Lineage: Planet → Rasi → Nakshatra → Aspect → Theme → Sector → Stock",
        font: { size: 12 },
      },
      scene: {
        bgcolor: bg,
        xaxis: { showgrid: false, zeroline: false, showticklabels: false, title: { text: "" } },
        yaxis: { showgrid: false, zeroline: false, showticklabels: false, title: { text: "" } },
        zaxis: {
          showgrid: true, zeroline: false, showticklabels: true,
          tickvals: [0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0],
          ticktext: ["Planets", "Rasi", "Nakshatra", "Aspects", "Themes", "Sectors", "Stocks"],
          title: { text: "" },
          gridcolor: isDark ? "#334155" : "#e2e8f0",
        },
        camera: { eye: { x: 1.5, y: 1.5, z: 0.8 } },
      },
      legend: { x: 0, y: 1, bgcolor: "rgba(0,0,0,0.3)" },
      height: 650,
    };
    if (radial) {
      const hidden = { visible: false };
      layout.title.text = "Ontological Vector Graph — Regime: " + graphData.radial.regime;
      layout.showlegend = false;
      layout.scene.xaxis = hidden;
      layout.scene.yaxis = hidden;
      layout.scene.zaxis = { visible: false, range: [-8, 8] };
      layout.scene.aspectmode = "data";
      layout.scene.camera = { eye: { x: 0.35, y: -1.05, z: 1.55 } };
      layout.height = 760;
    }
    container.style.minHeight = "650px";
    // A fresh plot per render, so one view's camera never carries to the other.
    if (container._fullLayout) Plotly3d.purge(container);
    container.replaceChildren();
    Plotly3d.newPlot(container, traces, layout, { responsive: true, displayModeBar: true });
  }

  // ── Load and render ───────────────────────────────────────────────────────
  function loadAndRender() {
    const dateInput = el("ontology-date");
    const timeInput = el("ontology-time");
    if (!dateInput || !dateInput.value) return;
    const date = dateInput.value;
    const time = timeInput ? timeInput.value : "09:15";
    loadPlotly()
      .then(() => fetchGraph(date, time, "Asia/Kolkata"))
      .then((data) => {
        _graphData = data;
        renderGraph(data);
      })
      .catch((err) => {
        const container = el("og-container");
        if (container) {
          const p = document.createElement("p");
          p.className = "og-note og-error";
          p.textContent = "Graph error: " + err.message;
          container.replaceChildren(p);
        }
      });
  }

  // ── Filter handlers ───────────────────────────────────────────────────────
  function onSentimentChange(btn) {
    qsa(".og-sentiment-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    _activeSentiment = btn.dataset.sentiment;
    if (_graphData) renderGraph(_graphData);
  }

  function onViewChange(btn) {
    qsa(".og-view-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    _view = btn.dataset.view;
    const layers = el("og-layer-controls");
    if (layers) layers.hidden = _view !== "layered";
    if (_graphData) renderGraph(_graphData);
  }

  function onLayerChange() {
    _visibleLayers = new Set(
      qsa(".og-layer-cb:checked").map((cb) => cb.dataset.layer)
    );
    if (_graphData) renderGraph(_graphData);
  }

  // ── Expand/collapse toggle ────────────────────────────────────────────────
  function onToggle(btn) {
    const body = el("og-body");
    if (!body) return;
    const expanded = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", String(!expanded));
    btn.querySelector(".og-chevron").textContent = expanded ? "▼" : "▲";
    body.hidden = expanded;
    // Load on first expand if date available
    if (!expanded && !_graphData) loadAndRender();
    else if (!expanded && _view === "cards") renderGraph(_graphData);  // lines need real sizes
  }

  // ── Wire up ───────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    const toggle = el("og-toggle");
    if (toggle) toggle.addEventListener("click", () => onToggle(toggle));

    qsa(".og-sentiment-btn").forEach((btn) =>
      btn.addEventListener("click", () => onSentimentChange(btn))
    );

    qsa(".og-view-btn").forEach((btn) =>
      btn.addEventListener("click", () => onViewChange(btn))
    );

    qsa(".og-layer-cb").forEach((cb) =>
      cb.addEventListener("change", onLayerChange)
    );

    // Also load when the main "Compute Ontology" button is clicked
    const runBtn = el("ontology-run");
    if (runBtn) {
      runBtn.addEventListener("click", () => {
        // Slight delay to let the main ontology computation start first
        setTimeout(() => {
          const body = el("og-body");
          if (body && !body.hidden) loadAndRender();
          else _graphData = null; // reset so expand will re-fetch
        }, 200);
      });
    }
  });
})();
