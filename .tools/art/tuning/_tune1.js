// One-shot tuning patch #1 for paint.js, driven by the vanilla comparison table:
//   too dark       value.mean 0.325 vs 0.462, darkPct 45 vs 26, lightPct 11 vs 30
//   too noisy      distinctColors 330 vs 158, top1Pct 7.7 vs 29.1, top5Pct 25 vs 62
//   too busy       edges.interiorPct 48 vs 37
//   too soft       softAlphaPct 54 vs 28.5   (fixed in artrefine.js)
// Changes: brighter ramps whose base sits at luma ~0.50, less ambient-occlusion darkening,
// less texture, a warm key light on every family (vanilla highlights are warm and tinted).
// Throwaway tooling - run once with `node _tune1.js`.
'use strict';
const fs = require('fs');
const p = require('path').join(__dirname, 'paint.js');
let t = fs.readFileSync(p, 'utf8');
const R = [];

// ---------------------------------------------------------------- ramps
const oldFam = t.slice(t.indexOf('  var FAM = {'), t.indexOf('  };', t.indexOf('  var FAM = {')) + 4);
R.push([oldFam, `  var FAM = {
    // stop luma targets: .95 .80 .67 .50 .36 .24 .12  (vanilla body mass sits in 0.30-0.85)
    violet:    ['#f6ecff', '#d9bcff', '#b795f5', '#8f68dd', '#6a45b4', '#472b80', '#241542'],
    crimson:   ['#ffe6d2', '#ffb489', '#ef7a52', '#d4523a', '#9c2c1e', '#6b1a12', '#360c08'],
    emerald:   ['#e8ffe2', '#b0f0a8', '#74d182', '#3fa458', '#24713c', '#124a26', '#06230f'],
    steel:     ['#e6f6ff', '#a8daf7', '#66a9e0', '#3f88c6', '#1f5386', '#103357', '#06172a'],
    slate:     ['#f2f7f8', '#cad6d8', '#9dadaf', '#75868a', '#526063', '#333e40', '#181f21'],
    gold:      ['#fff8da', '#ffe07a', '#e8b32c', '#b98a14', '#8a6508', '#5a4104', '#2b1e01'],
    rose:      ['#ffe8f2', '#ffaecd', '#ec6ba3', '#c04378', '#8c2851', '#571530', '#2a0a17'],
    bronze:    ['#fff4d8', '#f6d79c', '#d5a44e', '#a87b2c', '#7a5518', '#4d350c', '#241804'],
    starlight: ['#f6fbff', '#cfe8ff', '#96c4f7', '#5f8ede', '#3d63b4', '#233c80', '#0e1740'],
    orb:       ['#f8f0ff', '#dcc0ff', '#b795f5', '#8a5fd8', '#6138a8', '#3d2170', '#1c0f38'],
  };
`]);

// ---------------------------------------------------------------- body()
R.push([`    ctx.fillStyle = axisGrad(ctx, 62, 12, 210, 252, [
      [0.00, tint(ramp[1], 0.12)], [0.13, ramp[1]], [0.32, ramp[2]],
      [0.53, ramp[3]], [0.74, ramp[4]], [0.89, ramp[5]], [1.00, ramp[6]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 74, 52, 134, ramp[0], 0.40, 'lighter');
    pool(ctx, 116, 96, 78, ramp[1], 0.28, 'lighter');
    pool(ctx, 216, 228, 118, opt.bounce || ramp[2], 0.13, 'lighter');
    pool(ctx, 238, 246, 150, INK_DARK, 0.44);
    pool(ctx, 248, 130, 98, INK_DARK, 0.20);
    ctx.save();
    ctx.globalAlpha = 0.58;
    ctx.fillStyle = axisGrad(ctx, 40, 18, 222, 252, [[0.0, rgba(ramp[6], 0)], [0.52, rgba(ramp[6], 0)], [1.0, rgba(ramp[6], 0.88)]]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    ctx.restore();
    texture(ctx, seed, opt.grain === undefined ? 0.30 : opt.grain);
    pool(ctx, 44, 28, 98, opt.warm || ramp[0], 0.16, 'lighter');`,
`    ctx.fillStyle = axisGrad(ctx, 58, 8, 214, 252, [
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
    pool(ctx, 40, 24, 96, WARM_KEY, 0.16, 'lighter');`]);

// ---------------------------------------------------------------- texture()
R.push([`    ctx.globalAlpha = 0.13;
    ctx.lineCap = 'round';
    for (var i = 0; i < 54; i++) {`,
`    ctx.globalAlpha = 0.07;
    ctx.lineCap = 'round';
    for (var i = 0; i < 30; i++) {`]);
R.push([`    ctx.globalAlpha = 0.17;
    for (var k = 0; k < 100; k++) {`,
`    ctx.globalAlpha = 0.10;
    for (var k = 0; k < 55; k++) {`]);

// ---------------------------------------------------------------- raised()
R.push([`    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, tint(ramp[0], 0.06)], [0.20, ramp[1]], [0.48, ramp[3]], [0.76, ramp[4]], [1.0, ramp[5]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 58, 38, 98, ramp[0], 0.32, 'lighter');
    pool(ctx, 228, 238, 112, INK_DARK, 0.34);`,
`    ctx.fillStyle = axisGrad(ctx, 70, 28, 202, 242, [
      [0.0, ramp[0]], [0.22, ramp[1]], [0.55, ramp[2]], [0.82, ramp[3]], [1.0, ramp[4]]
    ]);
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    pool(ctx, 54, 34, 104, WARM_KEY, 0.26, 'lighter');
    pool(ctx, 232, 240, 108, INK_DARK, 0.19);`]);

// ---------------------------------------------------------------- recessed() a touch lighter
R.push([`      [0.0, shade(ramp[4], 0.32)], [0.34, ramp[5]], [0.78, ramp[6]], [1.0, shade(ramp[6], 0.35)]`,
`      [0.0, shade(ramp[3], 0.28)], [0.36, ramp[4]], [0.78, ramp[5]], [1.0, shade(ramp[6], 0.25)]`]);

// ---------------------------------------------------------------- warm light constant
R.push([`  var INK_DARK = [10, 7, 14];
  var DESIGN = 256;`,
`  var INK_DARK = [10, 7, 14];
  var WARM_KEY = '#ffeccb';    // the key light is warm on every family - a base-game signature
  var DESIGN = 256;`]);

// ---------------------------------------------------------------- bbox cap: the soft skirt adds
// up to ~17 px outside the mask, so 0.93 keeps the measured bbox fill inside vanilla's p90 (96.9)
R.push([`    var sBboxMax = 0.98 * RENDER / Math.max(bw, bh);`,
`    var sBboxMax = 0.93 * RENDER / Math.max(bw, bh);`]);

let n = 0, miss = [];
for (const [a, b] of R) {
  if (!t.includes(a)) { miss.push(a.split('\n')[0].trim().slice(0, 70)); continue; }
  t = t.replace(a, b); n++;
}
fs.writeFileSync(p, t);
console.log('patched ' + n + '/' + R.length);
if (miss.length) { console.log('MISSED:'); miss.forEach(m => console.log('  ' + m)); }
