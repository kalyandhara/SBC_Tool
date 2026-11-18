// Navigator chart view: North Indian diamond, graha table and Vimshottari tree.
// Uses navigator.js helpers (loaded first). Every value is set with textContent;
// SVG nodes come from createElementNS. Houses are whole-sign from the Lagna.

const NAV_SVG = "http://www.w3.org/2000/svg";
// Text anchor per house, 1..12, counter-clockwise from the top centre (400 x 400 box).
const NAV_HOUSE_XY = [[200, 100], [100, 45], [45, 100], [100, 200], [45, 300], [100, 355],
  [200, 300], [300, 355], [355, 300], [300, 200], [355, 100], [300, 45]];
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

function navDiamond(data) {
  const svg = navSvg("svg", { viewBox: "0 0 400 400", class: "nav-diamond", role: "img",
    "aria-label": `North Indian chart, Lagna in ${data.lagna.sign}` });
  svg.appendChild(navSvg("rect", { x: 1, y: 1, width: 398, height: 398, class: "nav-d-line" }));
  svg.appendChild(navSvg("line", { x1: 0, y1: 0, x2: 400, y2: 400, class: "nav-d-line" }));
  svg.appendChild(navSvg("line", { x1: 400, y1: 0, x2: 0, y2: 400, class: "nav-d-line" }));
  svg.appendChild(navSvg("polygon", { points: "200,0 400,200 200,400 0,200", class: "nav-d-line" }));
  const byCode = Object.fromEntries((data.points || []).filter((p) => p.code).map((p) => [p.code, p]));
  for (const house of data.houses) {
    const [x, y] = NAV_HOUSE_XY[house.house - 1];
    const g = navSvg("g", { class: "nav-d-house" });
    g.appendChild(navSvg("text", { x, y: y - 14, class: "nav-d-sign" }, String(house.sign_number)));
    const lines = house.points.map((code) => `${code} ${navDms(byCode[code] ? byCode[code].degree : 0).split("°")[0]}°`);
    if (house.house === 1) lines.unshift(`Lagna ${navDms(data.lagna.degree)}`);
    lines.forEach((line, i) => g.appendChild(navSvg("text",
      { x, y: y + 4 + i * 15, class: house.house === 1 && i === 0 ? "nav-d-lagna" : "nav-d-graha" }, line)));
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
    const text = `${p.lord}  ${p.start} to ${p.end}`;
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
