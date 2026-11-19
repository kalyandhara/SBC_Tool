// Navigator chart view: North Indian diamond, graha table and Vimshottari tree.
// Uses navigator.js helpers (loaded first). Every value is set with textContent;
// SVG nodes come from createElementNS. Houses are whole-sign from the Lagna.

const NAV_SVG = "http://www.w3.org/2000/svg";
// Per-house centroid and shape class on the 400 x 400 box, house 1..12 counter-clockwise
// from the top-centre kite. Kinds: kite, top / bottom (base on that edge), side (left or right edge).
const NAV_LINE = 13;
const NAV_HOUSE_GEOM = [
  { x: 200, y: 100, kind: "kite" }, { x: 100, y: 33, kind: "top" }, { x: 36, y: 100, kind: "side" },
  { x: 100, y: 200, kind: "kite" }, { x: 36, y: 300, kind: "side" }, { x: 100, y: 367, kind: "bottom" },
  { x: 200, y: 300, kind: "kite" }, { x: 300, y: 367, kind: "bottom" }, { x: 364, y: 300, kind: "side" },
  { x: 300, y: 200, kind: "kite" }, { x: 364, y: 100, kind: "side" }, { x: 300, y: 33, kind: "top" }];
const NAV_FLAG_TEXT = { own: "Own sign", exalted: "Exalted", debilitated: "Debilitated" };

function navSvg(tag, attrs = {}, text = null) {
  const node = document.createElementNS(NAV_SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  if (text !== null) node.textContent = text;
  return node;
}

// Clamp so a rounded 30.0 never displays as 30 degrees 00 minutes.
function navDms(deg) {
  const v = Math.min(Number(deg) || 0, 29.9999);
  const d = Math.floor(v);
  const m = Math.floor((v - d) * 60);
  return `${d}°${String(m).padStart(2, "0")}′`;
}

// Pure layout for one house: returns [{x, y, text, cls}] centred on the house centroid.
// Kites and top/bottom triangles pack two labels per line when there are more than two;
// side triangles use one per line. opts: {lagna, sign}.
function navHouseLines(house, labels, opts = {}) {
  const g = NAV_HOUSE_GEOM[house - 1];
  const rows = [];
  if (opts.lagna) rows.push({ text: opts.lagna, cls: "nav-d-lagna" });
  const pack = g.kind !== "side" && labels.length > 2;
  for (let i = 0; i < labels.length; i += pack ? 2 : 1) {
    rows.push({ text: labels.slice(i, i + (pack ? 2 : 1)).join("  "), cls: "nav-d-graha" });
  }
  let first = g.y - (rows.length - 1) * NAV_LINE / 2;
  if (g.kind === "bottom") first = Math.min(first, 381 - (rows.length - 1) * NAV_LINE);
  else first = Math.max(first, 22);
  const out = rows.map((r, i) => ({ x: g.x, y: first + i * NAV_LINE, text: r.text, cls: r.cls }));
  if (opts.sign !== undefined && opts.sign !== null) {
    const signY = g.kind === "bottom" ? first + (rows.length - 1) * NAV_LINE + NAV_LINE : first - NAV_LINE;
    out.unshift({ x: g.x, y: signY, text: String(opts.sign), cls: "nav-d-sign" });
  }
  return out;
}

function navDiamond(data) {
  const svg = navSvg("svg", { viewBox: "0 0 400 400", class: "nav-diamond", role: "img",
    "aria-label": `North Indian chart, Lagna in ${data.lagna.sign}` });
  svg.appendChild(navSvg("rect", { x: 1, y: 1, width: 398, height: 398, class: "nav-d-line" }));
  svg.appendChild(navSvg("line", { x1: 0, y1: 0, x2: 400, y2: 400, class: "nav-d-line" }));
  svg.appendChild(navSvg("line", { x1: 400, y1: 0, x2: 0, y2: 400, class: "nav-d-line" }));
  svg.appendChild(navSvg("polygon", { points: "200,0 400,200 200,400 0,200", class: "nav-d-line" }));
  const byCode = Object.fromEntries((data.points || []).filter((p) => p.code).map((p) => [p.code, p]));
  for (const house of data.houses) {
    const labels = house.points.map((code) => {
      const deg = byCode[code] ? byCode[code].degree : null;
      return typeof deg === "number" && isFinite(deg)
        ? `${code} ${Math.floor(Math.min(deg, 29.9999))}°` : code;
    });
    const opts = { sign: house.sign_number };
    if (house.house === 1) opts.lagna = `Lagna ${navDms(data.lagna.degree)}`;
    const g = navSvg("g", { class: "nav-d-house" });
    for (const l of navHouseLines(house.house, labels, opts)) {
      g.appendChild(navSvg("text", { x: l.x, y: l.y, class: l.cls }, l.text));
    }
    svg.appendChild(g);
  }
  return svg;
}

function navFlags(p) {
  const flags = [];
  if (p.dignity && NAV_FLAG_TEXT[p.dignity]) flags.push(NAV_FLAG_TEXT[p.dignity]);
  if (p.combust) flags.push("Combust");
  if (p.retro) flags.push("R");
  return flags.join(", ");
}

function navRenderChartView(data) {
  const out = navId("nav-chart");
  navClear(out);
  out.appendChild(navHeading(`Chart: ${data.label}`));
  out.appendChild(navNote(`Lagna ${data.lagna.sign_sa} (${data.lagna.sign}) ${navDms(data.lagna.degree)}. Whole-sign houses, Lahiri.`));
  out.appendChild(navEl("div", { class: "nav-diamond-wrap" }, [navDiamond(data)]));
  const grahas = (data.points || []).filter((p) => p.name !== "Lagna");
  out.appendChild(navTable("Grahas", ["Graha", "Rashi", "Degree", "Nakshatra", "Bhava", "Flags"],
    grahas.map((p) => [p.sanskrit, `${p.sign_sa} (${p.sign})`, navDms(p.degree), `${p.nakshatra} ${p.pada}`, p.bhava, navFlags(p)])));
}

function navNowTag() { return navEl("span", { class: "nav-tag nav-now", text: "NOW" }); }

function navPeriods(list) {
  return list.map((p) => {
    const text = `${p.lord} ${p.start} to ${p.end}`;
    if (!p.children || !p.children.length) {
      const leaf = navEl("li", { text });
      if (p.now) leaf.appendChild(navNowTag());
      return leaf;
    }
    const summary = navEl("summary", {}, [navEl("span", { text })]);
    if (p.now) summary.appendChild(navNowTag());
    const box = navEl("details", { class: "nav-details" }, [summary,
      navEl("ul", { class: "nav-list" }, navPeriods(p.children))]);
    if (p.now) box.open = true;
    return box;
  });
}

function navRenderDasha(data) {
  const out = navId("nav-dasha");
  navClear(out);
  const r = data.running || {};
  out.appendChild(navHeading("Vimshottari dasha"));
  out.appendChild(navEl("p", { class: "nav-strong",
    text: `Running now: ${[r.maha, r.antar, r.pratyantar].filter(Boolean).join(" / ")}` }));
  out.appendChild(navEl("div", { class: "nav-dasha" }, navPeriods(data.periods || [])));
}
