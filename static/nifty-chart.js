/* NIFTY 50 price chart + date-wise astro prediction overlay.
   Uses TradingView Lightweight Charts (self-hosted, MIT license). */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  var chart = null;
  var candleSeries = null;
  var bandSeriesList = [];
  var lastPredictionByDate = {};
  var tradingDays = [];
  var predByDate = {};
  var crashLineSeries = null;
  var crashByDate = {};
  var statusEl, tipEl;

  function fetchWithTimeout(url, ms) {
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, ms || 150000);
    return fetch(url, { signal: ctrl.signal }).finally(function () { clearTimeout(t); });
  }

  function setStatus(msg, isErr) {
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("error", !!isErr);
  }

function bizDay(iso) { return iso; } // lightweight-charts accepts YYYY-MM-DD

  function sentimentOf(p) {
    if (!p || p.error) return "neutral";
    var v = (p.verdict || "").toUpperCase();
    if (v.indexOf("BEAR") >= 0) return "bearish";
    if (v.indexOf("BULL") >= 0) return "bullish";
    if (v.indexOf("CAUTION") >= 0) return "caution";
    return "neutral";
  }

  function strengthOf(p) {
    var s = ((p && p.strength) || "").toUpperCase();
    if (s.indexOf("STRONG") >= 0) return 2;
    if (s.indexOf("MODERATE") >= 0) return 1;
    return 0;
  }

  function buildBands(tradingDays, predByDate) {
    /* Group consecutive trading days of the same non-neutral sentiment and
       return arrays of {time, value} segments for area-series backgrounds. */
    var segments = [];
    var current = null;
    var prevKnown = "neutral";
    tradingDays.forEach(function (d) {
      var p = predByDate[d] || null;
      var sent = p ? sentimentOf(p) : prevKnown;
      if (sent === "caution") sent = "bearish";
      if (sent === "neutral") sent = prevKnown;
      prevKnown = sent;
      if (!current || current.sent !== sent) {
        if (current) segments.push(current);
        current = { sent: sent, points: [] };
      }
      current.points.push({ time: d, value: 100 });
    });
    if (current) segments.push(current);

    // pad segments so each area spans its full extent inclusively
    return segments.map(function (seg) {
      // close off by adding a 0 after last point
      var pts = seg.points.slice();
      return { sent: seg.sent, data: pts };
    });
  }

  function buildMarkers(tradingDays, predByDate, alertRunActive) {
    var markers = [];
    var inAlertRun = !!alertRunActive;
    tradingDays.forEach(function (d) {
      var p = predByDate[d];
      if (!p || p.error) { inAlertRun = false; return; }
      var sent = sentimentOf(p);
      var strong = strengthOf(p) >= 1;
      // Reversal / risk alert: mark only the first day of a contiguous
      // alert run so blanket multi-week windows don't drown the chart.
      if (p.alert && !inAlertRun) {
        markers.push({
          time: d,
          position: "aboveBar",
          color: "#f59e0b",
          shape: "circle",
          text: p.alert_level === "EXTREME" ? "!!" : "!"
        });
      }
      inAlertRun = !!p.alert;
      if (sent === "bullish" && strong) {
        markers.push({
          time: d,
          position: "belowBar",
          color: "#16a34a",
          shape: "arrowUp",
          text: strengthOf(p) === 2 ? "▲▲" : "▲"
        });
      } else if (sent === "bearish" && strong) {
        markers.push({
          time: d,
          position: "aboveBar",
          color: "#dc2626",
          shape: "arrowDown",
          text: strengthOf(p) === 2 ? "▼▼" : "▼"
        });
      }
      // Lunar phase markers
      if (p.lunar_phase === "PURNIMA") {
        markers.push({
          time: d,
          position: "aboveBar",
          color: "#ffffff",
          shape: "circle",
          text: "🌕"
        });
      } else if (p.lunar_phase === "AMAVASYA") {
        markers.push({
          time: d,
          position: "aboveBar",
          color: "#ffd700",
          shape: "circle",
          text: "🌑"
        });
      } else if (p.lunar_phase === "PRE_PURNIMA") {
        markers.push({
          time: d,
          position: "aboveBar",
          color: "#e0e0e0",
          shape: "circle",
          text: "🌔"
        });
      } else if (p.lunar_phase === "PRE_AMAVASYA") {
        markers.push({
          time: d,
          position: "aboveBar",
          color: "#b0b0b0",
          shape: "circle",
          text: "🌘"
        });
      }
    });
    buildMarkers.lastAlertState = inAlertRun;
    return markers;
  }

  var CRASH_COLORS = {
    1: "rgba(251,146,60,0.07)",
    2: "rgba(251,146,60,0.09)",
    3: "rgba(248,113,113,0.11)",
    4: "rgba(239,68,68,0.15)",
    5: "rgba(239,68,68,0.19)",
    6: "rgba(239,68,68,0.25)",
    7: "rgba(220,38,38,0.32)"
  };

  function buildCrashBands(tradingDays, predByDate) {
    /* Contiguous runs of days sharing the same crash-calendar severity. */
    var segments = [];
    var current = null;
    tradingDays.forEach(function (d) {
      var p = predByDate[d] || {};
      var rank = p.risk_rank || 0;
      if (!current || current.rank !== rank) {
        if (current && current.rank > 0) segments.push(current);
        current = { rank: rank, points: [] };
      }
      if (rank > 0) current.points.push({ time: d, value: 100 });
      else if (current) { if (current.points.length) segments.push(current); current = null; }
    });
    if (current && current.rank > 0 && current.points.length) segments.push(current);
    return segments;
  }

  function renderCrashBands(chart, tradingDays, predByDate, bandList) {
    buildCrashBands(tradingDays, predByDate).forEach(function (seg) {
      var s = chart.addAreaSeries({
        priceScaleId: "bands",
        lineVisible: false,
        topColor: CRASH_COLORS[seg.rank] || CRASH_COLORS[3],
        bottomColor: CRASH_COLORS[seg.rank] || CRASH_COLORS[3],
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false
      });
      s.setData(seg.points);
      bandList.push(s);
    });
  }

  function createBase(candles) {
    var el = $("nifty-chart");
    el.innerHTML = "";
    if (chart) { try { chart.remove(); } catch (e) {} }
    if (crashLineSeries) crashLineSeries = null;
    chart = LightweightCharts.createChart(el, {
      autoSize: true,
      layout: {
        background: { color: "#0d1420" },
        textColor: "#c8d3e0",
        fontFamily: "Segoe UI, sans-serif",
        fontSize: 11
      },
      grid: {
        vertLines: { color: "#1d2a3d" },
        horzLines: { color: "#1d2a3d" }
      },
      rightPriceScale: { borderColor: "#2a3a52" },
      timeScale: { borderColor: "#2a3a52", timeVisible: false }
    });

    candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      borderVisible: false
    });
    candleSeries.setData(candles.map(function (c) {
      return { time: bizDay(c.time), open: c.open, high: c.high, low: c.low, close: c.close };
    }));
    tradingDays = candles.map(function (c) { return c.time; });
    predByDate = {};
    bandSeriesList = [];

    // hover tooltip: bullish/bearish + reversal confluence details
    chart.subscribeCrosshairMove(function (param) {
      handleCrosshair(param);
    });
    chart.timeScale().fitContent();
  }

  function applyOverlay(series) {
    predByDate = {};
    series.forEach(function (p) { predByDate[p.date] = p; });
    lastPredictionByDate = predByDate;

    // drop previous overlay series before rebuilding
    bandSeriesList.forEach(function (s) { try { chart.removeSeries(s); } catch (e) {} });
    bandSeriesList = [];
    candleSeries.setMarkers([]);

    // sentiment color bands (background tint at bottom overlay)
    var bandColors = {
      bullish: "rgba(34,197,94,0.14)",
      bearish: "rgba(239,68,68,0.16)",
      neutral: "rgba(120,130,150,0.05)"
    };
    var bandsBefore = bandSeriesList.length;
    buildBands(tradingDays, predByDate).forEach(function (seg) {
      if (seg.sent === "neutral") return;
      var s = chart.addAreaSeries({
        priceScaleId: "bands",
        lineVisible: false,
        topColor: bandColors[seg.sent],
        bottomColor: bandColors[seg.sent],
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false
      });
      s.setData(seg.data);
      bandSeriesList.push(s);
    });

    // Crash calendar severity bands (red intensity by window level)
    renderCrashBands(chart, tradingDays, predByDate, bandSeriesList);

    // Configure the hidden overlay scale only if a series actually created it
    if (bandSeriesList.length > bandsBefore) {
      try {
        chart.priceScale("bands").applyOptions({
          visible: false,
          scaleMargins: { top: 0, bottom: 0 }
        });
      } catch (e) { /* scale not yet created - skip */ }
    }

    candleSeries.setMarkers(buildMarkers(tradingDays, predByDate));
    var histAlertState = buildMarkers.lastAlertState;

    // Future forecast: extend bands + markers on business days after last candle
    var todayIso = new Date().toISOString().slice(0, 10);
    var futureDays = series
      .map(function (p) { return p.date; })
      .filter(function (d) {
        if (d <= (tradingDays.length ? tradingDays[tradingDays.length - 1] : todayIso)) return false;
        var dow = new Date(d + "T00:00:00").getDay();
        return dow >= 1 && dow <= 5; // Mon-Fri only
      });
    if (futureDays.length) {
      buildBands(futureDays, predByDate).forEach(function (seg) {
        if (seg.sent === "neutral") return;
        var s = chart.addAreaSeries({
          priceScaleId: "bands",
          lineVisible: false,
          topColor: bandColors[seg.sent],
          bottomColor: bandColors[seg.sent],
          crosshairMarkerVisible: false,
          lastValueVisible: false,
          priceLineVisible: false
        });
        s.setData(seg.data);
        bandSeriesList.push(s);
      });
      // dedicated marker line so future markers have a host series
      var futLine = chart.addLineSeries({
        priceScaleId: "bands",
        lineVisible: false,
        pointMarkersVisible: false,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false
      });
      futLine.setData(futureDays.map(function (d) { return { time: d, value: 0 }; }));
      futLine.setMarkers(buildMarkers(futureDays, predByDate, histAlertState));
      bandSeriesList.push(futLine);
    }

    // Auto-fit chart to container window on load
    setTimeout(function () {
      try { chart.timeScale().fitContent(); } catch(e){}
    }, 50);
  }

  function handleCrosshair(param) {
    var el = $("nifty-chart");
    if (!param.time || !param.point) { tipEl.classList.add("hidden"); return; }
    var p = predByDate[param.time];
    if (!p || p.error) { tipEl.classList.add("hidden"); return; }

      var v = (p.verdict || "NEUTRAL").toUpperCase();
      var vClass = v.indexOf("BULL") >= 0 ? "bull" : (v.indexOf("BEAR") >= 0 ? "bear" : "neut");
      var html = "";

      // Header: date + verdict badge + net score
      html += "<div class='tip-head'><strong>" + param.time + "</strong>" +
        "<span class='tip-badge " + vClass + "'>" + (p.verdict || "-") +
        (p.strength ? " · " + p.strength : "") + "</span></div>";
      html += "<div class='tip-score'>Net score: <b>" + (p.net != null ? p.net : p.score) + "</b></div>";

      // Lunar phase
      var lp = p.lunar_phase;
      if (lp) {
        var lpLabel = lp === "PURNIMA" ? "🌕 Purnima (Full Moon)" :
                      lp === "AMAVASYA" ? "🌑 Amavasya (New Moon)" :
                      lp === "PRE_PURNIMA" ? "🌔 Pre-Purnima" :
                      lp === "PRE_AMAVASYA" ? "🌘 Pre-Amavasya" : lp;
        var lpColor = lp === "PURNIMA" ? "#ffffff" :
                      lp === "AMAVASYA" ? "#ffd700" :
                      lp === "PRE_PURNIMA" ? "#e0e0e0" : "#b0b0b0";
        html += "<div class='tip-row' style='color:" + lpColor + "'><b>Lunar:</b> " + lpLabel + "</div>";
      }

      // Bullish / bearish vedha drivers
      var drv = p.drivers || {};
      function drvLine(h) {
        return h.symbol + " " + h.planet + " → " + h.point + " (" + h.ray + " ray)";
      }
      if (drv.benefic && drv.benefic.length) {
        html += "<div class='tip-sec tip-sup'>Support</div>";
        drv.benefic.forEach(function (h) {
          html += "<div class='tip-row sup'>▲ " + drvLine(h) + "</div>";
        });
      }
      if (drv.malefic && drv.malefic.length) {
        html += "<div class='tip-sec tip-pres'>Pressure</div>";
        drv.malefic.forEach(function (h) {
          html += "<div class='tip-row pres'>▼ " + drvLine(h) + "</div>";
        });
      }

      // Reversal / risk windows
      if (p.alert) {
        html += "<div class='tip-sec tip-alert'>⚠ Reversal / risk" +
          (p.alert_level ? " · " + p.alert_level : "") + "</div>";
        (p.windows || []).forEach(function (w) {
          html += "<div class='tip-row win'><b>" + (w.level || "?") + "</b> · " +
            (w.bias || "-") + "<br><span>" + (w.title || "") + "</span></div>";
        });
      }

      // Crash calendar severity badge
      if ((p.risk_rank || 0) > 0) {
        html += "<div class='tip-row'><span class='tip-badge bear'>☠ Crash calendar: " +
          (p.risk_label || "ACTIVE") + "</span></div>";
      }

      // Bearish crash-score overlay (if enabled)
      var cs = crashByDate[param.time];
      if (cs && cs.score > 0) {
        html += "<div class='tip-row'><b style='color:#ef4444'>Crash score: " + cs.score + "/20</b>" +
          (cs.reasons && cs.reasons.length
            ? "<div class='tip-row dim'>" + cs.reasons.slice(0, 3).join(" · ") + "</div>"
            : "") + "</div>";
      }

      // Confluence snapshot
      var cf = p.confluence;
      if (cf && cf.signal && cf.signal !== "NEUTRAL") {
        var cfClass = cf.signal === "BULLISH" ? "bull" : "bear";
        html += "<div class='tip-sec'>Confluence</div>" +
          "<div class='tip-row'><span class='tip-badge " + cfClass + "'>" + cf.signal + "</span>" +
          " bull " + (cf.bull != null ? cf.bull : 0) + " vs bear " + (cf.bear != null ? cf.bear : 0) +
          " (net " + (cf.net != null ? cf.net : 0) + ")</div>";
        if (cfClass === "bull" && cf.bull_sectors.length) {
          html += "<div class='tip-row dim'>Agreeing: " + cf.bull_sectors.join(", ") + "</div>";
        } else if (cfClass === "bear" && cf.bear_sectors.length) {
          html += "<div class='tip-row dim'>Agreeing: " + cf.bear_sectors.join(", ") + "</div>";
        }
      }

      if (p.rec) html += "<div class='tip-rec'>" + p.rec + "</div>";

      tipEl.innerHTML = html;
      var tw = tipEl.offsetWidth || 300, th = tipEl.offsetHeight || 160;
      tipEl.style.left = Math.max(4, Math.min(param.point.x + 14, el.clientWidth - tw - 6)) + "px";
      tipEl.style.top = Math.max(4, Math.min(param.point.y + 12, el.clientHeight - th - 6)) + "px";
      tipEl.classList.remove("hidden");
  }

  function defaultDates() {
    // Year-over-year default: 1 yr back -> today (no future forecast by default)
    var to = new Date();
    var from = new Date();
    from.setFullYear(from.getFullYear() - 1);
    return [from, to];
  }

  async function loadCrashScore() {
    var on = $("nifty-chart-crashscore").checked;
    if (!on) {
      if (crashLineSeries && chart) { chart.removeSeries(crashLineSeries); crashLineSeries = null; }
      crashByDate = {};
      return;
    }
    var from = $("nifty-chart-start").value;
    var to = $("nifty-chart-to").value;
    if (!from || !to || !chart) return;
    setStatus("Loading crash scores (first run can take a few seconds)...");
    try {
      var resp = await fetch("/api/crash_score_series?start=" + from + "&end=" + to);
      var data = await resp.json();
      if (!resp.ok || data.error) throw new Error(data.error || resp.status);
      crashByDate = {};
      var pts = [];
      (data.series || []).forEach(function (s) {
        if (s.error) return;
        crashByDate[s.date] = s;
        pts.push({ time: s.date, value: s.score });
      });
      if (!crashLineSeries) {
        crashLineSeries = chart.addLineSeries({
          color: "rgba(239,68,68,0.85)",
          lineWidth: 1,
          priceScaleId: "",
          lastValueVisible: true,
          priceLineVisible: false,
          crosshairMarkerRadius: 3
        });
        crashLineSeries.priceScale().applyOptions({
          scaleMargins: { top: 0.85, bottom: 0 }
        });
      }
      crashLineSeries.setData(pts);
      setStatus("Loaded crash scores for " + pts.length + " days.");
    } catch (e) {
      setStatus("Crash score overlay failed: " + e.message, true);
    }
  }

  async function loadChart() {
    var from = $("nifty-chart-start").value;
    var to = $("nifty-chart-to").value;
    if (!from || !to) { setStatus("Pick both dates.", true); return; }
    if (from > to) { setStatus("'From' must be before 'To'.", true); return; }
    // prediction API caps range at 730 days — clamp 'from' if needed
    var spanDays = Math.round((new Date(to) - new Date(from)) / 864e5);
    if (spanDays > 730) {
      var fc = new Date(to);
      fc.setDate(fc.getDate() - 730);
      from = fc.toISOString().slice(0, 10);
      $("nifty-chart-start").value = from;
    }

    setStatus("Loading price data...");
    var cResp = await fetchWithTimeout("/api/nifty_chart?start=" + from + "&end=" + to, 120000);
    var cData = await cResp.json();
    var candles = [];
    if (!cResp.ok || !cData.candles || !cData.candles.length) {
      // Fallback to cached OHLC from /api/engine/market/ohlc
      if (window._cachedOHLC && window._cachedOHLC.length) {
        candles = window._cachedOHLC.map(function(r){
          return {
            time: r.date,
            open: parseFloat(r.open),
            high: parseFloat(r.high),
            low: parseFloat(r.low),
            close: parseFloat(r.close)
          };
        });
        setStatus("Using cached OHLC fallback (" + candles.length + " bars).");
      } else {
        setStatus("No price data for this range (network offline and cache empty?).", true);
        return;
      }
    } else {
      candles = cData.candles;
    }
    cData = { candles: candles };

    // Draw candles immediately — astro overlay streams in afterwards
    createBase(cData.candles);
    if (cData.candles.length > 0 && cData.candles[0].time > from) {
      setStatus("Price data available from " + cData.candles[0].time +
        " (earlier dates missing from cache). Loading astro overlay...");
    } else {
      setStatus("Loading astro predictions (first run can take a minute)...");
    }
    // Extend prediction end date by ~6 months (180 calendar days) for forward forecast
      var predEnd = new Date(to);
      predEnd.setDate(predEnd.getDate() + 180);
      var predEndStr = predEnd.toISOString().slice(0, 10);
      try {
      var pResp = await fetchWithTimeout("/api/prediction_series?start=" +
        cData.candles[0].time + "&end=" + predEndStr + "&anchor=nifty", 300000);
      var pData = await pResp.json();
      if (!pResp.ok) {
        setStatus("Candles shown; astro overlay failed: " + (pData.error || pResp.status), true);
        return;
      }
      applyOverlay(pData.series || []);
      var today = new Date().toISOString().slice(0, 10);
      var nFuture = (pData.series || []).filter(function (p) { return p.date > today; }).length;
      setStatus("Loaded " + cData.candles.length + " candles; " +
        (pData.series || []).length + " prediction days (" + nFuture + " future days forecast).");
    } catch (e) {
      console.error("Overlay failed (candles kept):", e);
      setStatus("Candles shown; astro overlay failed: " + e.message, true);
      return;
    }
    if ($("nifty-chart-crashscore").checked) {
      loadCrashScore().catch(function (e) { setStatus("Error: " + e.message, true); });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    statusEl = $("nifty-chart-status");
    tipEl = $("nifty-chart-tip");
    window.addEventListener("error", function (e) {
      if (!e.filename || e.filename.indexOf("nifty-chart") === -1) return;
      console.error("nifty-chart error:", e.message, e.lineno);
      setStatus("JS error: " + e.message + " (line " + e.lineno + ")", true);
    });
    var def = defaultDates();
    $("nifty-chart-start").value = def[0].toISOString().slice(0, 10);
    $("nifty-chart-to").value = def[1].toISOString().slice(0, 10);

    $("nifty-chart-range").addEventListener("change", function () {
      var months = parseInt(this.value, 10);
      var from = new Date();
      from.setMonth(from.getMonth() - months);
      $("nifty-chart-start").value = from.toISOString().slice(0, 10);
    });
    $("nifty-chart-run").addEventListener("click", function () {
      loadChart().catch(function (e) { setStatus("Error: " + e.message, true); });
    });
    $("nifty-chart-crashscore").addEventListener("change", function () {
      loadCrashScore().catch(function (e) { setStatus("Error: " + e.message, true); });
    });

    loadChart().catch(function (e) { setStatus("Error: " + e.message, true); });
  });
})();
