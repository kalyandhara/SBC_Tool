const CELL = 60;
const TOL = 0.5;
const FETCH_TIMEOUT = 8000;

const $ = (id) => document.getElementById(id);
function esc(s){ return String(s ?? '').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }

// Endpoints that compute on demand and can take a minute or more on a cold cache (B-13).
const HEAVY_TIMEOUT = 120000;
const HEAVY_ENDPOINTS = [
  "/api/prediction", "/api/futurecast", "/api/bullish_futurecast", "/api/sector_vedha",
  "/api/largecap_divergence", "/api/kp_intraday_report", "/api/engine/intraday_path",
  "/api/monthly_heatmap", "/api/weekly_commentary", "/api/lunar_forecast",
  // Called from static/js (formerly inline in index.html, which used plain fetch):
  // yfinance downloads, per-month heatmaps and chart rendering can exceed 8 s.
  "/api/astro/personal", "/api/backtest", "/api/signal/moon", "/api/price",
  "/api/vedha_daily", "/api/daily_confluence", "/api/nakshatra_chart",
  "/api/intraday_projection", "/api/rahu_ketu_trap_calendar",
];

const INFLIGHT = new Map();

// fetchWithTimeout(url), (url, options), (url, timeoutMs) or (url, options, timeoutMs).
async function fetchWithTimeout(url, options = {}, timeoutMs) {
  if (typeof options === "number") {
    timeoutMs = options;
    options = {};
  }
  if (timeoutMs == null) {
    timeoutMs = HEAVY_ENDPOINTS.some((p) => String(url).startsWith(p)) ? HEAVY_TIMEOUT : FETCH_TIMEOUT;
  }
  // B-66: identical GETs already in flight share one network request; each caller
  // gets its own clone of the response.
  const method = (options.method || "GET").toUpperCase();
  const shareable = method === "GET" && !options.body && !options.signal;
  if (shareable && INFLIGHT.has(url)) {
    return (await INFLIGHT.get(url)).clone();
  }
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const pending = fetch(url, { ...options, signal: controller.signal });
    if (shareable) {
      INFLIGHT.set(url, pending);
      pending.finally(() => INFLIGHT.delete(url)).catch(() => {});
      return (await pending).clone();
    }
    return await pending;
  } catch (e) {
    if (e && e.name === "AbortError") {
      throw new Error(`Timed out after ${Math.round(timeoutMs / 1000)} s. The server may still be computing; try again in a moment.`);
    }
    throw e;
  } finally {
    clearTimeout(id);
  }
}

// Local (IST-aware) calendar date, not the UTC date — new Date().toISOString()
// returns the previous day for UTC+5:30 between 00:00 and 05:30.
function localTodayISO(tz) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: tz || 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date());
}

// Format a local Date object as YYYY-MM-DD without converting through UTC
// (toISOString() shifts the date back one day for UTC+ timezones).
function isoDateOf(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
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
  // Reset any badges still stuck on "Loading..." (no successful result yet);
  // previously loaded results are left untouched.
  const resetBadge = (badgeId, placeholder) => {
    const el = $(badgeId);
    if (el && el.textContent.trim() === "Loading...") el.innerHTML = placeholder;
  };
  resetBadge("exec-bias-badge", '<span class="dir-badge dir-neutral">Awaiting prediction</span>');
  resetBadge("exec-risk-badge", '<span class="dir-badge dir-neutral">Awaiting prediction</span>');
  resetBadge("exec-reversal-badge", '<span class="reversal-date">Not calculated</span>');
  resetBadge("exec-leaders", '<span class="exec-empty">No sector ranking yet</span>');
  const subs = [
    ["exec-bias-badge", "exec-bias-sub", "Run a prediction to calculate market bias."],
    ["exec-risk-badge", "exec-risk-sub", "Risk is shown after the forecast is ready."],
    ["exec-reversal-badge", "exec-reversal-sub", "Reversal windows appear after the forecast is ready."],
  ];
  for (const [badgeId, subId, subText] of subs) {
    const badge = $(badgeId);
    if (badge && badge.textContent.includes("Awaiting")) {
      if ($(subId)) $(subId).textContent = subText;
    }
  }
  if ($("exec-data-status")) $("exec-data-status").textContent = "Forecast status: unavailable; last successful result is unchanged.";
}

function cellCenter(row, col) {
  return { x: (col - 1) * CELL + CELL / 2, y: (row - 1) * CELL + CELL / 2 };
}

let state = null;

function setTodayAsDefault() {
  const dateInput = $("date");
  if (!dateInput) return;
  // Always start from today's date in IST, even if a previous session persisted one.
  // (The browser's own clock gives the wrong day outside India, e.g. US evenings.)
  dateInput.value = localTodayISO("Asia/Kolkata");
}

// B-72: one visible "as of" for the pages that follow the header date.
function updateNavAsOf() {
  const el = $("nav-asof");
  const v = $("date") && $("date").value;
  if (!el) return;
  if (!v) { el.textContent = ""; return; }
  const d = new Date(`${v}T12:00:00Z`);
  const label = d.toLocaleDateString("en-GB", { timeZone: "UTC", weekday: "short", day: "numeric", month: "short", year: "numeric" });
  el.innerHTML = `Session <b>${esc(label)}</b>`;
}

// B-61: move the header date to the next NSE session when today is a weekend or holiday,
// so every panel (prediction, KP report, sectors) asks about a real trading day.
async function defaultToNextSession() {
  const dateInput = $("date");
  if (!dateInput || !dateInput.value) return;
  try {
    const r = await fetchWithTimeout(`/api/market/next_session?date=${encodeURIComponent(dateInput.value)}`, 5000);
    const d = await r.json();
    if (r.ok && d.session && d.moved) {
      dateInput.value = d.session;
      dateInput.title = `Next NSE session. ${d.date} is ${d.reason || "not a trading day"}.`;
    }
  } catch (e) {
    console.warn("Could not look up the next session; keeping today's date.", e);
  }
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
    if (alert.start_time && alert.end_time) {
      const timeSpan = document.createElement("span");
      timeSpan.className = "yoga-time";
      timeSpan.textContent = `${alert.start_time} – ${alert.end_time}`;
      item.appendChild(timeSpan);
    }
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
  if (!window.currentLunarClipboardText) {
    showToast("Generate a forecast first");
    return;
  }
  const text = window.currentLunarClipboardText;
  if (!navigator.clipboard) { showToast("Clipboard isn't available in this browser"); return; }
  navigator.clipboard.writeText(text).then(() => {
    showToast("Copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy");
  });
}

function shareLunarForecast() {
  if (!window.currentLunarCard && !window.currentLunarSocialText) {
    showToast("Generate a forecast first");
    return;
  }
  const text = window.currentLunarSocialText || "";
  if (navigator.share) {
    // Rejects when the user cancels the share sheet; nothing to report then.
    navigator.share({ title: "Lunar Cycle Sector Forecast", text: text }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Copied for sharing!");
    }).catch(() => {
      showToast("Couldn't copy (clipboard blocked); select the text instead");
    });
  } else {
    showToast("Sharing isn't available in this browser");
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

  renderVedhaWheel(d);
  renderVedhaSankey(d);
  renderVedhaStrength(d);

  const fold = $("vedha-dashboard");
  if (fold && !fold.dataset.wired) {
    fold.dataset.wired = "1";
    fold.addEventListener("toggle", function () {
      if (fold.open && window.vedhaStrengthChart) window.vedhaStrengthChart.resize();
    });
  }
}

// ---- Combined Dashboard: three vedha layers ----

// 28-star ring in chakra (clockwise) order, starting Krittika on the East side.
const WHEEL_RING = ["Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
  "Pushya", "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni", "Hasta", "Chitra",
  "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "P.Ashadha",
  "U.Ashadha", "Abhijit", "Shravana", "Dhanishta", "Shatabhisha",
  "P.Bhadrapada", "U.Bhadrapada", "Revati", "Ashwini", "Bharani"];
// Corner cells sit in the slot between the two adjacent sides (half-index).
const WHEEL_CORNERS = { "1,9": 27.5, "9,9": 6.5, "9,1": 13.5, "1,1": 20.5 };

function renderVedhaWheel(d) {
  const host = $("vedha-wheel");
  if (!host) return;
  const W = 460, C = W / 2, R_OUT = 178, R_IN = 138, R_MID = (R_IN + R_OUT) / 2;
  const ringIdx = {};
  WHEEL_RING.forEach((n, i) => { ringIdx[n] = i; });

  const cellLabel = {};
  (d.grid || []).forEach((rowArr) => (rowArr || []).forEach((c) => {
    cellLabel[c.row + "," + c.col] = c.label;
  }));

  function pos(slot, r) {
    const a = (slot / 28) * 2 * Math.PI;
    return [C + r * Math.cos(a), C + r * Math.sin(a)];
  }
  function slotOfCell(row, col) {
    const label = cellLabel[row + "," + col];
    if (label && ringIdx[label] !== undefined) return ringIdx[label];
    return WHEEL_CORNERS[row + "," + col];
  }

  let svg = `<svg viewBox="0 0 ${W} ${W}" xmlns="http://www.w3.org/2000/svg">`;
  svg += `<circle cx="${C}" cy="${C}" r="${R_OUT}" fill="none" stroke="rgba(148,163,184,0.35)" stroke-width="1"/>`;
  svg += `<circle cx="${C}" cy="${C}" r="${R_IN}" fill="none" stroke="rgba(148,163,184,0.35)" stroke-width="1"/>`;
  svg += `<circle cx="${C}" cy="${C}" r="${R_MID}" fill="none" stroke="rgba(148,163,184,0.15)" stroke-width="1" stroke-dasharray="2,4"/>`;

  // Ring ticks (28 stars + 4 corner slots)
  for (let i = 0; i < 28; i++) {
    const [x1, y1] = pos(i, R_IN), [x2, y2] = pos(i, R_OUT);
    svg += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="rgba(148,163,184,0.35)" stroke-width="1"/>`;
  }
  [27.5, 6.5, 13.5, 20.5].forEach((s) => {
    const [x1, y1] = pos(s, R_IN), [x2, y2] = pos(s, R_OUT);
    svg += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="rgba(148,163,184,0.2)" stroke-width="1" stroke-dasharray="2,3"/>`;
  });

  // Nakshatra labels around the ring
  WHEEL_RING.forEach((n, i) => {
    const a = (i / 28) * 2 * Math.PI;
    const [x, y] = pos(i, R_OUT + 13);
    const cosA = Math.cos(a);
    const anchor = cosA > 0.35 ? "start" : (cosA < -0.35 ? "end" : "middle");
    svg += `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-size="9" fill="#9fb3c8" text-anchor="${anchor}" dominant-baseline="middle">${n}</text>`;
  });

  // Vedha rays: chord from the graha's star to the far end of each ray
  for (const p of (d.planets || [])) {
    if (!p.rays || !p.rays.length || ringIdx[p.nakshatra] === undefined) continue;
    const color = p.nature === "benefic" ? "#22c55e" : "#ef4444";
    for (const grp of p.rays) {
      if (!grp.cells || !grp.cells.length) continue;
      const lastCell = grp.cells[grp.cells.length - 1];
      const endSlot = slotOfCell(lastCell[0], lastCell[1]);
      if (endSlot === undefined) continue;
      const [x1, y1] = pos(ringIdx[p.nakshatra], R_MID);
      const [x2, y2] = pos(endSlot, R_MID);
      const style = grp.ray === "front" ? "" : (grp.ray === "left" ? ' stroke-dasharray="6,3"' : ' stroke-dasharray="2,3"');
      svg += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${color}" stroke-width="1.6" opacity="0.7"${style}><title>${p.name} ${grp.ray} ray to ${cellLabel[lastCell[0] + "," + lastCell[1]] || "border"}</title></line>`;
    }
  }

  // Sensitive-star piercing highlights
  for (const hit of (d.point_hits || [])) {
    if (ringIdx[hit.nakshatra] === undefined) continue;
    const [x, y] = pos(ringIdx[hit.nakshatra], R_MID);
    svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="10" fill="none" stroke="#fbbf24" stroke-width="1.5"><title>${hit.point} pierced by ${hit.planet} (${hit.ray} ray)</title></circle>`;
  }

  // Graha dots on their stars
  for (const p of (d.planets || [])) {
    if (ringIdx[p.nakshatra] === undefined) continue;
    const [x, y] = pos(ringIdx[p.nakshatra], R_MID);
    const fill = p.nature === "benefic" ? "#22c55e" : "#ef4444";
    svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="8" fill="${fill}" stroke="#0d1420" stroke-width="1.5"><title>${p.name} in ${p.nakshatra} (strength ${p.signed_strength})</title></circle>`;
    svg += `<text x="${x.toFixed(1)}" y="${(y + 2.5).toFixed(1)}" font-size="7.5" fill="#0d1420" font-weight="bold" text-anchor="middle">${p.symbol}</text>`;
  }
  svg += "</svg>";
  host.innerHTML = svg;

  const legend = $("vedha-wheel-legend");
  if (legend) {
    legend.innerHTML =
      '<span><i class="mk" style="background:#22c55e"></i> Benefic graha / ray</span>' +
      '<span><i class="mk" style="background:#ef4444"></i> Malefic graha / ray</span>' +
      '<span><i class="mk" style="background:#94a3b8"></i> Solid = front ray</span>' +
      '<span><i class="mk" style="background:repeating-linear-gradient(90deg,#94a3b8 0 4px,transparent 4px 6px)"></i> Long dash = left ray</span>' +
      '<span><i class="mk" style="background:repeating-linear-gradient(90deg,#94a3b8 0 2px,transparent 2px 4px)"></i> Short dash = right ray</span>' +
      '<span><i class="mk" style="background:none;border:2px solid #fbbf24;border-radius:50%"></i> Sensitive star pierced</span>';
  }
}

function renderVedhaSankey(d) {
  const host = $("vedha-sankey");
  if (!host) return;

  const flows = [];
  (d.vedhas || []).forEach((v) => {
    const perTarget = {};
    v.rays.forEach((r) => (r.cells || []).forEach((c) => {
      const t = perTarget[c.label] || (perTarget[c.label] = { impact: 0, point: false });
      t.impact += 1;
      if (c.point) t.point = true;
    }));
    Object.keys(perTarget).forEach((t) => {
      flows.push({ source: v.planet, nature: v.nature, target: t, impact: perTarget[t].impact, point: perTarget[t].point });
    });
  });
  if (!flows.length) {
    host.innerHTML = '<div class="exec-empty">No vedha rays active today.</div>';
    return;
  }

  const byTarget = {};
  flows.forEach((f) => { byTarget[f.target] = (byTarget[f.target] || 0) + f.impact; });
  const targets = Object.keys(byTarget).sort((a, b) => byTarget[b] - byTarget[a]).slice(0, 14);
  const tFlows = flows.filter((f) => targets.includes(f.target));
  if (!tFlows.length) {
    host.innerHTML = '<div class="exec-empty">No vedha rays active today.</div>';
    return;
  }
  // Only grahas whose flows survived the top-14 cut get a node
  const sources = [...new Set(tFlows.map((f) => f.source))];

  const W = 780, nodeW = 118, gap = 8;
  const totalFlow = tFlows.reduce((n, f) => n + f.impact, 0);
  const maxCount = Math.max(sources.length, targets.length);
  const H = Math.max(240, maxCount * 30 + 30);
  const usable = H - 24;
  const k = (usable - (maxCount - 1) * gap) / totalFlow;

  const srcTotals = {}, tgtTotals = {};
  tFlows.forEach((f) => {
    srcTotals[f.source] = (srcTotals[f.source] || 0) + f.impact;
    tgtTotals[f.target] = (tgtTotals[f.target] || 0) + f.impact;
  });

  // Node y positions (precomputed)
  const srcY = {}, tgtY = {};
  let acc = 12;
  sources.forEach((s) => { srcY[s] = acc; acc += srcTotals[s] * k + gap; });
  acc = 12;
  targets.forEach((t) => { tgtY[t] = acc; acc += tgtTotals[t] * k + gap; });

  // Stack ribbons within nodes: by target order, then source order
  const tgtOrder = {};
  targets.forEach((t, i) => { tgtOrder[t] = i; });
  const sortedFlows = tFlows.slice().sort((a, b) =>
    (tgtOrder[a.target] - tgtOrder[b.target]) ||
    (sources.indexOf(a.source) - sources.indexOf(b.source)));
  const srcOff = {}, tgtOff = {};
  sources.forEach((s) => { srcOff[s] = 0; });
  targets.forEach((t) => { tgtOff[t] = 0; });

  let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="background:transparent">`;

  // Links first (under nodes)
  for (const f of sortedFlows) {
    const sy = srcY[f.source] + srcOff[f.source];
    const ty = tgtY[f.target] + tgtOff[f.target];
    srcOff[f.source] += f.impact * k;
    tgtOff[f.target] += f.impact * k;
    const x1 = nodeW, x2 = W - nodeW;
    const mid = (x1 + x2) / 2;
    const color = f.nature === "benefic" ? "rgba(34,197,94,0.45)" : "rgba(239,68,68,0.45)";
    const bw = Math.max(2, f.impact * k);
    svg += `<path d="M ${x1} ${sy.toFixed(1)} C ${mid} ${sy.toFixed(1)}, ${mid} ${ty.toFixed(1)}, ${x2} ${ty.toFixed(1)}" fill="none" stroke="${color}" stroke-width="${bw.toFixed(1)}"><title>${f.source} → ${f.target}: ${f.impact} cell(s)${f.point ? " · sensitive star" : ""}</title></path>`;
  }

  // Source nodes
  sources.forEach((s) => {
    const h = srcTotals[s] * k;
    const y = srcY[s];
    const nature = tFlows.find((f) => f.source === s).nature;
    const fill = nature === "benefic" ? "rgba(34,197,94,0.85)" : "rgba(239,68,68,0.85)";
    svg += `<rect x="0" y="${y.toFixed(1)}" width="${nodeW}" height="${h.toFixed(1)}" rx="3" fill="${fill}"><title>${s}: ${srcTotals[s]} pierced cell(s)</title></rect>`;
    svg += `<text x="${nodeW / 2}" y="${(y + h / 2 + 3).toFixed(1)}" font-size="10" fill="#0d1420" font-weight="bold" text-anchor="middle">${s} (${srcTotals[s]})</text>`;
  });

  // Target nodes
  for (const t of targets) {
    const h = tgtTotals[t] * k;
    const y = tgtY[t];
    const gold = tFlows.some((f) => f.target === t && f.point);
    svg += `<rect x="${W - nodeW}" y="${y.toFixed(1)}" width="${nodeW}" height="${h.toFixed(1)}" rx="3" fill="#334155"${gold ? ' stroke="#fbbf24" stroke-width="1.5"' : ""}><title>${t}: hit ${tgtTotals[t]} time(s)${gold ? " · anchor sensitive star" : ""}</title></rect>`;
    svg += `<text x="${W - nodeW / 2}" y="${(y + h / 2 + 3).toFixed(1)}" font-size="10" fill="#e2e8f0" text-anchor="middle">${t} (${tgtTotals[t]})</text>`;
  }
  svg += "</svg>";
  host.innerHTML = svg;

  const note = document.createElement("div");
  note.className = "backtest-note";
  note.textContent = "Link width = pierced-cell count · green = benefic flow, red = malefic flow · gold outline = anchor sensitive star · targets sorted by total hits (top 14).";
  host.appendChild(note);
}

function renderVedhaStrength(d) {
  const host = $("vedha-strength");
  if (!host) return;
  const planets = (d.planets || [])
    .filter((p) => p.signed_strength !== undefined)
    .sort((a, b) => b.signed_strength - a.signed_strength);
  if (!planets.length) {
    host.innerHTML = '<div class="exec-empty">No strength data.</div>';
    return;
  }
  host.innerHTML = "";
  const canvas = document.createElement("canvas");
  host.appendChild(canvas);
  if (window.vedhaStrengthChart) { try { window.vedhaStrengthChart.destroy(); } catch (e) {} }
  window.vedhaStrengthChart = new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: planets.map((p) => p.name + (p.retrograde ? " (R)" : "")),
      datasets: [{
        label: "Signed strength",
        data: planets.map((p) => p.signed_strength),
        backgroundColor: planets.map((p) =>
          p.nature === "benefic" ? "rgba(34,197,94,0.8)" : "rgba(239,68,68,0.8)"),
        borderRadius: 3
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: "rgba(29,42,61,0.6)" }, ticks: { color: "#c8d3e0", font: { size: 10 } } },
        y: { grid: { display: false }, ticks: { color: "#c8d3e0", font: { size: 10 } } }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (item) {
              const p = planets[item.dataIndex];
              const reasons = (p.dignity_reasons || []).join(", ");
              return `Signed strength ${p.signed_strength} (${p.nature}${reasons ? " · " + reasons : ""})`;
            }
          }
        }
      }
    }
  });
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

  if (rec.actionable) {
    const a = rec.actionable;
    const hdr = document.createElement("h3");
    hdr.textContent = "Rule-based directive (unvalidated: see the forecast evidence card)";
    hdr.style.marginTop = "16px";
    hdr.style.color = "var(--accent)";
    box.appendChild(hdr);

    const items = [
      `Bias: ${a.bias}`,
      `Sizing: ${a.sizing}`,
      `Risk: ${a.risk}`,
      `Action: ${a.action}`,
      `Timing Note: ${a.tithi_note}`
    ];
    for (const t of items) {
      const p = document.createElement("p");
      p.style.fontWeight = "500";
      p.style.margin = "6px 0";
      p.textContent = t;
      box.appendChild(p);
    }
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
    // B-60: one retry when the request itself fails (cold server, dropped connection,
    // timeout). An error the server reports in the body is not retried.
    let r;
    try {
      r = await fetchWithTimeout("/api/prediction?" + params);
    } catch (netErr) {
      console.warn("Prediction request failed; retrying once.", netErr);
      await new Promise((res) => setTimeout(res, 1500));
      r = await fetchWithTimeout("/api/prediction?" + params);
    }
    const data = await r.json();
    if (data.error) throw new Error(data.error);

    // add planet cell coords for ray drawing
    for (const p of data.planets) {
      const found = data.grid.flat().find((c) =>
        c.planets && c.planets.some((pl) => pl.name === p.name));
      p.planetCell = found ? [found.row, found.col] : [0, 0];
    }

    state = data;
    updateNavAsOf();
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

    // B-60: supporting panels load on their own; a failure there must not report
    // the prediction itself as unavailable.
    const quietly = (label, p) => Promise.resolve(p).catch((err) => console.warn(`${label} failed:`, err));
    await quietly("Futurecast", loadFuturecast(data.date));
    // Panels commented out in UI: Sector Vedha, LargeCap, FMCG, Tourism, Chemical, Alcohol, Bullion Vedha, Transit Vedha
    // await loadSectorVedha(data.date);
    // await loadLargecapDivergence(data.date);
    // await loadFmcgSignals(data.date);
    // await loadTourismSignals(data.date);
    // await loadChemicalSignals(data.date);
    // await loadAlcoholSignals(data.date);
    await quietly("Lunar forecast", loadLunarForecast(data.date));
    // SBC Sector Dashboard reuses the prediction payload (no extra API call)
    if ($("sd-status")) loadSectorDashboard(data.date, data).catch(() => {});
    // await loadBullionVedha(data.date, true);  // weekly view
    // await loadTransitVedha(data.date, true);  // weekly view
    const kpInst = $("kp-intraday-instrument") ? $("kp-intraday-instrument").value : "NIFTY";
    const kpFmt = $("kp-intraday-format") ? $("kp-intraday-format").value : "html";
    quietly("KP intraday report", loadKPIntradayReport(data.date, kpInst, kpFmt));
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
      const dayStr = isoDateOf(d);
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
// B-09: the lunar card's Copy / Share buttons.
if ($("lunar-forecast-copy")) $("lunar-forecast-copy").addEventListener("click", copyLunarForecast);
if ($("lunar-forecast-share")) $("lunar-forecast-share").addEventListener("click", shareLunarForecast);

if ($("lunar-forecast-run")) {
  $("lunar-forecast-run").addEventListener("click", () => {
    const date = $("lunar-forecast-date") ? $("lunar-forecast-date").value : "";
    if (date) loadLunarForecast(date);
  });
}


// KP Intraday Trend Change Prediction
// Red banner when the backend's KP sanity check says the source file is not
// real ephemeris data (sbc.kp_intraday.assess_kp_data).
function initCrashWindowsDefaults() {
  const startEl = $("crash-start-date");
  const endEl = $("crash-end-date");
  if (!startEl || !endEl) return;
  const todayISO = localTodayISO();
  if (!startEl.value) startEl.value = todayISO;
  if (!endEl.value) {
    const today = new Date(todayISO + "T00:00:00");
    const oneMonthLater = new Date(today);
    oneMonthLater.setMonth(oneMonthLater.getMonth() + 1);
    const endISO = oneMonthLater.toISOString().slice(0,10);
    endEl.value = endISO;
  }
  const genBtn = $("crash-generate");
  if (genBtn) genBtn.addEventListener("click", () => loadCrashWindows().catch(() => {}));
  loadCrashWindows().catch(() => {});
}

// Daily risk score as a step area with the ELEVATED and HIGH lines (Plotly, loaded on first use).
async function drawCrashScoreChart(d) {
  const box = $("crash-score-chart");
  if (!box || !d.series.length) return;
  if (!window.Plotly) {
    await new Promise((ok, fail) => {
      const s = document.createElement("script");
      s.src = "/static/vendor/plotly-basic-4.1.1.min.js"; s.onload = ok; s.onerror = fail;
      document.head.appendChild(s);
    });
  }
  const css = (n, f) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f;
  const text = css("--text", "#e2e8f0"), muted = css("--muted", "#94a3b8"), line = css("--line", "#1f2c47");
  const x = d.series.map((r) => r.date), y = d.series.map((r) => r.score);
  const hline = (v, color, name) => ({ type: "scatter", mode: "lines", name, x: [x[0], x[x.length - 1]], y: [v, v],
    line: { color, width: 1.4, dash: "dash" }, hoverinfo: "skip" });
  const axis = { gridcolor: line, zerolinecolor: line, color: muted };
  Plotly.react(box, [
    { type: "scatter", mode: "lines", name: "Risk score", x, y, fill: "tozeroy", line: { shape: "hv", color: "#5b7bb0", width: 1 },
      fillcolor: "rgba(91,123,176,.75)", hovertemplate: "%{x|%d-%m-%Y}<br>score %{y:.2f}<extra></extra>" },
    hline(d.thresholds.elevated, "#d4a017", `Elevated ≥ ${d.thresholds.elevated}`),
    hline(d.thresholds.high, "#dc2626", `High ≥ ${d.thresholds.high}`),
  ], {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { color: text, size: 11 }, height: 300,
    margin: { l: 52, r: 12, t: 8, b: 36 }, showlegend: true, legend: { x: 0.01, y: 0.99, bgcolor: "rgba(0,0,0,0)" },
    xaxis: Object.assign({ type: "date", tickformat: "%d %b" }, axis),
    yaxis: Object.assign({ title: { text: "Risk score" }, rangemode: "tozero" }, axis),
  }, { responsive: true, displaylogo: false });
}

// Crash windows report: /api/crash_windows scores every day in the chosen period.
async function loadCrashWindows() {
  const s = $("crash-start-date")?.value, e = $("crash-end-date")?.value;
  const box = $("crash-report-text"), btn = $("crash-generate");
  if (!box || !s || !e) return;
  const dmy = (iso) => iso.split("-").reverse().join("-");
  const runs = (rs) => (rs && rs.length ? rs.map(([a, b]) => (a === b ? dmy(a) : `${dmy(a)} – ${dmy(b)}`)).join("; ") : "Not active");
  const typeCls = { "Trigger": "trig", "Slow backdrop": "slow", "Seasonal": "seas" };
  if (btn) btn.disabled = true;
  const meta = $("crash-report-meta");
  if (meta) meta.textContent = `Scoring ${dmy(s)} to ${dmy(e)}…`;
  try {
    const res = await fetch(`/api/crash_windows?start=${s}&end=${e}`);
    const d = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(d.error || `request failed (${res.status})`);
    const top = d.periods[0];
    const summary = top
      ? `Strongest window: ${dmy(top.start)} to ${dmy(top.end)}, peak score ${top.peak_score.toFixed(2)} on ${dmy(top.peak_date)} — ${top.reasons.map((r) => esc(r.label)).join(", ")}.`
      : "No day in this range crossed the ELEVATED threshold.";
    const slow = d.strong_slow_active.length
      ? `Strong slow-cycle signal active: ${d.strong_slow_active.map(esc).join(", ")}.`
      : "Neither of the two strongest slow-cycle signals (Saturn–Uranus, Jupiter–Saturn hard aspects) is active in this range, so any windows below rely on shorter-term triggers.";
    const clip = (rs, p) => rs.map(([x, y]) => [x < p.start ? p.start : x, y > p.end ? p.end : y]).filter(([x, y]) => x <= y);
    const reasonLine = (r, p) => {
      const span = clip(r.runs, p).map(([x, y]) => `${dmy(x)} to ${dmy(y)}`).join("; ");
      const ev = `Historical lift ${r.lift.toFixed(2)}×${r.seen ? `; seen in ${esc(r.seen)}` : ""}`;
      return `<li><strong>${esc(r.label)}</strong> <span class="crash-dates">[${span}]</span> — ${esc(r.position)}. ${esc(r.meaning)} <span class="crash-seen">(${ev}.)</span></li>`;
    };
    const periodRows = d.periods.map((p, n) => `
      <tr><td>${n + 1}</td>
        <td class="nowrap">${dmy(p.start)}<br>to<br>${dmy(p.end)}${p.high_runs.length ? `<br><br><span class="muted">HIGH days:<br>${p.high_runs.map(([x, y]) => (x === y ? dmy(x) : `${dmy(x)} – ${dmy(y)}`)).join("<br>")}</span>` : ""}</td>
        <td class="num">${p.days}</td><td><span class="crash-level ${p.level === "HIGH" ? "high" : "elev"}">${p.level}</span></td>
        <td class="nowrap">${p.peak_score.toFixed(2)}<br>${dmy(p.peak_date)}</td>
        <td><ul class="crash-reasons">${p.reasons.map((r) => reasonLine(r, p)).join("")}</ul></td></tr>`).join("");
    const reasonTables = "";
    const cal = d.calendar.map((c) => `
      <tr class="${c.runs.length ? "crash-on" : "crash-off"}"><td>${esc(c.label)}</td>
        <td><span class="crash-type ${typeCls[c.type] || ""}">${esc(c.type)}</span></td>
        <td class="num">${c.lift.toFixed(2)}</td><td class="num">${c.weight.toFixed(2)}</td><td>${runs(c.runs)}</td></tr>`).join("");
    const ecl = d.eclipses.length ? d.eclipses.map((x) => `${x.kind} eclipse ${dmy(x.date)}`).join("; ") : "None in this range.";
    const t = d.thresholds;
    box.innerHTML = `
      <header class="crash-head">
        <h3>Indicative Market Crash Windows — Planetary Combinations</h3>
        <p class="crash-meta" id="crash-report-meta">Period analysed: ${dmy(d.start)} to ${dmy(d.end)} | Generated: ${dmy(d.generated)} | Sidereal (Lahiri), mean nodes</p>
      </header>
      <section class="crash-sec"><h4>1. Summary</h4>
        <div class="crash-kpis">
          <div><span>Days scanned</span><b>${d.days_scanned}</b></div>
          <div><span>Risk periods</span><b>${d.periods.length}</b></div>
          <div><span>HIGH / ELEVATED</span><b>${d.n_high} / ${d.n_elevated}</b></div>
          <div><span>Days covered</span><b>${d.days_covered}</b></div>
        </div>
        <p>${summary}</p><p class="muted">${slow}</p><div id="crash-score-chart" class="crash-chart"></div></section>
      <section class="crash-sec"><h4>2. Indicative crash / correction periods</h4>
        ${d.periods.length ? `<div class="analog-table-wrap"><table class="analog-table crash-table">
          <thead><tr><th>#</th><th>Period</th><th>Days</th><th>Level</th><th>Peak score / date</th><th>Reasons (combination [active dates] — position. Meaning. Evidence.)</th></tr></thead>
          <tbody>${periodRows}</tbody></table></div>${reasonTables}` : `<p class="muted">None in this range.</p>`}</section>
      <section class="crash-sec"><h4>3. Combination calendar</h4>
        <p class="muted">When each combination is active in the range (whether or not the day crossed the threshold).</p>
        <div class="analog-table-wrap"><table class="analog-table crash-table">
          <thead><tr><th>Combination</th><th>Type</th><th>Lift</th><th>Weight</th><th>Active dates in range</th></tr></thead>
          <tbody>${cal}</tbody></table></div></section>
      <section class="crash-sec"><h4>4. Eclipses in the range (reference only)</h4>
        <p class="muted">In the historical study, eclipses within ±15 days showed no edge (lift 0.95); listed for completeness.</p><p>${ecl}</p></section>
      <section class="crash-sec"><h4>5. How the score works</h4><ul class="crash-how">
        <li>Each day's planetary positions are computed (11:30 IST; sidereal Lahiri; mean Rahu/Ketu). The Venus-in-11th tests use the Mumbai 09:15 IST opening-bell chart with whole-sign houses.</li>
        <li>Each active combination adds its weight. Weight = (historical lift − 1) × n/(n+5), from 26 crash days (1929–2025) against all weekdays since 1925; combinations seen in only a few crashes are discounted.</li>
        <li>ELEVATED = score above ${t.elevated} (about the top 10% of days since 1925). HIGH = score ≥ ${t.high} (about the top 3%). Flagged days less than ${t.join_gap_days} days apart are joined into one period.</li>
        <li>The weights are in-sample, so expect weaker results going forward. Most flagged periods will not contain a crash, and many crashes occur outside flagged periods.</li>
        <li>None of the combinations passed a strict multiple-testing correction. Use the windows as a risk-management prompt (position size, stops, hedges), not as a sell signal.</li>
      </ul><p class="crash-foot">Research tool only. Not investment advice.</p></section>`;
    drawCrashScoreChart(d).catch(() => {});
  } catch (err) {
    if (meta) meta.textContent = `Couldn't generate the report: ${err.message}`;
  } finally {
    if (btn) btn.disabled = false;
  }
}
document.addEventListener("DOMContentLoaded", initCrashWindowsDefaults);

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
  // B-62: the Advanced analysis dropdown closes on an outside click or Escape.
  const advMenu = document.querySelector("details.advanced-workspaces");
  if (advMenu) {
    document.addEventListener("click", (e) => { if (advMenu.open && !advMenu.contains(e.target)) advMenu.open = false; });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && advMenu.open) { advMenu.open = false; advMenu.querySelector("summary")?.focus(); } });
  }

  function switchTab(targetId) {
    // SBC is now hosted inline on the overview tab; remap stale deep links
    if (targetId === "tab-chakra") {
      targetId = "tab-overview";
    }
    tabs.forEach((t) => {
      const isTarget = t.getAttribute("data-tab") === targetId;
      t.classList.toggle("active", isTarget);
      t.setAttribute("aria-selected", isTarget ? "true" : "false");
    });
    panes.forEach((p) => {
      p.classList.toggle("active", p.id === targetId);
    });
    // B-62: close the Advanced analysis dropdown after a pick, and mark it when the
    // active page lives inside it so the bar still shows where you are.
    const adv = document.querySelector("details.advanced-workspaces");
    if (adv) {
      adv.open = false;
      adv.classList.toggle("has-active", !!adv.querySelector(`.nav-tab[data-tab="${targetId}"]`));
    }

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
        window._cachedOHLCFreshness = data.freshness;
        console.log("OHLC cache loaded", data.bars.length, "bars");
      }).catch(()=>{});
    }

    // B-70: KP Chart (NIFTY) loads the header date's report on first open.
    if (targetId === "tab-kp-nifty") {
      const content = $("kp-nifty-content");
      const globalDate = $("date") ? $("date").value : "";
      if (content && globalDate && !content.innerHTML.trim()) {
        if ($("kp-nifty-date")) $("kp-nifty-date").value = globalDate;
        loadKPIntradayReportNifty(globalDate, $("kp-nifty-format") ? $("kp-nifty-format").value : "html");
      }
    }

    // B-69: KP Intraday Report shows the live report (it used to be a frozen
    // September sample pasted into the page).
    if (targetId === "tab-kp-report") {
      const globalDate = $("date") ? $("date").value : "";
      const box = $("kp-report-text");
      if (box && globalDate && box.dataset.reportDate !== globalDate) loadKPReportPage(globalDate);
    }

    // When switching to KP Intraday tab, auto-load if empty, error, or stale
    if (targetId === "tab-kp") {
      const dateEl = $("kp-intraday-date");
      const globalDate = $("date") ? $("date").value : "";
      if (dateEl && globalDate && dateEl.value !== globalDate) {
        dateEl.value = globalDate;
      }
      const targetDate = (dateEl && dateEl.value) || globalDate;
      const content = $("kp-intraday-content");
      const shownFor = content && (content.dataset.requestedDate || content.dataset.reportDate);
      const kpStale = content && targetDate && shownFor && shownFor !== targetDate;
      if (content && (kpStale || !content.innerHTML.trim() || content.querySelector(".kp-error"))) {
        const inst = $("kp-intraday-instrument") ? $("kp-intraday-instrument").value : "NIFTY";
        const fmt = $("kp-intraday-format") ? $("kp-intraday-format").value : "html";
        if (targetDate) loadKPIntradayReport(targetDate, inst, fmt);
      }
    }

    // When switching to Daily Balance tab, auto-load if empty or stale
    if (targetId === "tab-balance") {
      const dateEl = $("daily-balance-date");
      const globalDate = $("date") ? $("date").value : "";
      if (dateEl && globalDate && dateEl.value !== globalDate) {
        dateEl.value = globalDate;
      }
      const targetDate = (dateEl && dateEl.value) || globalDate || localTodayISO();
      const balanceStale = targetDate && window.dailyBalanceLoadedFor &&
                           window.dailyBalanceLoadedFor !== targetDate;
      if (targetDate && (balanceStale || !window.dailyBalanceChart)) {
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
async function loadAstroCycles(dateOverride) {
  const statusEl = $("astrocycle-status");
  const resultsEl = $("astrocycle-results");
  if (!statusEl || !resultsEl) return;
  const date = dateOverride || ($("astrocycle-date") ? $("astrocycle-date").value : "") ||
    new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  if ($("astrocycle-date") && !$("astrocycle-date").value) $("astrocycle-date").value = date;

  statusEl.textContent = "Loading AstroCycle time bars...";
  statusEl.className = "nifty-chart-status";
  try {
    const res = await fetchWithTimeout(`/api/astro/cycles?date=${encodeURIComponent(date)}&ticker=^NSEI`, 120000);
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || res.status);

    const bars = data.bars || [];
    const ingresses = data.moon_ingresses || [];
    let html = "";
    if (data.ref_price != null) {
      html += `<p class="backtest-note">Reference price: <b>${data.ref_price}</b> · SL distance ${data.sl_points} pts (targets at 2x)</p>`;
    } else {
      html += `<p class="backtest-note">Reference price unavailable (offline) — levels shown at 0. Add ticker data for real levels.</p>`;
    }

    if (!bars.length && !ingresses.length) {
      html += `<p class="backtest-note">No Mercury/Moon horas or Moon ingresses fall within market hours on ${date}.</p>`;
    } else {
      if (bars.length) {
        html += `<table class="astrocycle-table"><thead><tr>
          <th>Time</th><th>Cycle</th><th>Entry Above</th><th>Entry Below</th><th>SL</th><th>Target</th><th>Rule</th>
        </tr></thead><tbody>`;
        bars.forEach((b) => {
          html += `<tr>
            <td><b>${b.time}&ndash;${b.end}</b></td>
            <td><span class="astrocycle-badge astrocycle-${b.type}">${b.lord}</span></td>
            <td>${b.entry_above}</td>
            <td>${b.entry_below}</td>
            <td>${b.stop_loss}</td>
            <td>${b.target_above} / ${b.target_below}</td>
            <td class="astrocycle-rule">${b.entry_rule}</td>
          </tr>`;
        });
        html += `</tbody></table>`;
      }
      if (ingresses.length) {
        html += `<h4 style="margin-top:10px">Moon Nakshatra Ingresses</h4>`;
        ingresses.forEach((g) => {
          html += `<div class="astrocycle-ingress">${g.time} &mdash; Moon enters <b>${g.into_nakshatra}</b> (from ${g.from_nakshatra}): ${g.entry_rule}</div>`;
        });
      }
    }
    resultsEl.innerHTML = html;
    statusEl.textContent = `Loaded ${bars.length} cycle bars, ${ingresses.length} Moon ingresses for ${date}.`;
  } catch (e) {
    statusEl.textContent = "AstroCycle load failed: " + e.message;
    statusEl.className = "nifty-chart-status error";
  }
}

// ---------------------------------------------------------------
// Expiry Range Indicator: expiry-day S/R forecast + backtest
// ---------------------------------------------------------------
async function loadExpiryForecast(mode) {
  const statusEl = $("expiry-status");
  const resultsEl = $("expiry-results");
  if (!statusEl || !resultsEl) return;
  const instrument = $("expiry-instrument") ? $("expiry-instrument").value : "NIFTY";

  statusEl.textContent = mode === "backtest" ? "Running expiry backtest..." : "Loading expiry forecast...";
  statusEl.className = "nifty-chart-status";
  try {
    if (mode === "backtest") {
      const res = await fetchWithTimeout(`/api/expiry/backtest?instrument=${encodeURIComponent(instrument)}&months=3`, 300000);
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || res.status);
      let html = `<table class="expiry-table"><thead><tr>
        <th>Expiry</th><th>Contained</th><th>Breakout Up</th><th>Breakout Down</th><th>False Up</th><th>False Down</th>
      </tr></thead><tbody>`;
      (data.results || []).forEach((r) => {
        html += `<tr>
          <td><b>${r.expiry}</b></td>
          <td class="${r.contained ? "exp-ok" : "exp-warn"}">${r.contained ? "Yes" : "No"}</td>
          <td>${r.breakout_up ? (r.false_breakout_up ? "False" : "Yes") : "-"}</td>
          <td>${r.breakout_down ? (r.false_breakout_down ? "False" : "Yes") : "-"}</td>
          <td>${r.false_breakout_up ? "Yes" : "-"}</td>
          <td>${r.false_breakout_down ? "Yes" : "-"}</td>
        </tr>`;
      });
      html += `</tbody></table>`;
      html += `<p class="backtest-note">${data.expiry_days_evaluated} expiry days · containment ${data.containment_rate != null ? (data.containment_rate * 100).toFixed(1) + "%" : "-"} · false-breakout rate ${data.false_breakout_rate != null ? (data.false_breakout_rate * 100).toFixed(1) + "%" : "-"} (buffer ${(data.buffer_pct * 100).toFixed(2)}%)</p>`;
      resultsEl.innerHTML = html;
      statusEl.textContent = `Expiry backtest loaded: ${data.expiry_days_evaluated} days for ${data.instrument}.`;
    } else {
      const res = await fetchWithTimeout(`/api/expiry/range?instrument=${encodeURIComponent(instrument)}`, 300000);
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || res.status);
      const lv = data.levels || {};
      let html = `<p class="backtest-note">Next expiry: <b>${data.expiry}</b> · pivot <b>${lv.pivot}</b> · buffer ${(lv.buffer_pct * 100).toFixed(2)}%</p>`;
      html += `<table class="expiry-table"><thead><tr><th>Level</th><th>Price</th><th>Breakout Valid</th></tr></thead><tbody>`;
      (lv.resistances || []).slice().reverse().forEach((l) => {
        html += `<tr><td class="exp-res"><b>${l.level}</b></td><td>${l.price}</td><td>above ${l.valid_above}</td></tr>`;
      });
      html += `<tr><td class="exp-piv"><b>PP</b></td><td>${lv.pivot}</td><td>-</td></tr>`;
      (lv.supports || []).forEach((l) => {
        html += `<tr><td class="exp-sup"><b>${l.level}</b></td><td>${l.price}</td><td>below ${l.valid_below}</td></tr>`;
      });
      html += `</tbody></table>`;
      resultsEl.innerHTML = html;
      statusEl.textContent = `Expiry forecast loaded for ${data.instrument} (${data.expiry}).`;
    }
  } catch (e) {
    statusEl.textContent = "Expiry load failed: " + e.message;
    statusEl.className = "nifty-chart-status error";
  }
}

// ---------------------------------------------------------------
// Bootstrap: wire up all initialisers once the DOM is ready
// ---------------------------------------------------------------
// One failing initialiser must not stop the rest of the page (auto-run, AstroCycle,
// futurecast) from loading.
function safeInit(label, fn) {
  try {
    const out = fn();
    if (out && typeof out.catch === "function") out.catch((e) => console.error(`${label} failed:`, e));
  } catch (e) {
    console.error(`${label} failed:`, e);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Load and apply persisted settings
  safeInit("settings", () => applySettings(loadSettings()));

  safeInit("setTodayAsDefault", () => setTodayAsDefault());
  safeInit("loadPresets", () => loadPresets());
  safeInit("initWeekCalendar", () => initWeekCalendar());
  safeInit("initSectorFilters", () => initSectorFilters());
  safeInit("initWorkspaceTabs", () => initWorkspaceTabs());
  safeInit("initKPIntradayChart", () => initKPIntradayChart());
  safeInit("initMonthlyHeatmap", () => initMonthlyHeatmap());
  safeInit("initConfluenceMatrix", () => initConfluenceMatrix());
  safeInit("initKeyboardNavigation", () => initKeyboardNavigation());
  safeInit("initThemeToggle", () => initThemeToggle());

  // Auto-run the prediction with today's date so the page (including the
  // hosted SBC chakra) renders without clicking Predict
  if ($("date")) $("date").addEventListener("change", updateNavAsOf);
  defaultToNextSession().finally(() => { updateNavAsOf(); run().catch(() => {}); });

  // AstroCycle Pro panel
  if ($("astrocycle-run")) {
    $("astrocycle-run").addEventListener("click", () => loadAstroCycles());
    loadAstroCycles().catch(() => {});
  }

  // Expiry Range Indicator panel
  if ($("expiry-run")) {
    $("expiry-run").addEventListener("click", () => loadExpiryForecast("forecast"));
    loadExpiryForecast("forecast").catch(() => {});
  }
  if ($("expiry-backtest")) {
    $("expiry-backtest").addEventListener("click", () => loadExpiryForecast("backtest"));
  }

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

  // Transit Report tab
  if ($("transit-generate")) {
    const TRANSIT_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
      "Saturn", "Rahu", "Ketu", "Uranus", "Neptune", "Pluto"];
    const planetWrap = $("transit-planets");
    TRANSIT_PLANETS.forEach((name) => {
      const label = document.createElement("label");
      label.className = "chk";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.value = name;
      box.checked = true;
      label.appendChild(box);
      label.appendChild(document.createTextNode(" " + name));
      planetWrap.appendChild(label);
    });
    $("transit-planets-toggle").addEventListener("click", () => {
      const boxes = [...planetWrap.querySelectorAll("input")];
      const anyOff = boxes.some((b) => !b.checked);
      boxes.forEach((b) => { b.checked = anyOff; });
    });

    const today = new Date();
    const iso = (d) => d.toISOString().slice(0, 10);
    $("transit-start").value = iso(today);
    $("transit-end").value = iso(new Date(today.getTime() + 365 * 86400000));

    let cityTimer = null;
    $("transit-city").addEventListener("input", () => {
      clearTimeout(cityTimer);
      const q = $("transit-city").value.trim();
      if (q.length < 2) return;
      cityTimer = setTimeout(async () => {
        try {
          const res = await fetchWithTimeout(`/api/transits/cities?q=${encodeURIComponent(q)}&limit=8`);
          const data = await res.json();
          const list = $("transit-city-list");
          list.innerHTML = "";
          (data.results || []).forEach((c) => {
            const opt = document.createElement("option");
            opt.value = c.name;
            opt.label = `${c.name}, ${c.country} (${c.timezone})`;
            list.appendChild(opt);
          });
        } catch (e) { /* autocomplete is best-effort */ }
      }, 250);
    });

    $("transit-generate").addEventListener("click", () => {
      const status = $("transit-status");
      const start = $("transit-start").value;
      const end = $("transit-end").value;
      const types = [...$("transit-types").querySelectorAll("input:checked")].map((b) => b.value);
      const planets = [...planetWrap.querySelectorAll("input:checked")].map((b) => b.value);
      if (!start || !end) { status.textContent = "Pick a start and end date."; return; }
      if (!types.length) { status.textContent = "Pick at least one transit type."; return; }
      if (!planets.length) { status.textContent = "Pick at least one planet."; return; }
      const params = new URLSearchParams({
        city: $("transit-city").value.trim() || "Mumbai",
        start, end,
        ayanamsa: $("transit-ayanamsa").value,
        node_mode: $("transit-node").value,
        types: types.join(","),
        planets: planets.join(","),
      });
      status.textContent = "Building workbook (large ranges can take ~30s)...";
      const url = `/api/transits/report?${params}`;
      // Kick off the download and confirm via HEAD-less GET: navigating
      // with as_attachment streams straight to the file.
      const done = () => { status.textContent = "Download started: " + start + " to " + end + "."; };
      fetch(url).then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.blob(); })
        .then((blob) => {
          const a = document.createElement("a");
          const match = url.match(/start=([^&]+)/);
          a.href = URL.createObjectURL(blob);
          a.download = `transit_report_${start}_${end}.xlsx`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          done();
        })
        .catch((e) => { status.textContent = "Report failed: " + e.message; });
    });
  }


  // Momentum Screener tab
  if ($("scr-run")) {
    (async () => {
      try {
        const res = await fetchWithTimeout("/api/screener/universes");
        const body = await res.json();
        const sel = $("scr-universe");
        sel.innerHTML = "";
        body.universes.forEach((u) => {
          const opt = document.createElement("option");
          opt.value = u; opt.textContent = u;
          sel.appendChild(opt);
        });
      } catch (e) { /* population is best-effort */ }
    })();

    const today = new Date();
    $("scr-end").value = today.toISOString().slice(0, 10);

    const scrParams = () => {
      const watch = $("scr-watchlist").value.trim();
      const params = new URLSearchParams({
        universe: watch ? ("watchlist:" + watch) : $("scr-universe").value,
        mode: $("scr-mode").value,
        timeframe: $("scr-timeframe").value,
      });
      if ($("scr-end").value) params.set("end", $("scr-end").value);
      if ($("scr-lookback").value) params.set("lookback", $("scr-lookback").value);
      if ($("scr-ha").checked) params.set("as_ha", "1");
      return params;
    };

    const renderResults = (body) => {
      const wrap = $("scr-results");
      if (!body.signals || !body.signals.length) {
        wrap.innerHTML = '<div class="empty-note">No signals in this window.</div>';
        return;
      }
      const rows = body.signals.slice(0, 50).map((s) => {
        const pnl = s.pnl_pct == null ? "" : s.pnl_pct + "%";
        const exit = s.status === "exited"
          ? `${_fmt_ts(s.exit_ts)} @ ${s.exit_price} (${s.exit_reason || ""})`
          : "open";
        return `<tr><td>${s.symbol}</td><td>${s.side}</td><td>${_fmt_ts(s.entry_ts)}</td>` +
          `<td>${s.entry}</td><td>${s.change_pct == null ? "" : s.change_pct + "%"}</td>` +
          `<td>${s.rsi != null ? s.rsi : ""}</td><td>${s.stop_initial}</td>` +
          `<td>${s.stop_current != null ? s.stop_current : ""}</td><td>${s.status}</td>` +
          `<td>${exit}</td><td>${pnl}</td></tr>`;
      }).join("");
      wrap.innerHTML = `<div class="u-mt12"><strong>${body.signals_total}</strong> signals ` +
        `(showing ${Math.min(50, body.signals.length)}) — errors: ` +
        `${Object.keys(body.errors || {}).length}</div>` +
        `<table class="data-table"><thead><tr><th>Symbol</th><th>Side</th><th>Signal</th>` +
        `<th>Entry</th><th>% chg</th><th>RSI</th><th>Init SL</th><th>Trail SL</th>` +
        `<th>Status</th><th>Exit</th><th>P&L</th></tr></thead><tbody>${rows}</tbody></table>`;
    };

    const _fmt_ts = (v) => (v ? String(v).slice(0, 19).replace("T", " ") : "");

    const run = async (fmt) => {
      const status = $("scr-status");
      status.textContent = fmt === "xlsx"
        ? "Building Excel report (large scans can take a minute)..."
        : "Scanning...";
      const params = scrParams();
      params.set("format", fmt);
      try {
        const res = await fetchWithTimeout(`/api/screener/scan?${params}`, 300000);
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || ("HTTP " + res.status));
        }
        if (fmt === "xlsx") {
          const blob = await res.blob();
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = `nse_momentum_${$("scr-mode").value}_${$("scr-end").value || "today"}.xlsx`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          status.textContent = "Excel download started.";
        } else {
          const body = await res.json();
          status.textContent = `${body.signals_total} signals from ` +
            `${body.scanned} symbols.`;
          renderResults(body);
        }
      } catch (e) {
        status.textContent = "Scan failed: " + e.message;
      }
    };
    $("scr-run").addEventListener("click", () => run("json"));
    $("scr-download").addEventListener("click", () => run("xlsx"));
  }

});
