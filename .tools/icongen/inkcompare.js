// Compares glyph ink coverage between the 256px and 64px versions of each icon.
// A big drop means the downscale destroyed detail.
'use strict';
const fs = require('fs');
const path = require('path');
const { decode } = require('./pngread.js');

const ROOT = path.join(__dirname, '..', 'pckproject', 'Yetannia', 'images');

function inkPct(file) {
  const img = decode(file);
  const { width, height, channels, pixels } = img;
  let white = 0, total = width * height;
  for (let i = 0; i < total; i++) {
    const p = i * channels;
    const A = channels === 4 ? pixels[p + 3] : 255;
    if (A > 128 && pixels[p] > 200 && pixels[p + 1] > 203 && pixels[p + 2] > 208) white++;
  }
  return 100 * white / total;
}

const pairs = [
  ['powers_big', 'powers'], ['relics_big', 'relics'],
];
const rows = [];
for (const [big, small] of pairs) {
  for (const f of fs.readdirSync(path.join(ROOT, big)).sort()) {
    if (!f.endsWith('.png')) continue;
    const a = inkPct(path.join(ROOT, big, f));
    const b = inkPct(path.join(ROOT, small, f));
    rows.push({ name: big + '/' + f, big: +a.toFixed(2), small: +b.toFixed(2), ratio: +(b / a).toFixed(2) });
  }
}
const a = inkPct(path.join(ROOT, 'ui', 'energy_yetannia.png'));
const b = inkPct(path.join(ROOT, 'ui', 'energy_yetannia_small.png'));
rows.push({ name: 'ui/energy_yetannia.png', big: +a.toFixed(2), small: +b.toFixed(2), ratio: +(b / a).toFixed(2) });

let worst = 1;
for (const r of rows) {
  const flag = (r.small < 4 || r.ratio < 0.6 || r.ratio > 1.6) ? '  <-- check' : '';
  if (r.ratio < worst) worst = r.ratio;
  console.log(r.name.padEnd(36) + ' 256px=' + String(r.big).padStart(6) + '%' +
              '  64px=' + String(r.small).padStart(6) + '%  ratio=' + r.ratio + flag);
}
console.log('\nlowest 64/256 ink ratio: ' + worst.toFixed(2) + ' (want >= ~0.7)');
