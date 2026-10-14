// One-shot tuning patch #2 for paint.js + artrefine.js, driven by comparison round 2:
//   bbox.fillPct 84.3 vs 92.0 and ringAlphaPct 0.26 vs 3.57 -> the 0.93 bbox cap over-shrank things
//   coveragePct 54.0 vs 61.1
//   edges.interiorPct 58.5 vs 37.2 -> detail crammed too small, plus a too-wide ink ramp
//   distinctColors 337 vs 158, top1Pct 7.4 vs 29.1 -> the body gradient spread over too many
//      8x8x8 buckets. Vanilla icons are a few large near-flat masses with hard light/dark parts,
//      not one smooth global gradient. So: flatten body(), move contrast into raised/recessed.
//   value.p10 0.051 vs 0.016 and darkMassLuma 0.037 vs 0.012 -> the outline is not black enough
//   highlightChroma 59 vs 72 -> highlights need more chroma
// Throwaway tooling - run once with `node _tune2.js`.
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

patch(path.join(__dirname, 'paint.js'), [
  // warmer, more saturated key light
  [`  var WARM_KEY = '#ffeccb';    // the key light is warm on every family - a base-game signature`,
   `  var WARM_KEY = '#ffdc9a';    // the key light is warm on every family - a base-game signature`],

  // flatter body: most of the mass sits in two adjacent stops, contrast comes from the parts
  [`    ctx.fillStyle = axisGrad(ctx, 58, 8, 214, 252, [
      [0.00, ramp[1]], [0.16, ramp[2]], [0.38, ramp[2]],
      [0.60, ramp[3]], [0.80, ramp[4]], [0.93, ramp[5]], [1.00, ramp[6]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    // key light: warm cream on every family - vanilla highlights are warm and strongly tinted
    pool(ctx, 66, 44, 150, WARM_KEY, 0.30, 'lighter');
    pool(ctx, 92, 70, 92, ramp[0], 0.34, 'lighter');
    pool(ctx, 224, 232, 116, opt.bounce || ramp[2], 0.10, 'lighter');
    pool(ctx, 244, 250, 150, INK_DARK, 0.24);
    pool(ctx, 252, 134, 92, INK_DARK, 0.11);
    ctx.save();
    ctx.globalAlpha = 0.32;
    ctx.fillStyle = axisGrad(ctx, 40, 14, 224, 252, [[0.0, rgba(ramp[6], 0)], [0.58, rgba(ramp[6], 0)], [1.0, rgba(ramp[6], 0.80)]]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    ctx.restore();
    texture(ctx, seed, opt.grain === undefined ? 0.15 : opt.grain);
    pool(ctx, 40, 24, 96, WARM_KEY, 0.16, 'lighter');`,
   `    // one broad, slow gradient over a narrow slice of the ramp: large near-flat masses, which is
    // what gives the base game its low distinct-colour count and high top-1 colour share
    ctx.fillStyle = axisGrad(ctx, 54, 4, 218, 252, [
      [0.00, ramp[1]], [0.22, ramp[2]], [0.55, ramp[2]], [0.80, ramp[3]], [1.00, ramp[3]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    // key light: warm cream on every family - vanilla highlights are warm and strongly tinted
    pool(ctx, 60, 38, 132, WARM_KEY, 0.22, 'lighter');
    pool(ctx, 88, 64, 78, ramp[0], 0.26, 'lighter');
    pool(ctx, 246, 250, 138, INK_DARK, 0.20);
    ctx.save();
    ctx.globalAlpha = 0.20;
    ctx.fillStyle = axisGrad(ctx, 40, 14, 224, 252, [[0.0, rgba(ramp[5], 0)], [0.62, rgba(ramp[5], 0)], [1.0, rgba(ramp[5], 0.85)]]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    ctx.restore();
    texture(ctx, seed, opt.grain === undefined ? 0.09 : opt.grain);
    pool(ctx, 36, 20, 88, WARM_KEY, 0.13, 'lighter');`],

  // raised parts carry the light half of the value range and stay fairly flat themselves
  [`    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[0]], [0.22, ramp[1]], [0.55, ramp[2]], [0.82, ramp[3]], [1.0, ramp[4]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 54, 34, 104, WARM_KEY, 0.26, 'lighter');
    pool(ctx, 232, 240, 108, INK_DARK, 0.19);`,
   `    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[0]], [0.26, ramp[1]], [0.62, ramp[1]], [0.88, ramp[2]], [1.0, ramp[3]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 52, 32, 100, WARM_KEY, 0.20, 'lighter');
    pool(ctx, 234, 242, 104, INK_DARK, 0.15);`],

  // a kiss more room before the bbox clamp bites (the soft skirt adds ~10 px outside the mask)
  [`    var sBboxMax = 0.93 * RENDER / Math.max(bw, bh);`,
   `    var sBboxMax = 0.955 * RENDER / Math.max(bw, bh);`],
], 'paint.js');

patch(path.join(__dirname, 'artrefine.js'), [
  [`const INK_W = num('--ink', 20);          // ink band end, px at 512 (20 = 2.5 px at 64)`,
   `const INK_W = num('--ink', 18);          // ink band end, px at 512 (18 = 2.25 px at 64)`],
  [`const INK_RGB = [7, 5, 11];`, `const INK_RGB = [4, 3, 7];`],
  // sharper band edge: vanilla goes 94 % near-black at ring 1-2 and clean by ring 3
  [`      const lo = hi * 0.45;`, `      const lo = hi * 0.62;`],
  [`      const ir = INK_RGB[0] + br * 0.07, ig = INK_RGB[1] + bg * 0.07, ib = INK_RGB[2] + bb * 0.07;
      const k = inkA * 0.985;`,
   `      const ir = INK_RGB[0] + br * 0.015, ig = INK_RGB[1] + bg * 0.015, ib = INK_RGB[2] + bb * 0.015;
      const k = inkA;`],
], 'artrefine.js');
