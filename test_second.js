// Dummy start
 options = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

;

function cellCenter(row, col) {
  return { x: (col - 1) * CELL + CELL / 2, y: (row - 1) * CELL + CELL / 2 };
}



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
    sel.innerHTML = "";
    for (const a of data.anchors) {
      const opt = document.createElement("option");
      opt.value = a.key;
      opt.textContent = a.name;
      sel.appendChild(opt);
    }
    sel.value = "nse";
  } catch (e) {
    console.error(e);
    $("anchor").innerHTML = '<option value="">Failed to load anchors</option>';
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
  try {
    const response = await fetchWithTimeout("/api/bullish_futurecast?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderBullishFuturecast(data);
  } catch (e) {
    console.error("Bullish futurecast failed:", e);
    const timeline = $("bullish-timeline");
    if (timeline) {
      timeline.innerHTML = '<div class="bullish-cluster" style="flex:0 0 100%;text-align:center;color:var(--red);padding:40px;">Failed to load bullish futurecast: ' + e.message + '</div>';
    }
    $("bullish-center-marker").style.display = "none";
  }
}

async function loadFuturecast(date) {
  try {
    const response = await fetchWithTimeout("/api/futurecast?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderFuturecast(data);
  } catch (e) {
    console.error("Crash futurecast failed:", e);
    $("futurecast-results").innerHTML = '<p class="error" style="color:var(--red);padding:20px;">Failed to load crash futurecast: ' + e.message + '</p>';
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
  $("sector-vedha-sub").textContent =
    `${data.date} .  ${data.signals.length} active signal${data.signals.length === 1 ? "" : "s"} .  backtested 2021-26`;
  $("sector-vedha-note").textContent = data.disclaimer;

  const grid = $("sector-vedha-active");
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
  try {
    const response = await fetchWithTimeout("/api/sector_vedha?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderSectorVedha(data);
  } catch (e) {
    console.error("Sector vedha failed:", e);
    $("sector-vedha-active").innerHTML =
      '<div class="sv-empty" style="color:var(--red)">Failed to load sector vedha radar: ' + e.message + '</div>';
  }
}

function renderLargecapDivergence(data) {
  const content = $("largecap-divergence-content");
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
    lowSection.querySelector(".lcd-toggle").addEventListener("click", (e) => {
      lowList.style.display = lowList.style.display === "none" ? "block" : "none";
      e.target.textContent = lowList.style.display === "none" ? "▶" : "▼";
    });
    content.appendChild(lowSection);
  }

  $("largecap-divergence").classList.remove("hidden");
}

async function loadLargecapDivergence(date) {
  try {
    const response = await fetchWithTimeout("/api/largecap_divergence?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderLargecapDivergence(data);
  } catch (e) {
    console.error("Large-cap divergence failed:", e);
    $("largecap-divergence-content").innerHTML = 
      '<div class="lcd-empty" style="color:var(--red)">Failed to load large-cap divergence: ' + e.message + '</div>';
    $("largecap-divergence").classList.remove("hidden");
  }
}

function renderFmcgSignals(data) {
  const content = $("fmcg-signals-content");
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
    detailSection.querySelector(".fmcg-toggle").addEventListener("click", (e) => {
      detailList.style.display = detailList.style.display === "none" ? "block" : "none";
      e.target.textContent = detailList.style.display === "none" ? "▶" : "▼";
    });
    content.appendChild(detailSection);
  }

  $("fmcg-signals").classList.remove("hidden");
}

async function loadFmcgSignals(date, price) {
  try {
    let url = "/api/fmcg_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderFmcgSignals(data);
  } catch (e) {
    console.error("FMCG signals failed:", e);
    $("fmcg-signals-content").innerHTML = 
      '<div class="fmcg-empty" style="color:var(--red)">Failed to load FMCG signals: ' + e.message + '</div>';
    $("fmcg-signals").classList.remove("hidden");
  }




function renderTourismSignals(data) {
  const content = $("tourism-signals-content");
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

  if (data.active_signals.length > 0) {
    const signalsSection = document.createElement("div");
    signalsSection.className = "tourism-section";
    signalsSection.innerHTML = "<h4>Active Signals</h4>";
    for (const s of data.active_signals) {
      const card = document.createElement("div");
      card.className = "tourism-card";
      card.textContent = s;
      signalsSection.appendChild(card);
    }
    content.appendChild(signalsSection);
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

  if (data.details) {
    const detailSection = document.createElement("div");
    detailSection.className = "tourism-section";
    detailSection.innerHTML = `<h4>Details <span class="tourism-toggle">\u25bc</span></h4>`;
    const detailList = document.createElement("div");
    detailList.className = "tourism-detail-list";
    for (const [key, val] of Object.entries(data.details)) {
      const card = document.createElement("div");
      card.className = "tourism-card";
      card.textContent = `${key}: ${val}`;
      detailList.appendChild(card);
    }
    detailSection.appendChild(detailList);
    content.appendChild(detailSection);
  }

  $("tourism-signals").classList.remove("hidden");
}

async function loadTourismSignals(date, price) {
  try {
    let url = "/api/tourism_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderTourismSignals(data);
  } catch (e) {
    console.error("Tourism signals failed:", e);
    $("tourism-signals-content").innerHTML = 
      '<div class="tourism-empty" style="color:var(--red)">Failed to load Tourism signals: ' + e.message + '</div>';
    $("tourism-signals").classList.remove("hidden");
  }
}


function renderChemicalSignals(data) {
  const content = $("chemical-signals-content");
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
    } for (const [key, val] of  bject.entries(data.de ails)) {) {
  const content = $("tourism-signals-content");
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

  // Conviction badge
  const badge = document.createElement("div");
  badge.className = "tourism-badge " + data.conviction.toLowerCase();
  badge.textContent = data.conviction + (data.is_strong_bullish ? " .  STRONG" : data.is_bullish ? " .  BULLISH" : " .  WATCH");
  content.appendChild(badge);

  // Active signals
  if (data.active_signals.length > 0) {
    const signalsSection = document.createElement("div");
    signalsSection.className = "tourism-section";
    signalsSection.innerHTML = "<h4>Active Signals</h4>";
    for (const s of data.active_signals) {
      const card = document.createElement("div");
      card.className = "tourism-card";
      card.textContent = s;
      signalsSection.appendChild(card);
    }
    content.appendChild(signalsSection);
  }

  // Price levels
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

  // Details (collapsible)
  if (data.details) {
    const detailSection = document.createElement("div");
    detailSection.className = "tourism-section";
    detailSection.innerHTML = `<h4>Details <span class="tourism-toggle">▼</span></h4>`;
    const detailList = document.createElement("div");
    detailList.className = "tourism-detail-list";
    for (const [key, val] of Object.entries(data.details)) {
      if (typeof val === 'boolean' && val) {
        const card = document.createElement("div");
        card.className = "tourism-card";
        card.textContent = key;
        detailList.appendChild(card);
      }
    }
    detailSection.appendChild(detailList);
    detailSection.querySelector(".tourism-toggle").addEventListener("click", (e) => {
      detailList.style.display = detailList.style.display === "none" ? "block" : "none";
      e.target.textContent = detailList.style.display === "none" ? "▶" : "▼";
    });
    content.appendChild(detailSection);
  }

  $("tourism-signals").classList.remove("hidden");
}

, val] of Object.entries(data.details)) {
      if (typeof val === 'boolean' && val) {
        const card = document.createElement("div");
        card.className = "chemical-card";
        card.textContent = key;
        detailList.appendChild(card);
      }
    }
    detailSection.appendChild(detailList);
    detailSection.querySelector(".chemical-toggle").addEventListener("click", (e) => {
      detailList.style.display = detailList.style.display === "none" ? "block" : "none";
      e.target.textContent = detailList.style.display === "none" ? "▶" : "▼";
    });
    content.appendChild(detailSection);
  }

  $("chemical-signals").classList.remove("hidden");
}

async function loadChemicalSignals(date, price) {
  try {
    let url = "/api/chemical_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderChemicalSignals(data);
  } catch (e) {
    console.error("Chemical signals failed:", e);
    $("chemical-signals-content").innerHTML = 
      '<div class="chemical-empty" style="color:var(--red)">Failed to load Chemical signals: ' + e.message + '</div>';
    $("chemical-signals").classList.remove("hidden");
  }
}


function renderAlcoholSignals(data) {
  const content = $("alcohol-signals-content");
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
    detailSection.querySelector(".alcohol-toggle").addEventListener("click", (e) => {
      detailList.style.display = detailList.style.display === "none" ? "block" : "none";
      e.target.textContent = detailList.style.display === "none" ? "▶" : "▼";
    });
    content.appendChild(detailSection);
  }

  $("alcohol-signals").classList.remove("hidden");
}

async function loadAlcoholSignals(date, price) {
  try {
    let url = "/api/alcohol_signals?date=" + encodeURIComponent(date);
    if (price) url += "&price=" + encodeURIComponent(price);
    const response = await fetchWithTimeout(url);
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderAlcoholSignals(data);
  } catch (e) {
    console.error("Alcohol signals failed:", e);
    $("alcohol-signals-content").innerHTML = 
      '<div class="alcohol-empty" style="color:var(--red)">Failed to load Alcohol signals: ' + e.message + '</div>';
    $("alcohol-signals").classList.remove("hidden");
  }
}

function renderLunarForecast(data) {
  const content = $("lunar-forecast-content");
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
    row.innerHTML = `
      <td><strong>${sector}</strong></td>
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
  try {
    const response = await fetchWithTimeout("/api/lunar_forecast?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderLunarForecast(data);
    // Store for clipboard/share
    window.currentLunarCard = data.card;
    window.currentLunarForecast = data.forecast;
  } catch (e) {
    console.error("Lunar forecast failed:", e);
    $("lunar-forecast-content").innerHTML = 
      '<div class="lf-empty" style="color:var(--red)">Failed to load Lunar forecast: ' + e.message + '</div>';
    $("lunar-forecast").classList.remove("hidden");
  }
}

function copyLunarForecast() {
  if (!window.currentLunarCard) return;
  const text = formatCardForClipboard(window.currentLunarCard);
  navigator.clipboard.writeText(text).then(() => {
    showToast("Copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy");
  });
}

function shareLunarForecast() {
  if (!window.currentLunarCard) return;
  const text = formatCardForSocialMedia(window.currentLunarCard);
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
    $("weekly-commentary-content").innerHTML = '<p class="error" style="color:var(--red);padding:20px;">Failed to load weekly commentary: ' + e.message + '</p>';
    $("weekly-commentary").classList.remove("hidden");
  }
}

async function loadBullionVedha(date, weekly = false) {
  const endpoint = weekly ? "/api/bullion_vedha_week" : "/api/bullion_vedha";
  try {
    const response = await fetchWithTimeout(endpoint + "?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderBullionVedha(data, weekly);
  } catch (e) {
    console.error("Bullion vedha failed:", e);
    $("bullion-vedha-content").innerHTML = '<p class="error" style="color:var(--red);padding:20px;">Failed to load bullion vedha: ' + e.message + '</p>';
    $("bullion-vedha").classList.remove("hidden");
  }
}

async function loadTransitVedha(date, weekly = false) {
  const endpoint = weekly ? "/api/transit_vedha_week" : "/api/transit_vedha";
  try {
    const response = await fetchWithTimeout(endpoint + "?date=" + encodeURIComponent(date));
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    renderTransitVedha(data, weekly);
  } catch (e) {
    console.error("Transit vedha failed:", e);
    $("transit-vedha-content").innerHTML = '<p class="error" style="color:var(--red);padding:20px;">Failed to load transit vedha: ' + e.message + '</p>';
    $("transit-vedha").classList.remove("hidden");
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
  $("bullion-vedha").classList.remove("hidden");
}

function renderTransitVedha(data, weekly) {
  const box = $("transit-vedha-content");
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
  $("transit-vedha").classList.remove("hidden");
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
  const params = new URLSearchParams({
    date: $("date").value,
    time: $("time").value,
    tz: $("tz").value,
    anchor: $("anchor").value,
    school: $("school").value,
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
    await loadFuturecast(data.date);
    await loadSectorVedha(data.date);
    await loadLargecapDivergence(data.date);
    await loadFmcgSignals(data.date);
    await loadTourismSignals(data.date);
    await loadChemicalSignals(data.date);
    await loadAlcoholSignals(data.date);
    await loadLunarForecast(data.date);
    await loadWeeklyCommentary(data.date);
    await loadBullionVedha(data.date, true);  // weekly view
    await loadTransitVedha(data.date, true);  // weekly view
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
    $("verdict").classList.add("hidden");
    alert("Prediction failed: " + e.message);
  } finally {
    btn.disabled = false;
  }
}

$("run").addEventListener("click", run);
const dateInput = $("date");
dateInput.addEventListener("click", () => {
  if (typeof dateInput.showPicker === "function") dateInput.showPicker();
});

// Weekly commentary generate button
$("weekly-commentary-run").addEventListener("click", () => {
  const date = $("weekly-commentary-date").value;
  if (date) loadWeeklyCommentary(date);
});

// Bullion vedha generate button
$("bullion-vedha-run").addEventListener("click", () => {
  const date = $("bullion-vedha-date").value;
  const weekly = $("bullion-vedha-week").checked;
  if (date) loadBullionVedha(date, weekly);
});

// Transit vedha generate button
$("transit-vedha-run").addEventListener("click", () => {
  const date = $("transit-vedha-date").value;
  const weekly = $("transit-vedha-week").checked;
  if (date) loadTransitVedha(date, weekly);
});

// Large-cap divergence generate button
$("largecap-divergence-run").addEventListener("click", () => {
  const date = $("largecap-divergence-date").value;
  if (date) loadLargecapDivergence(date);
});

// FMCG signals generate button
$("fmcg-signals-run").addEventListener("click", () => {
  const date = $("fmcg-signals-date").value;
  const price = $("fmcg-signals-price").value;
  if (date) loadFmcgSignals(date, price ? parseFloat(price) : null);
});

// Tourism signals generate button
$("tourism-signals-run").addEventListener("click", () => {
  const date = $("tourism-signals-date").value;
  const price = $("tourism-signals-price").value;
  if (date) loadTourismSignals(date, price ? parseFloat(price) : null);
});

// Chemical signals generate button
$("chemical-signals-run").addEventListener("click", () => {
  const date = $("chemical-signals-date").value;
  const price = $("chemical-signals-price").value;
  if (date) loadChemicalSignals(date, price ? parseFloat(price) : null);
});

// Alcohol signals generate button
$("alcohol-signals-run").addEventListener("click", () => {
  const date = $("alcohol-signals-date").value;
  const price = $("alcohol-signals-price").value;
  if (date) loadAlcoholSignals(date, price ? parseFloat(price) : null);
});

// Lunar forecast run button
$("lunar-forecast-run").addEventListener("click", () => {
  const date = $("lunar-forecast-date").value;
  if (date) loadLunarForecast(date);
});

document.addEventListener("DOMContentLoaded", async () => {
  setTodayAsDefault();
  // Set weekly commentary date to today
  const wcDate = $("weekly-commentary-date");
  if (wcDate && !wcDate.value) {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    wcDate.value = `${now.getFullYear()}-${month}-${day}`;
  }
  // Set bullion vedha date to today
  const bvDate = $("bullion-vedha-date");
  if (bvDate && !bvDate.value) {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    bvDate.value = `${now.getFullYear()}-${month}-${day}`;
  }
  // Set transit vedha date to today
  const tvDate = $("transit-vedha-date");
  if (tvDate && !tvDate.value) {
    const now = new Date();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    tvDate.value = `${now.getFullYear()}-${month}-${day}`;
  }
  await loadPresets();
  await run();
});
