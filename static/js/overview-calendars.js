// Monthly Projection (daily balance), Bhadra calendar, confluence year grid and monthly heatmap.
// Moved out of static/app.js (B-78). Classic script: shares the page's global scope
// with app.js, which loads first and provides $, esc, fetchWithTimeout, localTodayISO.

const BALANCE_COLORS = {
  green: '#4CAF50',
  red: '#E53935',
  grey: '#BDBDBD',
  blue: '#1E88E5',
  brown: '#8D6E63',
  purple: '#8E24AA',
};
window.dailyBalanceChart = null;

function renderDailyIndicationBalance(data) {
  const container = document.getElementById('daily-balance-chart-container');
  if (!container) return;

  const days = data.days || [];
  const dates = data.dates || days.map((d) => String(d));
  const blend = data.blend_bias || [];
  const jyotish = data.jyotish_line || [];
  const kp = data.kp_line || [];
  const western = data.western_line || [];
  const bull = data.bullish_threshold || 4.0;
  const bear = data.bearish_threshold || 2.0;
  const neutral = data.neutral_range || [bear, bull];

  // Dispose any prior chart.
  if (window.dailyBalanceChart) {
    try { window.dailyBalanceChart.remove(); } catch (e) {}
    window.dailyBalanceChart = null;
  }

  const chart = LightweightCharts.createChart(container, {
    width: container.clientWidth || 800,
    height: 420,
    layout: {
      background: { type: 'solid', color: '#141821' },
      textColor: '#cdd3de',
    },
    grid: {
      vertLines: { visible: false },
      horzLines: { color: 'rgba(255,255,255,0.06)' },
    },
    rightPriceScale: {
      borderVisible: false,
      scaleMargins: { top: 0.08, bottom: 0.08 },
    },
    timeScale: {
      borderVisible: false,
      rightOffset: 1,
      barSpacing: 22,
    },
    crosshair: { mode: 'normal' },
  });
  window.dailyBalanceChart = chart;

  // Time is date string (yyyy-mm-dd); map day index -> date, fallback to index.
  const timeOf = (i) => (dates[i] ? dates[i] : (i + 1));

  // --- Background zones (BaselineSeries full-width bands) ---
  const maxY = 6.5, minY = -0.5;
  function addZone(bottom, top, color) {
    const s = chart.addBaselineSeries({
      baseValue: { type: 'price', price: bottom },
      topLineColor: 'transparent',
      bottomLineColor: 'transparent',
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    const pts = days.map((_, i) => ({ time: timeOf(i), value: top }));
    s.setData(pts);
    s.applyOptions({
      topFillColor1: color,
      topFillColor2: color,
      bottomFillColor1: color,
      bottomFillColor2: color,
      topLineColor: 'transparent',
      bottomLineColor: 'transparent',
    });
  }
  // Bullish zone (above neutral top), neutral zone, bearish zone (below neutral bottom).
  addZone(neutral[1], maxY, 'rgba(76, 175, 80, 0.16)');
  addZone(neutral[0], neutral[1], 'rgba(189, 189, 189, 0.12)');
  addZone(minY, neutral[0], 'rgba(229, 57, 53, 0.16)');

  // --- Blend bars (histogram) ---
  const barSeries = chart.addHistogramSeries({
    color: BALANCE_COLORS.grey,
    priceLineVisible: false,
    lastValueVisible: false,
    base: 0,
  });
  barSeries.setData(blend.map((v, i) => {
    let color = BALANCE_COLORS.grey;
    if (v > bull) color = BALANCE_COLORS.green;
    else if (v < bear) color = BALANCE_COLORS.red;
    return { time: timeOf(i), value: v, color };
  }));


  // --- SBC confluence indicator (single line) ---
  const confluenceLine = chart.addLineSeries({
    color: BALANCE_COLORS.blue,
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: true,
    crosshairMarkerVisible: false,
    lineStyle: 0,
  });
  confluenceLine.setData(blend.map((v, i) => ({ time: timeOf(i), value: v })));

  chart.timeScale().fitContent();
}

async function loadDailyIndicationBalance(date) {
  const chartContainer = $("daily-balance-chart-container");
  if (!chartContainer) return;
  // B-66: four triggers (tab open, date picker, calendar, start-up) used to start
  // the same 30-day computation up to three times at once.
  if (window.dailyBalanceInflight === date) return;
  window.dailyBalanceInflight = date;
  try {
    await loadDailyIndicationBalanceOnce(date);
  } finally {
    if (window.dailyBalanceInflight === date) window.dailyBalanceInflight = null;
  }
}

async function loadDailyIndicationBalanceOnce(date) {
  const chartContainer = $("daily-balance-chart-container");
  window.dailyBalanceLoadedFor = date;
  try {
    // This endpoint computes 30 days x 2 predictions and can exceed the
    // default 8s fetch timeout on a cold cache, so use a longer timeout.
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 120000);
    let response;
    try {
      response = await fetch("/api/daily_indication_balance?start=" + encodeURIComponent(date), { signal: controller.signal });
    } finally {
      clearTimeout(t);
    }
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderDailyIndicationBalance(data);
  } catch (e) {
    console.error("Daily Indication Balance failed:", e);
    const container = $("daily-balance-content");
    if (container) container.textContent = "Daily indication balance is unavailable. Try again.";
  }
}

if ($("daily-balance-run")) {
  $("daily-balance-run").addEventListener("click", () => {
    const date = ($("daily-balance-date") && $("daily-balance-date").value) || ($("date") && $("date").value);
    if (date) loadDailyIndicationBalance(date);
  });
}

// ---------------------------------------------------------------
// Bhadra (Vishti Karana) Monthly Calendar
// ---------------------------------------------------------------
const bhadraState = { date: null, offset: 0, tz: "Asia/Kolkata" };

function bhadraBaseDate() {
  const d = $("date") && $("date").value;
  return (d && /\d{4}-\d{2}-\d{2}/.test(d)) ? d : localTodayISO();
}

function fmtBhadraDate(iso) {
  const d = new Date(iso);
  const months = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  const days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

function fmtBhadraTime(iso) {
  const d = new Date(iso);
  let h = d.getHours();
  const m = String(d.getMinutes()).padStart(2, "0");
  const ap = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${m} ${ap}`;
}

async function loadBhadraCalendar() {
  const url = "/api/bhadra_calendar?date=" + encodeURIComponent(bhadraState.date) +
    "&tz=" + encodeURIComponent(bhadraState.tz) + "&offset=" + bhadraState.offset;
  try {
    const r = await fetchWithTimeout(url);
    const data = await r.json();
    if (data.error) throw new Error(data.error);
    renderBhadraCalendar(data);
  } catch (e) {
    console.error("Bhadra calendar failed:", e);
    const list = $("bhadra-list");
    if (list) list.textContent = "Bhadra calendar is unavailable. Try again.";
    const bt = $("bhadra-backtest");
    if (bt) bt.innerHTML = "";
  }
}

function renderBhadraCalendar(data) {
  const label = $("bhadra-month-label");
  if (label) label.textContent = data.month_year;
  const loc = $("bhadra-location");
  if (loc) loc.textContent = data.location;
  const sub = $("bhadra-sub");
  if (sub) sub.textContent = `${data.count} Bhadra window${data.count === 1 ? "" : "s"} in ${data.month_year} · ${data.timezone}`;

  const list = $("bhadra-list");
  if (!list) return;
  list.innerHTML = "";
  if (!data.windows.length) {
    list.innerHTML = '<div class="bhadra-empty">No Bhadra (Vishti) windows this month.</div>';
  } else {
    for (const w of data.windows) {
      const item = document.createElement("article");
      item.className = "bhadra-item" + (w.spans_midnight ? " bhadra-overnight" : "");
      const begin = document.createElement("div");
      begin.className = "bhadra-seg";
      begin.innerHTML = `<span class="bhadra-kind">Bhadra begins</span>
        <span class="bhadra-date">${w.begin_date}</span>
        <span class="bhadra-weekday">${w.begin_weekday}</span>
        <span class="bhadra-time">at ${w.begin_time}</span>`;
      const end = document.createElement("div");
      end.className = "bhadra-seg";
      end.innerHTML = `<span class="bhadra-kind">Bhadra ends</span>
        <span class="bhadra-date">${w.end_date}</span>
        <span class="bhadra-weekday">${w.end_weekday}</span>
        <span class="bhadra-time">at ${w.end_time}</span>`;
      item.appendChild(begin);
      item.appendChild(end);
      list.appendChild(item);
    }
  }

  renderBhadraBacktest(data);
}

function renderBhadraBacktest(data) {
  const box = $("bhadra-backtest");
  if (!box) return;
  box.innerHTML = "";
  const overlap = data.reversal_overlap;
  if (!overlap || overlap.error) {
    if (overlap && overlap.error) box.innerHTML = '<p class="bhadra-note">Reversal-calendar backtest unavailable: ' + overlap.error + '</p>';
    return;
  }
  const head = document.createElement("div");
  head.className = "bhadra-bt-head";
  head.innerHTML = `<span class="bhadra-bt-stats">${overlap.overlap_count} of ${overlap.total_reversal_days} reversal days overlap a Bhadra window</span>`;
  box.appendChild(head);

  if (overlap.reversal_days.length === 0) {
    box.innerHTML += '<p class="bhadra-note">No reversal-alert days in this month.</p>';
    return;
  }
  const ul = document.createElement("ul");
  ul.className = "bhadra-bt-list";
  for (const d of overlap.reversal_days) {
    const li = document.createElement("li");
    li.className = d.bhadra_overlap ? "bhadra-overlap" : "";
    let muhurtHtml = "";
    if (d.bhadra_overlap && d.bhadra_windows && d.bhadra_windows.length) {
      const spans = d.bhadra_windows.map((w) => {
        const start = fmtBhadraMuhurt(w.muhurt_begin_iso, w.muhurt_begin_time);
        const end = fmtBhadraMuhurt(w.muhurt_end_iso, w.muhurt_end_time);
        return `${start} → ${end}`;
      }).join("<br>");
      muhurtHtml = `<span class="bhadra-bt-muhurt">Bhadra muhurt: ${spans}</span>`;
    }
    li.innerHTML = `<span class="bhadra-bt-date">${d.date}</span>
      <span class="bhadra-bt-flag">${d.bhadra_overlap ? "⚠ overlaps Bhadra" : "no overlap"}</span>
      <span class="bhadra-bt-titles">${d.titles.join(", ")}</span>
      ${muhurtHtml}`;
    ul.appendChild(li);
  }
  box.appendChild(ul);
}

function fmtBhadraMuhurt(iso, time) {
  if (!iso) return time || "";
  const dt = new Date(iso);
  if (isNaN(dt.getTime())) return time || "";
  const hh = String(dt.getHours()).padStart(2, "0");
  const mm = String(dt.getMinutes()).padStart(2, "0");
  const mo = String(dt.getMonth() + 1).padStart(2, "0");
  const dd = String(dt.getDate()).padStart(2, "0");
  return `${dt.getFullYear()}-${mo}-${dd} ${hh}:${mm}`;
}

// ---------------------------------------------------------------
// Monthly Sector Confluence Heatmap
// ---------------------------------------------------------------
// ---- Confluence Calendar Matrix (year view, day-of-month) ----

function initConfluenceMatrix() {
  const yearSel = $("cm-year");
  if (!yearSel) return;
  const now = new Date();
  [now.getFullYear(), now.getFullYear() + 1,
   now.getFullYear() - 1, now.getFullYear() - 2].forEach((y) => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    if (y === now.getFullYear()) opt.selected = true;
    yearSel.appendChild(opt);
  });
  $("cm-run").addEventListener("click", loadConfluenceMatrix);
  // B-66: the year grid is 12 heavy requests and sits below the fold; start it when
  // it scrolls into view instead of on page load.
  const host = $("cm-matrix");
  if (host && "IntersectionObserver" in window) {
    host.innerHTML = '<div class="exec-empty">Loads when you scroll here.</div>';
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { io.disconnect(); loadConfluenceMatrix(); }
    }, { rootMargin: "200px" });
    io.observe(host);
  } else {
    loadConfluenceMatrix();
  }
}

async function loadConfluenceMatrix() {
  const year = $("cm-year").value || String(new Date().getFullYear());
  const statusEl = $("cm-status");
  if (!statusEl) return;
  statusEl.textContent = `Computing daily confluence verdicts for ${year}...`;
  statusEl.className = "nifty-chart-status";
  $("cm-matrix").innerHTML = '<div class="exec-empty">Loading...</div>';
  try {
    // Month-by-month: keeps each request short so one slow stretch (fresh
    // future dates, server busy) can't abort the whole load; each month
    // paints as it arrives. One retry per month rides out transient
    // contention (e.g. a background cache warm holding the server).
    const series = [];
    for (let m = 1; m <= 12; m++) {
      const last = new Date(year, m, 0).getDate();
      const mm = String(m).padStart(2, "0");
      const anchor = document.getElementById('anchor')?.value || 'nifty';
      const school = document.getElementById('school')?.value || 'classical';
      const url = `/api/prediction_series?start=${year}-${mm}-01&end=${year}-${mm}-${last}&anchor=${encodeURIComponent(anchor)}&school=${encodeURIComponent(school)}`;
      let data = null;
      for (let attempt = 0; attempt < 2 && !data; attempt++) {
        try {
          const resp = await fetchWithTimeout(url, 300000);
          const j = await resp.json();
          if (!resp.ok || j.error) throw new Error(j.error || ("HTTP " + resp.status));
          data = j.series || [];
        } catch (e) {
          if (attempt === 1) throw e;
          statusEl.textContent = `Server busy — retrying ${year}-${mm}...`;
          await new Promise((res) => setTimeout(res, 1500));
        }
      }
      series.push(...data);
      statusEl.textContent = `Computed ${series.length} days for ${year} (month ${m}/12)...`;
      if (m < 12) renderConfluenceMatrix(series, year, true);
    }
    renderConfluenceMatrix(series, year);
  } catch (e) {
    statusEl.textContent = "Confluence matrix failed: " + e.message;
    statusEl.className = "nifty-chart-status error";
  }
}

function renderConfluenceMatrix(series, year, partial) {
  const host = $("cm-matrix");
  const summaryEl = $("cm-summary");
  const statusEl = $("cm-status");
  if (!host) return;
  host.innerHTML = "";

  const byDate = {};
  series.forEach((r) => { if (!r.error) byDate[r.date] = r; });

  const now = new Date();
  const todayStr = now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0") + "-" + String(now.getDate()).padStart(2, "0");
  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const counts = { BULLISH: 0, BEARISH: 0, NEUTRAL: 0 };
  let missing = 0;

  let html = '<div class="cm-row">';
  html += '<div class="cm-month-label"></div>';
  for (let d = 1; d <= 31; d++) html += `<div class="cm-day-head">${d}</div>`;
  html += "</div>";

  for (let m = 0; m < 12; m++) {
    html += '<div class="cm-row">';
    html += `<div class="cm-month-label">${monthNames[m]} ${year}</div>`;
    const daysInMonth = new Date(year, m + 1, 0).getDate();
    for (let d = 1; d <= 31; d++) {
      if (d > daysInMonth) { html += '<div class="cm-cell empty"></div>'; continue; }
      const ds = `${year}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const r = byDate[ds];
      let cls = "cm-cell neut";
      let verdict = "NEUTRAL";
      if (r && r.verdict) {
        verdict = r.verdict;
        if (r.verdict === "BULLISH") { cls = "cm-cell bull"; counts.BULLISH++; }
        else if (r.verdict === "BEARISH") { cls = "cm-cell bear"; counts.BEARISH++; }
        else { counts.NEUTRAL++; }
      } else {
        missing++;
      }
      const tip = `${ds} · ${verdict}` +
        (r && r.net !== undefined && r.net !== null ? ` (net ${r.net})` : "") +
        (r && r.rec ? ` · ${r.rec}` : "") +
        (r && r.risk_label ? ` · risk: ${r.risk_label}` : "") +
        (r && r.lunar_phase ? ` · ${r.lunar_phase}` : "");
      const todayCls = ds === todayStr ? " today" : "";
      const tipAttr = tip.split(String.fromCharCode(34)).join("");
      html += `<div class="${cls}${todayCls}" data-date="${ds}" title="${tipAttr}"></div>`;
    }
    html += "</div>";
  }
  host.innerHTML = html;

  const total = counts.BULLISH + counts.BEARISH + counts.NEUTRAL;
  const anchor = document.getElementById('anchor')?.value || 'nifty';
  const school = document.getElementById('school')?.value || 'classical';
  if (summaryEl) {
    summaryEl.textContent =
      `${year} [${anchor}/${school}]: ${counts.BULLISH} bullish · ${counts.BEARISH} bearish · ${counts.NEUTRAL} neutral` +
      (missing ? ` · ${missing} days unavailable` : "") +
      (partial ? " · loading..." : " · click any day to load its Daily Indication Balance");
  }
  if (statusEl && !partial) statusEl.textContent = `Matrix ready for ${year} (${total} days).`;

  host.querySelectorAll(".cm-cell[data-date]").forEach((cell) => {
    cell.addEventListener("click", function () {
      const d = this.dataset.date;
      const balDate = $("daily-balance-date");
      if (balDate) balDate.value = d;
      if (typeof loadDailyIndicationBalance === "function") loadDailyIndicationBalance(d);
    });
  });
}

function initMonthlyHeatmap() {
  const run = $("monthly-heatmap-run");
  const dateEl = $("monthly-heatmap-date");
  if (!run || !dateEl) return;
  if (!dateEl.value) {
    const now = new Date();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    // Start of current month
    dateEl.value = `${now.getFullYear()}-${m}-01`;
  }
  run.addEventListener("click", loadMonthlyHeatmap);
  loadMonthlyHeatmap();
}

async function loadMonthlyHeatmap() {
  const dateEl = $("monthly-heatmap-date");
  const daysEl = $("monthly-heatmap-days");
  const statusEl = $("monthly-heatmap-status");
  const gridEl = $("monthly-heatmap-grid");
  const noteEl = $("monthly-heatmap-note");
  if (!dateEl) return;
  const date = dateEl.value;
  const days = daysEl ? daysEl.value : "30";
  if (!date) { statusEl.textContent = "Pick a start date for the heatmap."; return; }
  statusEl.textContent = "Computing sector \u00d7 day confluence...";
  try {
    const url = "/api/monthly_heatmap?date=" + encodeURIComponent(date) + "&days=" + days;
    const resp = await fetchWithTimeout(url);
    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error("HTTP " + resp.status + " (" + (txt.slice(0, 60) || "").replace(/</g, "&lt;") + ")");
    }
    const data = await resp.json();
    if (data.error) { statusEl.textContent = "Heatmap error: " + data.error; return; }
    renderMonthlyHeatmap(data);
    statusEl.textContent = "";
    noteEl.textContent = data.disclaimer || "";
  } catch (e) {
    statusEl.textContent = "Heatmap failed: " + e.message + " \u2014 restart the Flask server (python app.py) to pick up the /api/monthly_heatmap route.";
  }
}

function heatColor(net, maxAbs) {
  // blue/red divergence; neutral = transparent
  if (!maxAbs || maxAbs === 0) return "rgba(128,128,128,0.06)";
  const t = Math.max(-1, Math.min(1, net / maxAbs));
  if (t > 0.05) return `rgba(34,197,94,${0.12 + 0.7 * t})`;   // bullish green
  if (t < -0.05) return `rgba(239,68,68,${0.12 + 0.7 * -t})`;  // bearish red
  return "rgba(128,128,128,0.08)"; // neutral
}

let mhLastData = null;
let mhShowAll = false;

function renderMonthlyHeatmap(data) {
  mhLastData = data;
  drawMonthlyHeatmap();
}

// Strong-day cut-off: the top quartile of |net| across all sector cells.
// Anything weaker stays blank so the coloured cells are the signal.
function mhThreshold(values) {
  const abs = values.map(v => Math.abs(v)).filter(v => v > 0).sort((a, b) => a - b);
  if (!abs.length) return 0;
  return abs[Math.floor(0.75 * (abs.length - 1))];
}

function mhLunarIcons(markers, bhadraActive) {
  const labels = (markers || []).map(m => m.label || "");
  const icons = [];
  if (labels.includes("FULL MOON")) icons.push("\u{1F315}");
  if (labels.includes("NEW MOON")) icons.push("\u{1F311}");
  if (labels.includes("EKADASHI")) icons.push("11\uFE0F\u20E3");
  if (labels.includes("ASHTAMI")) icons.push("8\uFE0F\u20E3");
  if (labels.includes("CHATURDASHI")) icons.push("14\uFE0F\u20E3");
  if (bhadraActive) icons.push("\u26A0");
  return icons.join(" ");
}

function drawMonthlyHeatmap() {
  const data = mhLastData;
  const gridEl = $("monthly-heatmap-grid");
  const lunarEl = $("monthly-heatmap-lunar");
  const legendEl = $("monthly-heatmap-legend");
  if (!gridEl || !data) return;

  const sectors = data.sectors || [];
  const dates = data.dates || [];
  const matrix = data.matrix || {};
  const bhadra = data.bhadra || {};
  const valueOf = (s, d) => (matrix[s] && matrix[s][d] != null ? matrix[s][d] : 0);

  const allValues = [];
  for (const s of sectors) for (const d of dates) allValues.push(valueOf(s, d));
  const maxAbs = Math.max(0, ...allValues.map(v => Math.abs(v)));
  const thr = mhShowAll ? 0 : mhThreshold(allValues);

  // Blank unless the day clears the threshold; intensity scales with |net|.
  const cellBg = (v) => {
    if (!maxAbs || v === 0 || Math.abs(v) < thr) return "";
    const a = 0.25 + 0.6 * Math.min(1, Math.abs(v) / maxAbs);
    return v > 0 ? `rgba(34,197,94,${a})` : `rgba(239,68,68,${a})`;
  };
  const signed = (v) => (v >= 0 ? "+" : "") + v.toFixed(2);

  legendEl.innerHTML = "";
  const note = document.createElement("span");
  note.textContent = mhShowAll
    ? "Green = bullish, red = bearish. All days shown. Hover for values."
    : "Green = bullish, red = bearish. Only the strongest quarter of days is coloured. Hover for values.";
  const toggle = document.createElement("label");
  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.checked = mhShowAll;
  cb.addEventListener("change", () => { mhShowAll = cb.checked; drawMonthlyHeatmap(); });
  toggle.append(cb, " Show all days");
  legendEl.append(note, toggle);

  // Lunar markers per day, plus a detail panel filled on click.
  const markersByDay = {};
  for (const m of (data.lunar_markers || [])) (markersByDay[m.date] = markersByDay[m.date] || []).push(m);
  lunarEl.innerHTML = "";
  const key = document.createElement("div");
  key.className = "mh-lunar-key";
  key.textContent = "\u{1F315} Purnima \u00B7 \u{1F311} Amavasya \u00B7 11\uFE0F\u20E3 Ekadashi \u00B7 8\uFE0F\u20E3 Ashtami \u00B7 14\uFE0F\u20E3 Chaturdashi \u00B7 \u26A0 Bhadra \u2014 click an icon or a sector name for detail";
  const detailEl = document.createElement("div");
  detailEl.id = "mh-lunar-detail";
  detailEl.textContent = "";
  lunarEl.append(key, detailEl);

  const showDay = (d) => {
    const lines = [`Lunar timing for ${d}`];
    for (const e of (markersByDay[d] || [])) {
      lines.push(e.label === "MOON NAKSHATRA"
        ? `\u2022 Moon nakshatra: ${e.type.replace("Moon:", "").trim()}`
        : `\u2022 ${e.type} - ${e.label}`);
    }
    if (bhadra[d]) {
      lines.push("\u26A0 Bhadra/Vishti muhurt active");
      for (const w of bhadra[d]) lines.push(`  ${w.begin} - ${w.end}`);
    }
    if (lines.length === 1) lines.push("\u2022 No lunar markers");
    detailEl.textContent = lines.join("\n");
  };

  const showSector = (s) => {
    const ranked = dates
      .map(d => ({ d, v: valueOf(s, d) }))
      .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
      .slice(0, 5);
    const total = dates.reduce((acc, d) => acc + valueOf(s, d), 0);
    detailEl.textContent = [
      `${s} \u2014 month total ${signed(total)}`,
      "Strongest days:",
      ...ranked.map(r => `  ${r.d}  ${signed(r.v)}`),
    ].join("\n");
  };

  // Grid: label columns, then one column per day.
  const grid = document.createElement("div");
  grid.className = "mh-grid";
  grid.style.gridTemplateColumns = `150px 120px repeat(${dates.length}, 16px)`;
  const add = (cls, text, title) => {
    const el = mkCell(cls, text, title);
    grid.appendChild(el);
    return el;
  };

  // Lunar row sits above the date header.
  add("mh-corner", "Lunar");
  add("mh-corner", "");
  for (const d of dates) {
    const el = add("mh-lunar-cell", mhLunarIcons(markersByDay[d], !!bhadra[d]), d);
    el.addEventListener("click", () => showDay(d));
  }

  // Date header: a day number every 5 days keeps the axis readable.
  add("mh-corner", "Sector");
  add("mh-corner", "Month total");
  dates.forEach((d, i) => add("mh-date", i % 5 === 0 ? d.slice(8) : "", d));

  // Summary row: sum of sector nets per day, same colour rule.
  add("mh-sector-cell mh-overall", "All sectors");
  add("mh-total", "");
  for (const d of dates) {
    const v = sectors.reduce((acc, s) => acc + valueOf(s, d), 0);
    const el = add("mh-cell", "", `All sectors \u00B7 ${d} \u00B7 net ${signed(v)}`);
    el.style.background = cellBg(v);
  }

  // Sector rows, sorted by month total (most bullish first).
  const totals = sectors
    .map(s => ({ s, total: dates.reduce((acc, d) => acc + valueOf(s, d), 0) }))
    .sort((a, b) => b.total - a.total);
  const maxTotal = Math.max(0, ...totals.map(t => Math.abs(t.total)));
  for (const { s, total } of totals) {
    const name = add("mh-sector-cell", s, `${s} \u2014 click for strongest days`);
    name.addEventListener("click", () => showSector(s));

    const bar = document.createElement("div");
    bar.className = "mh-bar";
    const track = document.createElement("div");
    track.className = "mh-bar-track";
    const fill = document.createElement("div");
    fill.className = "mh-bar-fill " + (total >= 0 ? "mh-pos" : "mh-neg");
    fill.style.width = (maxTotal ? (Math.abs(total) / maxTotal) * 50 : 0) + "%";
    track.appendChild(fill);
    const val = document.createElement("span");
    val.className = "mh-bar-val";
    val.textContent = signed(total);
    bar.append(track, val);
    const barCell = add("mh-total", "");
    barCell.appendChild(bar);

    for (const d of dates) {
      const v = valueOf(s, d);
      const el = add("mh-cell", "", `${s} \u00B7 ${d} \u00B7 net ${signed(v)}`);
      el.style.background = cellBg(v);
    }
  }

  gridEl.innerHTML = "";
  gridEl.appendChild(grid);
}

function mkCell(cls, text, title) {
  const el = document.createElement("div");
  el.className = cls;
  el.textContent = text;
  if (title) el.title = title;
  return el;
}

