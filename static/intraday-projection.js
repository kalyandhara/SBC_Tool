/* Intraday NIFTY 50 Astro-Projection chart.
   Cumulative KP composite path with hora-lord shading bands, reversal
   turning-point markers, and intraday momentum bars (green benefic /
   red malefic / grey Dahan) — market hours, forward projection.
   Uses Chart.js (self-hosted). */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  var chart = null;
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

  // Format a local Date as YYYY-MM-DD without converting through UTC
  // (toISOString() shifts the date back one day for UTC+ timezones like IST).
  function isoDateOf(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  function fmtDayLabel(date) {
    var d = new Date(date + "T00:00:00");
    var days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    return days[d.getDay()] + " " + date.slice(5);
  }

  function fmtDayShort(date) {
    var d = new Date(date + "T00:00:00");
    var days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    return days[d.getDay()] + " " + date.slice(8);
  }

  // Yoga type -> glyph + color
  var YOGA_STYLE = {
    "Abhijit Muhurta": { glyph: "AM", color: "#fbbf24" },
    "Bhadra (Vishti Karana)": { glyph: "B", color: "#f87171" },
    "Panchanga Yoga": { glyph: "Y", color: "#5eead4" },
  };

  // Hora lord -> subtle background band colour
  var HORA_BAND_COLORS = {
    "Jupiter": "rgba(96, 165, 250, 0.10)",
    "Mars": "rgba(248, 113, 113, 0.09)",
    "Sun": "rgba(251, 191, 36, 0.10)",
    "Mercury": "rgba(52, 211, 153, 0.09)",
    "Venus": "rgba(244, 114, 182, 0.09)",
    "Moon": "rgba(167, 139, 250, 0.10)",
    "Saturn": "rgba(148, 163, 184, 0.09)"
  };

  function horaSegments(hours) {
    // Group consecutive points by (date, hora lord).
    var segs = [];
    hours.forEach(function (h, i) {
      var last = segs[segs.length - 1];
      if (last && last.date === h.date && last.lord === h.hora_lord) last.end = i;
      else segs.push({ date: h.date, lord: h.hora_lord, start: i, end: i });
    });
    return segs;
  }

  function dayBoundaries(hours) {
    var out = [];
    hours.forEach(function (h, i) {
      if (i === 0 || h.date !== hours[i - 1].date) out.push({ date: h.date, idx: i });
    });
    return out;
  }

  function turningPoints(hours) {
    // Local extrema of the cumulative path: hora transitions where the
    // slope changes sign (benefic -> malefic = top, malefic -> benefic = bottom).
    var pts = [];
    var cum = hours.map(function (h) { return h.cumulative; });
    for (var i = 1; i < cum.length - 1; i++) {
      if (hours[i].date !== hours[i - 1].date || hours[i + 1].date !== hours[i].date) continue;
      var slopeIn = cum[i] - cum[i - 1];
      var slopeOut = cum[i + 1] - cum[i];
      if ((slopeIn > 0 && slopeOut < 0) || (slopeIn < 0 && slopeOut > 0)) {
        pts.push({ i: i, value: cum[i], time: hours[i].clock });
      }
    }
    return pts;
  }

  function momentumColors(hours) {
    return hours.map(function (h) {
      if (h.dahan) return "rgba(148,163,184,0.55)";
      if (h.momentum > 0) return "rgba(34,197,94,0.85)";
      if (h.momentum < 0) return "rgba(239,68,68,0.85)";
      return "rgba(100,116,139,0.45)";
    });
  }

  function buildBandsPlugin(segs) {
    return {
      id: "horaBands",
      beforeDatasetsDraw: function (c) {
        var ctx = c.ctx, area = c.chartArea;
        var step = (area.right - area.left) / c.data.labels.length;
        segs.forEach(function (s) {
          if (!s.lord) return;
          var x1 = area.left + s.start * step;
          var x2 = area.left + (s.end + 1) * step;
          ctx.fillStyle = HORA_BAND_COLORS[s.lord] || "rgba(148,163,184,0.06)";
          ctx.fillRect(x1, area.top, x2 - x1, area.bottom - area.top);
        });
      }
    };
  }

  function buildDaySepPlugin(bounds) {
    return {
      id: "daySep",
      beforeDatasetsDraw: function (c) {
        var ctx = c.ctx, area = c.chartArea;
        var step = (area.right - area.left) / c.data.labels.length;
        bounds.forEach(function (b, k) {
          if (k === 0) return;
          var x = area.left + b.idx * step;
          ctx.save();
          ctx.setLineDash([4, 4]);
          ctx.strokeStyle = "rgba(148,163,184,0.35)";
          ctx.beginPath();
          ctx.moveTo(x, area.top);
          ctx.lineTo(x, area.bottom);
          ctx.stroke();
          ctx.restore();
          ctx.fillStyle = "#94a3b8";
          ctx.font = "10px Segoe UI, sans-serif";
          ctx.textAlign = "left";
          ctx.fillText(fmtDayShort(b.date), x + 4, area.top + 12);
        });
      }
    };
  }

  function buildTpLabelPlugin(tp) {
    return {
      id: "tpLabels",
      afterDatasetsDraw: function (c) {
        var ctx = c.ctx, area = c.chartArea;
        var xs = c.scales.x, ys = c.scales.y;
        ctx.font = "9px Segoe UI, sans-serif";
        ctx.textAlign = "center";
        tp.forEach(function (p) {
          var x = xs.getPixelForValue(p.i);
          var y = ys.getPixelForValue(p.value);
          if (x < area.left || x > area.right) return;
          ctx.fillStyle = "#fbbf24";
          ctx.fillText(p.time, x, Math.max(area.top + 14, y - 9));
        });
      }
    };
  }

  function render(projection) {
    var el = $("intraday-proj-chart");
    el.innerHTML = "";
    if (chart) { try { chart.destroy(); } catch (e) {} chart = null; }

    var hours = projection.hours || [];
    var labels = hours.map(function (h) { return h.clock; });
    var cum = hours.map(function (h) { return h.cumulative; });
    var mom = hours.map(function (h) { return h.momentum; });
    var segs = horaSegments(hours);
    var bounds = dayBoundaries(hours);
    var tp = turningPoints(hours);
    var tpData = hours.map(function () { return null; });
    tp.forEach(function (p) { tpData[p.i] = p.value; });

    var canvas = document.createElement("canvas");
    el.appendChild(canvas);

    chart = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            type: "line",
            label: "Cumulative KP path",
            data: cum,
            yAxisID: "y",
            borderColor: "#3b82f6",
            backgroundColor: "rgba(59,130,246,0.08)",
            fill: true,
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 4,
            order: 1
          },
          {
            type: "line",
            label: "Turning points",
            data: tpData,
            yAxisID: "y",
            showLine: false,
            pointStyle: "circle",
            pointRadius: 4.5,
            pointHoverRadius: 6,
            backgroundColor: "#f59e0b",
            borderColor: "#b45309",
            order: 0
          },
          {
            type: "bar",
            label: "Momentum",
            data: mom,
            yAxisID: "y2",
            backgroundColor: momentumColors(hours),
            borderWidth: 0,
            barPercentage: 0.8,
            categoryPercentage: 0.9,
            order: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: {
            grid: { color: "rgba(29,42,61,0.6)" },
            ticks: {
              color: "#c8d3e0",
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 24,
              font: { size: 10 }
            }
          },
          y: {
            position: "left",
            title: { display: true, text: "Path (cumulative score)", color: "#9fb3c8" },
            grid: { color: "rgba(29,42,61,0.6)" },
            ticks: { color: "#c8d3e0", font: { size: 10 } }
          },
          y2: {
            position: "right",
            title: { display: true, text: "Momentum", color: "#9fb3c8" },
            grid: { drawOnChartArea: false },
            ticks: { color: "#c8d3e0", font: { size: 10 } }
          }
        },
        plugins: {
          legend: {
            display: true,
            labels: { color: "#9fb3c8", font: { size: 11 }, usePointStyle: true }
          },
          tooltip: {
            callbacks: {
              title: function (items) {
                var h = hours[items[0].dataIndex];
                return fmtDayLabel(h.date) + " " + h.clock + " IST";
              },
              label: function (item) {
                var h = hours[item.dataIndex];
                if (item.datasetIndex === 0) {
                  return "Path: " + h.cumulative + " (bias " + h.projection + ", day net " + h.day_net + ")";
                }
                if (item.datasetIndex === 1) return "Reversal turning point";
                return "Momentum: " + h.momentum + " — Hora: " + (h.hora_lord || "-") + " (" + h.hora_score + ")";
              },
              afterBody: function (items) {
                var h = hours[items[0].dataIndex];
                return (h.yoga_active || []).map(function (yn) { return yn; });
              }
            }
          }
        }
      },
      plugins: [buildBandsPlugin(segs), buildDaySepPlugin(bounds), buildTpLabelPlugin(tp)]
    });
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

  async function loadProjection() {
    var raw = $("intraday-proj-date").value;
    if (!raw) { setStatus("Pick a week.", true); return; }
    // Snap to Monday (week start) and project the 5 trading days.
    var d = new Date(raw + "T00:00:00");
    var dow = d.getDay(); // Sun=0
    var offset = dow === 0 ? 6 : dow - 1; // days back to Monday
    var monday = new Date(d); monday.setDate(d.getDate() - offset);
    var mondayStr = isoDateOf(monday);
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
      var nTp = turningPoints(data.hours || []).length;
      setStatus("Projected " + nHours + " intraday points (" + nTp + " turning points) over " + data.days + " days; " + nYoga + " yoga window" + (nYoga === 1 ? "" : "s") + ".");
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
        var weekStart = isoDateOf(monday);
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
    $("intraday-proj-date").value = isoDateOf(monday);
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
