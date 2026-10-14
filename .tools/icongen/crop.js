// Crops the rendered 256x256 icon sheet into individual PNGs, and writes
// RGB-dilated copies used for the high quality 64x64 downscale.
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { decode } = require('./pngread.js');

// ---------------------------------------------------------------- PNG write
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
  ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// -------------------------------------------------- crop / dilate / resize
function crop(img, x0, y0, w, h) {
  const out = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++) {
    img.pixels.copy(out, y * w * 4, ((y0 + y) * img.width + x0) * 4, ((y0 + y) * img.width + x0 + w) * 4);
  }
  return out;
}

// Spread edge RGB outward into fully transparent pixels so a bicubic downscale
// does not sample black-transparent pixels and darken the silhouette edges.
function dilateRGB(rgba, w, h, passes) {
  const known = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) if (rgba[i * 4 + 3] > 0) known[i] = 1;
  for (let p = 0; p < passes; p++) {
    const add = [];
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        if (known[i]) continue;
        let r = 0, g = 0, b = 0, n = 0;
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const nx = x + dx, ny = y + dy;
            if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
            const j = ny * w + nx;
            if (!known[j] || (dx === 0 && dy === 0)) continue;
            r += rgba[j * 4]; g += rgba[j * 4 + 1]; b += rgba[j * 4 + 2]; n++;
          }
        }
        if (n) add.push([i, (r / n) | 0, (g / n) | 0, (b / n) | 0]);
      }
    }
    for (const [i, r, g, b] of add) {
      rgba[i * 4] = r; rgba[i * 4 + 1] = g; rgba[i * 4 + 2] = b; known[i] = 1;
    }
  }
  return rgba;
}

// ------------------------------------------------------------------- main
const ROOT = 'D:\\桌面\\sts2mod\\.tools\\pckproject\\Yetannia\\images';
const PREP = 'C:\\temp\\icogen\\prep';
fs.mkdirSync(PREP, { recursive: true });

const man = JSON.parse(fs.readFileSync('C:\\temp\\icogen\\manifest.json', 'utf8'));
const sheet = decode('C:\\temp\\icogen\\sheet256.png');
console.log('sheet decoded', sheet.width + 'x' + sheet.height, 'expected', man.width + 'x' + man.height);
if (sheet.width !== man.width || sheet.height !== man.height) throw new Error('sheet size mismatch');

function outPath(icon, big) {
  if (icon.group === 'power') return path.join(ROOT, big ? 'powers_big' : 'powers', icon.name + '.png');
  if (icon.group === 'relic') return path.join(ROOT, big ? 'relics_big' : 'relics', icon.name + '.png');
  return path.join(ROOT, 'ui', big ? 'energy_yetannia.png' : 'energy_yetannia_small.png');
}

const report = [];
for (const icon of man.icons) {
  const px = crop(sheet, icon.x, icon.y, icon.size, icon.size);
  const big = outPath(icon, true);
  fs.mkdirSync(path.dirname(big), { recursive: true });
  fs.writeFileSync(big, encodePNG(256, 256, px));
  // prepared copy (dilated) for System.Drawing downscale
  const prep = Buffer.from(px);
  dilateRGB(prep, 256, 256, 6);
  fs.writeFileSync(path.join(PREP, icon.index + '_' + icon.name + '.png'), encodePNG(256, 256, prep));
  report.push({ index: icon.index, name: icon.name, big, small: outPath(icon, false) });
}

fs.writeFileSync('C:\\temp\\icogen\\crop-report.json', JSON.stringify(report, null, 2), 'utf8');
console.log('cropped', report.length, 'big icons ->', ROOT);
