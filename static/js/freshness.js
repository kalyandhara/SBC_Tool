/* "Data as of" badges for panels that show price or Kota data (B-05).
 * The server sends a freshness stamp {as_of, expected, sessions_behind, stale};
 * the badge is green when current and amber from one trading session behind. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

  // Price-series badge from a freshness stamp; label names the series ("NIFTY").
  function badge(f, label) {
    if (!f) return "";
    var who = label ? esc(label) + " " : "";
    if (!f.as_of) {
      return '<span class="asof-badge stale" title="Expected data through ' + esc(f.expected) +
        '">' + who + "no data</span>";
    }
    var title = f.stale
      ? plural(f.sessions_behind, "trading session") + " behind (expected " + f.expected + ")"
      : "Current: last settled session is " + f.expected;
    return '<span class="asof-badge ' + (f.stale ? "stale" : "ok") + '" title="' + esc(title) + '">' +
      who + "data as of " + esc(f.as_of) +
      (f.stale ? " · " + plural(f.sessions_behind, "session") + " behind" : "") + "</span>";
  }

  // Kota workbooks are forecasts for a fixed range, supplied by hand.
  function kotaBadge(c) {
    if (!c) return "";
    if (!c.to) {
      return '<span class="asof-badge stale">Kota range unknown (' + esc(c.file) + ")</span>";
    }
    var text = "Kota workbook covers " + esc(c.from) + " to " + esc(c.to);
    if (c.stale) text += " · ended, add a newer workbook to data/kota/";
    return '<span class="asof-badge ' + (c.stale ? "stale" : "ok") + '" title="' + esc(c.file) + '">' +
      text + "</span>";
  }

  // Put a badge into a slot element (created after `anchor` if missing).
  function show(slotId, html, anchor) {
    var el = document.getElementById(slotId);
    if (!el && anchor) {
      el = document.createElement("div");
      el.id = slotId;
      el.className = "asof-slot";
      anchor.parentNode.insertBefore(el, anchor.nextSibling);
    }
    if (el) el.innerHTML = html || "";
    return el;
  }

  window.SBCFreshness = { badge: badge, kotaBadge: kotaBadge, show: show };
})();
