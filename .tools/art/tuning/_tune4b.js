// One-shot tuning patch #4b: flatten the raised-part gradients and tighten the glow/shadow blurs,
// which is what spreads the palette over hundreds of 8x8x8 buckets.
// Throwaway tooling - run once with `node _tune4b.js`.
'use strict';
const fs = require('fs');
const path = require('path');
const FILE = path.join(__dirname, 'paint.js');
let t = fs.readFileSync(FILE, 'utf8');
const R = [
  // raised parts: nearly flat two-tone, so a large area lands in one or two colour buckets
  [`    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[1]], [0.30, ramp[1]], [0.66, ramp[2]], [0.90, ramp[2]], [1.0, ramp[3]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 52, 32, 100, WARM_KEY, 0.13, 'lighter');
    pool(ctx, 234, 242, 104, INK_DARK, 0.15);`,
   `    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[1]], [0.44, ramp[1]], [0.82, ramp[2]], [1.0, ramp[2]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 52, 32, 88, WARM_KEY, 0.11, 'lighter');
    pool(ctx, 236, 244, 96, INK_DARK, 0.13);`],
  // tighter drop shadows (a wide blur ramp is a lot of distinct colours for very little read)
  [`    ctx.shadowBlur = 5 + inkW * 1.7;
    ctx.shadowOffsetX = inkW * 0.9;
    ctx.shadowOffsetY = inkW * 1.3;`,
   `    ctx.shadowBlur = 3 + inkW * 1.2;
    ctx.shadowOffsetX = inkW * 0.75;
    ctx.shadowOffsetY = inkW * 1.05;`],
  [`    ctx.shadowBlur = 4 + inkW * 1.3;
    ctx.shadowOffsetX = inkW * 0.7; ctx.shadowOffsetY = inkW * 1.0;`,
   `    ctx.shadowBlur = 3 + inkW * 0.9;
    ctx.shadowOffsetX = inkW * 0.6; ctx.shadowOffsetY = inkW * 0.85;`],
  // interior ink 3 -> 2.4 design units (4.8 px at 512 = 0.6 px at 64)
  [`    var iw = 3;
    // ---- pass 1: silhouette only, to measure the content bbox and the covered area`,
   `    var iw = 2.4;
    // ---- pass 1: silhouette only, to measure the content bbox and the covered area`],
  [`    var iw = 3;                          // interior ink width, design units
    var obj = def.build(ctx, r, mulberry(seed), iw);`,
   `    var iw = 2.4;                        // interior ink width, design units
    var obj = def.build(ctx, r, mulberry(seed), iw);`],
  // interior ink a touch less black than the silhouette ink -> lower interior edge contrast
  [`  function inkOf(ramp) { return mixc(ramp[6], '#000000', 0.40); }`,
   `  function inkOf(ramp) { return mixc(ramp[6], '#000000', 0.40); }
  // interior detail ink: a hair lighter than the silhouette ink, so the interior reads busy
  // without out-edging the base game (vanilla interior sobel density is 37 %, not 58 %)
  function inkInner(ramp) { return mixc(ramp[5], '#000000', 0.20); }`],
  [`    ctx.strokeStyle = ink; ctx.lineWidth = inkW; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.stroke(path);
    ctx.restore();`,
   `    ctx.strokeStyle = inkInner(ramp); ctx.lineWidth = inkW; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.stroke(path);
    ctx.restore();`],
  [`    ctx.strokeStyle = ink; ctx.lineWidth = inkW; ctx.lineJoin = 'round';
    ctx.stroke(path);
    ctx.restore();
    ctx.save();
    ctx.clip(path);
    ctx.strokeStyle = 'rgba(0,0,0,0.58)';`,
   `    ctx.strokeStyle = inkInner(ramp); ctx.lineWidth = inkW; ctx.lineJoin = 'round';
    ctx.stroke(path);
    ctx.restore();
    ctx.save();
    ctx.clip(path);
    ctx.strokeStyle = 'rgba(0,0,0,0.58)';`],
];
let n = 0; const miss = [];
for (const [a, b] of R) {
  if (!t.includes(a)) { miss.push(a.split('\n')[0].trim().slice(0, 70)); continue; }
  t = t.replace(a, b); n++;
}
fs.writeFileSync(FILE, t);
console.log('patched ' + n + '/' + R.length);
if (miss.length) { console.log('MISSED:'); miss.forEach(x => console.log('  ' + x)); }
