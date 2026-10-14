// Where does the partial alpha live? For vanilla icons: distribution of distance-to-silhouette-edge
// for (a) fully opaque pixels and (b) partial-alpha pixels. Decides how thick the edge feather is
// versus how much translucency is interior glow.
// Usage: node alphaprobe.js <dir> [n]
'use strict';
const fs = require('fs');
const path = require('path');
const { decode } = require('../icongen/pngread.js');

function chamfer(mask, W, H) {
  const INF = 1e9;
  const d = new Float64Array(W * H);
  for (let i = 0; i < W * H; i++) d[i] = mask[i] ? INF : 0;
  const D1 = 1, D2 = Math.SQRT2;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x; let v = d[i];
    if (y > 0) { v = Math.min(v, d[i - W] + D1); if (x > 0) v = Math.min(v, d[i - W - 1] + D2); if (x < W - 1) v = Math.min(v, d[i - W + 1] + D2); }
    if (x > 0) v = Math.min(v, d[i - 1] + D1);
    d[i] = v;
  }
  for (let y = H - 1; y >= 0; y--) for (let x = W - 1; x >= 0; x--) {
    const i = y * W + x; let v = d[i];
    if (y < H - 1) { v = Math.min(v, d[i + W] + D1); if (x > 0) v = Math.min(v, d[i + W - 1] + D2); if (x < W - 1) v = Math.min(v, d[i + W + 1] + D2); }
    if (x < W - 1) v = Math.min(v, d[i + 1] + D1);
    d[i] = v;
  }
  return d;
}

const dir = process.argv[2];
const N = +(process.argv[3] || 80);
const files = fs.readdirSync(dir).filter(f => f.endsWith('.png')).slice(0, N);

// histogram of dIn for opaque vs partial
const BINS = 14;
const hop = new Float64Array(BINS), hpa = new Float64Array(BINS);
let opaqueN = 0, partN = 0;
let partNearSum = 0;

for (const f of files) {
  const img = decode(path.join(dir, f));
  const { width: W, height: H, channels: C, pixels: P } = img;
  const mask = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) mask[i] = P[i * C + 3] >= 32 ? 1 : 0;
  const d = chamfer(mask, W, H);
  for (let i = 0; i < W * H; i++) {
    const a = P[i * C + 3];
    if (a < 32) continue;               // only covered pixels, so dIn >= 1
    const dd = d[i];
    if (a >= 250) { opaqueN++; hop[Math.min(BINS - 1, Math.floor(dd))]++; }
    else { partN++; hpa[Math.min(BINS - 1, Math.floor(dd))]++; partNearSum += dd; }
  }
}

const pct = (h, n) => [...h].map(v => +(100 * v / n).toFixed(1));
console.log('dir=' + dir + '  n=' + files.length);
console.log('opaque pixels   = ' + opaqueN + '   partial pixels = ' + partN +
  '   (partial share of non-transparent = ' + (100 * partN / (opaqueN + partN)).toFixed(1) + '%)');
console.log('mean distance-to-edge of partial pixels = ' + (partNearSum / partN).toFixed(2) + ' px  (at 64)');
console.log('bin (distance to silhouette edge, px):  0    1    2    3    4    5    6    7    8    9   10   11   12  13+');
console.log('opaque  %: ' + pct(hop, opaqueN).map(v => String(v).padStart(4)).join(' '));
console.log('partial %: ' + pct(hpa, partN).map(v => String(v).padStart(4)).join(' '));
