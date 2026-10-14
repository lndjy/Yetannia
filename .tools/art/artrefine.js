// Post-processes each 512x512 rendered icon into the base game's silhouette treatment.
//
// Measured off the vanilla 256 px sources by walking the mid row's left edge and printing
// (alpha, rgb) per pixel:
//
//   demon_form  A 51,150,150,128,128,126,126,126,126,111,172,255   RGB (0,0,0) ... then hard cut
//   dexterity   A 1,120,135,135,135,127,127,115,138               RGB (0,0,0) ... then hard cut
//   juggernaut  A 85,149,127,128,128,128,121,128                  RGB (0,0,0) ... then hard cut
//   this mod    A 3,31,66,93,113,146,183,218,245,255              RGB (3,2,6) ramp
//
// So the vanilla outline is a FLAT PLATEAU of semi-transparent pure black (alpha 111-150, i.e. an
// even ~0.5 black band 7-9 px wide at 256) that stops almost instantly - one transition pixel, then
// the full-opacity body colour. It is NOT a feathered grey edge. The previous pass here built an
// 8 px linear alpha ramp (0.34 -> 1.0), which is exactly the "airbrushed edge" defect: the edge was
// softer than vanilla, not harder. This pass now emits the plateau and a hard inner cut, with the
// antialiasing confined to the outermost ~2 px at 512 (0.5 px at 64).
//
// Usage: node artrefine.js [--ink 17] [--edge 3] [--aa 2.5]
'use strict';
const fs = require('fs');
const path = require('path');
const { decode, savePNG, dilateRGB, chamferInside, chamferOutside } = require('./pngio.js');

const WORK = 'C:\\temp\\art';
const IN_DIR = path.join(WORK, 'w512');
const REF_DIR = path.join(WORK, 'w512r');
const DIL_DIR = path.join(WORK, 'w512d');

const argv = process.argv.slice(2);
function num(flag, dflt) { const i = argv.indexOf(flag); return i >= 0 ? +argv[i + 1] : dflt; }
const INK_W = num('--ink', 17);          // ink band end, px at 512 (17 = 2.1 px at 64)
const EDGE = num('--edge', 3);           // px at 512 over which the plateau cuts to the body
const AA = num('--aa', 5);               // px at 512 of antialiasing outside the silhouette. 2.5 px
                                         // leaves too few partial-alpha pixels: vanilla softAlphaPct
                                         // at 64 is 28.5 %, and 2.5 px only reached 18 %.
const PLATEAU = num('--plateau', 0.52);  // vanilla's flat outline alpha (111-150 / 255)
const INK_RGB = [4, 3, 7];

function smoothstep(e0, e1, x) {
  const t = Math.max(0, Math.min(1, (x - e0) / (e1 - e0 || 1)));
  return t * t * (3 - 2 * t);
}

fs.mkdirSync(REF_DIR, { recursive: true });
fs.mkdirSync(DIL_DIR, { recursive: true });
for (const f of fs.readdirSync(REF_DIR)) fs.unlinkSync(path.join(REF_DIR, f));
for (const f of fs.readdirSync(DIL_DIR)) fs.unlinkSync(path.join(DIL_DIR, f));

const cells = JSON.parse(fs.readFileSync(path.join(WORK, 'cells.json'), 'utf8'));
const report = [];

for (const cell of cells) {
  const img = decode(cell.file);
  const W = img.width, H = img.height, C = img.channels;
  const P = img.pixels;
  const N = W * H;

  const mask = new Uint8Array(N);
  for (let i = 0; i < N; i++) mask[i] = P[i * C + 3] >= 32 ? 1 : 0;
  const dIn = chamferInside(mask, W, H);
  const dOut = chamferOutside(mask, W, H);

  const out = Buffer.alloc(N * 4);
  let partial = 0, covered = 0, inked = 0;

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x, o = i * 4;

      // The ink band is a flat plateau; only its inner 3 px ease into the body colour and full
      // alpha, and the antialiasing lives just outside the silhouette.
      const hi = INK_W;
      let alpha, inkA;
      if (mask[i]) {
        covered++;
        const t = smoothstep(hi - EDGE, hi, dIn[i]);
        inkA = 1 - t;
        alpha = PLATEAU + (1 - PLATEAU) * t;
        if (inkA > 0.5) inked++;
      } else {
        const d = dOut[i];
        alpha = PLATEAU * (1 - smoothstep(0, AA, d));
        inkA = 1;
      }
      if (alpha <= 0.004) { out[o] = out[o + 1] = out[o + 2] = out[o + 3] = 0; continue; }
      if (alpha < 0.996) partial++;

      // colour: the body, pulled toward near-black inside the ink band, with a little colour bleed
      const br = P[i * C], bg = P[i * C + 1], bb = P[i * C + 2];
      const ir = INK_RGB[0], ig = INK_RGB[1], ib = INK_RGB[2];
      const k = inkA;
      out[o] = Math.round(br + (ir - br) * k);
      out[o + 1] = Math.round(bg + (ig - bg) * k);
      out[o + 2] = Math.round(bb + (ib - bb) * k);
      out[o + 3] = Math.round(Math.max(0, Math.min(1, alpha)) * 255);
    }
  }

  const name = cell.index + '_' + cell.name + '.png';
  savePNG(path.join(REF_DIR, name), W, H, out);
  const dil = Buffer.from(out);
  dilateRGB(dil, W, H, 16);
  savePNG(path.join(DIL_DIR, name), W, H, dil);

  report.push({
    index: cell.index, name: cell.name, group: cell.group, cat: cell.cat,
    coveragePct: +(100 * covered / N).toFixed(2),
    partialPctOfCovered: +(100 * partial / Math.max(1, covered)).toFixed(2),
    inkedPctOfCovered: +(100 * inked / Math.max(1, covered)).toFixed(2),
  });
  console.log('  ' + String(cell.index).padStart(2) + ' ' + cell.name.padEnd(20) +
    ' cov=' + String(report[report.length - 1].coveragePct).padStart(6) +
    ' partial=' + String(report[report.length - 1].partialPctOfCovered).padStart(6) +
    ' inked=' + String(report[report.length - 1].inkedPctOfCovered).padStart(6));
}

fs.writeFileSync(path.join(WORK, 'refine-report.json'), JSON.stringify(report, null, 2), 'utf8');
console.log('refined ' + report.length + ' icons -> ' + REF_DIR);
// Names the parameters this pass actually uses. It used to log FEATHER_IN / FEATHER_OUT, which were
// the previous feathered-edge constants and no longer exist — that ReferenceError made the script exit
// non-zero AFTER doing all of its work, which stopped artpipeline.ps1 before artresize.ps1 could write
// the resized PNGs. The numbers are worth printing: they are the thing that was matched to vanilla.
console.log('inkW=' + INK_W + ' edge=' + EDGE + ' aa=' + AA + ' plateau=' + PLATEAU);
