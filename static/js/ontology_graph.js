// static/js/ontology_graph.js
// 3D Impact Lineage Ontology Graph — Plotly scatter3d + lines
// Research-grade only. No validated edge. Dasha layer deferred to Phase 2.
(function () {
  "use strict";

  const PLOTLY_SRC = "/static/vendor/plotly-basic-4.1.1.min.js";

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const el = (id) => document.getElementById(id);
  const qsa = (sel) => Array.from(document.querySelectorAll(sel));

  // ── Lazy Plotly loader (same pattern as monthly-score.js) ─────────────────
  let plotlyPromise = null;
  function loadPlotly() {
    if (window.Plotly) return Promise.resolve(window.Plotly);
    if (!plotlyPromise) {
      plotlyPromise = new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = PLOTLY_SRC;
        s.onload = () => resolve(window.Plotly);
        s.onerror = () => {
          plotlyPromise = null;
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
  let _visibleLayers = new Set(["planet", "sector", "stock"]);

  // ── Fetch graph data ──────────────────────────────────────────────────────
  function fetchGraph(date, time, tz) {
    const container = el("og-container");
    if (!container) return Promise.reject(new Error("og-container not found"));
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

  // ── Render chart ──────────────────────────────────────────────────────────
  function renderGraph(graphData) {
    const container = el("og-container");
    if (!container) return;
    const traces = buildTraces(graphData, _visibleLayers, _activeSentiment);
    const isDark = document.documentElement.dataset.theme === "dark"
      || window.matchMedia("(prefers-color-scheme: dark)").matches;
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
        xaxis: { showgrid: false, zeroline: false, showticklabels: false, title: "" },
        yaxis: { showgrid: false, zeroline: false, showticklabels: false, title: "" },
        zaxis: {
          showgrid: true, zeroline: false, showticklabels: true,
          tickvals: [0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0],
          ticktext: ["Planets", "Rasi", "Nakshatra", "Aspects", "Themes", "Sectors", "Stocks"],
          title: "",
          gridcolor: isDark ? "#334155" : "#e2e8f0",
        },
        camera: { eye: { x: 1.5, y: 1.5, z: 0.8 } },
      },
      legend: { x: 0, y: 1, bgcolor: "rgba(0,0,0,0.3)" },
      height: 650,
    };
    container.style.minHeight = "650px";
    window.Plotly.react(container, traces, layout, { responsive: true, displayModeBar: true });
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
    qsa(".og-sent-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    _activeSentiment = btn.dataset.sentiment;
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
  }

  // ── Wire up ───────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    const toggle = el("og-toggle");
    if (toggle) toggle.addEventListener("click", () => onToggle(toggle));

    qsa(".og-sent-btn").forEach((btn) =>
      btn.addEventListener("click", () => onSentimentChange(btn))
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
