// PNG read/write helpers for the v2 art pipeline.
//   decode  - reuse the proven reader from ../icongen/pngread.js
//   encode  - minimal RGBA8 PNG writer, same chunk layout crop.js used
'use strict';
const fs = require('fs');
const zlib = require('zlib');
const { decode } = require('../icongen/pngread.js');

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
function savePNG(file, w, h, rgba) { fs.writeFileSync(file, encodePNG(w, h, rgba)); }

// spread edge RGB outward into fully transparent pixels so a bicubic downscale never samples
// black-transparent pixels and darkens the silhouette edge
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
            if (dx === 0 && dy === 0) continue;
            const j = ny * w + nx;
            if (!known[j]) continue;
            r += rgba[j * 4]; g += rgba[j * 4 + 1]; b += rgba[j * 4 + 2]; n++;
          }
        }
        if (n) add.push([i, (r / n) | 0, (g / n) | 0, (b / n) | 0]);
      }
    }
    for (const [i, r, g, b] of add) { rgba[i * 4] = r; rgba[i * 4 + 1] = g; rgba[i * 4 + 2] = b; known[i] = 1; }
  }
  return rgba;
}

// chamfer 3-4 distance transform: distance from every mask pixel to the nearest non-mask pixel
function chamferInside(mask, w, h) {
  const INF = 1e9, D1 = 1, D2 = Math.SQRT2;
  const d = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) d[i] = mask[i] ? INF : 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x; let v = d[i];
      if (y > 0) { if (d[i - w] + D1 < v) v = d[i - w] + D1; if (x > 0 && d[i - w - 1] + D2 < v) v = d[i - w - 1] + D2; if (x < w - 1 && d[i - w + 1] + D2 < v) v = d[i - w + 1] + D2; }
      if (x > 0 && d[i - 1] + D1 < v) v = d[i - 1] + D1;
      d[i] = v;
    }
  }
  for (let y = h - 1; y >= 0; y--) {
    for (let x = w - 1; x >= 0; x--) {
      const i = y * w + x; let v = d[i];
      if (y < h - 1) { if (d[i + w] + D1 < v) v = d[i + w] + D1; if (x > 0 && d[i + w - 1] + D2 < v) v = d[i + w - 1] + D2; if (x < w - 1 && d[i + w + 1] + D2 < v) v = d[i + w + 1] + D2; }
      if (x < w - 1 && d[i + 1] + D1 < v) v = d[i + 1] + D1;
      d[i] = v;
    }
  }
  return d;
}
// same, for non-mask pixels: distance to the nearest mask pixel
function chamferOutside(mask, w, h) {
  const inv = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) inv[i] = mask[i] ? 0 : 1;
  return chamferInside(inv, w, h);
}

module.exports = { decode, encodePNG, savePNG, dilateRGB, chamferInside, chamferOutside };
