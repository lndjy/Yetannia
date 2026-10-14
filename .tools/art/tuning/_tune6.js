// One-shot tuning patch #6 (final): round 5 over-darkened slightly (darkPct 35.7 vs 26.1,
// midPct 19.5 vs 30.0) and interior edge density is still a hair over vanilla's p90.
// Throwaway tooling - run once with `node _tune6.js`.
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
  // body: lift the shadow corner back up a little
  [`    ctx.globalAlpha = 0.20;
    ctx.fillStyle = axisGrad(ctx, 40, 14, 224, 252, [[0.0, rgba(ramp[5], 0)], [0.62, rgba(ramp[5], 0)], [1.0, rgba(ramp[5], 0.85)]]);`,
   `    ctx.globalAlpha = 0.15;
    ctx.fillStyle = axisGrad(ctx, 40, 14, 224, 252, [[0.0, rgba(ramp[5], 0)], [0.62, rgba(ramp[5], 0)], [1.0, rgba(ramp[5], 0.85)]]);`],
  [`    pool(ctx, 248, 252, 112, INK_DARK, 0.18);`, `    pool(ctx, 248, 252, 104, INK_DARK, 0.13);`],
  // raised parts stay bright; recessed hollows keep the dark mass but cover a little less area
  [`    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[5]], [0.30, ramp[5]], [0.80, ramp[6]], [1.0, ramp[6]]
    ]);`,
   `    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[4]], [0.34, ramp[5]], [0.82, ramp[5]], [1.0, ramp[6]]
    ]);`],
  // interior ink: 2.4 -> 2.1 design units, and a slightly narrower part outline
  [`    var iw = 2.4;
    // ---- pass 1: silhouette only, to measure the content bbox and the covered area`,
   `    var iw = 2.1;
    // ---- pass 1: silhouette only, to measure the content bbox and the covered area`],
  [`    var iw = 2.4;                        // interior ink width, design units
    var obj = def.build(ctx, r, mulberry(seed), iw);`,
   `    var iw = 2.1;                        // interior ink width, design units
    var obj = def.build(ctx, r, mulberry(seed), iw);`],
], 'paint.js');
