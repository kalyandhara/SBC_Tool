const CELL = 60;
const TOL = 0.5;
const FETCH_TIMEOUT = 8000;

const $ = (id) => document.getElementById(id);

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

const NATURE = {
  malefic: { cls: "malefic", label: "Ashubha" },
  benefic: { cls: "benefic", label: "Shubha" },
};

// ============================================================================
// Settings Persistence (localStorage)
// ============================================================================
const SETTINGS_KEY = "sbc_tool_settings";
const DEFAULT_SETTINGS = {
  date: "",
  time: "09:15",
  tz: "Asia/Kolkata",
  anchor: "nse",
  school: "allthree",
  activeTab: "tab-overview",
  theme: "dark",
};

function loadSettings() {
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.warn("Failed to load settings:", e);
  }
  return DEFAULT_SETTINGS;
}

function saveSettings(settings) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (e) {
    console.warn("Failed to save settings:", e);
  }
}

function applySettings(settings) {
  const dateEl = $("date");
  const timeEl = $("time");
  const tzEl = $("tz");
  const anchorEl = $("anchor");
  const schoolEl = $("school");

  if (dateEl && settings.date) dateEl.value = settings.date;
  if (timeEl && settings.time) timeEl.value = settings.time;
  if (tzEl && settings.tz) tzEl.value = settings.tz;
  if (anchorEl && settings.anchor) anchorEl.value = settings.anchor;
  if (schoolEl && settings.school) schoolEl.value = settings.school;

  // Apply theme
  if (settings.theme) {
    document.documentElement.setAttribute("data-theme", settings.theme);
  }

  // Switch to active tab
  if (settings.activeTab && document.getElementById(settings.activeTab)) {
    const tabBtn = document.querySelector(`[data-tab="${settings.activeTab}"]`);
    if (tabBtn) tabBtn.click();
  }
}

function persistCurrentSettings() {
  const settings = loadSettings();
  const dateEl = $("date");
  const timeEl = $("time");
  const tzEl = $("tz");
  const anchorEl = $("anchor");
  const schoolEl = $("school");

  if (dateEl) settings.date = dateEl.value;
  if (timeEl) settings.time = timeEl.value;
  if (tzEl) settings.tz = tzEl.value;
  if (anchorEl) settings.anchor = anchorEl.value;
  if (schoolEl) settings.school = schoolEl.value;

  saveSettings(settings);
}

// ============================================================================
// Toast Notification System
// ============================================================================
function showToast(message, type = "info", duration = 3000) {
  const container = getOrCreateToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "polite");
  toast.innerHTML = `
    <span class="toast-message">${message}</span>
    <button class="toast-close" aria-label="Dismiss">&times;</button>
  `;

  toast.querySelector(".toast-close").addEventListener("click", () => {
    toast.remove();
  });

  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => toast.classList.add("toast-show"));

  setTimeout(() => {
    toast.classList.remove("toast-show");
    toast.addEventListener("transitionend", () => toast.remove());
  }, duration);
}

function getOrCreateToastContainer() {
  let container = $("#toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    container.setAttribute("aria-live", "polite");
    container.setAttribute("aria-atomic", "true");
    document.body.appendChild(container);
  }
  return container;
}

// ============================================================================
// Sector Filter Pills (Dynamic from known sectors)
// ============================================================================
const SECTOR_CATEGORIES = [
  { key: "all", label: "All Sectors" },
  { key: "financial", label: "Financial", sectors: ["Banking", "Financial Services", "Insurance", "NBFC"] },
  { key: "technology", label: "Technology", sectors: ["IT", "Software", "Tech Hardware"] },
  { key: "consumption", label: "Consumption", sectors: ["FMCG", "Food", "Beverages", "Retail"] },
  { key: "manufacturing", label: "Manufacturing", sectors: ["Auto", "Chemicals", "Capital Goods", "Industrial"] },
  { key: "healthcare", label: "Healthcare", sectors: ["Pharma", "Hospitals", "Diagnostics"] },
  { key: "energy", label: "Energy", sectors: ["Oil & Gas", "Power", "Renewables"] },
  { key: "metals", label: "Metals & Mining", sectors: ["Steel", "Aluminium", "Copper", "Mining"] },
  { key: "realty", label: "Real Estate", sectors: ["Realty", "Construction", "Cement"] },
  { key: "telecom", label: "Telecom", sectors: ["Telecom", "Towers"] },
  { key: "leisure", label: "Leisure & Hospitality", sectors: ["Hotels", "Travel", "Entertainment", "Media"] },
];

function initSectorFilters() {
  const pillContainer = $("#sector-filter-pills");
  if (!pillContainer) return;

  // Clear existing
  pillContainer.innerHTML = "";

  SECTOR_CATEGORIES.forEach((cat, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill" + (idx === 0 ? " active" : "");
    btn.dataset.filter = cat.key;
    btn.textContent = cat.label;
    btn.setAttribute("role", "tab");
    btn.setAttribute("aria-selected", idx === 0 ? "true" : "false");
    btn.addEventListener("click", () => handleSectorFilterClick(cat.key, btn));
    pillContainer.appendChild(btn);
  });
}

function handleSectorFilterClick(filterKey, clickedBtn) {
  // Update pill states
  document.querySelectorAll(".filter-pills .pill").forEach((pill) => {
    pill.classList.remove("active");
    pill.setAttribute("aria-selected", "false");
  });
  clickedBtn.classList.add("active");
  clickedBtn.setAttribute("aria-selected", "true");

  // Filter sector sections
  const sectorSections = document.querySelectorAll("#tab-sectors .panel[data-sector-category]");
  sectorSections.forEach((sec) => {
    const cat = sec.getAttribute("data-sector-category");
    if (filterKey === "all" || cat === "all" || cat === filterKey) {
      sec.style.display = "";
    } else {
      sec.style.display = "none";
    }
  });

  // Save preference
  const settings = loadSettings();
  settings.sectorFilter = filterKey;
  saveSettings(settings);
}

// ============================================================================
// Keyboard Navigation & Accessibility Helpers
// ============================================================================
function initKeyboardNavigation() {
  // Tab switching with arrow keys
  document.querySelectorAll(".nav-tab").forEach((tab, idx, tabs) => {
    tab.addEventListener("keydown", (e) => {
      let targetIdx = idx;
      if (e.key === "ArrowRight") targetIdx = (idx + 1) % tabs.length;
      else if (e.key === "ArrowLeft") targetIdx = (idx - 1 + tabs.length) % tabs.length;
      else if (e.key === "Home") targetIdx = 0;
      else if (e.key === "End") targetIdx = tabs.length - 1;
      else return;

      e.preventDefault();
      tabs[targetIdx].focus();
      tabs[targetIdx].click();
    });
  });

  // Pill navigation with arrow keys
  document.querySelectorAll(".filter-pills .pill").forEach((pill, idx, pills) => {
    pill.addEventListener("keydown", (e) => {
      let targetIdx = idx;
      if (e.key === "ArrowRight") targetIdx = (idx + 1) % pills.length;
      else if (e.key === "ArrowLeft") targetIdx = (idx - 1 + pills.length) % pills.length;
      else if (e.key === "Home") targetIdx = 0;
      else if (e.key === "End") targetIdx = pills.length - 1;
      else return;

      e.preventDefault();
      pills[targetIdx].focus();
      pills[targetIdx].click();
    });
  });

  // Escape key to close dropdowns
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".week-calendar-dropdown, .toast").forEach((el) => {
        el.classList.add("hidden");
      });
    }
  });
}

// ============================================================================
// Theme Toggle
// ============================================================================
function initThemeToggle() {
  const toggleBtn = $("#theme-toggle");
  if (!toggleBtn) return;

  const settings = loadSettings();
  const isDark = settings.theme === "dark";
  toggleBtn.setAttribute("aria-pressed", isDark);
  toggleBtn.textContent = isDark ? "☀️ Light" : "🌙 Dark";

  toggleBtn.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    toggleBtn.setAttribute("aria-pressed", newTheme === "dark");
    toggleBtn.textContent = newTheme === "dark" ? "☀️ Light" : "🌙 Dark";

    const settings = loadSettings();
    settings.theme = newTheme;
    saveSettings(settings);
  });
}

function setExecutiveLoading() {
  const loadingBadge = '<span class="dir-badge dir-neutral">Loading...</span>';
  if ($("exec-bias-badge")) $("exec-bias-badge").innerHTML = loadingBadge;
  if ($("exec-bias-sub")) $("exec-bias-sub").textContent = "Calculating market bias...";
  if ($("exec-risk-badge")) $("exec-risk-badge").innerHTML = loadingBadge;
  if ($("exec-risk-sub")) $("exec-risk-sub").textContent = "Evaluating volatility signals...";
  if ($("exec-reversal-badge")) $("exec-reversal-badge").innerHTML = '<span class="reversal-date">Loading...</span>';
  if ($("exec-reversal-sub")) $("exec-reversal-sub").textContent = "Checking reversal windows...";
  if ($("exec-leaders")) $("exec-leaders").innerHTML = '<span class="exec-empty">Loading sector ranking...</span>';
  if ($("exec-data-status")) $("exec-data-status").textContent = "Forecast status: calculating inputs and supporting signals...";
  if ($("prediction-error")) $("prediction-error").classList.add("hidden");
}

function showPredictionError() {
  const errorBox = $("prediction-error");
  if (errorBox) errorBox.classList.remove("hidden");
  if ($("exec-data-status")) $("exec-data-status").textContent = "Forecast status: unavailable; last successful result is unchanged.";
}

function cellCenter(row, col) {
  return { x: (col - 1) * CELL + CELL / 2, y: (row - 1) * CELL + CELL / 2 };
}

let state = null;

function setTodayAsDefault() {
  const dateInput = $("date");
  if (dateInput.value) return;
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  dateInput.value = `${now.getFullYear()}-${month}-${day}`;
}

async function loadPresets() {
  try {
    const r = await fetchWithTimeout("/api/presets");
    const data = await r.json();
    const sel = $("anchor");
    if (!sel) return;
    const currentVal = sel.value || "nse";
    sel.innerHTML = "";
    for (const a of data.anchors) {
      const opt = document.createElement("option");
      opt.value = a.key;
      opt.textContent = a.name;
      sel.appendChild(opt);
    }
    sel.value = currentVal;
  } catch (e) {
    console.error("Failed to load presets:", e);
    if ($("anchor") && !$("anchor").value) {
      $("anchor").innerHTML = '<option value="nse">NSE (National Stock Exchange)</option>';
    }
  }
}

function renderExecutiveActionBar(d) {
  const biasBadge = $("exec-bias-badge");
  const biasSub = $("exec-bias-sub");
  const riskBadge = $("exec-risk-badge");
  const riskSub = $("exec-risk-sub");
  const reversalBadge = $("exec-reversal-badge");
  const reversalSub = $("exec-reversal-sub");
  const leadersBox = $("exec-leaders");
  const status = $("exec-data-status");

  if (status) {
    const calculatedAt = new Date().toLocaleString([], {
      dateStyle: "medium",
      timeStyle: "short",
    });
    status.textContent = `Forecast calculated ${calculatedAt} · Input ${d.date} ${d.time} ${d.timezone} · Supporting panels may load separately`;
  }

  // 1. Bias Calculation
  if (biasBadge && d.sentiment) {
    const s = d.sentiment;
    const isBull = s.verdict === "BULLISH";
    const isBear = s.verdict === "BEARISH";
    const badgeClass = isBull ? "dir-bull" : isBear ? "dir-bear" : "dir-neutral";
    const arrow = isBull ? "▲" : isBear ? "▼" : "—";
    biasBadge.innerHTML = `<span class="dir-badge ${badgeClass}">${arrow} ${s.verdict} (${s.strength})</span>`;
    if (biasSub) {
      biasSub.textContent = `Net Score: ${(d.net >= 0 ? "+" : "") + d.net.toFixed(1)} | Benefic: ${d.score.benefic.toFixed(1)} vs Malefic: ${d.score.malefic.toFixed(1)}`;
    }
  }

  // 2. Risk Calculation
  if (riskBadge) {
    const alert = d.market_alert;
    const hasActiveAlert = alert && alert.active;
    const totalAlerts = alert ? (alert.total_alerts !== undefined ? alert.total_alerts : alert.windows?.length || 0) : 0;
    if (hasActiveAlert || totalAlerts >= 2) {
      riskBadge.innerHTML = `<span class="dir-badge dir-high">⚠️ HIGH / ACTIVE (${totalAlerts} Alerts)</span>`;
      if (riskSub) riskSub.textContent = alert.message || "Active planetary reversal window";
    } else {
      riskBadge.innerHTML = `<span class="dir-badge dir-safe">✓ LOW / STABLE</span>`;
      if (riskSub) riskSub.textContent = "No severe planetary crash clusters active";
    }
  }

  // 3. Next Reversal Window
  if (reversalBadge) {
    const watchDays = (d.market_alert && d.market_alert.watch_days) || [];
    const nextWatch = watchDays.find(w => !w.today && w.windows && w.windows.length > 0);
    if (nextWatch) {
      reversalBadge.innerHTML = `<span class="reversal-date">${nextWatch.date} (+${nextWatch.offset}d)</span>`;
      if (reversalSub) reversalSub.textContent = `${nextWatch.windows.length} reversal alert(s) on ${nextWatch.date}`;
    } else {
      reversalBadge.innerHTML = `<span class="reversal-date">Within 7-10 Days</span>`;
      if (reversalSub) reversalSub.textContent = "Monitor weekly confluence synthesis";
    }
  }

  // 4. Sector Leaders & Outperformers
  if (leadersBox) {
    leadersBox.innerHTML = "";
    const list = d.planet_sectors || [];
    const favored = list.filter(s => s.read === "FAVOR").flatMap(s => s.sectors).slice(0, 2);
    const pressured = list.filter(s => s.read === "AVOID").flatMap(s => s.sectors).slice(0, 2);
    
    if (favored.length > 0) {
      for (const fav of favored) {
        const tag = document.createElement("span");
        tag.className = "leader-tag bull";
        tag.textContent = `${fav} ▲`;
        leadersBox.appendChild(tag);
      }
    } else {
      const tag = document.createElement("span");
      tag.className = "leader-tag bull";
      tag.textContent = "IT / Tech ▲";
      leadersBox.appendChild(tag);
    }
    
    if (pressured.length > 0) {
      for (const pr of pressured) {
        const tag = document.createElement("span");
        tag.className = "leader-tag bear";
        tag.textContent = `${pr} ▼`;
        leadersBox.appendChild(tag);
      }
    } else {
      const tag = document.createElement("span");
      tag.className = "leader-tag bear";
      tag.textContent = "Energy / Metal ▼";
      leadersBox.appendChild(tag);
    }
  }
}

function renderVerdict(d) {
  const s = d.sentiment;
  const chip = $("chip");
  chip.className = "verdict-chip " + (s.verdict === "BULLISH" ? "chip-bull" :
    s.verdict === "BEARISH" ? "chip-bear" : "chip-flat");
  chip.textContent = `${s.verdict} .  ${s.strength}`;
  $("meta").textContent =
    `${d.anchor.name} .  ${d.date} ${d.time} ${d.timezone} .  Lahiri ayanamsa ${d.ayanamsa} deg`;

  const tot = d.score.benefic + d.score.malefic;
  const bPct = tot ? (d.score.benefic / tot) * 100 : 0;
  const mPct = tot ? (d.score.malefic / tot) * 100 : 0;
  $("g-b").style.width = bPct + "%";
  $("g-m").style.width = mPct + "%";
  $("g-bn").textContent = d.score.benefic.toFixed(1);
  $("g-mn").textContent = d.score.malefic.toFixed(1);
  $("g-net").textContent = (d.net >= 0 ? "+" : "") + d.net.toFixed(1);
  $("verdict").classList.remove("hidden");
}

function renderMarketAlert(d) {
  const box = $("market-alert");
  const alert = d.market_alert;
  const totalAlerts = alert.total_alerts !== undefined ? alert.total_alerts :
    alert.windows.length + alert.upcoming_windows.length +
    (alert.transits || []).length + (alert.lunar_phase ? 1 : 0) +
    (alert.jupiter_analysis && alert.jupiter_analysis.active ? 1 : 0);
  box.className = "market-alert " + (alert.active ? "alert-active" : "alert-clear");

  const countEl = $("alert-count");
  countEl.textContent = alert.active ?
    `${totalAlerts} matching alert${totalAlerts === 1 ? "" : "s"}` :
    "No active window";

  // Add tooltip with details for active windows
  if (alert.active && alert.windows.length > 0) {
    const details = alert.windows.map(w =>
      `${w.title} | ${w.level} | ${w.bias}${w.detail ? " | " + w.detail : ""}${w.sectors && w.sectors.length ? " | Sectors: " + w.sectors.join(", ") : ""}`
    ).join("\n\n");
    countEl.title = details;
    countEl.style.cursor = "help";
    countEl.setAttribute("data-tooltip", details);
  } else {
    countEl.removeAttribute("title");
    countEl.style.cursor = "default";
    countEl.removeAttribute("data-tooltip");
  }

  $("alert-message").textContent = alert.message;

  const timeline = $("alert-timeline");
  timeline.innerHTML = "";
  const yogaByDate = {};
  for (const yoga of d.yoga_alerts || []) yogaByDate[yoga.date] = yoga.glyphs;

  // Group watch days by month for 3-month view
  const today = new Date();
  for (const day of alert.watch_days || []) {
    if (day.windows.length === 0) continue; // Only show days with alerts

    const card = document.createElement("article");
    card.className = "watch-day" + (day.today ? " watch-today" : "");
    card.style.cursor = "pointer";

    const label = document.createElement("span");
    label.className = "watch-label";
    label.textContent = day.today ? "TODAY" : `+${day.offset} DAY${day.offset === 1 ? "" : "S"}`;
    card.appendChild(label);

    const dateEl = document.createElement("strong");
    dateEl.textContent = day.date;
    card.appendChild(dateEl);

    const signal = document.createElement("span");
    signal.className = "watch-signal";
    signal.textContent = `${day.windows.length} reversal alert${day.windows.length === 1 ? "" : "s"}`;
    card.appendChild(signal);

    if (yogaByDate[day.date]) {
      const glyphs = document.createElement("b");
      glyphs.className = "watch-glyphs";
      glyphs.textContent = yogaByDate[day.date];
      glyphs.title = "Panchanga yoga glyphs";
      card.appendChild(glyphs);
    }

    // Add tooltip with all window details for this day
    if (day.windows.length > 0) {
      const dayDetails = day.windows.map(w =>
        `${w.title}\nLevel: ${w.level} | Bias: ${w.bias}\n${w.detail || ""}\nSectors: ${w.sectors.join(", ") || "N/A"}`
      ).join("\n\n---\n\n");
      card.title = dayDetails;
      card.setAttribute("data-tooltip", dayDetails);
    }

    // Click to show details in alert-windows panel
    card.addEventListener("click", () => {
      showDayDetails(day);
    });

    timeline.appendChild(card);
  }

  // If no alert days in 3-month window, show a message
  if (timeline.children.length === 0) {
    const empty = document.createElement("div");
    empty.className = "watch-empty";
    empty.textContent = "No reversal alerts in the next 3 months.";
    timeline.appendChild(empty);
  }
}

function showDayDetails(day) {
  const windows = $("alert-windows");
  windows.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = day.today ? `Today (${day.date}) - Reversal Alerts` : `${day.date} (+${day.offset} days) - Reversal Alerts`;
  windows.appendChild(title);

  for (const w of day.windows) {
    const item = document.createElement("article");
    item.className = "alert-window detail-window";

    const wTitle = document.createElement("h4");
    wTitle.textContent = w.title;
    item.appendChild(wTitle);

    const meta = document.createElement("div");
    meta.className = "alert-meta";
    meta.textContent = `${w.start} to ${w.end} .  ${w.level}`;
    item.appendChild(meta);

    const bias = document.createElement("strong");
    bias.className = w.bias.includes("BULLISH") ? "alert-bull" :
      w.bias.includes("BEARISH") ? "alert-bear" : "alert-neutral";
    bias.textContent = w.bias;
    item.appendChild(bias);

    if (w.detail) {
      const detail = document.createElement("p");
      detail.className = "alert-detail";
      detail.textContent = w.detail;
      item.appendChild(detail);
    }

    if (w.sectors && w.sectors.length) {
      const sectors = document.createElement("p");
      sectors.textContent = "Sectors: " + w.sectors.join(", ");
      item.appendChild(sectors);
    }
    windows.appendChild(item);
  }

  // Scroll to alert-windows
  windows.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderYogaAlerts(d) {
  const box = $("yoga-alerts");
  box.innerHTML = "";
  if (!d.yoga_alerts.length) {
    const empty = document.createElement("p");
    empty.className = "yoga-empty";
    empty.textContent = "No yoga or muhurta events in the next 7 days.";
    box.appendChild(empty);
    return;
  }
  for (const alert of d.yoga_alerts) {
    const item = document.createElement("article");
    item.className = "yoga-item";
    const type = document.createElement("strong");
    type.textContent = `${alert.glyph || ""} ${alert.type}`.trim();
    item.appendChild(type);
    const date = document.createElement("span");
    date.className = "yoga-date";
    date.textContent = alert.date;
    item.appendChild(date);
    const basis = document.createElement("small");
    basis.textContent = alert.basis;
    item.appendChild(basis);
    const details = document.createElement("p");
    details.textContent = alert.details;
    item.appendChild(details);
    box.appendChild(item);
  }
}

function renderFuturecast(data) {
  const timeline = data.timeline_windows || data.windows;
  $("futurecast-summary").textContent = `${data.range_start} to ${data.range_end} .  ${timeline.length} timeline window${timeline.length === 1 ? "" : "s"}`;
  $("futurecast-note").textContent = `${data.method} ${data.disclaimer}`;
  const box = $("futurecast-results");
  box.className = "backtest-results";
  box.innerHTML = "";
  let focusIndex = -1;
  for (let i = 0; i < timeline.length; i++) {
    const window = timeline[i];
    const row = document.createElement("article");
    row.className = `backtest-row ${window.timeline || ""} ` +
      (window.level === "EXTREME" ? "miss" : "match");
    row.dataset.index = i;
    const head = document.createElement("div");
    head.className = "backtest-head";
    const date = document.createElement("strong");
    date.textContent = `${window.start} to ${window.end}`;
    head.appendChild(date);
    const label = document.createElement("b");
    label.textContent = `${window.level} .  score ${window.peak_score}`;
    head.appendChild(label);
    row.appendChild(head);
    const reasons = document.createElement("p");
    reasons.textContent = window.reasons.join("; ");
    row.appendChild(reasons);
    box.appendChild(row);

    if (window.timeline === "current" || (focusIndex < 0 && window.timeline === "upcoming")) {
      focusIndex = i;
    }
  }
  if (focusIndex < 0 && timeline.length > 0) focusIndex = timeline.length - 1;

  // Center the most recent/current window in view
  requestAnimationFrame(() => {
    const cards = box.querySelectorAll(".backtest-row");
    const target = cards[focusIndex];
    if (!target) return;
    const maxScroll = box.scrollWidth - box.clientWidth;
    if (maxScroll > 0) {
      const offset = target.offsetLeft - (box.clientWidth - target.offsetWidth) / 2;
      box.scrollTo({ left: Math.max(0, Math.min(offset, maxScroll)), behavior: "smooth" });
    }
    target.style.boxShadow = "0 0 0 3px rgba(248,113,113,.35), 0 8px 24px rgba(0,0,0,.35)";
    setTimeout(() => { target.style.boxShadow = ""; }, 2000);
  });
}

function renderBullishFuturecast(data) {
  const summary = $("bullish-summary");
  summary.textContent = `${data.scan_window.start} to ${data.scan_window.end} .  ${data.clusters.length} bull clusters`;
  $("bullish-note").textContent = `${data.version} ${data.disclaimer}`;

  const timeline = $("bullish-timeline");
  const centerMarker = $("bullish-center-marker");
  timeline.className = "bullish-timeline";
  timeline.innerHTML = "";

  if (!data.clusters || data.clusters.length === 0) {
    timeline.innerHTML = '<div class="bullish-cluster" style="flex:0 0 100%;text-align:center;color:var(--muted);padding:40px;">No bullish clusters found in this window</div>';
    centerMarker.style.display = "none";
    return;
  }

  const centerDate = new Date(data.center_date);
  const scanStart = new Date(data.scan_window.start);
  const scanEnd = new Date(data.scan_window.end);
  const totalDays = (scanEnd - scanStart) / (1000 * 60 * 60 * 24);

  let centerClusterIndex = -1;
  let minDistance = Infinity;

  for (let i = 0; i < data.clusters.length; i++) {
    const cluster = data.clusters[i];
    const clusterStart = new Date(cluster.start);
    const clusterEnd = new Date(cluster.end);
    const clusterMid = new Date((clusterStart.getTime() + clusterEnd.getTime()) / 2);

    const card = document.createElement("article");
    card.className = `bullish-cluster ${cluster.level.toLowerCase()} ${cluster.timeline}`;
    card.setAttribute("role", "listitem");
    card.dataset.start = cluster.start;
    card.dataset.end = cluster.end;
    card.dataset.score = cluster.score;
    card.dataset.timeline = cluster.timeline;

    const durationDays = Math.max(1, Math.round((clusterEnd - clusterStart) / (1000 * 60 * 60 * 24)) + 1);

    // Header
    const header = document.createElement("div");
    header.className = "cluster-header";

    const dateEl = document.createElement("span");
    dateEl.className = "cluster-date";
    // Format: Jun 5 – Aug 4, 2026
    const fmt = (d) => {
      const dt = new Date(d);
      return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };
    const startDt = new Date(cluster.start);
    const endDt = new Date(cluster.end);
    const sameYear = startDt.getFullYear() === endDt.getFullYear();
    const yearStr = sameYear ? `, ${startDt.getFullYear()}` : '';
    dateEl.textContent = `${fmt(cluster.start)} – ${fmt(cluster.end)}${yearStr}`;
    dateEl.title = `${cluster.start} to ${cluster.end}`;
    header.appendChild(dateEl);

    const scoreEl = document.createElement("span");
    scoreEl.className = "cluster-score";
    scoreEl.textContent = `${cluster.level} .  ${cluster.score}`;
    header.appendChild(scoreEl);

    const timelineEl = document.createElement("span");
    timelineEl.className = "cluster-timeline";
    timelineEl.textContent = cluster.timeline;
    header.appendChild(timelineEl);

    card.appendChild(header);

    // Triggers
    const triggersWrap = document.createElement("div");
    triggersWrap.className = "cluster-triggers";
    const triggersToShow = cluster.triggers.slice(0, 6);
    for (const trigger of triggersToShow) {
      const tag = document.createElement("span");
      tag.className = "trigger-tag";
      tag.textContent = trigger;
      triggersWrap.appendChild(tag);
    }
    if (cluster.triggers.length > 6) {
      const more = document.createElement("span");
      more.className = "trigger-more";
      more.textContent = `+${cluster.triggers.length - 6} more`;
      triggersWrap.appendChild(more);
    }
    card.appendChild(triggersWrap);

    // Duration footer
    const footer = document.createElement("div");
    footer.className = "cluster-duration";
    footer.innerHTML = `<span class="days">${durationDays}d</span> window`;
    card.appendChild(footer);

    timeline.appendChild(card);

    // Find cluster nearest to center date
    const distance = Math.abs(clusterMid - centerDate);
    if (distance < minDistance) {
      minDistance = distance;
      centerClusterIndex = i;
    }
  }

  // Scroll to center cluster (or nearest upcoming if center is in past)
  requestAnimationFrame(() => {
    const cards = timeline.querySelectorAll(".bullish-cluster");
    if (centerClusterIndex >= 0 && cards[centerClusterIndex]) {
      const targetCard = cards[centerClusterIndex];
      targetCard.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
      // Add a highlight pulse
      targetCard.style.boxShadow = "0 0 0 3px rgba(52,211,153,.4), 0 8px 24px rgba(0,0,0,.35)";
      setTimeout(() => {
        targetCard.style.boxShadow = "";
      }, 2000);
    }
    // Position center marker at center date proportion
    const centerRatio = Math.max(0, Math.min(1, (centerDate - scanStart) / (scanEnd - scanStart)));
    const timelineWidth = timeline.scrollWidth;
    const viewportWidth = timeline.clientWidth;
    const maxScroll = timelineWidth - viewportWidth;
    if (maxScroll > 0) {
      centerMarker.style.left = `${centerRatio * 100}%`;
    }
    centerMarker.style.display = "flex";
  });

  // Keep old results hidden for backward compat
  const box = $("bullish-results");
  box.innerHTML = "";
  box.classList.add("hidden");
}

async function loadBullishFuturecast(date) {
  const timeline = $("bullish-timeline");
  if (timeline) {
    timeline.textContent = "Loading bullish futurecast windows...";
    timeline.className = "bullish-timeline panel-loading";
  }
  try {
    const response = await fetchWithTimeout("/api/bullish_futurecast?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderBullishFuturecast(data);
  } catch (e) {
    console.error("Bullish futurecast failed:", e);
    if (timeline) {
      timeline.textContent = "Bullish futurecast is unavailable. Try running the prediction again.";
      timeline.className = "bullish-timeline panel-error";
    }
    $("bullish-center-marker").style.display = "none";
  }
}

async function loadFuturecast(date) {
  const results = $("futurecast-results");
  if (results) {
    results.textContent = "Loading crash risk windows...";
    results.className = "backtest-results panel-loading";
  }
  try {
    const response = await fetchWithTimeout("/api/futurecast?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderFuturecast(data);
  } catch (e) {
    console.error("Crash futurecast failed:", e);
    if (results) {
      results.textContent = "Crash futurecast is unavailable. Try running the prediction again.";
      results.className = "backtest-results panel-error";
    }
  }
  await loadBullishFuturecast(date);
}

function sectorGroupClass(group) {
  const g = (group || "").toLowerCase();
  if (g.includes("strong bull")) return "sv-strong";
  if (g.includes("reversal") || g.includes("spike")) return "sv-reversal";
  if (g.includes("dip")) return "sv-dip";
  if (g.includes("bear")) return "sv-bear";
  return "sv-weak";
}

function renderSectorVedha(data) {
  const grid = $("sector-vedha-active");
  if (!grid) return;
  if ($("sector-vedha-sub")) {
    $("sector-vedha-sub").textContent =
      `${data.date} .  ${data.signals.length} active signal${data.signals.length === 1 ? "" : "s"} .  backtested 2021-26`;
  }
  if ($("sector-vedha-note")) $("sector-vedha-note").textContent = data.disclaimer;
  grid.innerHTML = "";
  if (!data.signals.length) {
    grid.innerHTML = '<div class="sv-empty">No scenario vedhas active today — check upcoming firings below.</div>';
  }
  for (const sig of data.signals) {
    const cls = sectorGroupClass(sig.group);
    const card = document.createElement("article");
    card.className = `sector-signal ${cls}`;

    const head = document.createElement("div");
    head.className = "sv-head";
    const pairEl = document.createElement("span");
    pairEl.className = "sv-pair";
    pairEl.textContent = sig.pair;
    head.appendChild(pairEl);
    const badge = document.createElement("span");
    badge.className = `sv-badge ${cls}`;
    badge.textContent = sig.group;
    head.appendChild(badge);
    card.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "sv-meta";
    meta.textContent = `${sig.sector}${sig.instruments.length ? " .  " + sig.instruments.join(", ") : ""}`;
    card.appendChild(meta);

    if (sig.span_start && sig.span_end) {
      const spanEl = document.createElement("div");
      spanEl.className = "sv-span";
      spanEl.innerHTML = `<span class="sv-span-icon">⏳</span> Window: <b>${sig.span_start} → ${sig.span_end}</b>` +
        ` (${sig.span_days}d${sig.span_day ? `, day ${sig.span_day}` : ""})`;
      card.appendChild(spanEl);
    }

    for (const f of sig.findings) {
      const stat = document.createElement("div");
      stat.className = "sv-stat" + (f.avg < 0 ? " sv-neg" : "");
      stat.innerHTML = `<b>${f.target}</b> ${f.h}d: <span>${f.avg > 0 ? "+" : ""}${f.avg.toFixed(2)}%</span>` +
        ` avg .  win ${f.win.toFixed(1)}% .  n=${f.n}`;
      card.appendChild(stat);
    }

    const note = document.createElement("p");
    note.className = "sv-note";
    note.textContent = sig.note;
    card.appendChild(note);

    grid.appendChild(card);
  }

  const upList = $("sector-vedha-upcoming");
  if (!upList) return;
  upList.innerHTML = "";
  if (!data.upcoming.length) {
    upList.innerHTML = '<div class="sv-empty">No scenario pairs fire in the next ' +
      Math.round((new Date(data.scan_end) - new Date(data.date)) / 864e5) + ' days.</div>';
  } else {
    for (const u of data.upcoming) {
      const row = document.createElement("div");
      row.className = "sv-upcoming-row";
      const dateEl = document.createElement("span");
      dateEl.className = "sv-upcoming-date";
      dateEl.textContent = `${u.start} → ${u.end}`;
      dateEl.title = `starts in ${u.days_ahead}d .  ${u.window_days}d window`;
      row.appendChild(dateEl);
      const chip = document.createElement("span");
      chip.className = `sv-chip ${sectorGroupClass(u.group)}`;
      chip.textContent = `${u.pair} (${u.sector})`;
      chip.title = u.group;
      row.appendChild(chip);
      const durEl = document.createElement("span");
      durEl.className = "sv-upcoming-dur";
      durEl.textContent = `${u.window_days}d`;
      row.appendChild(durEl);
      upList.appendChild(row);
    }
  }
}

async function loadSectorVedha(date) {
  if (!$("sector-vedha-active")) return;
  try {
    const response = await fetchWithTimeout("/api/sector_vedha?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderSectorVedha(data);
  } catch (e) {
    console.error("Sector vedha failed:", e);
    if ($("sector-vedha-active")) {
      $("sector-vedha-active").textContent = "Sector Vedha radar is unavailable. Try again.";
    }
  }
}

function renderLargecapDivergence(data) {
  const content = $("largecap-divergence-content");
  if (!content) return;
  content.innerHTML = "";

  const summary = document.createElement("div");
  summary.className = "lcd-summary";
  summary.innerHTML = `<strong>${data.summary}</strong> .  ${data.date}`;
  content.appendChild(summary);

  if (data.active_count === 0) {
    const none = document.createElement("div");
    none.className = "lcd-empty";
    none.textContent = "No divergence configurations active today.";
    content.appendChild(none);
    return;
  }

  const highConfigs = data.configs.filter(c => c.active && c.conviction === "HIGH");
  if (highConfigs.length > 0) {
    const highSection = document.createElement("div");
    highSection.className = "lcd-section high";
    highSection.innerHTML = "<h4>⚡ HIGH CONVICTION</h4>";
    for (const c of highConfigs) {
      const card = document.createElement("div");
      card.className = "lcd-card high";
      card.innerHTML = `<strong>${c.name}</strong><br><span class="lcd-summary-text">${c.summary}</span>`;
      highSection.appendChild(card);
    }
    content.appendChild(highSection);
  }

  const medConfigs = data.configs.filter(c => c.active && c.conviction === "MEDIUM");
  if (medConfigs.length > 0) {
    const medSection = document.createElement("div");
    medSection.className = "lcd-section medium";
    medSection.innerHTML = "<h4>📊 MEDIUM CONVICTION</h4>";
    for (const c of medConfigs) {
      const card = document.createElement("div");
      card.className = "lcd-card medium";
      card.innerHTML = `<strong>${c.name}</strong><br><span class="lcd-summary-text">${c.summary}</span>`;
      medSection.appendChild(card);
    }
    content.appendChild(medSection);
  }

  const lowConfigs = data.configs.filter(c => c.active && c.conviction === "LOW");
  if (lowConfigs.length > 0) {
    const lowSection = document.createElement("div");
    lowSection.className = "lcd-section low";
    lowSection.innerHTML = `<h4>⚪ LOW CONVICTION (${lowConfigs.length}) <span class="lcd-toggle">▼</span></h4>`;
    const lowList = document.createElement("div");
    lowList.className = "lcd-low-list";
    for (const c of lowConfigs) {
      const card = document.createElement("div");
      card.className = "lcd-card low";
      card.innerHTML = `<strong>${c.name}</strong><br><span class="lcd-summary-text">${c.summary}</span>`;
      lowList.appendChild(card);
    }
    lowSection.appendChild(lowList);
    const toggle = lowSection.querySelector(".lcd-toggle");
    if (toggle) {
      toggle.addEventListener("click", (e) => {
        lowList.style.display = lowList.style.display === "none" ? "block" : "none";
        e.target.textContent = lowList.style.display === "none" ? "▶" : "▼";
      });
    }
    content.appendChild(lowSection);
  }

  if ($("largecap-divergence")) $("largecap-divergence").classList.remove("hidden");
}

async function loadLargecapDivergence(date) {
  if (!$("largecap-divergence-content")) return;
  try {
    const response = await fetchWithTimeout("/api/largecap_divergence?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderLargecapDivergence(data);
  } catch (e) {
    console.error("Large-cap divergence failed:", e);
    if ($("largecap-divergence-content")) {
      $("largecap-divergence-content").textContent = "Large-cap divergence is unavailable. Try again.";
    }
    if ($("largecap-divergence")) $("largecap-divergence").classList.remove("hidden");
  }
}

function renderFmcgSignals(data) {
  const content = $("fmcg-signals-content");
  if (!content) return;
  content.innerHTML = "";

  const summary = document.createElement("div");
  summary.className = "fmcg-summary";
  summary.innerHTML = `<strong>${data.summary}</strong>`;
  content.appendChild(summary);

  if (!data.is_bullish && !data.active_signals.length) {
    const none = document.createElement("div");
    none.className = "fmcg-empty";
    none.textContent = "No FMCG bullish planetary syntax active today.";
    content.appendChild(none);
    return;
  }

  // Conviction badge
  const badge = document.createElement("div");
  badge.className = "fmcg-badge " + data.conviction.toLowerCase();
  badge.textContent = data.conviction + (data.is_strong_bullish ? " .  STRONG" : data.is_bullish ? " .  BULLISH" : " .  WATCH");
  content.appendChild(badge);

  // Active signals
  if (data.active_signals.length > 0) {
    const signalsSection = document.createElement("div");
    signalsSection.className = "fmcg-section";
    signalsSection.innerHTML = "<h4>Active Signals</h4>";
    for (const s of data.active_signals) {
      const card = document.createElement("div");
      card.className = "fmcg-card";
      card.textContent = s;
      signalsSection.appendChild(card);
    }
    content.appendChild(signalsSection);
  }

  // Price levels
  if (data.price_levels) {
    const pl = data.price_levels;
    const priceSection = document.createElement("div");
    priceSection.className = "fmcg-section";
    priceSection.innerHTML = `<h4>Price Levels (HUL)</h4>
      <div class="fmcg-price-row"><strong>Current:</strong> ${pl.current_price}</div>
      <div class="fmcg-price-row"><strong>Target:</strong> ${pl.target_high}</div>
      <div class="fmcg-price-row"><strong>Support:</strong> ${pl.support_zone}</div>
      <div class="fmcg-price-row"><strong>Stop Loss:</strong> ${pl.stop_loss}</div>
      <div class="fmcg-method">${pl.method}</div>`;
    content.appendChild(priceSection);
  }

  // Details (collapsible)
  if (data.details) {
    const detailSection = document.createElement("div");
    detailSection.className = "fmcg-section";
    detailSection.innerHTML = `<h4>Details <span class="fmcg-toggle">▼</span></h4>`;
    const detailList = document.createElement("div");
    detailList.className = "fmcg-detail-list";
    for (const [key, val] of Object.entries(data.details)) {
      if (typeof val === 'boolean' && val) {
        const card = document.createElement("div");
        card.className = "fmcg-card";
        card.textContent = key;
        detailList.appendChild(card);
      }
    }
    detailSection.appendChild(detailList);
    const toggle = detailSection.querySelector(".fmcg-toggle");
    if (toggle) {
      toggle.addEventListener("click", (e) => {
        detailList.style.display = detailList.style.display === "none" ? "block" : "none";
        e.target.textContent = detailList.style.display === "none" ? "▶" : "▼";
      });
    }
    content.appendChild(detailSection);
  }

  if ($("fmcg-signals")) $("fmcg-signals").classList.remove("hidden");
}

async function loadFmcgSignals(date, price) {
  if (!$("fmcg-signals-content")) return;
  try {
    let url = "/api/fmcg_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderFmcgSignals(data);
  } catch (e) {
    console.error("FMCG signals failed:", e);
    if ($("fmcg-signals-content")) {
      $("fmcg-signals-content").textContent = "FMCG signals are unavailable. Try again.";
    }
    if ($("fmcg-signals")) $("fmcg-signals").classList.remove("hidden");
  }
}




function renderTourismSignals(data) {
  const content = $("tourism-signals-content");
  if (!content) return;
  content.innerHTML = "";

  const summary = document.createElement("div");
  summary.className = "tourism-summary";
  summary.innerHTML = `<strong>${data.summary}</strong>`;
  content.appendChild(summary);

  if (!data.is_bullish && !data.active_signals.length) {
    const none = document.createElement("div");
    none.className = "tourism-empty";
    none.textContent = "No tourism/leisure bullish syntax active today.";
    content.appendChild(none);
    return;
  }

  const badge = document.createElement("div");
  badge.className = "tourism-badge " + data.conviction.toLowerCase();
  badge.textContent = data.conviction + (data.is_strong_bullish ? " \u00b7 STRONG" : data.is_bullish ? " \u00b7 BULLISH" : " \u00b7 WATCH");
  content.appendChild(badge);

  // Core signals (backtested)
  const coreSignals = data.active_signals.filter(s => 
    s.includes("MOON_STRONG") || s.includes("VENUS_STRONG") || s.includes("JUPITER-VENUS") || 
    s.includes("MOON-VENUS") || s.includes("MOON-JUPITER")
  );
  
  // Supporting signals
  const supportSignals = data.active_signals.filter(s => 
    s.includes("MERCURY TOURISM") || s.includes("VENUS_IDEAL") || s.includes("JUPITER_TOURISM_IDEAL")
  );
  
  // SBC/Structural signals
  const sbcSignals = data.active_signals.filter(s => s.includes("SBC"));
  
  // Other signals
  const otherSignals = data.active_signals.filter(s => 
    !coreSignals.includes(s) && !supportSignals.includes(s) && !sbcSignals.includes(s)
  );

  if (coreSignals.length > 0) {
    const coreSection = document.createElement("div");
    coreSection.className = "tourism-section";
    coreSection.innerHTML = "<h4>Core Signals (Backtested)</h4>";
    for (const s of coreSignals) {
      const card = document.createElement("div");
      card.className = "tourism-card core";
      card.textContent = s;
      coreSection.appendChild(card);
    }
    content.appendChild(coreSection);
  }

  if (supportSignals.length > 0) {
    const supSection = document.createElement("div");
    supSection.className = "tourism-section";
    supSection.innerHTML = "<h4>Supporting Signals</h4>";
    for (const s of supportSignals) {
      const card = document.createElement("div");
      card.className = "tourism-card support";
      card.textContent = s;
      supSection.appendChild(card);
    }
    content.appendChild(supSection);
  }

  if (sbcSignals.length > 0) {
    const sbcSection = document.createElement("div");
    sbcSection.className = "tourism-section";
    sbcSection.innerHTML = "<h4>SBC Vedha</h4>";
    for (const s of sbcSignals) {
      const card = document.createElement("div");
      card.className = "tourism-card sbc";
      card.textContent = s;
      sbcSection.appendChild(card);
    }
    content.appendChild(sbcSection);
  }

  if (otherSignals.length > 0) {
    const otherSection = document.createElement("div");
    otherSection.className = "tourism-section";
    otherSection.innerHTML = "<h4>Other</h4>";
    for (const s of otherSignals) {
      const card = document.createElement("div");
      card.className = "tourism-card";
      card.textContent = s;
      otherSection.appendChild(card);
    }
    content.appendChild(otherSection);
  }

  if (data.price_levels) {
    const pl = data.price_levels;
    const priceSection = document.createElement("div");
    priceSection.className = "tourism-section";
    priceSection.innerHTML = `<h4>Price Levels</h4>
      <div class="tourism-price-row"><strong>Current:</strong> ${pl.current_price}</div>
      <div class="tourism-price-row"><strong>Target:</strong> ${pl.target_high}</div>
      <div class="tourism-price-row"><strong>Support:</strong> ${pl.support_zone}</div>
      <div class="tourism-price-row"><strong>Stop Loss:</strong> ${pl.stop_loss}</div>
      <div class="tourism-method">${pl.method}</div>`;
    content.appendChild(priceSection);
  }

  // Remove verbose Details section - keep it simple

  if ($("tourism-signals")) $("tourism-signals").classList.remove("hidden");
}

async function loadTourismSignals(date, price) {
  if (!$("tourism-signals-content")) return;
  try {
    let url = "/api/tourism_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderTourismSignals(data);
  } catch (e) {
    console.error("Tourism signals failed:", e);
    if ($("tourism-signals-content")) {
      $("tourism-signals-content").textContent = "Tourism signals are unavailable. Try again.";
    }
    if ($("tourism-signals")) $("tourism-signals").classList.remove("hidden");
  }
}


function renderChemicalSignals(data) {
  const content = $("chemical-signals-content");
  if (!content) return;
  content.innerHTML = "";

  const summary = document.createElement("div");
  summary.className = "chemical-summary";
  summary.innerHTML = `<strong>${data.summary}</strong>`;
  content.appendChild(summary);

  if (!data.is_bullish && !data.active_signals.length) {
    const none = document.createElement("div");
    none.className = "chemical-empty";
    none.textContent = "No chemical sector bullish syntax active today.";
    content.appendChild(none);
    return;
  }

  // Conviction badge
  const badge = document.createElement("div");
  badge.className = "chemical-badge " + data.conviction.toLowerCase();
  badge.textContent = data.conviction + (data.is_strong_bullish ? " .  STRONG" : data.is_bullish ? " .  BULLISH" : " .  WATCH");
  content.appendChild(badge);

  // Active signals
  if (data.active_signals.length > 0) {
    const signalsSection = document.createElement("div");
    signalsSection.className = "chemical-section";
    signalsSection.innerHTML = "<h4>Active Signals</h4>";
    for (const s of data.active_signals) {
      const card = document.createElement("div");
      card.className = "chemical-card";
      card.textContent = s;
      signalsSection.appendChild(card);
    }
    content.appendChild(signalsSection);
  }

  // Price levels
  if (data.price_levels) {
    const pl = data.price_levels;
    const priceSection = document.createElement("div");
    priceSection.className = "chemical-section";
    priceSection.innerHTML = `<h4>Price Levels</h4>
      <div class="chemical-price-row"><strong>Current:</strong> ${pl.current_price}</div>
      <div class="chemical-price-row"><strong>Target:</strong> ${pl.target_high}</div>
      <div class="chemical-price-row"><strong>Support:</strong> ${pl.support_zone}</div>
      <div class="chemical-price-row"><strong>Stop Loss:</strong> ${pl.stop_loss}</div>
      <div class="chemical-method">${pl.method}</div>`;
    content.appendChild(priceSection);
  }

// Details (collapsible)
  if (data.details) {
    const detailSection = document.createElement("div");
    detailSection.className = "chemical-section";
    detailSection.innerHTML = `<h4>Details <span class="chemical-toggle">▼</span></h4>`;
    const detailList = document.createElement("div");
    detailList.className = "chemical-detail-list";
    for (const [key, val] of Object.entries(data.details)) {
      if (typeof val === 'boolean' && val) {
        const card = document.createElement("div");
        card.className = "chemical-card";
        card.textContent = key;
        detailList.appendChild(card);
      }
    }
    detailSection.appendChild(detailList);
    const toggle = detailSection.querySelector(".chemical-toggle");
    if (toggle) {
      toggle.addEventListener("click", (e) => {
        detailList.style.display = detailList.style.display === "none" ? "block" : "none";
        e.target.textContent = detailList.style.display === "none" ? "▶" : "▼";
      });
    }
    content.appendChild(detailSection);
  }

  if ($("chemical-signals")) $("chemical-signals").classList.remove("hidden");
}

async function loadChemicalSignals(date, price) {
  if (!$("chemical-signals-content")) return;
  try {
    let url = "/api/chemical_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderChemicalSignals(data);
  } catch (e) {
    console.error("Chemical signals failed:", e);
    if ($("chemical-signals-content")) {
      $("chemical-signals-content").textContent = "Chemical signals are unavailable. Try again.";
    }
    if ($("chemical-signals")) $("chemical-signals").classList.remove("hidden");
  }
}


function renderAlcoholSignals(data) {
  const content = $("alcohol-signals-content");
  if (!content) return;
  content.innerHTML = "";

  const summary = document.createElement("div");
  summary.className = "alcohol-summary";
  summary.innerHTML = `<strong>${data.summary}</strong>`;
  content.appendChild(summary);

  if (!data.is_bullish && !data.active_signals.length) {
    const none = document.createElement("div");
    none.className = "alcohol-empty";
    none.textContent = "No alcohol sector bullish syntax active today.";
    content.appendChild(none);
    return;
  }

  // Conviction badge
  const badge = document.createElement("div");
  badge.className = "alcohol-badge " + data.conviction.toLowerCase();
  badge.textContent = data.conviction + (data.is_strong_bullish ? " .  STRONG" : data.is_bullish ? " .  BULLISH" : " .  WATCH");
  content.appendChild(badge);

  // Active signals
  if (data.active_signals.length > 0) {
    const signalsSection = document.createElement("div");
    signalsSection.className = "alcohol-section";
    signalsSection.innerHTML = "<h4>Active Signals</h4>";
    for (const s of data.active_signals) {
      const card = document.createElement("div");
      card.className = "alcohol-card";
      card.textContent = s;
      signalsSection.appendChild(card);
    }
    content.appendChild(signalsSection);
  }

  // Price levels
  if (data.price_levels) {
    const pl = data.price_levels;
    const priceSection = document.createElement("div");
    priceSection.className = "alcohol-section";
    priceSection.innerHTML = `<h4>Price Levels</h4>
      <div class="alcohol-price-row"><strong>Current:</strong> ${pl.current_price}</div>
      <div class="alcohol-price-row"><strong>Target:</strong> ${pl.target_high}</div>
      <div class="alcohol-price-row"><strong>Support:</strong> ${pl.support_zone}</div>
      <div class="alcohol-price-row"><strong>Stop Loss:</strong> ${pl.stop_loss}</div>
      <div class="alcohol-method">${pl.method}</div>`;
    content.appendChild(priceSection);
  }

  // Details (collapsible)
  if (data.details) {
    const detailSection = document.createElement("div");
    detailSection.className = "alcohol-section";
    detailSection.innerHTML = `<h4>Details <span class="alcohol-toggle">▼</span></h4>`;
    const detailList = document.createElement("div");
    detailList.className = "alcohol-detail-list";
    for (const [key, val] of Object.entries(data.details)) {
      if (typeof val === 'boolean' && val) {
        const card = document.createElement("div");
        card.className = "alcohol-card";
        card.textContent = key;
        detailList.appendChild(card);
      }
    }
    detailSection.appendChild(detailList);
    const toggle = detailSection.querySelector(".alcohol-toggle");
    if (toggle) {
      toggle.addEventListener("click", (e) => {
        detailList.style.display = detailList.style.display === "none" ? "block" : "none";
        e.target.textContent = detailList.style.display === "none" ? "▶" : "▼";
      });
    }
    content.appendChild(detailSection);
  }

  if ($("alcohol-signals")) $("alcohol-signals").classList.remove("hidden");
}

async function loadAlcoholSignals(date, price) {
  if (!$("alcohol-signals-content")) return;
  try {
    let url = "/api/alcohol_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderAlcoholSignals(data);
  } catch (e) {
    console.error("Alcohol signals failed:", e);
    if ($("alcohol-signals-content")) {
      $("alcohol-signals-content").textContent = "Alcohol signals are unavailable. Try again.";
    }
    if ($("alcohol-signals")) $("alcohol-signals").classList.remove("hidden");
  }
}

function renderLunarForecast(data) {
  const content = $("lunar-forecast-content");
  content.className = "lunar-forecast-content";
  content.innerHTML = "";

  const forecast = data.forecast;
  const card = data.card;

  // Header with overall bias
  const header = document.createElement("div");
  header.className = "lf-header";
  const biasClass = forecast.overall_bias.toLowerCase().replace("_", "-");
  header.innerHTML = `
    <div class="lf-bias-badge ${biasClass}">${forecast.overall_bias}</div>
    <div class="lf-date">${data.card.date}</div>
    <div class="lf-lunar">${data.card.lunar_phase} | Tithi: ${data.card.tithi}</div>
  `;
  content.appendChild(header);

  // Lunar info bar
  const lunarBar = document.createElement("div");
  lunarBar.className = "lf-lunar-bar";
  lunarBar.innerHTML = `
    <span>🌙 Moon: <strong>${data.card.moon_nakshatra}</strong></span>
    <span>☀️ Sun: <strong>${data.card.sun_nakshatra}</strong></span>
    <span>📅 ${data.card.lunar_info.paksha} Paksha</span>
    <span>🌙 Moon Nature: <strong>${data.card.lunar_info.moon_nature}</strong></span>
  `;
  content.appendChild(lunarBar);

  // Overall bias score
  const scoreBar = document.createElement("div");
  scoreBar.className = "lf-score-bar";
  scoreBar.innerHTML = `
    <div class="lf-score-label">Overall Score: <strong>${data.card.avg_score}</strong></div>
    <div class="lf-score-visual">
      <div class="lf-score-fill ${forecast.overall_bias.toLowerCase().includes('bullish') ? 'bullish' : forecast.overall_bias.toLowerCase().includes('bearish') ? 'bearish' : 'neutral'}" 
           style="width: ${Math.min(100, Math.max(0, (forecast.avg_score + 10) * 5))}%"></div>
    </div>
  `;
  content.appendChild(scoreBar);

  // Sector forecasts table
  const tableSection = document.createElement("div");
  tableSection.className = "lf-table-section";
  tableSection.innerHTML = "<h4>Sector Forecasts</h4>";
  
  const table = document.createElement("table");
  table.className = "lf-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>Sector</th>
        <th>Score</th>
        <th>Bias</th>
        <th>Confluence</th>
        <th>SBC Net</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  
  const tbody = table.querySelector("tbody");
  for (const [sector, fc] of Object.entries(forecast.sector_forecasts)) {
    if (Math.abs(fc.score) < 0.1) continue; // Skip near-zero
    const row = document.createElement("tr");
    row.className = fc.bias.toLowerCase().includes("bullish") ? "bullish" : 
                   fc.bias.toLowerCase().includes("bearish") ? "bearish" : "neutral";
    // Themes (Growth, Consolidation, ...) score like sectors but are not
    // tradeable; label them so the table can't be misread as a sector call.
    const themeTag = fc.kind === "theme"
      ? ' <span class="lf-kind" title="Market theme, not a tradeable sector">theme</span>'
      : '';
    row.innerHTML = `
      <td><strong>${sector}</strong>${themeTag}</td>
      <td>${fc.score.toFixed(1)}</td>
      <td><span class="lf-bias ${fc.bias.toLowerCase().replace('_', '-')}">${fc.bias}</span></td>
      <td>${fc.confluence_score > 0 ? '+' + fc.confluence_score.toFixed(1) : fc.confluence_score.toFixed(1)}</td>
      <td>${fc.sbc_net > 0 ? '+' : ''}${fc.sbc_net.toFixed(1)}</td>
    `;
    tbody.appendChild(row);
  }
  tableSection.appendChild(table);
  content.appendChild(tableSection);

  // Key dates
  if (forecast.key_dates && forecast.key_dates.length > 0) {
    const datesSection = document.createElement("div");
    datesSection.className = "lf-dates-section";
    datesSection.innerHTML = "<h4>Key Lunar Dates</h4>";
    const datesList = document.createElement("ul");
    datesList.className = "lf-dates-list";
    for (const kd of forecast.key_dates) {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${kd.event}</strong> (${kd.impact}): ${kd.note}`;
      datesList.appendChild(li);
    }
    datesSection.appendChild(datesList);
    content.appendChild(datesSection);
  }

  // SBC Summary
  const sbcSection = document.createElement("div");
  sbcSection.className = "lf-sbc-section";
  sbcSection.innerHTML = `
    <h4>SBC Vedha Summary</h4>
    <div class="lf-sbc-grid">
      <div>Overall Bias: <strong>${forecast.sbc.overall_bias || 'NEUTRAL'}</strong></div>
      <div>Total Net: <strong>${forecast.sbc.total_net}</strong></div>
      <div>Bullish Rashis: <strong>${forecast.sbc.bullish_rashis}</strong></div>
      <div>Bearish Rashis: <strong>${forecast.sbc.bearish_rashis}</strong></div>
    </div>
  `;
  content.appendChild(sbcSection);

  // Action buttons
  const actionsSection = document.createElement("div");
  actionsSection.className = "lf-actions";
  actionsSection.innerHTML = `
    <button class="btn btn-secondary" onclick="copyLunarForecast()">📋 Copy to Clipboard</button>
    <button class="btn btn-secondary" onclick="shareLunarForecast()">📤 Share</button>
  `;
  content.appendChild(actionsSection);

  $("lunar-forecast").classList.remove("hidden");
}

async function loadLunarForecast(date) {
  const content = $("lunar-forecast-content");
  if (content) {
    content.textContent = "Loading lunar forecast...";
    content.className = "lunar-forecast-content panel-loading";
  }
  if ($("lunar-forecast")) $("lunar-forecast").classList.remove("hidden");
  try {
    const response = await fetchWithTimeout("/api/lunar_forecast?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderLunarForecast(data);
    // Store for clipboard/share
    window.currentLunarCard = data.card;
    window.currentLunarForecast = data.forecast;
    window.currentLunarClipboardText = data.clipboard_text;
    window.currentLunarSocialText = data.social_text;
  } catch (e) {
    console.error("Lunar forecast failed:", e);
    if (content) {
      content.textContent = "Lunar forecast is unavailable. Try running the prediction again.";
      content.className = "lunar-forecast-content panel-error";
    }
  }
}

function copyLunarForecast() {
  if (!window.currentLunarClipboardText) return;
  const text = window.currentLunarClipboardText;
  navigator.clipboard.writeText(text).then(() => {
    showToast("Copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy");
  });
}

function shareLunarForecast() {
  if (!window.currentLunarCard && !window.currentLunarSocialText) return;
  const text = window.currentLunarSocialText || "";
  if (navigator.share) {
    navigator.share({ title: "Lunar Cycle Sector Forecast", text: text });
  } else {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Copied for sharing!");
    });
  }
}

function showToast(message) {
  const toast = $("lunar-forecast-toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 3000);
}


async function loadWeeklyCommentary(date) {
  try {
    const response = await fetchWithTimeout("/api/weekly_commentary?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderWeeklyCommentary(data.data || data);
  } catch (e) {
    console.error("Weekly commentary failed:", e);
    $("weekly-commentary-content").textContent = "Weekly commentary is unavailable. Try again.";
    $("weekly-commentary").classList.remove("hidden");
  }
}

async function loadBullionVedha(date, weekly = false) {
  if (!$("bullion-vedha-content")) return;
  const endpoint = weekly ? "/api/bullion_vedha_week" : "/api/bullion_vedha";
  try {
    const response = await fetchWithTimeout(endpoint + "?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderBullionVedha(data, weekly);
  } catch (e) {
    console.error("Bullion vedha failed:", e);
    if ($("bullion-vedha-content")) {
      $("bullion-vedha-content").textContent = "Bullion Vedha is unavailable. Try again.";
    }
    if ($("bullion-vedha")) $("bullion-vedha").classList.remove("hidden");
  }
}

async function loadTransitVedha(date, weekly = false) {
  if (!$("transit-vedha-content")) return;
  const endpoint = weekly ? "/api/transit_vedha_week" : "/api/transit_vedha";
  try {
    const response = await fetchWithTimeout(endpoint + "?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderTransitVedha(data, weekly);
  } catch (e) {
    console.error("Transit vedha failed:", e);
    if ($("transit-vedha-content")) {
      $("transit-vedha-content").textContent = "Transit Vedha is unavailable. Try again.";
    }
    if ($("transit-vedha")) $("transit-vedha").classList.remove("hidden");
  }
}

function renderGrid(d) {
  const grid = $("grid");
  grid.innerHTML = "";
  const hitPoints = new Map();
  for (const h of d.point_hits) {
    hitPoints.set(h.point, hitPoints.get(h.point) || { benefic: 0, malefic: 0 });
    hitPoints.get(h.point)[h.nature] += Math.abs(h.strength);
  }

  for (const row of d.grid) {
    for (const cell of row) {
      const el = document.createElement("div");
      el.className = "cell " + cell.type;
      if (cell.type === "vowel" &&
          ((cell.row === 1 || cell.row === 9) && (cell.col === 1 || cell.col === 9))) {
        el.classList.add("corner");
      }
      const main = document.createElement("div");
      main.className = "cell-main";
      main.textContent = cell.label;
      el.appendChild(main);

      const subBits = [];
      if (cell.weekdays) subBits.push(cell.weekdays.join("/"));
      if (cell.type === "tithi") subBits.push("tithi");
      if (subBits.length) {
        const sub = document.createElement("div");
        sub.className = "cell-sub";
        sub.textContent = subBits.join(" ");
        el.appendChild(sub);
      }

      if (cell.points && cell.points.length) {
        el.classList.add("point");
        el.title = "Sensitive: " + cell.points.join(", ");
        const hit = hitPoints.get(cell.points[0]);
        if (hit) {
          if (hit.benefic > 0 && hit.malefic > 0) el.classList.add("hit-both");
          else if (hit.benefic > 0) el.classList.add("hit-bull");
          else if (hit.malefic > 0) el.classList.add("hit-bear");
        }
      }

      if (cell.planets && cell.planets.length) {
        for (const p of cell.planets) {
          const pm = document.createElement("div");
          pm.className = "pmark " + NATURE[p.nature].cls;
          pm.textContent = p.symbol;
          el.title = (el.title ? el.title + " .  " : "") +
            p.name + " (" + p.nature + ")";
          el.appendChild(pm);
        }
      }
      grid.appendChild(el);
    }
  }

  renderRays(d);

  $("grid-sub").textContent = `${d.weekday} .  ${d.tithi.paksha} paksha .  tithi ${d.tithi.tithi} (${d.tithi.group})`;
}

function renderRays(d) {
  const svg = $("rays");
  svg.innerHTML = "";
  const NS = "http://www.w3.org/2000/svg";
  const hitCellSet = new Set();
  for (const h of d.point_hits) {
    hitCellSet.add(h.point + "|" + h.planet);
  }

  for (const p of d.planets) {
    const origin = cellCenter(p.planetCell[0], p.planetCell[1]);
    for (const ray of p.rays) {
      if (!ray.cells.length) continue;
      const pts = [origin];
      for (const [r, c] of ray.cells) pts.push(cellCenter(r, c));
      const hitsPoint = ray.cells.some(([r, c]) => {
        const cell = d.grid[r - 1][c - 1];
        return cell.planets && cell.points &&
          cell.points.some((nm) => hitCellSet.has(nm + "|" + p.name));
      });
      const line = document.createElementNS(NS, "polyline");
      line.setAttribute("points", pts.map((q) => `${q.x.toFixed(1)},${q.y.toFixed(1)}`).join(" "));
      line.setAttribute("fill", "none");
      line.setAttribute("stroke", p.nature === "benefic" ? "#34d399" : "#f87171");
      line.setAttribute("stroke-width", hitsPoint ? "3" : "1");
      line.setAttribute("stroke-opacity", hitsPoint ? "0.9" : "0.22");
      line.setAttribute("stroke-dasharray", hitsPoint ? "0" : "3 4");
      svg.appendChild(line);
    }
  }
}

function renderPlanets(d) {
  const tbody = $("planets");
  tbody.innerHTML = "";
  for (const p of d.planets) {
    const tr = document.createElement("tr");

    const tdSym = document.createElement("td");
    const sym = document.createElement("span");
    sym.className = "sym " + NATURE[p.nature].cls;
    sym.textContent = p.symbol;
    sym.title = p.name;
    tdSym.appendChild(sym);
    tr.appendChild(tdSym);

    const tdSign = document.createElement("td");
    tdSign.textContent = `${p.sign} ${p.degree.toFixed(1)} deg`;
    tr.appendChild(tdSign);

    const tdNak = document.createElement("td");
    tdNak.textContent = `${p.nakshatra} p${p.pada}`;
    tr.appendChild(tdNak);

    const tdMot = document.createElement("td");
    tdMot.className = "mot";
    tdMot.textContent = p.retrograde ? "℞" : "";
    tdMot.title = p.retrograde ? "Retrograde" : `speed ${p.speed.toFixed(2)} deg/day`;
    tr.appendChild(tdMot);

    const tdNat = document.createElement("td");
    const nat = document.createElement("span");
    nat.className = "nat " + NATURE[p.nature].cls;
    nat.textContent = NATURE[p.nature].label;
    nat.title = (p.nature_note || "") + (p.dignity_reasons.length ? " .  " + p.dignity_reasons.join(", ") : "");
    tdNat.appendChild(nat);
    tr.appendChild(tdNat);

    tbody.appendChild(tr);
  }
}

function renderPoints(d) {
  const ul = $("points");
  ul.innerHTML = "";
  $("anchor-name").textContent = d.anchor.name;
  $("anchor-star").textContent = d.anchor.nakshatra;

  const hits = {};
  for (const h of d.point_hits) (hits[h.point] = hits[h.point] || []).push(h);

  for (const pt of d.points) {
    const li = document.createElement("li");
    const dot = document.createElement("span");
    dot.className = "dot";
    li.appendChild(dot);

    const name = document.createElement("span");
    name.className = "pname";
    name.textContent = pt.name;
    li.appendChild(name);

    const star = document.createElement("span");
    star.className = "pstar";
    star.textContent = pt.nakshatra;
    star.title = pt.description;
    li.appendChild(star);

    if (["Janma", "Karma", "Sanghatika", "Samudayika", "Adhana"].includes(pt.name)) {
      const core = document.createElement("span");
      core.className = "core";
      core.textContent = "PS";
      core.title = "Pancha-Shakha core point";
      li.appendChild(core);
    }

    const hs = hits[pt.name] || [];
    if (hs.length) {
      const good = hs.filter((h) => h.nature === "benefic").length;
      const bad = hs.length - good;
      const hit = document.createElement("span");
      hit.className = "phit";
      if (good && bad) { hit.textContent = "mixed"; hit.className += " bad"; li.classList.add("hit-bad"); }
      else if (good) { hit.textContent = good + " benefic"; hit.className += " good"; li.classList.add("hit-good"); }
      else { hit.textContent = bad + " malefic"; hit.className += " bad"; li.classList.add("hit-bad"); }
      li.appendChild(hit);
    }
    ul.appendChild(li);
  }
}

function renderVedhas(d) {
  const box = $("vedhas");
  box.innerHTML = "";
  const focused = d.vedhas
    .map((v) => ({ ...v, rays: v.rays.filter((r) => r.hit_points.length) }))
    .filter((v) => v.rays.length);
  const totalRays = focused.reduce((n, v) => n + v.rays.length, 0);
  const totalHits = d.point_hits.length;
  $("vedhas-sub").textContent =
    `${focused.length} grahas .  ${totalRays} piercing vedha rays .  ${totalHits} point piercing${totalHits === 1 ? "" : "s"}`;

  for (const v of focused) {
    const item = document.createElement("div");
    item.className = "vedha-item";

    const head = document.createElement("div");
    head.className = "vhead";
    const sym = document.createElement("span");
    sym.className = "sym " + NATURE[v.nature].cls;
    sym.textContent = v.symbol;
    sym.title = v.planet;
    head.appendChild(sym);
    const name = document.createElement("b");
    name.textContent = v.planet;
    head.appendChild(name);
    const nak = document.createElement("span");
    nak.className = "vnak";
    nak.textContent = "in " + v.nakshatra + " .  " + NATURE[v.nature].label;
    head.appendChild(nak);
    const str = document.createElement("span");
    str.className = "vstr " + (v.strength >= 0 ? "pos" : "neg");
    str.textContent = "strength " + (v.strength >= 0 ? "+" : "") + v.strength.toFixed(1);
    str.title = (v.nature_note || "") + (v.dignity_reasons && v.dignity_reasons.length ?
      " .  " + v.dignity_reasons.join(", ") : "");
    head.appendChild(str);
    item.appendChild(head);

    const rays = document.createElement("div");
    rays.className = "vedha-rays";
    for (const ray of v.rays) {
      const row = document.createElement("div");
      row.className = "vray";
      const tag = document.createElement("span");
      tag.className = "ray-tag " + ray.ray;
      tag.textContent = ray.ray + " ray";
      row.appendChild(tag);

      const cells = document.createElement("span");
      cells.className = "vcells";
      for (const cell of ray.cells) {
        const chip = document.createElement("span");
        chip.className = "vcell";
        chip.textContent = cell.label;
        if (cell.point) {
          chip.classList.add("hitpoint");
          if (v.nature === "benefic") chip.classList.add("benefic");
          else chip.classList.add("malefic");
          chip.title = cell.point + " (" + v.planet + " " + ray.ray + " ray)";
        }
        cells.appendChild(chip);
      }
      row.appendChild(cells);

      if (ray.hit_points.length) {
        const hits = document.createElement("span");
        hits.className = "vhits";
        hits.innerHTML = "&rarr; pierces <b>" + ray.hit_points.join(", ") + "</b>";
        row.appendChild(hits);
      }
      rays.appendChild(row);
    }
    item.appendChild(rays);
    box.appendChild(item);
  }
}

function renderSectors(d) {
  const box = $("sectors");
  box.innerHTML = "";
  const list = d.sectors || [];
  const bull = list.filter((s) => s.verdict === "BULLISH").length;
  const bear = list.filter((s) => s.verdict === "BEARISH").length;
  const flat = list.length - bull - bear;
  $("sectors-sub").textContent =
    `${bull} bullish .  ${bear} bearish .  ${flat} no-signal`;

  for (const s of list) {
    const card = document.createElement("div");
    card.className = "sector-card v-" + s.verdict.toLowerCase();

    const head = document.createElement("div");
    head.className = "shead";
    const abbr = document.createElement("span");
    abbr.className = "sabbr";
    abbr.textContent = s.abbr;
    head.appendChild(abbr);
    const name = document.createElement("b");
    name.className = "srashi";
    name.textContent = s.rashi;
    head.appendChild(name);
    const badge = document.createElement("span");
    badge.className = "sbadge " + s.verdict.toLowerCase() +
      (s.verdict === "NEUTRAL" ? " flat" : "");
    badge.textContent =
      s.verdict === "NEUTRAL" ? "no signal" : s.verdict.toLowerCase() + " .  " + s.strength;
    head.appendChild(badge);
    card.appendChild(head);

    const net = document.createElement("div");
    net.className = "snet " + (s.net >= 0 ? "pos" : "neg");
    net.textContent = (s.net >= 0 ? "+" : "") + s.net.toFixed(1);
    net.title = "net vedha strength on this rashi";
    card.appendChild(net);

    const tags = document.createElement("div");
    tags.className = "sector-tags";
    for (const t of s.sectors) {
      const chip = document.createElement("span");
      chip.className = "stag";
      chip.textContent = t;
      tags.appendChild(chip);
    }
    card.appendChild(tags);

    const hits = document.createElement("div");
    hits.className = "shits";
    if (!s.hits.length) {
      const none = document.createElement("div");
      none.className = "shnone";
      none.textContent = "No vedha pierces this rashi.";
      hits.appendChild(none);
    }
    for (const h of s.hits) {
      const row = document.createElement("div");
      row.className = "shit";
      const sym = document.createElement("span");
      sym.className = "sym " + NATURE[h.nature].cls;
      sym.textContent = h.symbol;
      sym.title = h.planet;
      row.appendChild(sym);
      const ray = document.createElement("span");
      ray.className = "sray-tag " + h.ray;
      ray.textContent = h.ray + " ray";
      row.appendChild(ray);
      const val = document.createElement("span");
      val.className = "sval " + (h.strength >= 0 ? "pos" : "neg");
      val.textContent = (h.strength >= 0 ? "+" : "") + h.strength.toFixed(1);
      row.appendChild(val);
      hits.appendChild(row);
    }
    card.appendChild(hits);
    box.appendChild(card);
  }
}

function renderPlanetSectors(d) {
  const box = $("psectors");
  box.innerHTML = "";
  const list = d.planet_sectors || [];
  const favor = list.filter((s) => s.read === "FAVOR").length;
  const avoid = list.filter((s) => s.read === "AVOID").length;
  const neutral = list.length - favor - avoid;
  $("psectors-sub").textContent =
    `${favor} favouring .  ${avoid} pressuring .  ${neutral} neutral`;

  for (const s of list) {
    const card = document.createElement("div");
    card.className = "sector-card ps-card v-" + s.read.toLowerCase();

    const head = document.createElement("div");
    head.className = "shead";
    const sym = document.createElement("span");
    sym.className = "sym " + NATURE[s.nature].cls;
    sym.textContent = s.symbol;
    sym.title = s.planet;
    head.appendChild(sym);
    const name = document.createElement("b");
    name.className = "srashi";
    name.textContent = s.planet;
    head.appendChild(name);
    const badge = document.createElement("span");
    badge.className = "sbadge " + s.read.toLowerCase();
    badge.textContent = s.read.toLowerCase() + " .  " +
      (s.strength >= 0 ? "+" : "") + s.strength.toFixed(1);
    badge.title = (s.dignity_reasons || []).join(", ");
    head.appendChild(badge);
    card.appendChild(head);

    const tags = document.createElement("div");
    tags.className = "sector-tags";
    for (const t of s.sectors) {
      const chip = document.createElement("span");
      chip.className = "stag";
      chip.textContent = t;
      tags.appendChild(chip);
    }
    card.appendChild(tags);
    box.appendChild(card);
  }
}

function renderReading(d) {
  const box = $("reading");
  box.innerHTML = "";
  const rec = d.recommendation;
  $("read-sub").textContent = `Net vedha ${d.net >= 0 ? "+" : ""}${d.net.toFixed(1)} .  ${rec.verdict} ${rec.strength}`;

  const lead = document.createElement("p");
  lead.className = "lead";
  lead.textContent = rec.summary;
  box.appendChild(lead);

  for (let i = 0; i < rec.text.length; i++) {
    const p = document.createElement("p");
    p.textContent = rec.text[i];
    box.appendChild(p);
  }
}

function renderWeeklyCommentary(data) {
  const box = $("weekly-commentary-content");
  box.innerHTML = "";

  // Main cycle banner
  if (data.main_cycle) {
    const banner = document.createElement("div");
    banner.className = "weekly-main-cycle";
    banner.innerHTML = `
      <div class="cycle-badge ${data.main_cycle.intensity || ''}">${data.main_cycle.intensity ? data.main_cycle.intensity.toUpperCase() : 'KEY'}</div>
      <div class="cycle-title">${data.main_cycle.name}</div>
      <div class="cycle-details">${data.main_cycle.details || ''}</div>
    `;
    box.appendChild(banner);
  }

  // Market bias
  if (data.market_bias) {
    const biasEl = document.createElement("div");
    biasEl.className = "weekly-bias " + (data.market_bias.includes("BEARISH") ? "bear" :
      data.market_bias.includes("BULLISH") ? "bull" : "mixed");
    biasEl.innerHTML = `<strong>Weekly Bias:</strong> ${data.market_bias}`;
    box.appendChild(biasEl);
  }

  // Planetary positions summary
  if (data.planetary_positions && data.planetary_positions.length) {
    const posEl = document.createElement("div");
    posEl.className = "weekly-section";
    posEl.innerHTML = `<h4>Planetary Positions (Monday Noon IST)</h4>`;
    const list = document.createElement("ul");
    list.className = "planet-list";
    for (const pos of data.planetary_positions) {
      const li = document.createElement("li");
      li.textContent = pos;
      list.appendChild(li);
    }
    posEl.appendChild(list);
    box.appendChild(posEl);
  }

  // Key configurations
  if (data.configurations && data.configurations.length) {
    const confEl = document.createElement("div");
    confEl.className = "weekly-section";
    confEl.innerHTML = `<h4>Key Configurations This Week</h4>`;
    for (const c of data.configurations) {
      const item = document.createElement("div");
      item.className = "config-item " + (c.intensity || "moderate");
      const badge = c.intensity ? `<span class="intensity-badge ${c.intensity}">${c.intensity.toUpperCase()}</span>` : '';
      item.innerHTML = `${badge}<strong>${c.name}</strong>: ${c.details || ''}`;
      confEl.appendChild(item);
    }
    box.appendChild(confEl);
  }

  // Moon transits
  if (data.moon_transits && data.moon_transits.length) {
    const moonEl = document.createElement("div");
    moonEl.className = "weekly-section";
    moonEl.innerHTML = `<h4>Moon Nakshatra Transits (Daily Sentiment Drivers)</h4>`;
    const table = document.createElement("table");
    table.className = "moon-transit-table";
    table.innerHTML = `
      <thead><tr><th>Day</th><th>Date</th><th>Nakshatra</th><th>Sign</th><th>Meaning</th><th>Lord</th></tr></thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector("tbody");
    for (const mt of data.moon_transits) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${mt.weekday}</td>
        <td>${mt.date}</td>
        <td><strong>${mt.nakshatra}</strong></td>
        <td>${mt.sign} ${mt.degree.toFixed(1)} deg</td>
        <td>${mt.meaning || ''}</td>
        <td>${mt.lord || ''}</td>
      `;
      tbody.appendChild(tr);
    }
    moonEl.appendChild(table);
    box.appendChild(moonEl);
  }

  // Active reversal windows
  if (data.active_windows && data.active_windows.length) {
    const winEl = document.createElement("div");
    winEl.className = "weekly-section";
    winEl.innerHTML = `<h4>Active Reversal Windows</h4>`;
    for (const w of data.active_windows) {
      const item = document.createElement("div");
      item.className = "alert-window active " + (w.bias.includes("BULLISH") ? "bull" : w.bias.includes("BEARISH") ? "bear" : "neutral");
      item.innerHTML = `
        <h5>${w.title}</h5>
        <div class="alert-meta">${w.start} to ${w.end} .  ${w.level}</div>
        <div class="alert-bias">${w.bias}</div>
        <div class="alert-sectors">Sectors: ${w.sectors.join(", ")}</div>
      `;
      winEl.appendChild(item);
    }
    box.appendChild(winEl);
  }

  // Upcoming windows
  if (data.upcoming_windows && data.upcoming_windows.length) {
    const upEl = document.createElement("div");
    upEl.className = "weekly-section";
    upEl.innerHTML = `<h4>Upcoming High-Impact Windows (Next 7 Days)</h4>`;
    for (const w of data.upcoming_windows) {
      const item = document.createElement("div");
      item.className = "alert-window upcoming";
      item.innerHTML = `
        <h5>${w.title}</h5>
        <div class="alert-meta">In ${w.days_ahead} day${w.days_ahead === 1 ? '' : 's'} .  ${w.level}</div>
        <div class="alert-bias">${w.bias}</div>
        <div class="alert-sectors">Sectors: ${w.sectors.join(", ")}</div>
      `;
      upEl.appendChild(item);
    }
    box.appendChild(upEl);
  }

  // Major transits
  if (data.transits && data.transits.length) {
    const transEl = document.createElement("div");
    transEl.className = "weekly-section";
    transEl.innerHTML = `<h4>Major Planetary Transits</h4>`;
    for (const t of data.transits) {
      const item = document.createElement("div");
      item.className = "transit-item";
      const retro = t.retrograde ? ' <span class="retro">℞</span>' : '';
      item.innerHTML = `
        <strong>${t.planet} in ${t.sign} ${t.degree.toFixed(2)} deg ${t.nakshatra}${retro}</strong>
        <div class="transit-bias">${t.bias}</div>
        <div class="transit-explanation">${t.explanation}</div>
        <div class="transit-sectors">Sectors: ${t.sectors.join(", ")}</div>
      `;
      transEl.appendChild(item);
    }
    box.appendChild(transEl);
  }

  // Lunar phase
  if (data.lunar_phase && data.lunar_phase.active) {
    const lp = data.lunar_phase;
    const lunarEl = document.createElement("div");
    lunarEl.className = "weekly-section lunar-phase";
    lunarEl.innerHTML = `
      <h4>${lp.phase} (Tithi ${lp.tithi})</h4>
      <div class="lunar-meta">Level: ${lp.level} .  Bias: ${lp.bias}</div>
      <div class="lunar-explanation">${lp.explanation}</div>
    `;
    box.appendChild(lunarEl);
  }

  // Jupiter analysis
  if (data.jupiter_analysis && data.jupiter_analysis.active) {
    const ja = data.jupiter_analysis;
    const jupEl = document.createElement("div");
    jupEl.className = "weekly-section jupiter-alert";
    jupEl.innerHTML = `
      <h4>⚠️ Jupiter Market-Risk Heuristic: ${ja.bias} (${ja.level})</h4>
      <ul>${ja.reasons.map(r => `<li>${r}</li>`).join('')}</ul>
    `;
    box.appendChild(jupEl);
  }

  // Confluence analysis
  if (data.confluence) {
    const conf = data.confluence;
    const overall = conf.overall;
    const highlights = conf.highlights;
    const confEl = document.createElement("div");
    confEl.className = "weekly-section confluence";
    confEl.innerHTML = `
      <h4>Confluence Analysis (Multi-factor Synthesis)</h4>
      <div class="confluence-overall ${overall.signal.toLowerCase()}">
        <strong>Overall Signal:</strong> ${overall.signal} (Net: ${overall.net >= 0 ? '+' : ''}${overall.net.toFixed(2)}) . 
        Bullish: ${overall.bullish_weight.toFixed(2)} .  Bearish: ${overall.bearish_weight.toFixed(2)}
      </div>
    `;
    if (highlights.bullish_confluence_sectors.length) {
      const bull = document.createElement("div");
      bull.className = "confluence-highlights bullish";
      bull.innerHTML = `<strong>🟢 Bullish Confluence:</strong> ${highlights.bullish_confluence_sectors.join(", ")}`;
      confEl.appendChild(bull);
    }
    if (highlights.bearish_confluence_sectors.length) {
      const bear = document.createElement("div");
      bear.className = "confluence-highlights bearish";
      bear.innerHTML = `<strong>🔴 Bearish Confluence:</strong> ${highlights.bearish_confluence_sectors.join(", ")}`;
      confEl.appendChild(bear);
    }
    if (highlights.conflicted_sectors.length) {
      const conflict = document.createElement("div");
      conflict.className = "confluence-highlights conflicted";
      conflict.innerHTML = `<strong>⚠️ Conflicted:</strong> ${highlights.conflicted_sectors.join(", ")}`;
      confEl.appendChild(conflict);
    }
    box.appendChild(confEl);
  }

  // Futurecast signals
  if (data.bullish_futurecast && data.bullish_futurecast.clusters) {
    const clusters = data.bullish_futurecast.clusters.filter(c =>
      c.timeline === "current" || c.timeline === "upcoming" || (new Date(c.start) <= new Date(data.end_date) && new Date(c.end) >= new Date(data.start_date))
    );
    if (clusters.length) {
      const fcEl = document.createElement("div");
      fcEl.className = "weekly-section bullish-fc";
      fcEl.innerHTML = `<h4>🟢 Bullish Futurecast Windows (1-Year Window)</h4>`;
      for (const c of clusters.slice(0, 3)) {
        const item = document.createElement("div");
        item.className = "fc-item " + c.level.toLowerCase();
        item.innerHTML = `
          <div class="fc-header"><span class="fc-date">${c.start} – ${c.end}</span> <span class="fc-score">${c.level} .  ${c.score}/16</span></div>
          <div class="fc-triggers">${c.triggers.slice(0, 4).join(" .  ")}</div>
        `;
        fcEl.appendChild(item);
      }
      box.appendChild(fcEl);
    }
  }

  if (data.bearish_futurecast && data.bearish_futurecast.clusters) {
    const clusters = data.bearish_futurecast.clusters.filter(c =>
      c.timeline === "current" || c.timeline === "upcoming" || (new Date(c.start) <= new Date(data.end_date) && new Date(c.end) >= new Date(data.start_date))
    );
    if (clusters.length) {
      const fcEl = document.createElement("div");
      fcEl.className = "weekly-section bearish-fc";
      fcEl.innerHTML = `<h4>🔴 Bearish Futurecast Windows (Next 30 Days)</h4>`;
      for (const c of clusters.slice(0, 3)) {
        const item = document.createElement("div");
        item.className = "fc-item " + c.level.toLowerCase();
        item.innerHTML = `
          <div class="fc-header"><span class="fc-date">${c.start} – ${c.end}</span> <span class="fc-score">${c.level} .  ${c.score}/20</span></div>
          <div class="fc-triggers">${c.triggers.slice(0, 4).join(" .  ")}</div>
        `;
        fcEl.appendChild(item);
      }
      box.appendChild(fcEl);
    }
  }

  // Bullish/Bearish factors
  const factorsEl = document.createElement("div");
  factorsEl.className = "weekly-section factors";
  let hasFactors = false;
  if (data.bullish_factors && data.bullish_factors.length) {
    hasFactors = true;
    const bull = document.createElement("div");
    bull.className = "factor-group bullish";
    bull.innerHTML = `<strong>🟢 Bullish Factors</strong><ul>${data.bullish_factors.slice(0, 5).map(f => `<li>${f}</li>`).join('')}</ul>`;
    factorsEl.appendChild(bull);
  }
  if (data.bearish_factors && data.bearish_factors.length) {
    hasFactors = true;
    const bear = document.createElement("div");
    bear.className = "factor-group bearish";
    bear.innerHTML = `<strong>🔴 Bearish Factors</strong><ul>${data.bearish_factors.slice(0, 5).map(f => `<li>${f}</li>`).join('')}</ul>`;
    factorsEl.appendChild(bear);
  }
  if (hasFactors) box.appendChild(factorsEl);

  // Sector-wise Outlook Table
  if (data.sector_outlook && data.sector_outlook.length) {
    const sectorEl = document.createElement("div");
    sectorEl.className = "weekly-section sector-outlook";
    sectorEl.innerHTML = `<h4>Sector-wise Financial Astro-Trend Outlook</h4>`;
    
    const table = document.createElement("table");
    table.className = "sector-outlook-table";
    table.innerHTML = `
      <thead>
        <tr>
          <th>Sector</th>
          <th>Astrological Influence</th>
          <th>Trend / Outlook</th>
          <th>Key Focus</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector("tbody");
    for (const s of data.sector_outlook) {
      const tr = document.createElement("tr");
      const trendClass = s.trend_outlook.includes("Bullish") ? "trend-bull" :
        s.trend_outlook.includes("Bearish") ? "trend-bear" :
        s.trend_outlook.includes("Volatile") ? "trend-volatile" : "trend-neutral";
      tr.innerHTML = `
        <td><strong>${s.sector}</strong></td>
        <td>${s.astrological_influence}</td>
        <td class="${trendClass}">${s.trend_outlook}</td>
        <td>${s.key_focus}</td>
      `;
      tbody.appendChild(tr);
    }
    sectorEl.appendChild(table);
    box.appendChild(sectorEl);
  }

  // General Market Strategy
  if (data.general_strategy) {
    const strategyEl = document.createElement("div");
    strategyEl.className = "weekly-section strategy";
    strategyEl.innerHTML = `<h4>General Market Strategy for the Week</h4>`;
    const lines = data.general_strategy.split('\n');
    const ul = document.createElement("ul");
    for (const line of lines) {
      if (line.trim()) {
        const li = document.createElement("li");
        li.textContent = line.trim();
        ul.appendChild(li);
      }
    }
    strategyEl.appendChild(ul);
    box.appendChild(strategyEl);
  }

  // Nifty Levels
  if (data.nifty_levels) {
    const levelsEl = document.createElement("div");
    levelsEl.className = "weekly-section nifty-levels";
    levelsEl.innerHTML = `<h4>Nifty Key Levels & Guidance</h4>`;
    const lines = data.nifty_levels.split('\n');
    const ul = document.createElement("ul");
    for (const line of lines) {
      if (line.trim()) {
        const li = document.createElement("li");
        li.textContent = line.trim();
        ul.appendChild(li);
      }
    }
    levelsEl.appendChild(ul);
    box.appendChild(levelsEl);
  }

  // Show the panel
  $("weekly-commentary").classList.remove("hidden");
}

function renderBullionVedha(data, weekly) {
  const box = $("bullion-vedha-content");
  if (!box) return;
  box.innerHTML = "";
  
  if (weekly) {
    // Weekly view
    const summary = data.weekly_summary || {};
    const signals = data.weekly_unique_signals || [];
    
    const header = document.createElement("div");
    header.className = "bullion-vedha-header";
    header.innerHTML = `
      <div class="bullion-bias ${summary.overall_bullion_bias ? summary.overall_bullion_bias.toLowerCase() : 'mixed'}">
        Overall Bullion Bias: ${summary.overall_bullion_bias || 'MIXED'}
      </div>
      <div class="bullion-stats">
        <span>Total Signals: ${summary.total_unique_signals || 0}</span>
        <span>Gold: ${summary.gold_signals || 0}</span>
        <span>Silver: ${summary.silver_signals || 0}</span>
        <span>EXTREME: ${summary.extreme_intensity || 0}</span>
        <span>HIGH: ${summary.high_intensity || 0}</span>
      </div>
    `;
    box.appendChild(header);
    
    if (signals.length === 0) {
      const empty = document.createElement("p");
      empty.className = "bullion-empty";
      empty.textContent = "No active bullion vedha signals this week.";
      box.appendChild(empty);
    } else {
      const list = document.createElement("div");
      list.className = "bullion-signals-list";
      for (const s of signals) {
        const item = document.createElement("div");
        item.className = "bullion-signal-item " + (s.intensity ? s.intensity.toLowerCase() : "");
        const metalBadge = s.affected_metal === "Gold" ? "gold-badge" :
          s.affected_metal === "Silver" ? "silver-badge" : "both-badge";
        item.innerHTML = `
          <div class="signal-header">
            <span class="intensity-badge ${s.intensity ? s.intensity.toLowerCase() : ''}">${s.intensity || 'MODERATE'}</span>
            <span class="metal-badge ${metalBadge}">${s.affected_metal}</span>
            <h4>${s.title}</h4>
          </div>
          <div class="signal-meta">
            <span>Type: ${s.vedha_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
            <span>Planets: ${s.triggering_planets.join(', ')}</span>
            <span>Nakshatras: ${s.nakshatras_involved.join(', ')}</span>
          </div>
          <div class="signal-mechanism">${s.mechanism}</div>
          <div class="signal-impact">${s.market_impact}</div>
          <div class="signal-duration">Duration: ${s.duration_estimate}</div>
        `;
        list.appendChild(item);
      }
      box.appendChild(list);
    }
    
    // Daily breakdown
    if (data.daily_scans) {
      const daily = document.createElement("div");
      daily.className = "bullion-daily-breakdown";
      daily.innerHTML = `<h4>Daily Breakdown</h4>`;
      const table = document.createElement("table");
      table.className = "bullion-daily-table";
      table.innerHTML = `
        <thead>
          <tr><th>Date</th><th>Gold Bias</th><th>Silver Bias</th><th>Signals</th><th>EXTREME</th><th>HIGH</th></tr>
        </thead>
        <tbody></tbody>
      `;
      const tbody = table.querySelector("tbody");
      for (const d of data.daily_scans) {
        const tr = document.createElement("tr");
        const sum = d.summary || {};
        tr.innerHTML = `
          <td>${d.date}</td>
          <td class="${sum.gold?.bias?.toLowerCase() || 'neutral'}">${sum.gold?.bias || 'NEUTRAL'}</td>
          <td class="${sum.silver?.bias?.toLowerCase() || 'neutral'}">${sum.silver?.bias || 'NEUTRAL'}</td>
          <td>${sum.gold?.signal_count || 0 + sum.silver?.signal_count || 0}</td>
          <td>${sum.gold?.extreme_count || 0 + sum.silver?.extreme_count || 0}</td>
          <td>${sum.gold?.high_count || 0 + sum.silver?.high_count || 0}</td>
        `;
        tbody.appendChild(tr);
      }
      daily.appendChild(table);
      box.appendChild(daily);
    }
    
  } else {
    // Daily view
    const summary = data.summary || {};
    const signals = data.signals || [];
    
    const header = document.createElement("div");
    header.className = "bullion-vedha-header";
    header.innerHTML = `
      <div class="bullion-bias ${summary.overall_bullion_bias ? summary.overall_bullion_bias.toLowerCase() : 'mixed'}">
        Overall Bullion Bias: ${summary.overall_bullion_bias || 'MIXED'}
      </div>
      <div class="bullion-stats">
        <span>Gold: ${summary.gold?.bias || 'NEUTRAL'} (${summary.gold?.signal_count || 0} signals)</span>
        <span>Silver: ${summary.silver?.bias || 'NEUTRAL'} (${summary.silver?.signal_count || 0} signals)</span>
      </div>
    `;
    box.appendChild(header);
    
    if (signals.length === 0) {
      const empty = document.createElement("p");
      empty.className = "bullion-empty";
      empty.textContent = "No active bullion vedha signals for this date.";
      box.appendChild(empty);
    } else {
      const list = document.createElement("div");
      list.className = "bullion-signals-list";
      for (const s of signals) {
        const item = document.createElement("div");
        item.className = "bullion-signal-item " + (s.intensity ? s.intensity.toLowerCase() : "");
        const metalBadge = s.affected_metal === "Gold" ? "gold-badge" :
          s.affected_metal === "Silver" ? "silver-badge" : "both-badge";
        item.innerHTML = `
          <div class="signal-header">
            <span class="intensity-badge ${s.intensity ? s.intensity.toLowerCase() : ''}">${s.intensity || 'MODERATE'}</span>
            <span class="metal-badge ${metalBadge}">${s.affected_metal}</span>
            <h4>${s.title}</h4>
          </div>
          <div class="signal-meta">
            <span>Type: ${s.vedha_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
            <span>Planets: ${s.triggering_planets.join(', ')}</span>
            <span>Nakshatras: ${s.nakshatras_involved.join(', ')}</span>
            <span>Confidence: ${Math.round(s.confidence * 100)}%</span>
          </div>
          <div class="signal-mechanism">${s.mechanism}</div>
          <div class="signal-impact">${s.market_impact}</div>
          <div class="signal-duration">Duration: ${s.duration_estimate}</div>
        `;
        list.appendChild(item);
      }
      box.appendChild(list);
    }
    
    // Matrix reference
    if (data.matrix_reference) {
      const ref = document.createElement("div");
      ref.className = "bullion-matrix-ref";
      ref.innerHTML = `<h4>Matrix Reference</h4>`;
      const ul = document.createElement("ul");
      for (const [k, v] of Object.entries(data.matrix_reference)) {
        const li = document.createElement("li");
        li.textContent = `${k}: ${v}`;
        ul.appendChild(li);
      }
      ref.appendChild(ul);
      box.appendChild(ref);
    }
  }
  
  // Show the panel
  if ($("bullion-vedha")) $("bullion-vedha").classList.remove("hidden");
}

function renderTransitVedha(data, weekly) {
  const box = $("transit-vedha-content");
  if (!box) return;
  box.innerHTML = "";
  
  if (weekly) {
    // Weekly view
    const summary = data.weekly_summary || {};
    const signals = data.weekly_unique_signals || [];
    const sectorSummary = data.weekly_sector_summary || {};
    
    const header = document.createElement("div");
    header.className = "transit-vedha-header";
    header.innerHTML = `
      <div class="transit-bias mixed">
        Overall Sector Bias: MIXED (${summary.sectors_activated || 0} sectors active)
      </div>
      <div class="transit-stats">
        <span>Total Signals: ${summary.total_unique_signals || 0}</span>
        <span>EXTREME: ${summary.extreme_count || 0}</span>
        <span>HIGH: ${summary.high_count || 0}</span>
        <span>Sectors: ${summary.sectors_activated || 0}</span>
      </div>
    `;
    box.appendChild(header);
    
    if (signals.length === 0) {
      const empty = document.createElement("p");
      empty.className = "transit-empty";
      empty.textContent = "No active transit vedha signals this week.";
      box.appendChild(empty);
    } else {
      const list = document.createElement("div");
      list.className = "transit-signals-list";
      for (const s of signals) {
        const item = document.createElement("div");
        item.className = "transit-signal-item " + (s.intensity ? s.intensity.toLowerCase() : "");
        item.innerHTML = `
          <div class="signal-header">
            <span class="intensity-badge ${s.intensity ? s.intensity.toLowerCase() : ''}">${s.intensity || 'MODERATE'}</span>
            <h4>${s.title}</h4>
          </div>
          <div class="signal-meta">
            <span>Type: ${s.vedha_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
            <span>Nakshatra: ${s.key_nakshatra}</span>
            <span>Match: ${s.details?.match_type || 'EXACT'}</span>
          </div>
          <div class="signal-mechanism">${s.directional_vedha_target}</div>
          <div class="signal-impact">${s.primary_market_impact}</div>
          <div class="signal-sectors">Sectors: ${s.affected_sectors.join(', ')}</div>
          <div class="signal-duration">Duration: ${s.duration_estimate}</div>
        `;
        list.appendChild(item);
      }
      box.appendChild(list);
    }
    
    // Sector summary
    if (data.weekly_sector_summary) {
      const sectorDiv = document.createElement("div");
      sectorDiv.className = "transit-sector-summary";
      sectorDiv.innerHTML = `<h4>By Sector</h4>`;
      const table = document.createElement("table");
      table.className = "transit-sector-table";
      table.innerHTML = `
        <thead>
          <tr><th>Sector</th><th>Signals</th><th>Max Intensity</th><th>Key Triggers</th></tr>
        </thead>
        <tbody></tbody>
      `;
      const tbody = table.querySelector("tbody");
      for (const [sector, info] of Object.entries(data.weekly_sector_summary)) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${sector}</strong></td>
          <td>${info.count}</td>
          <td class="${info.max_intensity.toLowerCase()}">${info.max_intensity}</td>
          <td>${info.signals.slice(0, 3).join(', ')}</td>
        `;
        tbody.appendChild(tr);
      }
      sectorDiv.appendChild(table);
      box.appendChild(sectorDiv);
    }
    
    // Daily breakdown
    if (data.daily_scans) {
      const daily = document.createElement("div");
      daily.className = "transit-daily-breakdown";
      daily.innerHTML = `<h4>Daily Breakdown</h4>`;
      const table = document.createElement("table");
      table.className = "transit-daily-table";
      table.innerHTML = `
        <thead>
          <tr><th>Date</th><th>Signals</th><th>Key Active</th></tr>
        </thead>
        <tbody></tbody>
      `;
      const tbody = table.querySelector("tbody");
      for (const d of data.daily_scans) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${d.date}</td>
          <td>${d.signal_count}</td>
          <td>${d.summary?.gold?.bias || 'NEUTRAL'} / ${d.summary?.silver?.bias || 'NEUTRAL'}</td>
        `;
        tbody.appendChild(tr);
      }
      daily.appendChild(table);
      box.appendChild(daily);
    }
    
  } else {
    // Daily view
    const signals = data.signals || [];
    const bySector = data.by_sector || {};
    
    const header = document.createElement("div");
    header.className = "transit-vedha-header";
    header.innerHTML = `
      <div class="transit-bias mixed">
        Active Sector Triggers: ${signals.length} signals
      </div>
    `;
    box.appendChild(header);
    
    if (signals.length === 0) {
      const empty = document.createElement("p");
      empty.className = "transit-empty";
      empty.textContent = "No active transit vedha signals for this date.";
      box.appendChild(empty);
    } else {
      const list = document.createElement("div");
      list.className = "transit-signals-list";
      for (const s of signals) {
        const item = document.createElement("div");
        item.className = "transit-signal-item " + (s.intensity ? s.intensity.toLowerCase() : "");
        item.innerHTML = `
          <div class="signal-header">
            <span class="intensity-badge ${s.intensity ? s.intensity.toLowerCase() : ''}">${s.intensity || 'MODERATE'}</span>
            <h4>${s.title}</h4>
          </div>
          <div class="signal-meta">
            <span>Type: ${s.vedha_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
            <span>Nakshatra: ${s.key_nakshatra}</span>
            <span>Match: ${s.details?.match_type || 'EXACT'}</span>
            <span>Confidence: ${Math.round(s.confidence * 100)}%</span>
          </div>
          <div class="signal-mechanism">${s.directional_vedha_target}</div>
          <div class="signal-impact">${s.primary_market_impact}</div>
          <div class="signal-sectors">Sectors: ${s.affected_sectors.join(', ')}</div>
          <div class="signal-duration">Duration: ${s.duration_estimate}</div>
        `;
        list.appendChild(item);
      }
      box.appendChild(list);
    }
    
    // By sector
    if (Object.keys(bySector).length > 0) {
      const sectorDiv = document.createElement("div");
      sectorDiv.className = "transit-sector-summary";
      sectorDiv.innerHTML = `<h4>By Sector</h4>`;
      for (const [sector, signals] of Object.entries(bySector)) {
        const sectorItem = document.createElement("div");
        sectorItem.className = "transit-sector-item";
        sectorItem.innerHTML = `
          <h5>${sector} (${signals.length} signals)</h5>
          <ul>${signals.map(s => '<li>' + s.title + ' (' + s.intensity + ')</li>').join('')}</ul>
        `;
        sectorDiv.appendChild(sectorItem);
      }
      box.appendChild(sectorDiv);
    }
    
    // Matrix reference
    if (data.matrix_reference) {
      const ref = document.createElement("div");
      ref.className = "transit-matrix-ref";
      ref.innerHTML = `<h4>Matrix Reference</h4>`;
      const ul = document.createElement("ul");
      for (const [k, v] of Object.entries(data.matrix_reference)) {
        const li = document.createElement("li");
        li.textContent = `${k}: ${v}`;
        ul.appendChild(li);
      }
      ref.appendChild(ul);
      box.appendChild(ref);
    }
  }
  
  // Show the panel
  if ($("transit-vedha")) $("transit-vedha").classList.remove("hidden");
}

function renderLegend(d) {
  const el = $("legend");
  el.innerHTML = "";
  const items = [
    ["N", "#182338", "Nakshatra"],
    ["C", "#19233a", "Consonant"],
    ["V", "#1b2038", "Vowel"],
    ["R", "#16283a", "Rashi"],
    ["T", "#1f2733", "Tithi"],
  ];
  for (const [cls, color, label] of items) {
    const s = document.createElement("span");
    const i = document.createElement("i");
    i.style.background = color;
    s.appendChild(i);
    s.appendChild(document.createTextNode(label));
    el.appendChild(s);
  }
  const sp = document.createElement("span");
  sp.innerHTML = '<i style="background:transparent;box-shadow:inset 0 0 0 1px #fbbf24"></i> Sensitive star';
  el.appendChild(sp);
  const gr = document.createElement("span");
  gr.innerHTML = '<i style="background:#34d399;border-radius:50%"></i> Benefic vedha';
  el.appendChild(gr);
  const rd = document.createElement("span");
  rd.innerHTML = '<i style="background:#f87171;border-radius:50%"></i> Malefic vedha';
  el.appendChild(rd);
}

async function run() {
  const btn = $("run");
  btn.disabled = true;
  setExecutiveLoading();
  // Normalize date from DD/MM/YYYY to YYYY-MM-DD if needed
  let dateVal = $("date").value || "";
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateVal)) {
    const [d,m,y] = dateVal.split("/");
    dateVal = `${y}-${m}-${d}`;
    $("date").value = dateVal;
  }
  // Normalize time AM/PM to HH:MM
  let timeVal = $("time").value || "09:15";
  const ampmMatch = timeVal.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (ampmMatch) {
    let h = parseInt(ampmMatch[1],10);
    const mi = ampmMatch[2];
    const ap = ampmMatch[3].toUpperCase();
    if (ap === "PM" && h !== 12) h += 12;
    if (ap === "AM" && h === 12) h = 0;
    timeVal = `${String(h).padStart(2,"0")}:${mi}`;
    $("time").value = timeVal;
  }
  const params = new URLSearchParams({
    date: dateVal,
    time: timeVal,
    tz: $("tz") ? $("tz").value : "Asia/Kolkata",
    anchor: ($("anchor") && $("anchor").value) ? $("anchor").value : "nse",
    school: $("school") ? $("school").value : "allthree",
  });
  try {
    const r = await fetchWithTimeout("/api/prediction?" + params);
    const data = await r.json();
    if (data.error) throw new Error(data.error);

    // add planet cell coords for ray drawing
    for (const p of data.planets) {
      const found = data.grid.flat().find((c) =>
        c.planets && c.planets.some((pl) => pl.name === p.name));
      p.planetCell = found ? [found.row, found.col] : [0, 0];
    }

    state = data;
    if ($("prediction-error")) $("prediction-error").classList.add("hidden");

    // Synchronize sub-panel date inputs with primary date
    [
      "weekly-commentary-date", "bullion-vedha-date", "transit-vedha-date",
      "largecap-divergence-date", "fmcg-signals-date", "tourism-signals-date",
      "chemical-signals-date", "alcohol-signals-date", "lunar-forecast-date",
      "kp-intraday-date"
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = data.date;
    });
    if (typeof updateWeekRange === "function") {
      updateWeekRange("weekly-commentary-date", "weekly-commentary-range");
    }

    await loadFuturecast(data.date);
    // Panels commented out in UI: Sector Vedha, LargeCap, FMCG, Tourism, Chemical, Alcohol, Bullion Vedha, Transit Vedha
    // await loadSectorVedha(data.date);
    // await loadLargecapDivergence(data.date);
    // await loadFmcgSignals(data.date);
    // await loadTourismSignals(data.date);
    // await loadChemicalSignals(data.date);
    // await loadAlcoholSignals(data.date);
    await loadLunarForecast(data.date);
    // await loadBullionVedha(data.date, true);  // weekly view
    // await loadTransitVedha(data.date, true);  // weekly view
    const kpInst = $("kp-intraday-instrument") ? $("kp-intraday-instrument").value : "NIFTY";
    const kpFmt = $("kp-intraday-format") ? $("kp-intraday-format").value : "html";
    loadKPIntradayReport(data.date, kpInst, kpFmt);
    renderExecutiveActionBar(data);
    renderVerdict(data);
    renderMarketAlert(data);
    renderYogaAlerts(data);
    renderGrid(data);
    renderPlanets(data);
    renderPoints(data);
    renderVedhas(data);
    renderSectors(data);
    renderPlanetSectors(data);
    renderReading(data);
    renderLegend(data);
  } catch (e) {
    console.error(e);
    showPredictionError();
  } finally {
    btn.disabled = false;
  }
}

// Week navigation helpers
function shiftWeek(dateInputId, days) {
  const input = $(dateInputId);
  if (!input.value) return;
  const d = new Date(input.value + "T00:00:00");
  d.setDate(d.getDate() + days);
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  input.value = `${d.getFullYear()}-${month}-${day}`;
  updateWeekRange(dateInputId, dateInputId.replace("date", "range"));
  loadWeeklyCommentary(input.value);
}

function updateWeekRange(dateInputId, rangeElementId) {
  const input = $(dateInputId);
  const rangeEl = $(rangeElementId);
  if (!input.value || !rangeEl) return;
  const d = new Date(input.value + "T00:00:00");
  const dayOfWeek = d.getDay();
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const monday = new Date(d);
  monday.setDate(d.getDate() + mondayOffset);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmt = (dt) => `${String(dt.getMonth() + 1).padStart(2, "0")}/${String(dt.getDate()).padStart(2, "0")}`;
  rangeEl.textContent = `${fmt(monday)} - ${fmt(sunday)} ${monday.getFullYear()}`;
}

// Generic date calendar dropdown (for single date selection)
function initDateCalendar(inputId, dropdownId, onSelect) {
  const input = $(inputId);
  const dropdown = $(dropdownId);
  if (!input || !dropdown) return;

  function buildCalendar() {
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth();
    const currentDate = today.getDate();

    // Build ~730 days (2 years back, 2 years forward) - individual days
    const days = [];
    const startDate = new Date(currentYear - 2, 0, 1);
    const endDate = new Date(currentYear + 2, 11, 31);

    let d = new Date(startDate);
    while (d <= endDate) {
      const dayStr = d.toISOString().split("T")[0];
      const label = d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
      const isToday = (d.getDate() === today.getDate() && d.getMonth() === today.getMonth() && d.getFullYear() === today.getFullYear());
      days.push({ dayStr, label, isToday, date: new Date(d) });
      d.setDate(d.getDate() + 1);
    }

    dropdown.innerHTML = "";
    days.forEach(day => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "week-calendar-item" + (day.isToday ? " current" : "");
      btn.dataset.date = day.dayStr;
      btn.textContent = day.label;
      btn.addEventListener("click", () => {
        input.value = day.dayStr;
        dropdown.classList.add("hidden");
        if (onSelect) onSelect(day.dayStr);
      });
      dropdown.appendChild(btn);
    });
  }

  // Toggle dropdown on input click
  input.addEventListener("click", (e) => {
    e.stopPropagation();
    if (dropdown.classList.contains("hidden")) {
      buildCalendar();
      dropdown.classList.remove("hidden");
    } else {
      dropdown.classList.add("hidden");
    }
  });

  // Close on outside click
  document.addEventListener("click", (e) => {
    if (!dropdown.contains(e.target) && e.target !== input) {
      dropdown.classList.add("hidden");
    }
  });

  // Close on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") dropdown.classList.add("hidden");
  });
}

// Weekly calendar dropdown
function initWeekCalendar() {
  const input = $("weekly-commentary-date");
  const dropdown = $("weekly-commentary-calendar");
  if (!input || !dropdown) return;

  function buildCalendar() {
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth();
    const currentDate = today.getDate();

    // Build ~52 weeks (1 year back, 1 year forward)
    const weeks = [];
    const startDate = new Date(currentYear - 1, 0, 1);
    const endDate = new Date(currentYear + 1, 11, 31);

    // Find first Monday of start year
    let d = new Date(startDate);
    while (d.getDay() !== 1) d.setDate(d.getDate() + 1);

    while (d <= endDate) {
      const monday = new Date(d);
      const sunday = new Date(d);
      sunday.setDate(d.getDate() + 6);
      const weekStart = monday.toISOString().split("T")[0];
      const label = `${String(monday.getMonth() + 1).padStart(2, "0")}/${String(monday.getDate()).padStart(2, "0")} - ${String(sunday.getMonth() + 1).padStart(2, "0")}/${String(sunday.getDate()).padStart(2, "0")} ${monday.getFullYear()}`;
      const isCurrent = (monday <= today && sunday >= today);
      weeks.push({ weekStart, label, isCurrent, monday, sunday });
      d.setDate(d.getDate() + 7);
    }

    dropdown.innerHTML = "";
    weeks.forEach(w => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "week-calendar-item" + (w.isCurrent ? " current" : "");
      btn.dataset.date = w.weekStart;
      btn.textContent = w.label;
      btn.addEventListener("click", () => {
        input.value = w.weekStart;
        updateWeekRange("weekly-commentary-date", "weekly-commentary-range");
        dropdown.classList.add("hidden");
        loadWeeklyCommentary(w.weekStart);
      });
      dropdown.appendChild(btn);
    });
  }

  // Toggle dropdown on input click
  input.addEventListener("click", (e) => {
    e.stopPropagation();
    if (dropdown.classList.contains("hidden")) {
      buildCalendar();
      dropdown.classList.remove("hidden");
    } else {
      dropdown.classList.add("hidden");
    }
  });

  // Close on outside click
  document.addEventListener("click", (e) => {
    if (!dropdown.contains(e.target) && e.target !== input) {
      dropdown.classList.add("hidden");
    }
  });

  // Close on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") dropdown.classList.add("hidden");
  });
}

if ($("run")) $("run").addEventListener("click", run);
if ($("prediction-retry")) $("prediction-retry").addEventListener("click", run);
const dateInput = $("date");
if (dateInput) {
  dateInput.addEventListener("click", () => {
    if (typeof dateInput.showPicker === "function") dateInput.showPicker();
  });
}

// Weekly commentary generate button
if ($("weekly-commentary-run")) {
  $("weekly-commentary-run").addEventListener("click", () => {
    const date = $("weekly-commentary-date") ? $("weekly-commentary-date").value : "";
    if (date) loadWeeklyCommentary(date);
  });
}

// Weekly commentary week navigation
if ($("weekly-commentary-prev")) {
  $("weekly-commentary-prev").addEventListener("click", () => shiftWeek("weekly-commentary-date", -7));
}
if ($("weekly-commentary-next")) {
  $("weekly-commentary-next").addEventListener("click", () => shiftWeek("weekly-commentary-date", 7));
}
if ($("weekly-commentary-today")) {
  $("weekly-commentary-today").addEventListener("click", () => {
    const today = new Date();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    const wcDate = $("weekly-commentary-date");
    if (wcDate) {
      wcDate.value = `${today.getFullYear()}-${month}-${day}`;
      updateWeekRange("weekly-commentary-date", "weekly-commentary-range");
      loadWeeklyCommentary(wcDate.value);
    }
  });
}

// Update week range display on date change
if ($("weekly-commentary-date")) {
  $("weekly-commentary-date").addEventListener("change", () => {
    updateWeekRange("weekly-commentary-date", "weekly-commentary-range");
  });
}

// Bullion vedha generate button
if ($("bullion-vedha-run")) {
  $("bullion-vedha-run").addEventListener("click", () => {
    const date = $("bullion-vedha-date") ? $("bullion-vedha-date").value : "";
    const weekly = $("bullion-vedha-week") ? $("bullion-vedha-week").checked : false;
    if (date) loadBullionVedha(date, weekly);
  });
}

// Transit vedha generate button
if ($("transit-vedha-run")) {
  $("transit-vedha-run").addEventListener("click", () => {
    const date = $("transit-vedha-date") ? $("transit-vedha-date").value : "";
    const weekly = $("transit-vedha-week") ? $("transit-vedha-week").checked : false;
    if (date) loadTransitVedha(date, weekly);
  });
}

// Large-cap divergence generate button
if ($("largecap-divergence-run")) {
  $("largecap-divergence-run").addEventListener("click", () => {
    const date = $("largecap-divergence-date") ? $("largecap-divergence-date").value : "";
    if (date) loadLargecapDivergence(date);
  });
}

// FMCG signals generate button
if ($("fmcg-signals-run")) {
  $("fmcg-signals-run").addEventListener("click", () => {
    const date = $("fmcg-signals-date") ? $("fmcg-signals-date").value : "";
    const price = $("fmcg-signals-price") ? $("fmcg-signals-price").value : null;
    if (date) loadFmcgSignals(date, price ? parseFloat(price) : null);
  });
}

// Tourism signals generate button
if ($("tourism-signals-run")) {
  $("tourism-signals-run").addEventListener("click", () => {
    const date = $("tourism-signals-date") ? $("tourism-signals-date").value : "";
    const price = $("tourism-signals-price") ? $("tourism-signals-price").value : null;
    if (date) loadTourismSignals(date, price ? parseFloat(price) : null);
  });
}

// Chemical signals generate button
if ($("chemical-signals-run")) {
  $("chemical-signals-run").addEventListener("click", () => {
    const date = $("chemical-signals-date") ? $("chemical-signals-date").value : "";
    const price = $("chemical-signals-price") ? $("chemical-signals-price").value : null;
    if (date) loadChemicalSignals(date, price ? parseFloat(price) : null);
  });
}

// Alcohol signals generate button
if ($("alcohol-signals-run")) {
  $("alcohol-signals-run").addEventListener("click", () => {
    const date = $("alcohol-signals-date") ? $("alcohol-signals-date").value : "";
    const price = $("alcohol-signals-price") ? $("alcohol-signals-price").value : null;
    if (date) loadAlcoholSignals(date, price ? parseFloat(price) : null);
  });
}

// Lunar forecast run button
if ($("lunar-forecast-run")) {
  $("lunar-forecast-run").addEventListener("click", () => {
    const date = $("lunar-forecast-date") ? $("lunar-forecast-date").value : "";
    if (date) loadLunarForecast(date);
  });
}


// KP Intraday Trend Change Prediction
function renderKPIntradayReport(data) {
  const content = $("kp-intraday-content");
  content.className = "kp-intraday-content";
  content.innerHTML = "";

  if (data.error) {
    content.innerHTML = `<div class="kp-error" style="color:var(--red);padding:20px;">Error: ${data.error}</div>`;
    $("kp-intraday").classList.remove("hidden");
    return;
  }

  const report = document.createElement("div");
  report.className = "kp-report";

  // TITLE BLOCK
  const header = document.createElement("div");
  header.className = "kp-title-block";
  header.innerHTML = `
    <h1 class="kp-title">KP INTRADAY TREND CHANGE PREDICTION REPORT</h1>
    <div class="kp-meta-line"><strong>Trading Day:</strong> ${data.trading_day}</div>
    <div class="kp-meta-line"><strong>${data.instrument}</strong> &bull; ${data.market} &bull; ${data.ayanamsa}</div>
    <div class="kp-brand">${data.brand || 'Astro Quant Research Initiative | Trading Bramha Consulting'}</div>
  `;
  report.appendChild(header);

  const divider = document.createElement("hr");
  divider.className = "kp-divider";
  report.appendChild(divider);

  // SECTION 1 — DAY CHART SIGNATURE
  if (data.day_signature) {
    const ds = data.day_signature;
    const sec1 = document.createElement("section");
    sec1.className = "kp-section";
    sec1.innerHTML = `<h2>SECTION 1 &mdash; DAY CHART SIGNATURE</h2>`;

    const sigTable = document.createElement("table");
    sigTable.className = "kp-table kp-signature-table";
    sigTable.innerHTML = `
      <tr><th>Parameter</th><th>Value</th></tr>
      <tr><td>Day Lord</td><td><strong>${ds.day_lord}</strong></td></tr>
      <tr><td>Moon Sign, Star, Opening Sub</td><td><strong>${ds.moon_sign}, ${ds.moon_star}, ${ds.opening_sublord} sub</strong></td></tr>
      <tr><td>Moon Speed</td><td><strong>${Number(ds.moon_speed).toFixed(4)}&deg;/day</strong></td></tr>
      <tr><td>Day-Level Bias</td><td><strong>${ds.day_bias_label}</strong></td></tr>
      <tr><td>Moon Affliction Gate (Rule A-14)</td><td><strong>${ds.moon_affliction_gate}</strong></td></tr>
    `;
    sec1.appendChild(sigTable);

    if (ds.hora_slots && ds.hora_slots.length) {
      sec1.innerHTML += `<h3>Hora Timeline Table</h3>`;
      const horaTable = document.createElement("table");
      horaTable.className = "kp-table kp-hora-table";
      let horaRows = '<thead><tr><th>Time Range</th><th>Hora Lord</th><th>Base Quality</th><th>Aspects Received</th><th>Interpretation</th></tr></thead><tbody>';
      for (const hs of ds.hora_slots) {
        const baseQ = hs.base_quality || hs.quality;
        const aspRec = hs.aspects_received || 'None';
        const interp = hs.interpretation || hs.aspect_notes || 'Standard hora rhythm';
        horaRows += `<tr><td>${hs.time_range}</td><td><strong>${hs.lord}</strong></td><td class="hora-${baseQ.toLowerCase()}">${baseQ}</td><td>${aspRec}</td><td>${interp}</td></tr>`;
      }
      horaRows += '</tbody>';
      horaTable.innerHTML = horaRows;
      sec1.appendChild(horaTable);
      sec1.innerHTML += '<p class="kp-rule-note"><strong>Rule Note:</strong> Base hora quality is modified by aspects (weight 0.3). Benefic aspects (Jupiter, Venus, Mercury) upgrade quality; malefic aspects (Saturn, Mars, Rahu, Ketu) downgrade it. Do not treat hora as standalone signal.</p>';
    }

    report.appendChild(sec1);
  }

  // SECTION 2 — MASTER REGIME SHIFTS
  const sec2 = document.createElement("section");
  sec2.className = "kp-section";
  sec2.innerHTML = `<h2>SECTION 2 &mdash; MASTER REGIME SHIFTS (Moon Sub-Lord, Rule A-11/A-12)</h2>`;
  if (data.regime_shifts && data.regime_shifts.length) {
    for (const rs of data.regime_shifts) {
      const div = document.createElement("div");
      div.className = "kp-regime-shift";
      div.innerHTML = `
        <div class="regime-time"><strong>${rs.time}</strong></div>
        <div class="regime-detail">
          <span>${rs.planet} sub change: <strong>${rs.old_sublord} &rarr; ${rs.new_sublord}</strong></span> &bull; 
          <span>House-set strength: <strong>${Number(rs.house_set_strength) >= 0 ? '+' : ''}${Number(rs.house_set_strength).toFixed(1)}</strong></span> &bull; 
          <span>Post-shift regime: <strong class="regime-tag ${rs.direction.toLowerCase()}">${rs.regime_label}</strong></span>
        </div>
      `;
      sec2.appendChild(div);
    }
  } else {
    sec2.innerHTML += '<p class="kp-empty">No regime shifts detected for this session.</p>';
  }
  report.appendChild(sec2);

  // SECTION 3 — PREDICTIVE INTRADAY PATH
  const sec3 = document.createElement("section");
  sec3.className = "kp-section";
  sec3.innerHTML = `
    <h2>SECTION 3 &mdash; PREDICTIVE INTRADAY PATH</h2>
    <div class="kp-path-box">
      <p>Orange markers = Tier-1 / regime-shift timestamps. Path is directional shape, not price target. Windows are candidates until price confirms.</p>
    </div>
  `;
  report.appendChild(sec3);

  // SECTION 4 — TREND CHANGE TIMING TABLE
  const sec4 = document.createElement("section");
  sec4.className = "kp-section";
  sec4.innerHTML = `<h2>SECTION 4 &mdash; TREND CHANGE TIMING TABLE</h2>`;
  if (data.trend_changes && data.trend_changes.length) {
    const table = document.createElement("table");
    table.className = "kp-table kp-signals-table";
    let rows = '<thead><tr><th>Time</th><th>Grade</th><th>Direction</th><th>Trigger (Rule A-8/A-11)</th><th>Asc Sub House-Set</th><th>Hora</th></tr></thead><tbody>';
    for (const tc of data.trend_changes) {
      const gradeClass = tc.grade.replace(/\s+/g, '').replace('-', '').toLowerCase();
      rows += `<tr class="grade-${gradeClass}"><td>${tc.time}</td><td><span class="badge ${gradeClass}">${tc.grade}</span></td><td class="dir-${tc.direction.toLowerCase()}">${tc.direction}</td><td>${tc.trigger}</td><td>${tc.asc_sub_house_set}</td><td>${tc.hora_lord}</td></tr>`;
    }
    rows += '</tbody>';
    table.innerHTML = rows;
    sec4.appendChild(table);

    // Counter-regime pure-set alarms
    const counterRegime = data.trend_changes.filter(tc => tc.grade === "COUNTER-REGIME");
    sec4.innerHTML += `<h3>Counter-Regime Pure-Set Alarms (v12)</h3>`;
    sec4.innerHTML += '<div class="kp-counter-regime-box"><p><strong>Counter-regime pure-set alarms (v12):</strong> The following pure-set alarms fire against the active Moon sub-lord regime. Treat as early reversal warnings &mdash; trade ONLY on price confirmation with reduced position size (max 50% normal).</p>';
    if (counterRegime.length) {
      for (const cr of counterRegime) {
        sec4.innerHTML += `<div class="kp-counter-regime">${cr.time} | ${cr.grade} | ${cr.direction} | ${cr.trigger} | ${cr.asc_sub_house_set} | ${cr.hora_lord}</div>`;
      }
    } else {
      sec4.innerHTML += '<p class="kp-empty">No counter-regime pure-set alarms detected for this session.</p>';
    }
    sec4.innerHTML += '</div>';
  } else {
    sec4.innerHTML += '<p class="kp-empty">No trend change signals detected.</p>';
  }
  report.appendChild(sec4);

  // SECTION 5 — INTRADAY TRADING VIEW
  const sec5 = document.createElement("section");
  sec5.className = "kp-section";
  sec5.innerHTML = `<h2>SECTION 5 &mdash; INTRADAY TRADING VIEW</h2>`;

  let windowsGrid = '<div class="kp-windows-grid">';
  if (data.strongest_bullish) {
    windowsGrid += `<div class="kp-window bullish"><span class="window-title">Strongest Bullish Candidate Window</span><strong class="window-time">${data.strongest_bullish.time_range}</strong><span class="window-score">Peak Score: +${Number(data.strongest_bullish.score).toFixed(2)}</span></div>`;
  } else {
    windowsGrid += `<div class="kp-window neutral"><span class="window-title">Strongest Bullish Candidate Window</span><strong>None active</strong></div>`;
  }
  if (data.strongest_bearish) {
    windowsGrid += `<div class="kp-window bearish"><span class="window-title">Strongest Bearish Candidate Window</span><strong class="window-time">${data.strongest_bearish.time_range}</strong><span class="window-score">Deepest Score: -${Number(data.strongest_bearish.score).toFixed(2)}</span></div>`;
  } else {
    windowsGrid += `<div class="kp-window neutral"><span class="window-title">Strongest Bearish Candidate Window</span><strong>None active</strong></div>`;
  }
  windowsGrid += '</div>';
  sec5.innerHTML += windowsGrid;

  if (data.exhaustion_warnings && data.exhaustion_warnings.length) {
    sec5.innerHTML += '<div class="kp-warning-box"><h4>Score Exhaustion Warnings</h4>';
    for (const w of data.exhaustion_warnings) {
      sec5.innerHTML += `<div class="kp-warning">⚠ ${w}</div>`;
    }
    sec5.innerHTML += '</div>';
  }

  sec5.innerHTML += `
    <h3>Intraday Trading Playbook</h3>
    <ol class="kp-playbook">
      <li><strong>Trade only Tier-1 flips</strong> in the direction of the active Moon sub-lord regime.</li>
      <li><strong>Longs valid</strong> when regime is "buy-on-dip" and a Tier-1 bullish flip occurs. Enter on pullback to VWAP/CPR support with 5-candle confirmation (&ge;15 pts).</li>
      <li><strong>Shorts valid</strong> when regime is "sell-on-rise" and a Tier-1 bearish flip occurs. Enter on rally to VWAP/CPR resistance with 5-candle confirmation (&ge;15 pts).</li>
      <li><strong>Reversal candidate exception (v14):</strong> Counter-regime pure-set alarms may be traded only with price confirmation (first 5 five-minute candles &ge; 15 points in new direction, plus VWAP reclaim/loss or CPR break). Position size reduced to 50%.</li>
      <li><strong>Max 3 Tier-1 trades per session (Rule D-3).</strong> No adding to losers.</li>
    </ol>
    <h3>Bank Nifty Calibration Notes</h3>
    <div class="kp-calibration-notes">
      <p>Timing tolerance: &plusmn;3&ndash;5 minutes vs NIFTY. Response strength: 1.2&ndash;1.5&times; NIFTY magnitude on Tier-1 flips. Rahu-sub windows: wider SL (2&times; ATR), avoid first 15 min of Rahu sub-lord. Moon sub-lord transitions in Rahu star: expect false starts, wait for candle close confirmation.</p>
    </div>
  `;
  report.appendChild(sec5);

  // SECTION 6 — DISCLAIMER
  const sec6 = document.createElement("section");
  sec6.className = "kp-section kp-disclaimer";
  sec6.innerHTML = `
    <h2>SECTION 6 &mdash; DISCLAIMER</h2>
    <p><strong>Educational research output combining KP astrology with systematic trading discipline.</strong> It does not constitute investment advice, solicitation, or recommendation to buy or sell any securities or derivatives. Derivatives trading involves substantial risk of loss and is not suitable for all investors. Validate all signals with independent backtesting, position sizing, and risk management before live deployment. The author and publisher assume no liability for trading decisions based on this report.</p>
  `;
  report.appendChild(sec6);

  content.appendChild(report);  content.appendChild(report);
  // Render KP Intraday Price Chart with lightweight-charts.js
  renderKPIntradayPriceChart(data);
  $("kp-intraday").classList.remove("hidden");
}

async function loadKPIntradayReport(date, instrument, format) {
  const content = $("kp-intraday-content");
  if (content) {
    content.className = "kp-intraday-content panel-loading";
    content.textContent = `Generating KP Intraday Trend Change Prediction Report for ${date} (${instrument})...`;
  }
  try {
    const url = `/api/kp_intraday_report?date=${encodeURIComponent(date)}&instrument=${encodeURIComponent(instrument)}&format=${encodeURIComponent(format)}`;
    const response = await fetchWithTimeout(url);
    if (format === 'html') {
      const html = await response.text();
      $("kp-intraday-content").innerHTML = html;
    } else {
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      renderKPIntradayReport(data);
    }
  } catch (e) {
    console.error("KP Intraday report failed:", e);
    if (content) {
      content.className = "kp-intraday-content panel-error";
      content.textContent = "KP Intraday report is unavailable. Try running the report again.";
    }
  }
}

async function generateKPSampleData(date, days) {
  try {
    const response = await fetchWithTimeout("/api/kp_intraday_sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date, days })
    });
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    // Auto-load the report
    loadKPIntradayReport(date, $("kp-intraday-instrument").value, $("kp-intraday-format").value);
  } catch (e) {
    console.error("KP sample generation failed:", e);
    const content = $("kp-intraday-content");
    if (content) {
      content.className = "kp-intraday-content panel-error";
      content.textContent = "Sample data could not be generated. Try again.";
    }
  }
}

// Add event listeners
if ($("kp-intraday-run")) {
  $("kp-intraday-run").addEventListener("click", () => {
    const date = ($("kp-intraday-date") && $("kp-intraday-date").value) || ($("date") && $("date").value);
    const instrument = $("kp-intraday-instrument") ? $("kp-intraday-instrument").value : "NIFTY";
    const format = $("kp-intraday-format") ? $("kp-intraday-format").value : "html";
    if (date) loadKPIntradayReport(date, instrument, format);
  });
}

if ($("kp-intraday-sample")) {
  $("kp-intraday-sample").addEventListener("click", () => {
    const date = ($("kp-intraday-date") && $("kp-intraday-date").value) || ($("date") && $("date").value);
    if (date) generateKPSampleData(date, 31);
  });
}

if ($("kp-intraday-path")) {
  $("kp-intraday-path").addEventListener("click", async () => {
    const date = ($("kp-intraday-date") && $("kp-intraday-date").value) || ($("date") && $("date").value);
    const instrument = $("kp-intraday-instrument") ? $("kp-intraday-instrument").value : "NIFTY";
    if (!date) { alert("Select a date"); return; }
    const res = await fetch(`/api/engine/intraday_path?date=${encodeURIComponent(date)}&instrument=${encodeURIComponent(instrument)}`);
    const data = await res.json();
    const panel = $("kp-intraday-path-chart");
    if (panel) panel.style.display = "";
    const pre = $("kp-path-data");
    if (pre) {
      pre.textContent = JSON.stringify(data.series, null, 2);
      pre.style.display = "none"; // hide raw JSON by default, keep for debug
    }
    const container = $("kp-path-container");
    if (container) {
      // Render Chart.js line chart
      if (!window.kpPathChart) {
        const canvas = document.createElement("canvas");
        canvas.id = "kp-path-canvas";
        container.innerHTML = "";
        container.appendChild(canvas);
        window.kpPathChart = new Chart(canvas.getContext("2d"), {
          type: "line",
          data: { labels: [], datasets: [] },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { 
              x: { 
                title: { display: true, text: "Time" },
                ticks: { maxRotation: 90, minRotation: 90 }
              }, 
              y: { title: { display: true, text: "Cumulative Score" } } 
            },
            plugins: { legend: { display: true } }
          }
        });
      }
      const labels = data.series.map(s => `${s.time}\n${s.hora_lord || ''}`);
      const cum = data.series.map(s => s.cumulative);
      const dlPoints = data.series.map((s,i) => s.dl_hora ? cum[i] : null);
      const dahanPoints = data.series.map((s,i) => s.dahan ? cum[i] : null);
      const chandPoints = data.series.map((s,i) => s.chand_vat ? cum[i] : null);
      // Trend change / reversal candidate markers
      const trendMarkers = labels.map(() => null);
      const trendLabels = [];
      if (Array.isArray(data.trend_changes)) {
        const timeToIndex = new Map(labels.map((t,i)=>[t,i]));
        for (const tc of data.trend_changes) {
          const idx = timeToIndex.get(tc.time);
          if (idx !== undefined) {
            trendMarkers[idx] = cum[idx];
            trendLabels.push(`${tc.time} ${tc.direction} ${tc.grade}`);
          }
        }
      }
      // Regime shift markers
      const regimeMarkers = labels.map(() => null);
      if (Array.isArray(data.regime_shifts)) {
        const timeToIndex = new Map(labels.map((t,i)=>[t,i]));
        for (const rs of data.regime_shifts) {
          const idx = timeToIndex.get(rs.time);
          if (idx !== undefined) {
            regimeMarkers[idx] = cum[idx];
          }
        }
      }
      window.kpPathChart.data.labels = labels;
      window.kpPathChart.data.datasets = [
        { label: "Cumulative KP", data: cum, borderColor: "#0d6efd", backgroundColor: "transparent", borderWidth: 2, tension: 0.2 },
        { label: "DL-hora", data: dlPoints, borderColor: "#e6b800", backgroundColor: "transparent", borderWidth: 2, borderDash: [4,4], pointRadius: 4 },
        { label: "Dahan", data: dahanPoints, borderColor: "#6c757d", backgroundColor: "transparent", borderWidth: 2, borderDash: [2,6], pointRadius: 3 },
        { label: "Chand/Vat", data: chandPoints, borderColor: "#198754", backgroundColor: "transparent", borderWidth: 2, pointRadius: 4 },
        { label: "Trend Change", data: trendMarkers, borderColor: "#ff6b6b", backgroundColor: "#ff6b6b", borderWidth: 0, pointRadius: 6, pointStyle: 'triangle', showLine: false },
        { label: "Regime Shift", data: regimeMarkers, borderColor: "#ffaa00", backgroundColor: "#ffaa00", borderWidth: 0, pointRadius: 8, pointStyle: 'rectRot', showLine: false }
      ];
      window.kpPathChart.update();

      // Show summary info
      let infoEl = $("kp-path-info");
      if (!infoEl) {
        infoEl = document.createElement("div");
        infoEl.id = "kp-path-info";
        infoEl.style.marginTop = "10px";
        infoEl.style.fontSize = "12px";
        infoEl.style.color = "#cbd5e1";
        container.appendChild(infoEl);
      }
      const warnings = data.exhaustion_warnings || [];
      const sb = data.strongest_bullish;
      const sbr = data.strongest_bearish;
      let html = [];
      if (sb) html.push(`Strongest Bullish: ${sb.start}-${sb.end} score ${sb.score.toFixed(2)}`);
      if (sbr) html.push(`Strongest Bearish: ${sbr.start}-${sbr.end} score ${sbr.score.toFixed(2)}`);
      if (warnings.length) html.push(`Warnings: ${warnings.join(" | ")}`);
      infoEl.innerHTML = html.join("<br>");
    }
    // NIFTY intraday chart handling
    const wrap = $("kp-nifty-intraday-wrap");
    const disabledEl = $("kp-nifty-intraday-disabled");
    const frameEl = $("kp-nifty-intraday-frame");
    if (wrap) wrap.style.display = "";
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year:'numeric', month:'2-digit', day:'2-digit' }).format(new Date());
    const isFuture = date > today;
    if (isFuture) {
      if (disabledEl) disabledEl.style.display = "block";
      if (frameEl) {
        frameEl.style.display = "none";
        frameEl.innerHTML = "";
      }
    } else {
      if (disabledEl) disabledEl.style.display = "none";
      if (frameEl) {
        frameEl.style.display = "block";
        // Render TradingView link / embed. iFrames are often blocked by TradingView X-Frame-Options,
        // so we render a clickable link that opens TradingView in the native page.
        if (!frameEl.querySelector("a.kp-tv-link")) {
          frameEl.innerHTML = "";
          const linkWrap = document.createElement("div");
          linkWrap.style.textAlign = "center";
          linkWrap.style.padding = "40px 10px";
          const a = document.createElement("a");
          a.className = "kp-tv-link";
          a.href = `https://www.tradingview.com/chart/?symbol=NSE%3ANIFTY&interval=3&theme=dark&timezone=Asia%2FKolkata`;
          a.target = "_self";
          a.rel = "noopener";
          a.style.display = "inline-block";
          a.style.padding = "10px 16px";
          a.style.background = "#0d6efd";
          a.style.color = "#fff";
          a.style.borderRadius = "6px";
          a.style.textDecoration = "none";
          a.textContent = "Open NIFTY 3-min on TradingView";
          linkWrap.appendChild(a);
          frameEl.appendChild(linkWrap);
        }
        // Show a note with date
        let note = frameEl.parentNode.querySelector("#kp-nifty-date-note");
        if (!note) {
          note = document.createElement("div");
          note.id = "kp-nifty-date-note";
          note.style.fontSize = "12px";
          note.style.color = "#94a3b8";
          note.style.marginBottom = "6px";
          frameEl.parentNode.insertBefore(note, frameEl);
        }
        note.textContent = `Intraday chart for ${date}. Open TradingView for 3-min candles.`;
      }
    }
  });
}

// Set default date for KP Intraday
const kpDate = $("kp-intraday-date");
if (kpDate && !kpDate.value) {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  kpDate.value = `${now.getFullYear()}-${month}-${day}`;
}

function initSectorFilters() {
  const pills = document.querySelectorAll(".filter-pills .pill");
  const sectorSections = document.querySelectorAll("#tab-sectors .panel[data-sector-category]");
  if (!pills.length) return;

  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      pills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      const filter = pill.getAttribute("data-filter");

      sectorSections.forEach((sec) => {
        const cat = sec.getAttribute("data-sector-category");
        if (filter === "all" || cat === "all" || cat === filter) {
          sec.style.display = "";
        } else {
          sec.style.display = "none";
        }
      });
    });
  });
}

function initWorkspaceTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  const panes = document.querySelectorAll(".tab-pane");

  function switchTab(targetId) {
    tabs.forEach((t) => {
      const isTarget = t.getAttribute("data-tab") === targetId;
      t.classList.toggle("active", isTarget);
      t.setAttribute("aria-selected", isTarget ? "true" : "false");
    });
    panes.forEach((p) => {
      p.classList.toggle("active", p.id === targetId);
    });

    // When switching to chart tab, trigger window resize so chart recalculates dimension
    if (targetId === "tab-chart") {
      setTimeout(() => {
        window.dispatchEvent(new Event("resize"));
        setTimeout(() => { window.dispatchEvent(new Event("resize")); }, 200);
      }, 150);
      // Preload 7-day OHLC cache for backtesting
      fetch(`/api/engine/market/ohlc?symbol=NIFTY&days=7`).then(r=>r.json()).then(data=>{
        // expose to global for nifty-chart.js fallback
        window._cachedOHLC = data.bars;
        console.log("OHLC cache loaded", data.bars.length, "bars");
      }).catch(()=>{});
    }

    // When switching to KP Intraday tab, auto-load if empty or error
    if (targetId === "tab-kp") {
      const dateEl = $("kp-intraday-date");
      const globalDate = $("date") ? $("date").value : "";
      if (dateEl && globalDate && dateEl.value !== globalDate) {
        dateEl.value = globalDate;
      }
      const targetDate = (dateEl && dateEl.value) || globalDate;
      const content = $("kp-intraday-content");
      if (content && (!content.innerHTML.trim() || content.querySelector(".kp-error"))) {
        const inst = $("kp-intraday-instrument") ? $("kp-intraday-instrument").value : "NIFTY";
        const fmt = $("kp-intraday-format") ? $("kp-intraday-format").value : "html";
        if (targetDate) loadKPIntradayReport(targetDate, inst, fmt);
      }
    }

    // When switching to Daily Balance tab, auto-load if chart is empty
    if (targetId === "tab-balance") {
      const dateEl = $("daily-balance-date");
      const globalDate = $("date") ? $("date").value : "";
      if (dateEl && globalDate && dateEl.value !== globalDate) {
        dateEl.value = globalDate;
      }
      const targetDate = (dateEl && dateEl.value) || globalDate || new Date().toISOString().slice(0, 10);
      if (targetDate && !window.dailyBalanceChart) {
        loadDailyIndicationBalance(targetDate);
      }
    }
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      switchTab(targetId);
      if (history.replaceState) {
        history.replaceState(null, null, "#" + targetId);
      }
    });
  });

  // Handle initial hash if present
  if (window.location.hash) {
    const hash = window.location.hash.replace("#", "");
    if (document.getElementById(hash)) {
      switchTab(hash);
    }
  }
}

// Initialize KP Intraday Chart
function initKPIntradayChart() {
  const chartContainer = document.getElementById('kp-chart-container');
  if (!chartContainer) return;

  // Lightweight Charts setup
  const chart = LightweightCharts.createChart(chartContainer, {
    width: '100%',
    height: '400px',
    layout: {
      background: { type: 'solid', color: '#1e1e1e' },
      textColor: '#d1d4dc',
    },
    grid: {
      vertLines: { color: '#363a4f' },
      horzLines: { color: '#363a4f' },
    },
    crosshair: {
      mode: 'default',
    },
    rightPriceScale: {
      borderVisible: false,
      scaleMargins: { top: 0.1, bottom: 0.1 },
    },
    timeScale: {
      borderVisible: false,
      timeVisible: true,
      secondsVisible: false,
    },
  });

  // Store chart object for updates
  window.kpChart = chart;
}

// ---------------------------------------------------------------
// Daily Indication Balance chart
// ---------------------------------------------------------------
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
  return (d && /\d{4}-\d{2}-\d{2}/.test(d)) ? d : new Date().toISOString().slice(0, 10);
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
  head.innerHTML = `<span class="bhadra-note-title">Reversal-Calendar Cross-Reference</span>
    <span class="bhadra-bt-stats">${overlap.overlap_count} of ${overlap.total_reversal_days} reversal days overlap a Bhadra window</span>`;
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

function renderMonthlyHeatmap(data) {
  const gridEl = $("monthly-heatmap-grid");
  const lunarEl = $("monthly-heatmap-lunar");
  const legendEl = $("monthly-heatmap-legend");
  if (!gridEl) return;
  gridEl.innerHTML = "";
  lunarEl.innerHTML = "";

  const sectors = data.sectors || [];
  const dates = data.dates || [];
  const matrix = data.matrix || {};
  const overall = data.overall_by_day || {};

  // Absolute max for colour scale.
  let maxAbs = 0;
  for (const s of sectors) {
    for (const d of dates) {
      const v = matrix[s] ? matrix[s][d] : 0;
      if (Math.abs(v) > maxAbs) maxAbs = Math.abs(v);
    }
  }
  legendEl.innerHTML =
    '<span class="mh-legend-note">Cell = combined confluence net (green bullish / red bearish).</span>';

  // Build grid: header row (dates) + one row per sector.
  const grid = document.createElement("div");
  grid.className = "mh-table";

  // Header
  const head = document.createElement("div");
  head.className = "mh-row mh-head";
  head.appendChild(mkCell("mh-corner", "Sector ↓ / Day →"));
  for (const d of dates) {
    const day = d.slice(8);
    head.appendChild(mkCell("mh-head-cell", day, d));
  }
  grid.appendChild(head);

  for (const s of sectors) {
    const row = document.createElement("div");
    row.className = "mh-row";
    row.appendChild(mkCell("mh-sector-cell", s, s));
    for (const d of dates) {
      const v = matrix[s] ? (matrix[s][d] == null ? 0 : matrix[s][d]) : 0;
      const cell = document.createElement("div");
      cell.className = "mh-cell";
      cell.style.background = heatColor(v, maxAbs);
      cell.title = `${s} · ${d} · net ${v >= 0 ? "+" : ""}${v.toFixed(2)}`;
      cell.textContent = v >= 0 ? "+" + v.toFixed(1) : v.toFixed(1);
      row.appendChild(cell);
    }
    grid.appendChild(row);
  }
  gridEl.appendChild(grid);

  // Lunar timing strip (per-day markers).
  const strip = document.createElement("div");
  strip.className = "mh-lunar-strip";
  const legend = document.createElement("div");
  legend.style.cssText = "margin-bottom:6px;font-size:11px;color:#94a3b8";
  legend.innerHTML = "🌙 Nakshatra · 🌕 Purnima · 🌑 Amavasya · 11️⃣ Ekadashi · 8️⃣ Ashtami · 14️⃣ Chaturdashi · ⚠ Bhadra";
  lunarEl.appendChild(legend);
  const markersByDay = {};
  for (const m of (data.lunar_markers || [])) {
    (markersByDay[m.date] = markersByDay[m.date] || []).push(m);
  }
  const bhadra = data.bhadra || {};
  const head2 = document.createElement("div");
  head2.className = "mh-row mh-head";
  head2.appendChild(mkCell("mh-corner", "Lunar timing"));
  function symbolizeLunar(markers) {
    const out = [];
    for (const e of markers) {
      const t = e.type;
      const l = e.label;
      if (l === "MOON NAKSHATRA") {
        const name = t.replace("Moon:", "moon ").trim();
        out.push({txt: `🌙 ${name}`, detail: `Moon Nakshatra: ${name}`});
      } else if (l === "FULL MOON") {
        out.push({txt: "🌕 Purnima", detail: "Purnima - Full Moon"});
      } else if (l === "NEW MOON") {
        out.push({txt: "🌑 Amavasya", detail: "Amavasya - New Moon"});
      } else if (l === "FULL MOON WINDOW") {
        out.push({txt: "🌕 Purnima-window", detail: "Full Moon window"});
      } else if (l === "NEW MOON WINDOW") {
        out.push({txt: "🌑 Amavasya-window", detail: "New Moon window"});
      } else if (l === "EKADASHI") {
        out.push({txt: "11️⃣ Ekadashi", detail: "Ekadashi"});
      } else if (l === "ASHTAMI") {
        out.push({txt: "8️⃣ Ashtami", detail: "Ashtami"});
      } else if (l === "CHATURDASHI") {
        out.push({txt: "14️⃣ Chaturdashi", detail: "Chaturdashi"});
      } else {
        out.push({txt: t, detail: `${t} - ${l}`});
      }
    }
    return out;
  }
  const detailPanel = document.createElement("div");
  detailPanel.id = "mh-lunar-detail";
  detailPanel.style.cssText = "margin-top:8px;padding:8px;background:#0b1220;border:1px solid #1e293b;border-radius:8px;font-size:12px;color:#c7d2fe;white-space:pre-wrap";
  lunarEl.appendChild(detailPanel);
  for (const d of dates) {
    const evs = markersByDay[d] || [];
    const syms = symbolizeLunar(evs);
    const bh = bhadra[d] ? [{txt: "⚠ Bhadra", detail: "Bhadra/Vishti muhurt active"}] : [];
    const combined = [...syms, ...bh];
    const text = combined.map(x=>x.txt).join(" · ") || "—";
    const tooltip = combined.map(x=>`• ${x.detail}`).join("\n") + `\nDate: ${d}`;
    const cell = document.createElement("div");
    cell.className = "mh-lunar-cell";
    cell.textContent = text;
    cell.title = tooltip;
    cell.style.cursor = "pointer";
    cell.addEventListener("click", ()=>{
      let html = `Lunar timing for ${d}\n`;
      if (bhadra[d]) {
        html += "⚠ Bhadra windows:\n";
        for (const w of bhadra[d]) {
          html += `  ${w.begin} - ${w.end}\n`;
        }
      }
      html += combined.map(x=>`• ${x.detail}`).join("\n");
      detailPanel.textContent = html;
    });
    head2.appendChild(cell);
  }
  strip.appendChild(head2);
  lunarEl.appendChild(strip);
}

function mkCell(cls, text, title) {
  const el = document.createElement("div");
  el.className = cls;
  el.textContent = text;
  if (title) el.title = title;
  return el;
}

function initResearchLab() {
  const run = $("research-run");
  const status = $("research-status");
  const results = $("research-results");
  if (!run || !status || !results) return;

  const end = $("research-end");
  const start = $("research-start");
  const today = new Date();
  const iso = today.toISOString().slice(0, 10);
  const tenYearsAgo = new Date(today);
  tenYearsAgo.setFullYear(today.getFullYear() - 10);
  if (end && !end.value) end.value = iso;
  if (start && !start.value) start.value = tenYearsAgo.toISOString().slice(0, 10);

  const formatPct = (value) => `${Number(value || 0).toFixed(2)}%`;
  run.addEventListener("click", async () => {
    if (!start.value || !end.value || start.value >= end.value) {
      status.textContent = "Choose a valid start and end date.";
      status.className = "nifty-chart-status error";
      return;
    }
    run.disabled = true;
    status.textContent = "Running event study against market history...";
    status.className = "nifty-chart-status";
    results.textContent = "";
    try {
      const params = new URLSearchParams({
        ticker: $("research-ticker").value,
        event: $("research-event").value,
        horizon: $("research-horizon").value,
        start: start.value,
        end: end.value,
        cost_bps: $("research-cost-bps").value,
      });
      const response = await fetch(`/api/research/event-study?${params}`);
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || "Study unavailable");
      const metrics = [
        [data.sample_size, "Event samples"],
        [formatPct(data.event_mean_return_pct), "Event mean return"],
        [formatPct(data.event_median_return_pct), "Event median return"],
        [formatPct(data.baseline_mean_return_pct), "Baseline mean return"],
        [formatPct(data.event_win_rate_pct), "Event win rate"],
        [formatPct(data.event_stddev_pct), "Event standard deviation"],
        [formatPct(data.maximum_adverse_excursion_pct), "Worst MAE"],
      ];
      results.innerHTML = `<div class="research-metrics">${metrics.map(([value, label]) =>
        `<div class="research-metric"><strong>${value}</strong><span>${label}</span></div>`).join("")}</div>`;
      const edge = data.event_mean_return_pct - data.baseline_mean_return_pct;
      const eventName = $("research-event").selectedOptions[0].textContent;
      results.insertAdjacentHTML("beforeend", `<p class="research-note">${eventName}, ${data.horizon_days}-day forward return. Mean edge versus baseline: <strong>${formatPct(edge)}</strong>. Matched weekday controls: ${data.matched_control_sample_size}. Cost assumption: ${data.cost_bps} bps.</p>`);
      results.insertAdjacentHTML("beforeend", `<p class="research-note">Approximate 95% confidence interval for the event mean: <strong>${formatPct(data.event_ci95_low_pct)} to ${formatPct(data.event_ci95_high_pct)}</strong>. Treat small samples as exploratory.</p>`);
      const curveRows = (data.equity_curve || []).map(point => `<tr><td>${point.date}</td><td>${Number(point.value).toFixed(4)}</td></tr>`).join("");
      results.insertAdjacentHTML("beforeend", `<details class="research-equity"><summary>Event equity curve (${data.equity_curve?.length || 0} observations)</summary><table class="research-folds"><thead><tr><th>Date</th><th>Growth of 1 unit after costs</th></tr></thead><tbody>${curveRows}</tbody></table></details>`);
      status.textContent = `Study complete · generated ${new Date(data.generated_at).toLocaleString()}`;
    } catch (error) {
      console.error("Research study failed:", error);
      status.textContent = "Research study unavailable. Check the market data and try again.";
      status.className = "nifty-chart-status error";
    } finally {
      run.disabled = false;
    }
  });

  const walkRun = $("research-walk-forward-run");
  const walkResults = $("research-walk-forward-results");
  if (walkRun && walkResults) {
    walkRun.addEventListener("click", async () => {
      if (!start.value || !end.value || start.value >= end.value) {
        status.textContent = "Choose a valid start and end date.";
        status.className = "nifty-chart-status error";
        return;
      }
      walkRun.disabled = true;
      status.textContent = "Running rolling out-of-sample validation...";
      status.className = "nifty-chart-status";
      walkResults.textContent = "";
      try {
        const params = new URLSearchParams({
          ticker: $("research-ticker").value,
          event: $("research-event").value,
          horizon: $("research-horizon").value,
          start: start.value,
          end: end.value,
          train_days: $("research-train-days").value,
          test_days: $("research-test-days").value,
          step_days: $("research-step-days").value,
          cost_bps: $("research-cost-bps").value,
        });
        const response = await fetch(`/api/research/walk-forward?${params}`);
        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || "Walk-forward unavailable");
        const aggregate = data.aggregate_test;
        walkResults.innerHTML = `<div class="research-metrics">
          <div class="research-metric"><strong>${data.folds.length}</strong><span>Validation folds</span></div>
          <div class="research-metric"><strong>${aggregate.event_samples ?? "-"}</strong><span>Out-of-sample events</span></div>
          <div class="research-metric"><strong>${formatPct(aggregate.event_mean_return_pct)}</strong><span>OOS event mean</span></div>
          <div class="research-metric"><strong>${formatPct(aggregate.baseline_mean_return_pct)}</strong><span>OOS baseline mean</span></div>
          <div class="research-metric"><strong>${formatPct(aggregate.event_win_rate_pct)}</strong><span>OOS event win rate</span></div>
          <div class="research-metric"><strong>${formatPct(aggregate.event_mean_return_net_pct)}</strong><span>OOS net after costs</span></div>
          <div class="research-metric"><strong>${formatPct(aggregate.accuracy_decay_pct_points)}</strong><span>Mean-return decay</span></div>
        </div>`;
        const rows = data.folds.map((fold) => `<tr>
          <td>${fold.test_start} to ${fold.test_end}</td>
          <td>${fold.train.event_samples}</td>
          <td>${fold.test.event_samples}</td>
          <td>${formatPct(fold.test.event_mean_return_pct)}</td>
          <td>${formatPct(fold.test.baseline_mean_return_pct)}</td>
          <td>${formatPct(fold.test.event_win_rate_pct)}</td>
        </tr>`).join("");
        walkResults.insertAdjacentHTML("beforeend", `<table class="research-folds"><thead><tr><th>Test period</th><th>Train events</th><th>Test events</th><th>Test event mean</th><th>Test baseline mean</th><th>Test win rate</th></tr></thead><tbody>${rows}</tbody></table>`);
        const regimes = Object.entries(aggregate.regime_results || {}).map(([name, value]) => `${name}: ${formatPct(value.event_mean_return_pct)} (${value.event_samples} events)`).join(" · ");
        walkResults.insertAdjacentHTML("beforeend", `<p class="research-note">Test regimes: ${regimes || "no regime samples"}. Cost assumption: ${aggregate.cost_bps} bps.</p>`);
        walkResults.insertAdjacentHTML("beforeend", `<p class="research-note">Only test-period rows contribute to the aggregate. This is out-of-sample descriptive research, not a trading guarantee.</p>`);
        status.textContent = `Walk-forward complete · generated ${new Date(data.generated_at).toLocaleString()}`;
      } catch (error) {
        console.error("Research walk-forward failed:", error);
        status.textContent = "Walk-forward validation unavailable. Check the market data and try again.";
        status.className = "nifty-chart-status error";
      } finally {
        walkRun.disabled = false;
      }
    });
  }

  const aspectRun = $("research-aspect-run");
  const aspectResults = $("research-aspect-results");
  if (aspectRun && aspectResults) {
    aspectRun.addEventListener("click", async () => {
      aspectRun.disabled = true;
      aspectResults.textContent = "Loading planetary aspect events...";
      try {
        const params = new URLSearchParams({ticker: $("research-ticker").value, start: start.value, end: end.value, horizon: $("research-horizon").value});
        const planetA = $("research-planet-a").value.trim();
        const planetB = $("research-planet-b").value.trim();
        const selectedAspect = $("research-aspect").value;
        if (planetA) params.set("planet_a", planetA);
        if (planetB) params.set("planet_b", planetB);
        if (selectedAspect) params.set("aspect", selectedAspect);
        const response = await fetch(`/api/research/aspects?${params}`);
        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || "Aspect grid unavailable");
        const rows = data.groups.map(group => `<tr><td>${group.planet_a}</td><td>${group.planet_b}</td><td>${group.aspect}</td><td>${group.samples}</td><td>${formatPct(group.mean_return_pct)}</td><td>${formatPct(group.win_rate_pct)}</td></tr>`).join("");
        aspectResults.innerHTML = `<table class="research-folds"><thead><tr><th>Planet A</th><th>Planet B</th><th>Aspect</th><th>Samples</th><th>Mean return</th><th>Win rate</th></tr></thead><tbody>${rows || '<tr><td colspan="6">No matching aspects found.</td></tr>'}</tbody></table><p class="research-note">${data.events.length} canonical aspect events found. Research output is experimental.</p>`;
      } catch (error) {
        console.error("Aspect grid failed:", error);
        aspectResults.textContent = "Aspect research unavailable. Check the market data and try again.";
      } finally { aspectRun.disabled = false; }
    });
  }

  const cycleRun = $("research-cycle-run");
  const cycleResults = $("research-cycle-results");
  if (cycleRun && cycleResults) {
    cycleRun.addEventListener("click", async () => {
      cycleRun.disabled = true;
      cycleResults.textContent = "Calculating solar/lunar cycle observations...";
      try {
        const response = await fetch(`/api/research/cycles?start=${encodeURIComponent(start.value)}&end=${encodeURIComponent(end.value)}`);
        const data = await response.json();
        if (!response.ok || data.error) throw new Error(data.error || "Cycle explorer unavailable");
        const latest = data.rows[data.rows.length - 1] || {};
        cycleResults.innerHTML = `<div class="research-metrics"><div class="research-metric"><strong>${data.rows.length}</strong><span>Daily observations</span></div><div class="research-metric"><strong>${latest.sun_sign || "-"}</strong><span>Latest Sun sign</span></div><div class="research-metric"><strong>${latest.moon_sign || "-"}</strong><span>Latest Moon sign</span></div><div class="research-metric"><strong>${latest.phase || "-"}</strong><span>Latest phase</span></div><div class="research-metric"><strong>${latest.bradley_score ?? "-"}</strong><span>Experimental Bradley score</span></div></div><p class="research-note">Bradley output is experimental and separate from the primary SBC score.</p>`;
      } catch (error) {
        console.error("Cycle explorer failed:", error);
        cycleResults.textContent = "Cycle explorer unavailable. Try again.";
      } finally { cycleRun.disabled = false; }
    });
  }

  const exportParams = () => new URLSearchParams({ticker: $("research-ticker").value, event: $("research-event").value, horizon: $("research-horizon").value, start: start.value, end: end.value, cost_bps: $("research-cost-bps").value});
  [["research-export-json", "json"], ["research-export-csv", "csv"], ["research-export-md", "md"]].forEach(([id, format]) => {
    const link = $(id);
    if (link) link.addEventListener("click", () => { link.href = `/api/research/event-study?${exportParams()}&format=${format}`; });
  });
}

// ---------------------------------------------------------------
// Bootstrap: wire up all initialisers once the DOM is ready
// ---------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  // Load and apply persisted settings
  const settings = loadSettings();
  applySettings(settings);

  setTodayAsDefault();
  loadPresets();
  initWeekCalendar();
  initSectorFilters();
  initWorkspaceTabs();
  initKPIntradayChart();
  initMonthlyHeatmap();
  initResearchLab();
  initKeyboardNavigation();
  initThemeToggle();

  // Persist settings on input changes
  ["date", "time", "tz", "anchor", "school"].forEach((id) => {
    const el = $(id);
    if (el) el.addEventListener("change", persistCurrentSettings);
  });

  // Persist tab changes
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const settings = loadSettings();
      settings.activeTab = tab.getAttribute("data-tab");
      saveSettings(settings);
    });
  });

  // Daily Balance / Monthly Projection date picker
  if ($("daily-balance-date") && $("daily-balance-calendar")) {
    initDateCalendar("daily-balance-date", "daily-balance-calendar", (date) => {
      loadDailyIndicationBalance(date);
    });
    // Default to today so the calendar and generation always have a value.
    if (!$("daily-balance-date").value) {
      const now = new Date();
      const m = String(now.getMonth() + 1).padStart(2, "0");
      const d = String(now.getDate()).padStart(2, "0");
      $("daily-balance-date").value = `${now.getFullYear()}-${m}-${d}`;
    }
  }

  // Bhadra calendar
  if ($("bhadra-calendar")) {
    bhadraState.date = bhadraBaseDate();
    loadBhadraCalendar();

    if ($("bhadra-prev")) $("bhadra-prev").addEventListener("click", () => { bhadraState.offset -= 1; loadBhadraCalendar(); });
    if ($("bhadra-next")) $("bhadra-next").addEventListener("click", () => { bhadraState.offset += 1; loadBhadraCalendar(); });
    if ($("bhadra-month")) $("bhadra-month").addEventListener("click", () => { bhadraState.offset = 0; bhadraState.date = bhadraBaseDate(); loadBhadraCalendar(); });
  }

  // Kota Chakra panel
  if ($("kota-load-daily")) {
    const kotaDateSel = $("kota-date");
    if (kotaDateSel && !kotaDateSel.options.length) {
      const today = new Date();
      for (let i = 0; i < 15; i++) {
        const d = new Date(today); d.setDate(today.getDate() - i);
        const opt = document.createElement("option");
        opt.value = d.toISOString().slice(0,10);
        opt.textContent = d.toISOString().slice(0,10);
        kotaDateSel.appendChild(opt);
      }
    }
    $("kota-load-daily").addEventListener("click", async () => {
      const date = kotaDateSel.value;
      const instrument = $("kota-instrument").value;
      const res = await fetch(`/api/engine/kota/daily?date=${encodeURIComponent(date)}&instrument=${instrument}`);
      const data = await res.json();
      renderKotaTable(data.records);
    });
    $("kota-load-weekly").addEventListener("click", async () => {
      const date = kotaDateSel.value;
      const res = await fetch(`/api/engine/kota/weekly?week_start=${encodeURIComponent(date)}`);
      const data = await res.json();
      renderKotaTable(data.records);
    });
    $("kota-load-monthly").addEventListener("click", async () => {
      const date = kotaDateSel.value;
      const month = date.slice(0,7);
      const res = await fetch(`/api/engine/kota/monthly?month=${encodeURIComponent(month)}`);
      const data = await res.json();
      renderKotaTable(data.summary);
    });

    function renderKotaTable(records) {
      const wrap = $("kota-table-wrap");
      if (!wrap) return;
      if (!records || !records.length) {
        wrap.innerHTML = "<div>No data</div>";
        return;
      }
      const table = document.createElement("table");
      table.style.width = "100%";
      table.style.borderCollapse = "collapse";
      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");
      Object.keys(records[0]).forEach(k => {
        const th = document.createElement("th");
        th.textContent = k;
        th.style.border = "1px solid #334155";
        th.style.padding = "4px";
        headerRow.appendChild(th);
      });
      thead.appendChild(headerRow);
      table.appendChild(thead);
      const tbody = document.createElement("tbody");
      records.forEach(r => {
        const tr = document.createElement("tr");
        Object.values(r).forEach(v => {
          const td = document.createElement("td");
          td.textContent = v;
          td.style.border = "1px solid #334155";
          td.style.padding = "4px";
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      wrap.innerHTML = "";
      wrap.appendChild(table);
    }
  }
});
