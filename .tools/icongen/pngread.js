// Minimal PNG reader (IHDR + full RGBA decode) for verification purposes.
'use strict';
const fs = require('fs');
const zlib = require('zlib');

function readChunks(buf) {
  if (buf.length < 8 || buf.readUInt32BE(0) !== 0x89504e47) throw new Error('not a PNG');
  let off = 8;
  const chunks = [];
  while (off + 8 <= buf.length) {
    const len = buf.readUInt32BE(off);
    const type = buf.toString('ascii', off + 4, off + 8);
    const data = buf.slice(off + 8, off + 8 + len);
    chunks.push({ type, data });
    off += 12 + len;
    if (type === 'IEND') break;
  }
  return chunks;
}

function paeth(a, b, c) {
  const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
  return (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c);
}

function decode(file) {
  const buf = fs.readFileSync(file);
  const chunks = readChunks(buf);
  const ihdr = chunks.find(c => c.type === 'IHDR');
  if (!ihdr) throw new Error('no IHDR');
  const width = ihdr.data.readUInt32BE(0);
  const height = ihdr.data.readUInt32BE(4);
  const bitDepth = ihdr.data[8];
  const colorType = ihdr.data[9];
  const interlace = ihdr.data[12];
  const idat = Buffer.concat(chunks.filter(c => c.type === 'IDAT').map(c => c.data));
  const raw = zlib.inflateSync(idat);

  const channels = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[colorType];
  const bpp = channels * (bitDepth / 8);
  const stride = width * bpp;
  const out = Buffer.alloc(height * stride);
  let pos = 0;
  for (let y = 0; y < height; y++) {
    const ft = raw[pos++];
    const line = raw.slice(pos, pos + stride); pos += stride;
    const cur = out.slice(y * stride, (y + 1) * stride);
    const prev = y > 0 ? out.slice((y - 1) * stride, y * stride) : null;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? cur[x - bpp] : 0;
      const b = prev ? prev[x] : 0;
      const c = (prev && x >= bpp) ? prev[x - bpp] : 0;
      let v = line[x];
      if (ft === 1) v = (v + a) & 0xff;
      else if (ft === 2) v = (v + b) & 0xff;
      else if (ft === 3) v = (v + ((a + b) >> 1)) & 0xff;
      else if (ft === 4) v = (v + paeth(a, b, c)) & 0xff;
      else if (ft !== 0) throw new Error('bad filter ' + ft);
      cur[x] = v;
    }
  }
  if (bitDepth !== 8) throw new Error('unsupported bit depth ' + bitDepth);
  return { width, height, bitDepth, colorType, interlace, channels, pixels: out, chunks };
}

// Stats useful for "is this icon real" checks
function stats(file) {
  const img = decode(file);
  const { width, height, channels, pixels } = img;
  const colorSet = new Set();
  let opaque = 0, semi = 0, transparent = 0;
  let minX = width, minY = height, maxX = -1, maxY = -1;
  let sumA = 0;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * channels;
      let r, g, b, a;
      if (channels === 4) { r = pixels[i]; g = pixels[i + 1]; b = pixels[i + 2]; a = pixels[i + 3]; }
      else if (channels === 3) { r = pixels[i]; g = pixels[i + 1]; b = pixels[i + 2]; a = 255; }
      else if (channels === 2) { r = g = b = pixels[i]; a = pixels[i + 1]; }
      else { r = g = b = pixels[i]; a = 255; }
      sumA += a;
      if (a === 255) opaque++; else if (a === 0) transparent++; else semi++;
      if (a > 8) {
        if (x < minX) minX = x; if (x > maxX) maxX = x;
        if (y < minY) minY = y; if (y > maxY) maxY = y;
      }
      // bucket colours to keep the set bounded but meaningful
      colorSet.add(((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3));
    }
  }
  const total = width * height;
  return {
    file, width, height, channels,
    colorType: img.colorType, interlace: img.interlace,
    bytes: fs.statSync(file).size,
    opaquePct: +(100 * opaque / total).toFixed(2),
    semiPct: +(100 * semi / total).toFixed(2),
    transparentPct: +(100 * transparent / total).toFixed(2),
    meanAlpha: +(sumA / total).toFixed(2),
    distinctColors: colorSet.size,
    bbox: maxX < 0 ? null : { x: minX, y: minY, w: maxX - minX + 1, h: maxY - minY + 1 },
  };
}

module.exports = { decode, stats, readChunks };

if (require.main === module) {
  for (const f of process.argv.slice(2)) {
    try { console.log(JSON.stringify(stats(f))); }
    catch (e) { console.log(JSON.stringify({ file: f, error: String(e.message) })); }
  }
}
