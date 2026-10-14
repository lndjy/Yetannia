// Slices the true in-game icons (64x64 / trimmed) out of power_atlas + relic_atlas using the
// region rects from the game's own `*.sprites/<id>.tres` AtlasTexture resources.
//
// Outputs:
//   .tools/art/ref64/powers/<id>.png   (region-sized, usually 64x64)
//   .tools/art/ref64/relics/<name>.png (trimmed region)
// Usage: node slice-atlas.js
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { decode } = require('../icongen/pngread.js');

const WORK = 'C:\\temp\\artref';
const TRES = path.join(WORK, 'tres');
const OUT = 'D:\\桌面\\sts2mod\\.tools\\art\\ref64';

// ------------------------------------------------------------------ PNG writer
const CRC_TABLE = (() => {
  const t = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    t[n] = c;
  }
  return t;
})();
function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0);
  const td = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td), 0);
  return Buffer.concat([len, td, crc]);
}
function encodePNG(width, height, rgba) {
  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (stride + 1)] = 0;
    rgba.copy(raw, y * (stride + 1) + 1, y * stride, (y + 1) * stride);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0)),
  ]);
}

// ------------------------------------------------------------------ slice
const atlasFiles = fs.readdirSync(path.join(WORK, 'out')).filter(f => f.startsWith('atlas__') && f.endsWith('.png'));
const atlases = {};
for (const f of atlasFiles) {
  const key = f.replace(/^atlas__/, '').replace(/\.png-[0-9a-f]+\.(bptc|s3tc)\.png$/, '');
  atlases[key] = decode(path.join(WORK, 'out', f));
}
console.log('atlases decoded:', Object.keys(atlases).map(k => k + ' ' + atlases[k].width + 'x' + atlases[k].height).join(', '));

function parseTres(file) {
  const txt = fs.readFileSync(file, 'utf8');
  const rm = /region = Rect2\(\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\)/.exec(txt);
  if (!rm) return null;
  const mm = /margin = Rect2\(\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\)/.exec(txt);
  return {
    region: { x: +rm[1], y: +rm[2], w: +rm[3], h: +rm[4] },
    margin: mm ? { x: +mm[1], y: +mm[2], w: +mm[3], h: +mm[4] } : null,
  };
}

function cropAt(img, r) {
  const w = Math.round(r.w), h = Math.round(r.h), x0 = Math.round(r.x), y0 = Math.round(r.y);
  const out = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++) {
    img.pixels.copy(out, y * w * 4, ((y0 + y) * img.width + x0) * 4, ((y0 + y) * img.width + x0 + w) * 4);
  }
  return { w, h, px: out };
}

const summary = { powers: 0, relics: 0, sizes: {}, missing: [] };
for (const kind of ['power_atlas', 'relic_atlas']) {
  const atlas = atlases[kind];
  const dir = path.join(TRES, kind + '.sprites');
  if (!atlas || !fs.existsSync(dir)) { summary.missing.push(kind); continue; }
  const walk = (d, prefix) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { walk(p, prefix + e.name + '/'); continue; }
      if (!e.name.endsWith('.tres')) continue;
      const info = parseTres(p);
      if (!info) continue;
      const id = (prefix + e.name.replace(/\.tres$/, '')).replace(/\//g, '__');
      const c = cropAt(atlas, info.region);
      const outKind = kind === 'power_atlas' ? 'powers' : 'relics';
      const dst = path.join(OUT, outKind, id + '.png');
      fs.mkdirSync(path.dirname(dst), { recursive: true });
      fs.writeFileSync(dst, encodePNG(c.w, c.h, c.px));
      summary.sizes[c.w + 'x' + c.h] = (summary.sizes[c.w + 'x' + c.h] || 0) + 1;
      if (kind === 'power_atlas') summary.powers++; else summary.relics++;
    }
  };
  walk(dir, '');
}
console.log('sliced powers=' + summary.powers + ' relics=' + summary.relics + ' -> ' + OUT);
console.log('region sizes:', JSON.stringify(summary.sizes));
if (summary.missing.length) console.log('MISSING atlases:', summary.missing.join(', '));
