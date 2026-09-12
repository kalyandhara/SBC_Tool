/* Intraday NIFTY 50 Astro-Projection chart.
   Hourly astro bias + yoga windows (market hours) with forward projection.
   Uses TradingView Lightweight Charts (self-hosted, MIT license). */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  var chart = null;
  var lineSeries = null;
  var histogramSeries = null;
  var bandSeriesList = [];
  var statusEl, tipEl, yogaListEl;

  function fetchWithTimeout(url, ms) {
    var ctrl = new AbortController();
    var t = setTimeout(function () { ctrl.abort(); }, ms || 120000);
    return fetch(url, { signal: ctrl.signal }).finally(function () { clearTimeout(t); });
  }

  function setStatus(msg, isErr) {
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("error", !!isErr);
  }

  function fmtClock(clock) {
    return clock;
  }

  function fmtDayLabel(date) {
    var d = new Date(date + "T00:00:00");
    var days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    return days[d.getDay()] + " " + date.slice(5);
  }

  // Yoga type -> glyph + color
  var YOGA_STYLE = {
    "Abhijit Muhurta": { glyph: "AM", color: "#fbbf24" },
    "Bhadra (Vishti Karana)": { glyph: "B", color: "#f87171" },
    "Panchanga Yoga": { glyph: "Y", color: "#5eead4" },
  };

  function hourMarkers(hours) {
    // Group hours by date for day-separator markers
    var markers = [];
    var seenDays = {};
    hours.forEach(function (h) {
      if (!seenDays[h.date]) {
        seenDays[h.date] = true;
        markers.push({
          time: h.time,
          position: "belowBar",
          color: "#94a3b8",
          shape: "circle",
          text: fmtDayLabel(h.date),
        });
      }
    });
    return markers;
  }

  function yogaMarkers(yogas, hoursIndex) {
    // Place yoga markers at the nearest hourly point.
    var markers = [];
    var byDate = {};
    hoursIndex.forEach(function (h) { byDate[h.date] = byDate[h.date] || h; });

    yogas.forEach(function (y) {
      var style = YOGA_STYLE[y.type] || { glyph: "Y", color: "#5eead4" };
      var h = byDate[y.date];
      if (!h) return;
      var label = y.names ? y.names.join("/") : y.type;
      // For timed yogas, attach start time to the label where possible.
      var text = style.glyph;
      if (y.start) text += " " + y.start;
      markers.push({
        time: h.time,
        position: "aboveBar",
        color: style.color,
        shape: "circle",
        text: text,
        // custom metadata for hover
        id: "yoga-" + y.date + "-" + y.type,
      });
    });
    return markers;
  }

  function renderYogaList(yogas) {
    yogaListEl.innerHTML = "";
    if (!yogas.length) {
      yogaListEl.innerHTML = '<div class="intraday-yoga-empty">No yoga windows in the projected period.</div>';
      return;
    }
    var grouped = {};
    yogas.forEach(function (y) {
      grouped[y.date] = grouped[y.date] || [];
      grouped[y.date].push(y);
    });
    Object.keys(grouped).forEach(function (date) {
      var dayEl = document.createElement("div");
      dayEl.className = "intraday-yoga-day";
      var head = document.createElement("div");
      head.className = "intraday-yoga-day-label";
      head.textContent = fmtDayLabel(date);
      dayEl.appendChild(head);
      grouped[date].forEach(function (y) {
        var row = document.createElement("div");
        row.className = "intraday-yoga-row" + (y.day_level ? " day-level" : "");
        var style = YOGA_STYLE[y.type] || { glyph: "Y", color: "#5eead4" };
        var timeStr = y.day_level ? "all day" : (y.start + " - " + y.end);
        row.innerHTML =
          "<span class='intraday-yoga-glyph' style='color:" + style.color + "'>" +
          style.glyph + "</span>" +
          "<span class='intraday-yoga-name'>" + (y.names || []).join(" + ") + "</span>" +
          "<span class='intraday-yoga-time'>" + timeStr + "</span>";
        dayEl.appendChild(row);
      });
      yogaListEl.appendChild(dayEl);
    });
  }

  function render(projection) {
    var el = $("intraday-proj-chart");
    el.innerHTML = "";
    if (chart) { try { chart.remove(); } catch (e) {} }
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
      timeScale: {
        borderColor: "#2a3a52",
        timeVisible: true,
        secondsVisible: false
      }
    });

    var hours = projection.hours || [];

    // Neutral zero line using histogram of projections (green/red by sign)
    histogramSeries = chart.addHistogramSeries({
      priceLineVisible: false,
      lastValueVisible: false,
      base: 0
    });
    histogramSeries.setData(hours.map(function (h) {
      return {
        time: h.time,
        value: h.projection,
        color: h.projection >= 0 ? "rgba(34,197,94,0.75)" : "rgba(239,68,68,0.75)"
      };
    }));

    // Smooth projection line on top
    lineSeries = chart.addLineSeries({
      color: "#38bdf8",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4
    });
    lineSeries.setData(hours.map(function (h) { return { time: h.time, value: h.projection }; }));

    // Day separators + yoga markers
    lineSeries.setMarkers(hourMarkers(hours).concat(yogaMarkers(projection.yogas || [], hours)));

    chart.timeScale().fitContent();

    // Hover tooltip
    chart.subscribeCrosshairMove(function (param) {
      var tip = tipEl;
      if (!param.time || !param.point || param.point === undefined) { tip.classList.add("hidden"); return; }
      var hour = null;
      hours.forEach(function (h) { if (h.time === param.time) hour = h; });
      if (!hour) { tip.classList.add("hidden"); return; }
      var v = hour.projection;
      var dir = v >= 0 ? "BULLISH" : "BEARISH";
      var cls = v >= 0 ? "bull" : "bear";
      var html =
        "<div class='tip-head'><strong>" + fmtDayLabel(hour.date) + " " + hour.clock +
        " IST</strong><span class='tip-badge " + cls + "'>" + dir + "</span></div>" +
        "<div class='tip-score'>Projection: <b>" + v + "</b> (day net " + hour.day_net + ")</div>" +
        "<div class='tip-row'>Hora: <b>" + (hour.hora_lord || "-") + "</b> (" + hour.hora_score + ")</div>";
      if (hour.yoga_active && hour.yoga_active.length) {
        html += "<div class='tip-sec tip-alert'>Active yoga</div>";
        hour.yoga_active.forEach(function (yn) {
          html += "<div class='tip-row win'>" + yn + "</div>";
        });
      }
      tip.innerHTML = html;
      var tw = tip.offsetWidth || 300, th = tip.offsetHeight || 120;
      tip.style.left = Math.max(4, Math.min(param.point.x + 14, el.clientWidth - tw - 6)) + "px";
      tip.style.top = Math.max(4, Math.min(param.point.y + 12, el.clientHeight - th - 6)) + "px";
      tip.classList.remove("hidden");
    });
  }

async function loadProjection() {
    var raw = $("intraday-proj-date").value;
    if (!raw) { setStatus("Pick a week.", true); return; }
    // Snap to Monday (week start) and project the 5 trading days.
    var d = new Date(raw + "T00:00:00");
    var dow = d.getDay(); // Sun=0
    var offset = dow === 0 ? 6 : dow - 1; // days back to Monday
    var monday = new Date(d); monday.setDate(d.getDate() - offset);
    var mondayStr = monday.toISOString().split("T")[0];
    var days = 5;
    if (!mondayStr) { setStatus("Pick a start date.", true); return; }
    setStatus("Loading intraday astro-projection for week of " + mondayStr + " (5 days)...");
    try {
      var resp = await fetchWithTimeout(
        "/api/intraday_projection?date=" + encodeURIComponent(mondayStr) + "&days=" + days);
      var data = await resp.json();
      if (!resp.ok || data.error) throw new Error(data.error || resp.status);
      render(data);
      renderYogaList(data.yogas || []);
      var nHours = (data.hours || []).length;
      var nYoga = (data.yogas || []).length;
      setStatus("Projected " + nHours + " hourly points over " + data.days + " days; " + nYoga + " yoga window" + (nYoga === 1 ? "" : "s") + ".");
    } catch (e) {
      setStatus("Intraday projection failed: " + e.message, true);
    }
  }

  // Week-level calendar popover (mirrors initWeekCalendar).
  function initIntradayWeekCalendar() {
    var input = $("intraday-proj-date");
    var dropdown = $("intraday-proj-calendar");
    if (!input || !dropdown) return;

    function buildCalendar() {
      var today = new Date();
      var currentYear = today.getFullYear();
      var startDate = new Date(currentYear - 1, 0, 1);
      var endDate = new Date(currentYear + 1, 11, 31);
      var d = new Date(startDate);
      while (d.getDay() !== 1) d.setDate(d.getDate() + 1);
      var weeks = [];
      while (d <= endDate) {
        var monday = new Date(d);
        var sunday = new Date(d);
        sunday.setDate(d.getDate() + 6);
        var weekStart = monday.toISOString().split("T")[0];
        var label = String(monday.getMonth() + 1).padStart(2, "0") + "/" +
          String(monday.getDate()).padStart(2, "0") + " - " +
          String(sunday.getMonth() + 1).padStart(2, "0") + "/" +
          String(sunday.getDate()).padStart(2, "0") + " " + monday.getFullYear();
        var isCurrent = (monday <= today && sunday >= today);
        weeks.push({ weekStart, label, isCurrent, monday, sunday });
        d.setDate(d.getDate() + 7);
      }
      dropdown.innerHTML = "";
      weeks.forEach(function (w) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "week-calendar-item" + (w.isCurrent ? " current" : "");
        btn.dataset.date = w.weekStart;
        btn.textContent = w.label;
        btn.addEventListener("click", function () {
          input.value = w.weekStart;
          dropdown.classList.add("hidden");
          loadProjection();
        });
        dropdown.appendChild(btn);
      });
    }

    input.addEventListener("click", function (e) {
      e.stopPropagation();
      if (dropdown.classList.contains("hidden")) { buildCalendar(); dropdown.classList.remove("hidden"); }
      else { dropdown.classList.add("hidden"); }
    });

    document.addEventListener("click", function (e) {
      if (!dropdown.contains(e.target) && e.target !== input) dropdown.classList.add("hidden");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") dropdown.classList.add("hidden");
    });
  }

  function setTodayAsIntradayWeek() {
    var today = new Date();
    var dow = today.getDay();
    var offset = dow === 0 ? 6 : dow - 1;
    var monday = new Date(today); monday.setDate(monday.getDate() - offset);
    $("intraday-proj-date").value = monday.toISOString().slice(0, 10);
  }

  document.addEventListener("DOMContentLoaded", function () {
    statusEl = $("intraday-proj-status");
    tipEl = $("intraday-proj-tip");
    yogaListEl = $("intraday-proj-yoga-list");
    if (!statusEl) return;

    setTodayAsIntradayWeek();
    initIntradayWeekCalendar();
    $("intraday-proj-today").addEventListener("click", function () {
      setTodayAsIntradayWeek();
      loadProjection();
    });
    $("intraday-proj-run").addEventListener("click", function () { loadProjection(); });
    loadProjection();
  });
})();