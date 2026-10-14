// Glyph coverage report: how much near-white glyph ink each icon has, plus its bbox.
// Catches silently-empty glyphs and badly off-centre compositions.
'use strict';
const fs = require('fs');
const path = require('path');
const { decode } = require('./pngread.js');

const ROOT = path.join(__dirname, '..', 'pckproject', 'Yetannia', 'images');

function analyse(file) {
  const img = decode(file);
  const { width, height, channels, pixels } = img;
  let white = 0, dark = 0, total = width * height;
  let minX = width, minY = height, maxX = -1, maxY = -1;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * channels;
      const R = pixels[i], G = pixels[i + 1], B = pixels[i + 2];
      const A = channels === 4 ? pixels[i + 3] : 255;
      if (A > 128 && R > 205 && G > 208 && B > 212) {
        white++;
        if (x < minX) minX = x; if (x > maxX) maxX = x;
        if (y < minY) minY = y; if (y > maxY) maxY = y;
      } else if (A > 128 && R < 60 && G < 62 && B < 80) dark++;
    }
  }
  return {
    file: path.relative(ROOT, file),
    whitePct: +(100 * white / total).toFixed(2),
    darkPct: +(100 * dark / total).toFixed(2),
    bbox: maxX < 0 ? null : [minX, minY, maxX - minX + 1, maxY - minY + 1],
  };
}

const dirs = ['powers_big', 'relics_big', 'ui'];
const rows = [];
for (const d of dirs) {
  const dir = path.join(ROOT, d);
  if (!fs.existsSync(dir)) continue;
  for (const f of fs.readdirSync(dir).sort()) {
    if (!f.endsWith('.png')) continue;
    if (d === 'ui' && f.endsWith('_small.png')) continue;
    rows.push(analyse(path.join(dir, f)));
  }
}
let bad = 0;
for (const r of rows) {
  const cx = r.bbox ? r.bbox[0] + r.bbox[2] / 2 : -1;
  const cy = r.bbox ? r.bbox[1] + r.bbox[3] / 2 : -1;
  const ok = r.whitePct > 3 && r.whitePct < 60 && cx > 78 && cx < 178 && cy > 78 && cy < 178;
  if (!ok) bad++;
  console.log(
    (ok ? 'ok  ' : 'BAD ') + r.file.padEnd(34) +
    ' white=' + String(r.whitePct).padStart(6) + '%' +
    ' dark=' + String(r.darkPct).padStart(6) + '%' +
    ' bbox=' + JSON.stringify(r.bbox) +
    ' centre=(' + cx.toFixed(0) + ',' + cy.toFixed(0) + ')');
}
console.log('\n' + rows.length + ' icons checked, ' + bad + ' suspicious');
