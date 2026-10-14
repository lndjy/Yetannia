// One-shot tuning patch #3, driven by comparison round 3:
//   edges.interiorPct 59.0 vs 37.2  -> still ~1.6x too busy. Fewer, larger interior details and
//       thinner detail ink. Texture scratches/specks also read as edges after the 8x downscale.
//   distinctColors 308 vs 158       -> mostly texture speckle; cut it
//   highlightPct 20.8 vs 13.7, lightPct 22.3 vs 30.3, p90 0.847 vs 0.742 -> brights too bright
//   softAlphaPct 41.8 vs 28.5       -> narrow the feather a touch more
//   innerRimLuma 0.075 vs 0.042     -> sharpen the inner edge of the ink band
//   bbox.fillPct 88.8 vs 92.0       -> a little more room before the clamp
// Throwaway tooling - run once with `node _tune3.js`.
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
  // ---- gentler bright end
  [`    pool(ctx, 60, 38, 132, WARM_KEY, 0.22, 'lighter');
    pool(ctx, 88, 64, 78, ramp[0], 0.26, 'lighter');`,
   `    pool(ctx, 60, 38, 132, WARM_KEY, 0.16, 'lighter');
    pool(ctx, 88, 64, 78, ramp[0], 0.16, 'lighter');`],
  [`    pool(ctx, 36, 20, 88, WARM_KEY, 0.13, 'lighter');`,
   `    pool(ctx, 36, 20, 88, WARM_KEY, 0.09, 'lighter');`],
  [`    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[0]], [0.26, ramp[1]], [0.62, ramp[1]], [0.88, ramp[2]], [1.0, ramp[3]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 52, 32, 100, WARM_KEY, 0.20, 'lighter');`,
   `    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[1]], [0.30, ramp[1]], [0.66, ramp[2]], [0.90, ramp[2]], [1.0, ramp[3]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 52, 32, 100, WARM_KEY, 0.13, 'lighter');`],

  // ---- fewer, quieter texture marks (they dominate the distinct-colour count at 64 px)
  [`    ctx.globalAlpha = 0.07;
    ctx.lineCap = 'round';
    for (var i = 0; i < 30; i++) {`,
   `    ctx.globalAlpha = 0.05;
    ctx.lineCap = 'round';
    for (var i = 0; i < 16; i++) {`],
  [`    ctx.globalAlpha = 0.10;
    for (var k = 0; k < 55; k++) {`,
   `    ctx.globalAlpha = 0.07;
    for (var k = 0; k < 26; k++) {`],

  // ---- thinner interior ink: 3 design units = 6 px at 512 = 0.75 px at 64
  [`    var iw = 4;
    // ---- pass 1: silhouette only, to measure the content bbox and the covered area`,
   `    var iw = 3;
    // ---- pass 1: silhouette only, to measure the content bbox and the covered area`],
  [`    var iw = 4;                          // interior ink width, design units
    var obj = def.build(ctx, r, mulberry(seed), iw);`,
   `    var iw = 3;                          // interior ink width, design units
    var obj = def.build(ctx, r, mulberry(seed), iw);`],

  // ---- raised(): drop the second (highlight) stroke pass on everything; keep a light top edge
  [`    ctx.save();
    ctx.clip(path);
    ctx.strokeStyle = rgba(ramp[0], 0.55);
    ctx.lineWidth = inkW * 0.8; ctx.lineJoin = 'round';
    ctx.translate(-inkW * 0.8, -inkW * 0.8);
    ctx.stroke(path);
    ctx.restore();
  }`,
   `    // (no separate highlight stroke: vanilla gets its light edge from the value gradient, and an
    // extra stroke per part doubled the interior edge density at 64 px)
  }`],

  // ---- a little more room: bbox cap
  [`    var sBboxMax = 0.955 * RENDER / Math.max(bw, bh);`,
   `    var sBboxMax = 0.965 * RENDER / Math.max(bw, bh);`],
], 'paint.js');

patch(path.join(__dirname, 'artrefine.js'), [
  [`const FEATHER_OUT = num('--featherOut', 8);`, `const FEATHER_OUT = num('--featherOut', 6);`],
  [`      const lo = hi * 0.62;`, `      const lo = hi * 0.72;`],
  [`          alpha *= 1 - 0.13 * Math.max(0, wear - 0.46);`,
   `          alpha *= 1 - 0.10 * Math.max(0, wear - 0.50);`],
], 'artrefine.js');
