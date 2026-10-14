// Renders a PNG as ASCII art so the glyph silhouettes can be judged without an image viewer.
// Legend: '#' near-white glyph  '.' dark cut-out  '-' mid tone (shadow/edge)  ' ' frame colour
'use strict';
const { decode } = require('./pngread.js');

function art(file, cols, rows) {
  const img = decode(file);
  const { width, height, channels, pixels } = img;
  const cw = width / cols, ch = height / rows;
  const lines = [];
  for (let r = 0; r < rows; r++) {
    let line = '';
    for (let c = 0; c < cols; c++) {
      let white = 0, dark = 0, n = 0, lum = 0;
      const x0 = Math.floor(c * cw), x1 = Math.max(x0 + 1, Math.floor((c + 1) * cw));
      const y0 = Math.floor(r * ch), y1 = Math.max(y0 + 1, Math.floor((r + 1) * ch));
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const i = (y * width + x) * channels;
          const R = pixels[i], G = pixels[i + 1], B = pixels[i + 2];
          const A = channels === 4 ? pixels[i + 3] : 255;
          const L = (R * 0.299 + G * 0.587 + B * 0.114) * (A / 255);
          n++; lum += L;
          if (A > 128 && R > 205 && G > 208 && B > 212) white++;      // glyph near-white #f2f4f8
          else if (L < 92) dark++;                                     // dark cut-out / deep frame
        }
      }
      const wf = white / n, df = dark / n, al = lum / n;
      if (wf > 0.45) line += '#';
      else if (wf > 0.12) line += '+';
      else if (df > 0.45) line += '.';
      else if (df > 0.15) line += ',';
      else if (al < 60) line += ' ';
      else line += '-';
    }
    lines.push(line);
  }
  return lines;
}

if (require.main === module) {
  const files = process.argv.slice(2);
  const cols = 64, rows = 32;
  for (const f of files) {
    let a;
    try { a = art(f, cols, rows); } catch (e) { console.log(f + ': ERROR ' + e.message); continue; }
    const name = f.split(/[\\/]/).pop();
    console.log('=== ' + name + ' ' + '='.repeat(Math.max(0, 56 - name.length)));
    console.log('+' + '-'.repeat(cols) + '+');
    for (const l of a) console.log('|' + l + '|');
    console.log('+' + '-'.repeat(cols) + '+');
  }
}
module.exports = { art };
