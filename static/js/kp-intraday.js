// KP Intraday, KP Chart (NIFTY) and KP Intraday Report pages.
// Moved out of static/app.js (B-78). Classic script: shares the page's global scope
// with app.js, which loads first and provides $, esc, fetchWithTimeout, localTodayISO.

function kpDataQualityBanner(dq, sourceFile) {
  if (!dq || !dq.synthetic) return null;
  const el = document.createElement("div");
  el.className = "kp-data-quality-banner";
  el.setAttribute("role", "alert");
  el.style.cssText = "background:rgba(213,0,0,.12);border:1px solid var(--red,#d50000);color:var(--red,#d50000);padding:10px 14px;border-radius:6px;margin:0 0 12px;font-weight:600";
  el.textContent = `⚠ Not real KP data${sourceFile ? " (" + sourceFile + ")" : ""}: ${dq.message}`;
  return el;
}

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
  const dqBanner = kpDataQualityBanner(data.data_quality, data.source_file);
  if (dqBanner) report.appendChild(dqBanner);

  // TITLE BLOCK
  const header = document.createElement("div");
  header.className = "kp-title-block";
  header.innerHTML = `
    <h1 class="kp-title">KP INTRADAY TREND CHANGE PREDICTION REPORT</h1>
    <div class="kp-meta-line"><strong>Trading Day:</strong> ${data.trading_day}</div>
    <div class="kp-meta-line"><strong>${data.instrument}</strong> &bull; ${data.market} &bull; ${data.ayanamsa}</div>
    <div class="kp-brand">${data.brand || 'Astro Quant Research Initiative | Trading Bramha Consulting'}</div>
    ${data.status === 'experimental' ? `<p class="experimental-note"><span class="experimental-badge">Experimental</span> ${esc(data.experimental_notice || 'No validated edge; research only.')}</p>` : ''}
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
    <h2>SECTION 3 &mdash; PREDICTIVE INTRADAY PATH <span class="experimental-badge">Experimental</span></h2>
    <div class="kp-path-box">
      <p class="experimental-note"><strong>Experimental &mdash; no validated edge.</strong> On real KP data (4 Aug&ndash;30 Sep 2026) the path's direction hit rate was 50.8% and regime shifts 49.7%: chance level. Research only.</p>
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

  content.appendChild(report);
  // Render KP Intraday Price Chart with lightweight-charts.js
  renderKPIntradayPriceChart(data);
  $("kp-intraday").classList.remove("hidden");
}

async function loadKPIntradayReport(date, instrument, format, closedNote) {
  if (format === 'docx') {
    // Word export is a file download, not something to render in the panel.
    window.open('/api/kp_intraday_report?date=' + encodeURIComponent(date) +
      '&instrument=' + encodeURIComponent(instrument) + '&format=docx', '_blank');
    return;
  }

  const content = $("kp-intraday-content");
  // The date asked for; a closed day loads the next session but stays "asked for".
  if (content && !closedNote) content.dataset.requestedDate = date;
  if (content) {
    content.className = "kp-intraday-content panel-loading";
    content.textContent = `Generating KP Intraday Trend Change Prediction Report for ${date} (${instrument})...`;
  }
  try {
    const url = `/api/kp_intraday_report?date=${encodeURIComponent(date)}&instrument=${encodeURIComponent(instrument)}&format=${encodeURIComponent(format)}`;
    const response = await fetchWithTimeout(url);
    if (response.status === 400 && !closedNote) {
      // NSE closed (weekend/holiday): show the next session instead of an error.
      const err = await response.clone().json().catch(() => ({}));
      if (err.next_trading_day) {
        const dateEl = $("kp-intraday-date");
        if (dateEl) dateEl.value = err.next_trading_day;
        return loadKPIntradayReport(err.next_trading_day, instrument, format,
          `${err.error}; showing the next session, ${err.next_trading_day}.`);
      }
    }
    if (format === 'html') {
      if (!response.ok) throw new Error("unavailable (HTTP " + response.status + ")");
      const html = await response.text();
      $("kp-intraday-content").className = "kp-intraday-content";
      $("kp-intraday-content").innerHTML = html;
      $("kp-intraday-content").dataset.reportDate = date;
      if (closedNote) showKPClosedNote(closedNote);
    } else {
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      renderKPIntradayReport(data);
      content.dataset.reportDate = date;
      if (closedNote) showKPClosedNote(closedNote);
    }
  } catch (e) {
    console.error("KP Intraday report failed:", e);
    if (content) {
      content.className = "kp-intraday-content panel-error";
      content.textContent = "KP Intraday report is unavailable. Try running the report again.";
    }
  }
}

function showKPClosedNote(text) {
  const content = $("kp-intraday-content");
  if (!content) return;
  const note = document.createElement("p");
  note.className = "experimental-note";
  note.textContent = text;
  content.prepend(note);
}

function showKPNiftyClosedNote(text) {
  const content = $("kp-nifty-content");
  if (!content) return;
  const note = document.createElement("p");
  note.className = "experimental-note";
  note.textContent = text;
  content.prepend(note);
}

async function loadKPReportPage(date, note) {
  const box = $("kp-report-text");
  const status = $("kp-report-status");
  if (!box) return;
  box.dataset.reportDate = date;
  if (status) { status.className = "nifty-chart-status"; status.textContent = `Generating the report for ${date}…`; }
  try {
    const r = await fetchWithTimeout(`/api/kp_intraday_report?date=${encodeURIComponent(date)}&instrument=NIFTY&format=html`);
    if (r.status === 400 && !note) {
      const err = await r.clone().json().catch(() => ({}));
      if (err.next_trading_day) return loadKPReportPage(err.next_trading_day, `${err.error}; showing the next session.`);
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    box.innerHTML = await r.text();
    box.dataset.reportDate = date;
    if (status) status.textContent = `Live report for the NSE session of ${date}.${note ? " " + note : ""}`;
  } catch (e) {
    box.dataset.reportDate = "";
    if (status) { status.className = "nifty-chart-status error"; status.textContent = `Could not generate the report: ${e.message}`; }
  }
}

async function loadKPIntradayReportNifty(date, format, closedNote) {
  const instrument = "NIFTY";
  if (format === 'docx') {
    window.open('/api/kp_intraday_report?date=' + encodeURIComponent(date) +
      '&instrument=' + encodeURIComponent(instrument) + '&format=docx', '_blank');
    return;
  }
  const content = $("kp-nifty-content");
  if (content && !closedNote) content.dataset.requestedDate = date;
  if (content) {
    content.className = "kp-intraday-content panel-loading";
    content.textContent = `Generating KP Intraday Trend Change Prediction Report for ${date} (${instrument})...`;
  }
  try {
    const url = `/api/kp_intraday_report?date=${encodeURIComponent(date)}&instrument=${encodeURIComponent(instrument)}&format=${encodeURIComponent(format)}`;
    const response = await fetchWithTimeout(url);
    if (response.status === 400 && !closedNote) {
      const err = await response.clone().json().catch(() => ({}));
      if (err.next_trading_day) {
        const dateEl = $("kp-nifty-date");
        if (dateEl) dateEl.value = err.next_trading_day;
        return loadKPIntradayReportNifty(err.next_trading_day, format, `${err.error}; showing the next session, ${err.next_trading_day}.`);
      }
    }
    if (format === 'html') {
      if (!response.ok) throw new Error("unavailable (HTTP " + response.status + ")");
      const html = await response.text();
      $("kp-nifty-content").className = "kp-intraday-content";
      $("kp-nifty-content").innerHTML = html;
      $("kp-nifty-content").dataset.reportDate = date;
      if (closedNote) showKPNiftyClosedNote(closedNote);
    } else {
      const data = await response.json();
      if (data.error) throw new Error(data.error);
      // Render JSON into panel
      const content = $("kp-nifty-content");
      if (content) {
        content.className = "kp-intraday-content";
        content.innerHTML = `<pre style="white-space:pre-wrap;font-size:11px">${JSON.stringify(data, null, 2)}</pre>`;
      }
      if (closedNote) showKPNiftyClosedNote(closedNote);
    }
  } catch (e) {
    console.error("KP NIFTY report failed:", e);
    if (content) {
      content.className = "kp-intraday-content panel-error";
      content.textContent = "KP Intraday report for NIFTY is unavailable. Try running the report again.";
    }
  }
}

async function generateKPSampleDataNifty(date) {
  const content = $("kp-nifty-content");
  try {
    if (content) { content.className = "kp-intraday-content panel-loading"; content.textContent = "Computing KP data from Swiss Ephemeris…"; }
    const response = await fetchWithTimeout("/api/kp_intraday_sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date })
    });
    const data = await response.json();
    if (data.error && response.status !== 409) throw new Error(data.error);
    // Load NIFTY report after generation
    loadKPIntradayReportNifty(date, $("kp-nifty-format") ? $("kp-nifty-format").value : "html");
  } catch (e) {
    console.error("KP NIFTY data generation failed:", e);
    if (content) {
      content.className = "kp-intraday-content panel-error";
      content.textContent = `KP data could not be generated: ${e.message}`;
    }
  }
}

// Computes the month's KP data from Swiss Ephemeris on the server, then loads
// the report. 409 means real data already exists, which is fine: just load it.
async function generateKPSampleData(date) {
  const content = $("kp-intraday-content");
  try {
    if (content) { content.className = "kp-intraday-content panel-loading"; content.textContent = "Computing KP data from Swiss Ephemeris…"; }
    const response = await fetchWithTimeout("/api/kp_intraday_sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date })
    });
    const data = await response.json();
    if (data.error && response.status !== 409) throw new Error(data.error);
    loadKPIntradayReport(date, $("kp-intraday-instrument").value, $("kp-intraday-format").value);
  } catch (e) {
    console.error("KP data generation failed:", e);
    if (content) {
      content.className = "kp-intraday-content panel-error";
      content.textContent = `KP data could not be generated: ${e.message}`;
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
    if (date) generateKPSampleData(date);
  });
}

// KP NIFTY-only page listeners
if ($("kp-nifty-run")) {
  $("kp-nifty-run").addEventListener("click", () => {
    const date = ($("kp-nifty-date") && $("kp-nifty-date").value) || ($("date") && $("date").value);
    const instrument = "NIFTY";
    const format = $("kp-nifty-format") ? $("kp-nifty-format").value : "html";
    if (date) {
      // Re-use the existing loader but render into the NIFTY content panel
      loadKPIntradayReportNifty(date, format);
    }
  });
}

if ($("kp-nifty-sample")) {
  $("kp-nifty-sample").addEventListener("click", () => {
    const date = ($("kp-nifty-date") && $("kp-nifty-date").value) || ($("date") && $("date").value);
    if (date) generateKPSampleDataNifty(date);
  });
}

// Sync KP NIFTY date with main Date control
function syncKPNiftyDate() {
  const mainDate = $("date") && $("date").value;
  const kpNiftyDate = $("kp-nifty-date");
  if (kpNiftyDate && mainDate && (!kpNiftyDate.value || kpNiftyDate.value === "")) {
    kpNiftyDate.value = mainDate;
  }
}
if ($("date") && $("kp-nifty-date")) {
  // Initialize on load
  syncKPNiftyDate();
  // Update when main date changes
  $("date").addEventListener("change", syncKPNiftyDate);
}

// Crash Windows default one-month forward window
if ($("kp-intraday-path")) {
  $("kp-intraday-path").addEventListener("click", async () => {
    const date = ($("kp-intraday-date") && $("kp-intraday-date").value) || ($("date") && $("date").value);
    const instrument = $("kp-intraday-instrument") ? $("kp-intraday-instrument").value : "NIFTY";
    if (!date) { alert("Select a date"); return; }
    const btn = $("kp-intraday-path");
    btn.disabled = true;
    try {
      const res = await fetchWithTimeout(`/api/engine/intraday_path?date=${encodeURIComponent(date)}&instrument=${encodeURIComponent(instrument)}`);
      if (!res.ok) throw new Error("unavailable (HTTP " + res.status + ")");
      const data = await res.json();
      const panel = $("kp-intraday-path-chart");
      if (panel) {
        panel.style.display = "";
        panel.querySelectorAll(".kp-data-quality-banner").forEach(b => b.remove());
        const dqBanner = kpDataQualityBanner(data.data_quality);
        if (dqBanner) panel.prepend(dqBanner);
      }
      const pre = $("kp-path-data");
      if (pre) {
        pre.textContent = data.series ? JSON.stringify(data.series, null, 2) : "No path series returned.";
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
    } catch (e) {
      console.error("KP intraday path failed:", e);
      const panel = $("kp-intraday-path-chart");
      if (panel) panel.style.display = "";
      const pre = $("kp-path-data");
      if (pre) {
        pre.style.display = "";
        pre.textContent = "Predictive path is unavailable: " + (e.message || e);
      }
    } finally {
      btn.disabled = false;
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

function initKPIntradayChart() {
  const chartContainer = document.getElementById('kp-chart-container');
  if (!chartContainer) return null;

  // Dispose any prior chart (theme/size changes, re-renders)
  if (window.kpChart) {
    try { window.kpChart.remove(); } catch (e) {}
    window.kpChart = null;
  }

  // Lightweight Charts setup (numeric sizes + autoSize; strings are invalid)
  const chart = LightweightCharts.createChart(chartContainer, {
    autoSize: true,
    height: 400,
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
  return chart;
}

// Render the KP Intraday Price Chart panel: cumulative signal-score path for
// the generated report, with Tier-1 / regime-shift markers matching the legend.
function renderKPIntradayPriceChart(data) {
  const chart = initKPIntradayChart();
  if (!chart) return;

  // Drop any previous score series
  if (window.kpScoreSeries) {
    try { chart.removeSeries(window.kpScoreSeries); } catch (e) {}
    window.kpScoreSeries = null;
  }

  const day = String(data.trading_day || "");
  const [y, m, d] = day.split("-").map(Number);
  const tsOf = (hm) => {
    const [hh, mm] = String(hm).split(":").map(Number);
    return Date.UTC(y, (m || 1) - 1, d || 1, hh || 0, mm || 0) / 1000;
  };

  const changes = (data.trend_changes || []).slice().sort((a, b) => String(a.time).localeCompare(String(b.time)));
  const points = [];
  const markers = [];
  let cum = 0;
  for (const tc of changes) {
    const score = Number(tc.score) || 0;
    const step = tc.direction === "Bullish" ? score : tc.direction === "Bearish" ? -score : 0;
    cum += step;
    const t = tsOf(tc.time);
    points.push({ time: t, value: Number(cum.toFixed(2)) });
    const grade = String(tc.grade || "");
    if (grade.includes("REGIME SHIFT")) {
      markers.push({ time: t, position: "inBar", color: "#f59e0b", shape: "circle", text: "Regime" });
    } else if (grade.includes("TIER-1")) {
      markers.push({
        time: t, position: "aboveBar",
        color: tc.direction === "Bearish" ? "#ef4444" : "#22c55e",
        shape: tc.direction === "Bearish" ? "arrowDown" : "arrowUp", text: "T1",
      });
    }
  }
  // Flat baseline so the first change starts from zero
  if (points.length) points.unshift({ time: tsOf("09:15"), value: 0 });

  const series = chart.addLineSeries({
    color: "#38bdf8",
    lineWidth: 2,
    priceLineVisible: false,
  });
  series.setData(points);
  try { series.setMarkers(markers); } catch (e) {}
  window.kpScoreSeries = series;
  chart.timeScale().fitContent();
}

// ---------------------------------------------------------------
// Daily Indication Balance chart
// ---------------------------------------------------------------
