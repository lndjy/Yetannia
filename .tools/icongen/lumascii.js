// Luminance-band ASCII rendering - useful for checking gradient/shaded art like the energy orb.
'use strict';
const { decode } = require('./pngread.js');
const RAMP = ' .:-=+*#%@';

function art(file, cols, rows, alphaFloor) {
  const img = decode(file);
  const { width, height, channels, pixels } = img;
  const cw = width / cols, ch = height / rows;
  const lines = [];
  for (let r = 0; r < rows; r++) {
    let line = '';
    for (let c = 0; c < cols; c++) {
      let n = 0, sum = 0, maxA = 0;
      const x0 = Math.floor(c * cw), x1 = Math.max(x0 + 1, Math.floor((c + 1) * cw));
      const y0 = Math.floor(r * ch), y1 = Math.max(y0 + 1, Math.floor((r + 1) * ch));
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const i = (y * width + x) * channels;
          const A = channels === 4 ? pixels[i + 3] : 255;
          const L = pixels[i] * 0.299 + pixels[i + 1] * 0.587 + pixels[i + 2] * 0.114;
          sum += L * (A / 255); n++;
          if (A > maxA) maxA = A;
        }
      }
      const v = sum / n;
      const idx = Math.max(0, Math.min(RAMP.length - 1, Math.round(v / 255 * (RAMP.length - 1))));
      line += maxA < (alphaFloor || 32) ? ' ' : RAMP[idx];
    }
    lines.push(line);
  }
  return lines;
}

if (require.main === module) {
  const files = process.argv.slice(2);
  for (const f of files) {
    const a = art(f, 64, 32, 32);
    const name = f.split(/[\\/]/).pop();
    console.log('=== ' + name + ' ' + '='.repeat(Math.max(0, 56 - name.length)));
    console.log('+' + '-'.repeat(64) + '+');
    for (const l of a) console.log('|' + l + '|');
    console.log('+' + '-'.repeat(64) + '+');
  }
}
