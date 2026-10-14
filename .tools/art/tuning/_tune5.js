// One-shot tuning patch #5, driven by comparison round 5. Everything is inside vanilla's
// p10..p90 band except:
//   innerRimLuma 0.077 vs 0.042 -> the ink band's inner transition is still ~1 px wide at 64;
//       vanilla goes 94 % near-black at ring 1-2 and clean by ring 3, i.e. a harder edge
//   top1Pct 16.2 vs 29.1, top5Pct 37.9 vs 62.0 -> vanilla icons put most of their area in a
//       handful of 8x8x8 colour buckets. Fix: an exactly-constant ink core (no body bleed inside
//       the band) and a flatter, larger body mass.
// Throwaway tooling - run once with `node _tune5.js`.
'use strict';
const fs = require('fs');
const path = require('path');

function patch(file, reps, label) {
  let t = fs.readFileSync(file, 'utf8');
  let n = 0; const miss = [];
  for (const [a, b] of reps) {
    if (!t.includes(a)) { miss.push(a.split('\n')[0].trim().slice(0, 70)); continue; }
    t = t.replace(a, b); n++;
  }
  fs.writeFileSync(file, t);
  console.log(label + ': patched ' + n + '/' + reps.length);
  if (miss.length) { console.log('  MISSED:'); miss.forEach(m => console.log('    ' + m)); }
}

patch(path.join(__dirname, 'artrefine.js'), [
  // a hard band edge; still a ~0.4 px blend at 64 which is what vanilla's ring-3 reads as
  [`const INK_W = num('--ink', 18);          // ink band end, px at 512 (18 = 2.25 px at 64)`,
   `const INK_W = num('--ink', 17);          // ink band end, px at 512 (17 = 2.1 px at 64)`],
  [`      const lo = hi * 0.72;`, `      const lo = hi * 0.84;`],
  // the ink core is one constant colour: k = inkA already gives a natural bleed into the body at
  // the band's inner edge, while the core (inkA = 1) lands in exactly one 5-bit bucket. That is
  // what lifts top-1/top-5 colour share toward vanilla's 29 % / 62 %.
  [`      const ir = INK_RGB[0] + br * 0.015, ig = INK_RGB[1] + bg * 0.015, ib = INK_RGB[2] + bb * 0.015;
      const k = inkA;`,
   `      const ir = INK_RGB[0], ig = INK_RGB[1], ib = INK_RGB[2];
      const k = inkA;`],
], 'artrefine.js');

patch(path.join(__dirname, 'paint.js'), [
  // flatter body mass: a wider plateau at ramp[2] and a tighter key-light pool
  [`    ctx.fillStyle = axisGrad(ctx, 54, 4, 218, 252, [
      [0.00, ramp[1]], [0.22, ramp[2]], [0.55, ramp[2]], [0.80, ramp[3]], [1.00, ramp[3]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    // key light: warm cream on every family - vanilla highlights are warm and strongly tinted
    pool(ctx, 60, 38, 132, WARM_KEY, 0.16, 'lighter');
    pool(ctx, 88, 64, 78, ramp[0], 0.16, 'lighter');
    pool(ctx, 246, 250, 138, INK_DARK, 0.20);`,
   `    ctx.fillStyle = axisGrad(ctx, 54, 4, 218, 252, [
      [0.00, ramp[1]], [0.18, ramp[2]], [0.66, ramp[2]], [0.88, ramp[3]], [1.00, ramp[3]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    // key light: warm cream on every family - vanilla highlights are warm and strongly tinted
    pool(ctx, 56, 34, 96, WARM_KEY, 0.18, 'lighter');
    pool(ctx, 84, 60, 58, ramp[0], 0.18, 'lighter');
    pool(ctx, 248, 252, 112, INK_DARK, 0.18);`],
  // recessed hollows: flatter and darker, so they share the ink's colour buckets
  [`    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, shade(ramp[3], 0.28)], [0.36, ramp[4]], [0.78, ramp[5]], [1.0, shade(ramp[6], 0.25)]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 128, 234, 120, ramp[3], 0.24, 'lighter');`,
   `    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[5]], [0.30, ramp[5]], [0.80, ramp[6]], [1.0, ramp[6]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 128, 234, 112, ramp[3], 0.20, 'lighter');`],
  // quieter recessed inner shadow: it was adding a second strong edge per hollow
  [`    ctx.strokeStyle = 'rgba(0,0,0,0.58)';
    ctx.lineWidth = inkW * 1.1; ctx.lineJoin = 'round';
    ctx.translate(inkW * 0.85, inkW * 0.85);`,
   `    ctx.strokeStyle = 'rgba(0,0,0,0.52)';
    ctx.lineWidth = inkW * 0.9; ctx.lineJoin = 'round';
    ctx.translate(inkW * 0.8, inkW * 0.8);`],
], 'paint.js');
