// One-off: slices the base game's energy orb icons out of ui_atlas_0.png using the region rects in
// ui_atlas.sprites/card/energy_*.tres, and writes them to .tools/art/ref/ui/.
//   node slice-energy.js
'use strict';
const fs = require('fs');
const path = require('path');
const { decode, savePNG } = require('./pngio.js');

const SRC = 'C:\\temp\\artref\\out';
const TRES = 'C:\\temp\\artref\\tres\\ui_atlas.sprites\\card';
const OUT = path.join(__dirname, 'ref', 'ui');

const atlasFile = fs.readdirSync(SRC).find(f => f.startsWith('atlas__ui_atlas_0'));
if (!atlasFile) throw new Error('ui_atlas png not found in ' + SRC);
const atlas = decode(path.join(SRC, atlasFile));
console.log('ui_atlas ' + atlas.width + 'x' + atlas.height);

fs.mkdirSync(OUT, { recursive: true });
let n = 0;
for (const f of fs.readdirSync(TRES).sort()) {
  const txt = fs.readFileSync(path.join(TRES, f), 'utf8');
  const m = /region = Rect2\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\s*\)/.exec(txt);
  if (!m) continue;
  const x0 = Math.round(+m[1]), y0 = Math.round(+m[2]), w = Math.round(+m[3]), h = Math.round(+m[4]);
  const out = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++) {
    atlas.pixels.copy(out, y * w * 4,
      ((y0 + y) * atlas.width + x0) * 4, ((y0 + y) * atlas.width + x0 + w) * 4);
  }
  const id = f.replace(/\.tres$/, '');
  savePNG(path.join(OUT, id + '.png'), w, h, out);
  console.log('  ' + id + '  ' + w + 'x' + h);
  n++;
}
console.log('sliced ' + n + ' base-game energy icons -> ' + OUT);
