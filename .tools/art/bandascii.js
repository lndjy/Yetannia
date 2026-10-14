// Banded ASCII preview: shows alpha structure AND ink structure at once.
//   ' ' transparent   '.' alpha<128   then luma ramp ':-=+*#%@' for covered pixels,
//   '#'->'@' replaced by 'x'/'X' where the pixel is near-black ink (luma<0.10).
// Usage: node bandascii.js <png> [cols] [rows]
'use strict';
const { decode } = require('../icongen/pngread.js');
const RAMP = '.:-=+*#%@';

function render(file, cols, rows) {
  const img = decode(file);
  const { width, height, channels, pixels } = img;
  const cw = width / cols, ch = height / rows;
  const out = [];
  for (let r = 0; r < rows; r++) {
    let line = '';
    for (let c = 0; c < cols; c++) {
      let n = 0, sumL = 0, sumA = 0, inkN = 0;
      const x0 = Math.floor(c * cw), x1 = Math.max(x0 + 1, Math.floor((c + 1) * cw));
      const y0 = Math.floor(r * ch), y1 = Math.max(y0 + 1, Math.floor((r + 1) * ch));
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const i = (y * width + x) * channels;
          const a = channels === 4 ? pixels[i + 3] : 255;
          const L = 0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2];
          sumA += a; sumL += L * (a / 255); n++;
          if (a > 128 && L < 25.5) inkN++;
        }
      }
      const a = sumA / n, L = sumL / n;
      if (a < 6) { line += ' '; continue; }
      if (a < 128) { line += '.'; continue; }
      if (inkN / n > 0.5) { line += (a > 240 ? 'X' : 'x'); continue; }
      line += RAMP[Math.max(1, Math.min(RAMP.length - 1, Math.round(L / 255 * (RAMP.length - 1))))];
    }
    out.push(line);
  }
  return out;
}

const files = process.argv.slice(2).filter(a => !/^\d+$/.test(a));
const nums = process.argv.slice(2).filter(a => /^\d+$/.test(a));
const cols = nums[0] ? +nums[0] : 64;
const rows = nums[1] ? +nums[1] : 32;
for (const f of files) {
  const name = f.split(/[\\/]/).pop();
  console.log('=== ' + name + ' ' + '='.repeat(Math.max(0, 62 - name.length)));
  console.log('+' + '-'.repeat(cols) + '+');
  for (const l of render(f, cols, rows)) console.log('|' + l + '|');
  console.log('+' + '-'.repeat(cols) + '+');
}
