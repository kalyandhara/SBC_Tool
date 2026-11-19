// Checks the North Indian diamond per-house text layout (no DOM needed).
// Usage: node tests/js/diamond_layout_check.mjs [path-to-navigator-chart.js]
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const file = process.argv[2] || path.join(here, "..", "..", "static", "js", "navigator-chart.js");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(file, "utf8"), ctx, { filename: file });
const layout = vm.runInContext("typeof navHouseLines === 'function' ? navHouseLines : null", ctx);
if (!layout) { console.error("FAIL: navHouseLines is not defined"); process.exit(1); }

// Independent house polygons on the 400 x 400 box (house 1 = top-centre kite, counter-clockwise).
const POLY = {
  1: [[200, 0], [300, 100], [200, 200], [100, 100]],
  2: [[0, 0], [200, 0], [100, 100]],
  3: [[0, 0], [0, 200], [100, 100]],
  4: [[0, 200], [100, 100], [200, 200], [100, 300]],
  5: [[0, 200], [0, 400], [100, 300]],
  6: [[0, 400], [200, 400], [100, 300]],
  7: [[200, 200], [100, 300], [200, 400], [300, 300]],
  8: [[200, 400], [400, 400], [300, 300]],
  9: [[400, 200], [400, 400], [300, 300]],
  10: [[400, 200], [300, 100], [200, 200], [300, 300]],
  11: [[400, 0], [400, 200], [300, 100]],
  12: [[200, 0], [400, 0], [300, 100]],
};
function inside(px, py, poly) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}

const CODES = ["Su", "Mo", "Ma", "Me", "Ju", "Ve"];
const errors = [];
for (let house = 1; house <= 12; house++) {
  for (let n = 1; n <= 6; n++) {
    const labels = CODES.slice(0, n).map((c) => `${c} 29°`);
    const opts = { sign: 12 };
    if (house === 1) opts.lagna = "Lagna 29°59′";
    const lines = layout(house, labels, opts);
    const tag = `house ${house} with ${n} labels`;
    const joined = lines.map((l) => l.text).join(" ");
    for (const l of labels) if (!joined.includes(l)) errors.push(`${tag}: label "${l}" missing`);
    if (house === 1 && !lines.some((l) => l.text.startsWith("Lagna"))) errors.push(`${tag}: Lagna missing`);
    for (const l of lines) {
      if (!(l.y >= 8 && l.y <= 396 && l.x >= 4 && l.x <= 396))
        errors.push(`${tag}: "${l.text}" out of bounds at (${l.x}, ${l.y})`);
      if (!inside(l.x, l.y, POLY[house]))
        errors.push(`${tag}: "${l.text}" anchor (${l.x}, ${l.y}) outside house polygon`);
    }
    const ys = lines.map((l) => l.y).sort((a, b) => a - b);
    for (let i = 1; i < ys.length; i++)
      if (ys[i] - ys[i - 1] < 11) errors.push(`${tag}: lines overlap vertically (${ys[i - 1]}, ${ys[i]})`);
  }
}
if (errors.length) {
  console.error(`FAIL: ${errors.length} violation(s)\n` + errors.slice(0, 25).join("\n"));
  process.exit(1);
}
console.log("OK: all houses x 1..6 labels inside bounds and polygons");
