// SBC Sector Dashboard (Sector Heatmap tab).
// Moved out of static/app.js (B-78). Classic script: shares the page's global scope
// with app.js, which loads first and provides $, esc, fetchWithTimeout, localTodayISO.

const SD_COLORS = { bull: "#00C853", bear: "#D50000", neutral: "#9E9E9E" };
const SD_BADGE_COLORS = { benefic: "#2196F3", malefic: "#FF9800", node: "#9C27B0" };
const SD_INTENSITY = { strong: 1.0, moderate: 0.7, mild: 0.4, flat: 0.4 };

function sdTrendOf(confluence) {
  const signal = (confluence.signal || "NEUTRAL").toUpperCase();
  const net = confluence.net || 0;
  const magnitude = Math.abs(net);
  const label = magnitude >= 2 ? (signal === "BEARISH" ? "strongly bearish" : signal === "BULLISH" ? "strongly bullish" : "neutral")
    : magnitude >= 0.5 ? (signal === "BEARISH" ? "mildly bearish" : signal === "BULLISH" ? "mildly bullish" : "neutral")
    : "neutral";
  return label;
}

function renderSdSummary(d) {
  const bar = $("sd-summary-bar");
  if (!bar) return;
  const list = d.sectors || [];
  const bull = list.filter((s) => s.verdict === "BULLISH").length;
  const bear = list.filter((s) => s.verdict === "BEARISH").length;
  const neutral = list.filter((s) => s.verdict === "NEUTRAL").length;
  const conf = ((d.market_alert || {}).confluence || {}).overall || {};
  const net = conf.net != null ? conf.net : (d.net || 0);
  const trend = sdTrendOf(conf);
  const trendClass = net <= -0.5 ? "bear" : net >= 0.5 ? "bull" : "neut";
  bar.innerHTML =
    "<span class='sd-stat'><span class='sd-dot' style='background:" + SD_COLORS.bull + "'></span>Bullish sectors: <b>" + bull + "</b></span>" +
    "<span class='sd-stat'><span class='sd-dot' style='background:" + SD_COLORS.bear + "'></span>Bearish sectors: <b>" + bear + "</b></span>" +
    "<span class='sd-stat'><span class='sd-dot' style='background:" + SD_COLORS.neutral + "'></span>Neutral sectors: <b>" + neutral + "</b></span>" +
    "<span class='sd-stat'>Net confluence: <b class='sd-net " + trendClass + "'>" + (net >= 0 ? "+" : "") + net.toFixed(1) + "</b></span>" +
    "<span class='sd-stat'>Trend: <b class='sd-net " + trendClass + "'>" + trend + "</b></span>";
}

function sdHitBadge(h) {
  const nature = (h.nature || "benefic").toLowerCase();
  const color = SD_BADGE_COLORS[nature] || SD_BADGE_COLORS.benefic;
  const initial = (h.symbol || h.planet || "?").charAt(0);
  const ray = (h.ray || "right").toLowerCase();
  const posClass = "sd-vpos-" + ray;
  const val = (h.strength >= 0 ? "+" : "") + (h.strength || 0).toFixed(1);
  return "<span class='sd-badge " + posClass + "' style='background:" + color + "' title='" +
    (h.planet || "") + " → " + ray + " ray, strength " + val + "'>" + initial +
    " <span class='sd-badge-val'>" + val + "</span></span>";
}

function renderSdHeatmap(d) {
  const grid = $("sd-heatmap");
  if (!grid) return;
  const list = d.sectors || [];
  grid.innerHTML = "";
  for (const s of list) {
    const verdict = (s.verdict || "NEUTRAL").toLowerCase();
    const colorKey = verdict === "bullish" ? "bull" : verdict === "bearish" ? "bear" : "neutral";
    const intensity = SD_INTENSITY[(s.strength || "flat").toLowerCase()] || 0.4;
    const box = document.createElement("div");
    box.className = "sd-box sd-" + colorKey;
    box.style.setProperty("--sd-alpha", intensity);

    const head = document.createElement("div");
    head.className = "sd-box-head";
    head.innerHTML = "<span class='sd-abbr'>" + (s.abbr || "") + "</span>" +
      "<span class='sd-signal sd-" + colorKey + "-text'>" +
      (verdict === "neutral" ? "no signal" : verdict) + "</span>";
    box.appendChild(head);

    const strength = document.createElement("div");
    strength.className = "sd-strength " + (s.net >= 0 ? "pos" : "neg");
    strength.textContent = (s.net >= 0 ? "+" : "") + (s.net || 0).toFixed(1);
    strength.title = "net vedha strength on this rashi";
    box.appendChild(strength);

    const badges = document.createElement("div");
    badges.className = "sd-badges";
    (s.hits || []).forEach((h) => { badges.innerHTML += sdHitBadge(h); });
    box.appendChild(badges);

    const tags = document.createElement("div");
    tags.className = "sd-chips";
    (s.sectors || []).slice(0, 5).forEach((t) => {
      const chip = document.createElement("span");
      chip.className = "sd-chip";
      chip.textContent = t;
      tags.appendChild(chip);
    });
    if ((s.sectors || []).length > 5) {
      const more = document.createElement("span");
      more.className = "sd-chip sd-chip-more";
      more.textContent = "+" + (s.sectors.length - 5);
      more.title = s.sectors.slice(5).join(", ");
      tags.appendChild(more);
    }
    box.appendChild(tags);
    grid.appendChild(box);
  }
}

function renderSdTrendRibbon(hours) {
  const ribbon = $("sd-trend-ribbon");
  if (!ribbon) return;
  const buckets = [
    { label: "Morning", from: 555, to: 720 },   // 09:15-12:00
    { label: "Midday", from: 720, to: 840 },    // 12:00-14:00
    { label: "Closing", from: 840, to: 930 },   // 14:00-15:30
  ];
  ribbon.innerHTML = "";
  buckets.forEach((b) => {
    const inBucket = (hours || []).filter((h) => {
      const m = h.minute != null ? h.minute : null;
      return m != null && m >= b.from && m < b.to;
    });
    let avg = 0;
    if (inBucket.length) {
      avg = inBucket.reduce((sum, h) => sum + (h.projection || 0), 0) / inBucket.length;
    }
    const colorKey = avg < -0.2 ? "bear" : avg > 0.2 ? "bull" : "neutral";
    const seg = document.createElement("div");
    seg.className = "sd-ribbon-seg sd-ribbon-" + colorKey;
    seg.innerHTML = "<span class='sd-ribbon-label'>" + b.label + "</span>" +
      "<span class='sd-ribbon-val'>" + (inBucket.length ? (avg >= 0 ? "+" : "") + avg.toFixed(1) : "-") + "</span>";
    ribbon.appendChild(seg);
  });
}

function renderSdRadar(secs) {
  const el = $("sd-radar");
  if (!el) return;
  const list = secs || [];
  const size = 260, cx = size / 2, cy = size / 2, rMax = size / 2 - 30;
  const n = list.length || 12;

  const maxAbs = Math.max(1, ...list.map((s) => Math.abs(s.net || 0)));
  const pointOf = (i, value) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const r = (Math.abs(value) / maxAbs) * rMax;
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  };

  let svg = "<svg viewBox='0 0 " + size + " " + size + "' class='sd-radar-svg' role='img' aria-label='Rashi strength radar'>";
  // rings at 25/50/75/100%
  [0.25, 0.5, 0.75, 1.0].forEach((f) => {
    const r = rMax * f;
    svg += "<circle cx='" + cx + "' cy='" + cy + "' r='" + r + "' fill='none' stroke='#1d2a3d' stroke-width='1'/>";
  });
  // axes + labels + polygon points
  let poly = "";
  list.forEach((s, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const [x, y] = [cx + rMax * Math.cos(angle), cy + rMax * Math.sin(angle)];
    svg += "<line x1='" + cx + "' y1='" + cy + "' x2='" + x + "' y2='" + y + "' stroke='#1d2a3d' stroke-width='1'/>";
    const lx = cx + (rMax + 14) * Math.cos(angle);
    const ly = cy + (rMax + 14) * Math.sin(angle);
    const colorKey = (s.verdict || "").toLowerCase() === "bullish" ? "bull" :
      (s.verdict || "").toLowerCase() === "bearish" ? "bear" : "neutral";
    svg += "<text x='" + lx + "' y='" + ly + "' text-anchor='middle' dominant-baseline='middle' font-size='9' fill='#9fb3c8'>" +
      (s.abbr || s.rashi || "") + "</text>";
    const [px, py] = pointOf(i, s.net || 0);
    poly += px.toFixed(1) + "," + py.toFixed(1) + " ";
    svg += "<circle cx='" + px.toFixed(1) + "' cy='" + py.toFixed(1) + "' r='3.5' fill='" + SD_COLORS[colorKey] + "' stroke='#0d1420' stroke-width='1'/>";
  });
  svg += "<polygon points='" + poly.trim() + "' fill='rgba(56,189,248,0.12)' stroke='#38bdf8' stroke-width='1.2'/>";
  svg += "</svg>";
  el.innerHTML = svg;
}

function renderSdWheel(secs) {
  const wheel = $("sd-wheel");
  const legend = $("sd-wheel-legend");
  if (!wheel) return;
  const list = secs || [];
  const bull = list.filter((s) => s.verdict === "BULLISH").length;
  const bear = list.filter((s) => s.verdict === "BEARISH").length;
  const neutral = list.length - bull - bear;
  const total = list.length || 1;
  const fBull = bull / total, fBear = bear / total, fNeutral = neutral / total;

  const stops = [
    SD_COLORS.bull + " 0%",
    SD_COLORS.bull + " " + (fBull * 100).toFixed(1) + "%",
    SD_COLORS.bear + " " + (fBull * 100).toFixed(1) + "%",
    SD_COLORS.bear + " " + ((fBull + fBear) * 100).toFixed(1) + "%",
    SD_COLORS.neutral + " " + ((fBull + fBear) * 100).toFixed(1) + "%",
    SD_COLORS.neutral + " 100%",
  ];
  wheel.style.background = "conic-gradient(" + stops.join(",") + ")";

  if (legend) {
    legend.innerHTML =
      "<span><i class='sd-dot' style='background:" + SD_COLORS.bull + "'></i>Bullish " + bull + "</span>" +
      "<span><i class='sd-dot' style='background:" + SD_COLORS.bear + "'></i>Bearish " + bear + "</span>" +
      "<span><i class='sd-dot' style='background:" + SD_COLORS.neutral + "'></i>Neutral " + neutral + "</span>";
  }
}

async function loadSectorDashboard(dateOverride, predData) {
  const statusEl = $("sd-status");
  if (!statusEl) return;
  const date = dateOverride || localTodayISO();

  statusEl.textContent = "Loading sector dashboard...";
  statusEl.className = "nifty-chart-status";
  try {
    let d = predData;
    if (!d) {
      const resp = await fetchWithTimeout("/api/prediction?date=" + encodeURIComponent(date) +
        "&time=09:15&tz=Asia/Kolkata&anchor=nse&school=classical", 120000);
      d = await resp.json();
      if (!resp.ok || d.error) throw new Error(d.error || resp.status);
    }

    renderSdSummary(d);
    renderSdHeatmap(d);
    renderSdRadar(d.sectors || []);
    renderSdWheel(d.sectors || []);

    // Trend ribbon from the hourly astro-projection
    try {
      const pResp = await fetchWithTimeout("/api/intraday_projection?date=" + encodeURIComponent(date) +
        "&days=1&anchor=nse", 120000);
      const pData = await pResp.json();
      if (pResp.ok && !pData.error) renderSdTrendRibbon(pData.hours || []);
    } catch (e) { /* ribbon is optional */ }

    statusEl.textContent = "Sector dashboard loaded for " + date + ".";
  } catch (e) {
    statusEl.textContent = "Sector dashboard failed: " + e.message;
    statusEl.className = "nifty-chart-status error";
  }
}

// ---------------------------------------------------------------
// AstroCycle Pro: Mercury/Moon cycle time bars
// ---------------------------------------------------------------
