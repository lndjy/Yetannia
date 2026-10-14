// Pulls the REAL in-game icons: the sliced regions of power_atlas / relic_atlas.
//
// `.tools/decomp-proj/.../Models/PowerModel.cs` shows the game loads
//   res://images/atlases/power_atlas.sprites/<id>.tres
// and `strength_power.tres` carries `region = Rect2(1, 1057, 64, 64)` -- i.e. the icon the game
// actually draws is a 64x64 slice of the atlas, NOT the 256x256 images/powers/<id>.png source.
// So the 64x64 slices are the thing to match at 64, and the 256 sources the thing to match at 256.
//
// Usage: node fetch-atlas.js            (extract ctex + .tres + .tpsheet for both atlases)
'use strict';
const fs = require('fs');
const path = require('path');

const PCK = 'D:\\SteamLibrary\\steamapps\\common\\Slay the Spire 2\\SlayTheSpire2.pck';
const WORK = 'C:\\temp\\artref';
const OUT_CTEX = path.join(WORK, 'ctex');

const ATLASES = [
  '.godot/imported/power_atlas.png-042f9a9c120df1e2add731fa3af3c47d.bptc.ctex',
  '.godot/imported/relic_atlas.png-9b0d72cf095fb31862c28656d62b697f.bptc.ctex',
  '.godot/imported/relic_outline_atlas.png-2dc174faa3bc5a43922b0d25cdfa2564.bptc.ctex',
];

// reuse the index reader from the sibling script
const src = fs.readFileSync(path.join(__dirname, 'fetch-refs.js'), 'utf8');
const readerSrc = src.slice(src.indexOf('const MAGIC'), src.indexOf('const argv ='));
const readIndex = new Function('fs', readerSrc + '\nreturn readIndex;')(fs);

const idx = readIndex(PCK);
const fd = fs.openSync(PCK, 'r');
function readEntry(name) {
  const e = idx.get(name);
  if (!e) return null;
  const buf = Buffer.alloc(e.size);
  fs.readSync(fd, buf, 0, e.size, e.offset);
  return buf;
}

fs.mkdirSync(OUT_CTEX, { recursive: true });
const tresDir = path.join(WORK, 'tres');
fs.mkdirSync(tresDir, { recursive: true });

const got = { ctex: [], tres: 0, tpsheet: 0, missing: [] };

for (const a of ATLASES) {
  const blob = readEntry(a);
  if (!blob) { got.missing.push(a); continue; }
  const flat = 'atlas__' + path.basename(a);
  fs.writeFileSync(path.join(OUT_CTEX, flat), blob);
  got.ctex.push({ src: a, flat, bytes: blob.length });
}

for (const [name] of idx) {
  const m = /^images\/atlases\/(power_atlas|relic_atlas)\.sprites\/(.+)\.tres$/.exec(name);
  if (m) {
    const dst = path.join(tresDir, m[1] + '.sprites', m[2] + '.tres');
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.writeFileSync(dst, readEntry(name));
    got.tres++;
    continue;
  }
  const t = /^images\/atlases\/(power_atlas|relic_atlas)\.tpsheet$/.exec(name);
  if (t) {
    fs.writeFileSync(path.join(tresDir, t[1] + '.tpsheet'), readEntry(name));
    got.tpsheet++;
  }
}
fs.closeSync(fd);

console.log('atlas ctex extracted:', got.ctex.map(c => c.flat + ' (' + c.bytes + 'B)').join(', '));
console.log('sprite .tres extracted:', got.tres, ' tpsheets:', got.tpsheet);
if (got.missing.length) console.log('MISSING:', got.missing.join(', '));
