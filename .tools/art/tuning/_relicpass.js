// One-shot relic pass. Comparison round 6 showed the 5 relics diverging from vanilla relics:
//   coveragePct 46.5 vs 57.8      -> silhouettes too sparse inside their bbox
//   bbox.fillPct 72.6 vs 87.8     -> same
//   highlightPct 24.4 vs 5.1, p90 0.854 vs 0.681, meanSaturation 0.576 vs 0.337 -> too bright,
//       too saturated. Vanilla relics are muted: leather, iron, patina, stone
//   hueBinsAbove1Pct 1.2 vs 3.07  -> mine were monochrome bronze; vanilla relics combine several
//       materials, which is also what gives them their hue spread
// So: a MAT table of extra materials (leather/iron/ivory/amber/glass/agate), a warm-light mute for
// the relic group, denser relic silhouettes, and each relic rebuilt out of several materials.
// Throwaway tooling - run once with `node _relicpass.js`.
'use strict';
const fs = require('fs');
const path = require('path');
const FILE = path.join(__dirname, 'paint.js');
let src = fs.readFileSync(FILE, 'utf8');

// ---------------------------------------------------------------- 1. MAT table + warm mute
src = src.replace(
  `  function hex(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }`,
  `  // Extra materials for the relic group. Vanilla relics are not one metal: they mix leather,
  // iron, ivory, amber and glass, which is where their hue spread and their muted saturation
  // (0.34 vs the powers' 0.42) come from.
  var MAT = {
    leather: ['#f2e0c6', '#d9b183', '#a9764a', '#7d5230', '#54341d', '#331e0f', '#180d06'],
    iron:    ['#eef3f7', '#c2ccd5', '#8a97a3', '#5c6975', '#3c4650', '#242b32', '#0f1317'],
    ivory:   ['#fffbf2', '#f2e7cf', '#dbc9a2', '#b7a077', '#897352', '#5a4931', '#2b2114'],
    amber:   ['#fff3d0', '#ffd98a', '#e8a72c', '#b87a12', '#82530a', '#523304', '#261701'],
    glassG:  ['#eafff2', '#a8f0cf', '#4fc79a', '#1f8f6a', '#12614a', '#0a3a2c', '#041a13'],
    glassR:  ['#ffe9ea', '#ffb0b4', '#e8626a', '#b0323c', '#7a1e26', '#4a1016', '#220609'],
  };
  var WARM_MUL = 1;   // relics take a dimmer, cooler key light than powers

  function hex(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }`);

src = src.replace(
  `  var WARM_KEY = '#ffdc9a';    // the key light is warm on every family - a base-game signature`,
  `  var WARM_KEY = '#ffdc9a';    // the key light is warm on every family - a base-game signature
  // NOTE: WARM_MUL is declared next to FAM so the relic group can dial the key light down.`);

src = src.replace(`    pool(ctx, 56, 34, 96, WARM_KEY, 0.18, 'lighter');
    pool(ctx, 84, 60, 58, ramp[0], 0.18, 'lighter');`,
  `    pool(ctx, 56, 34, 96, WARM_KEY, 0.18 * WARM_MUL, 'lighter');
    pool(ctx, 84, 60, 58, ramp[0], 0.18 * WARM_MUL, 'lighter');`);
src = src.replace(`    pool(ctx, 36, 20, 88, WARM_KEY, 0.09, 'lighter');`,
  `    pool(ctx, 36, 20, 88, WARM_KEY, 0.09 * WARM_MUL, 'lighter');`);
src = src.replace(`    pool(ctx, 52, 32, 88, WARM_KEY, 0.11, 'lighter');`,
  `    pool(ctx, 52, 32, 88, WARM_KEY, 0.11 * WARM_MUL, 'lighter');`);

// set the mute per group
src = src.replace(`  window.__DRAW_ICON = function (ctx, def) {
    var r = FAM[def.cat] || FAM.violet;
    var seed = hashName(def.name);
    var iw = 2.1;`,
  `  window.__DRAW_ICON = function (ctx, def) {
    var r = FAM[def.cat] || FAM.violet;
    var seed = hashName(def.name);
    var iw = 2.1;
    WARM_MUL = def.group === 'relic' ? 0.45 : 1;`);

// ---------------------------------------------------------------- 2. rebuild the relics
const marks = [];
const re = /^  add\('/gm;
let m;
while ((m = re.exec(src)) !== null) marks.push(m.index);
marks.push(src.length);
const head = src.slice(0, marks[0]);
const blocks = [];
for (let i = 0; i < marks.length - 1; i++) {
  const text = src.slice(marks[i], marks[i + 1]);
  blocks.push({ name: /^  add\('([^']+)'/.exec(text)[1], text });
}

const RELICS = {
  agate_potion_belt: `  add('agate_potion_belt', 'relic', 'bronze', 0.70, function (ctx, r, rnd, iw) {
    // an agate-studded potion belt: leather strap, iron buckle, two glass vials
    var leather = MAT.leather, iron = MAT.iron, amb = MAT.amber, gA = MAT.glassG, gB = MAT.glassR;
    var strap = rr(0, 116, 256, 78, 22);
    var buckle = rr(76, 96, 104, 116, 17);
    var fl = function (cx) {
      var p = Pth();
      p.moveTo(cx - 30, 118);
      p.bezierCurveTo(cx - 52, 106, cx - 50, 78, cx - 28, 64);
      p.lineTo(cx - 28, 42); p.lineTo(cx - 35, 42); p.lineTo(cx - 35, 18); p.lineTo(cx + 35, 18);
      p.lineTo(cx + 35, 42); p.lineTo(cx + 28, 42); p.lineTo(cx + 28, 64);
      p.bezierCurveTo(cx + 50, 78, cx + 52, 106, cx + 30, 118);
      p.closePath(); return p;
    };
    return { sil: U(strap, buckle, fl(38), fl(218)), paint: function () {
      body(ctx, r, 22);
      raised(ctx, strap, leather, iw * 0.85, 620);
      for (var i = 0; i < 3; i++) raised(ctx, rr(20 + i * 100, 132, 42, 48, 8), iron, iw * 0.32, 630 + i);
      raised(ctx, buckle, iron, iw * 0.85, 640);
      recessed(ctx, rr(90, 112, 76, 84, 9), iron, iw * 0.42, 641);
      raised(ctx, rr(114, 112, 28, 84, 9), amb, iw * 0.34, 642);
      ctx.save(); ctx.translate(38, 0);
      raised(ctx, fl(0), amb, iw * 0.55, 650);
      recessed(ctx, ell(0, 92, 28, 21, 0), gA, iw * 0.3, 660);
      glowShape(ctx, ell(0, 92, 20, 14, 0), gA[1], rgba(gA[0], 0.45), 8); ctx.restore();
      ctx.save(); ctx.translate(218, 0);
      raised(ctx, fl(0), amb, iw * 0.55, 651);
      recessed(ctx, ell(0, 92, 28, 21, 0), gB, iw * 0.3, 661);
      glowShape(ctx, ell(0, 92, 20, 14, 0), gB[1], rgba(gB[0], 0.45), 8); ctx.restore();
      for (var m = 0; m < 4; m++) raised(ctx, circ(36 + m * 62, 208, 6.5), iron, iw * 0.22, 670 + m);
    } };
  });
`,
  foresight_charm: `  add('foresight_charm', 'relic', 'bronze', 0.72, function (ctx, r, rnd, iw) {
    // a hanging seeing-charm: iron loop, bronze disc, ivory star bezel, amber eye
    var iron = MAT.iron, iv = MAT.ivory, amb = MAT.amber;
    var loop = ring(128, 30, 40, 20);
    var disc = circ(128, 146, 114);
    return { sil: U(loop, disc), paint: function () {
      body(ctx, r, 23);
      raised(ctx, loop, iron, iw * 0.6, 680);
      raised(ctx, disc, r, iw * 0.85, 681);
      raised(ctx, ring(128, 146, 106, 84), iron, iw * 0.5, 682);
      recessed(ctx, circ(128, 146, 84), r, iw * 0.45, 683);
      for (var i = 0; i < 8; i++) {
        var a = i * Math.PI / 4;
        raised(ctx, star(128 + Math.cos(a) * 74, 146 + Math.sin(a) * 74, 16, 5.5, 4, a), amb, iw * 0.24, 690 + i);
      }
      glowShape(ctx, almond(128, 146, 54, 31), iv, null, 12);
      glowShape(ctx, circ(128, 146, 18), amb[2], rgba(amb[6], 0.92), 7);
      glowShape(ctx, circ(120, 138, 6), iv[0], null, 5);
      raised(ctx, sparkle(228, 50, 23, 8, -Math.PI / 2), amb, iw * 0.3, 700);
    } };
  });
`,
  prophets_bracelet: `  add('prophets_bracelet', 'relic', 'bronze', 0.68, function (ctx, r, rnd, iw) {
    // a heavy bronze armilla: iron teeth, amber cabochon, ivory setting
    var iron = MAT.iron, iv = MAT.ivory, amb = MAT.amber;
    var band = ring(128, 134, 130, 60);
    var clasp = rr(102, 0, 52, 52, 14);
    return { sil: U(band, clasp), paint: function () {
      body(ctx, r, 24);
      raised(ctx, band, r, iw * 0.85, 710);
      for (var i = 0; i < 5; i++) {
        var a = -Math.PI * 0.5 + i * (Math.PI * 2 / 5);
        recessed(ctx, star(128 + Math.cos(a) * 95, 134 + Math.sin(a) * 95, 17, 5.5, 4, a), iron, iw * 0.26, 720 + i);
      }
      raised(ctx, ring(128, 134, 88, 70), iron, iw * 0.45, 725);
      raised(ctx, clasp, iron, iw * 0.5, 730);
      glowShape(ctx, almond(128, 134, 46, 27), iv, null, 11);
      glowShape(ctx, circ(128, 134, 15), amb[2], rgba(amb[6], 0.92), 7);
      glowShape(ctx, circ(121, 127, 5.5), iv[0], null, 5);
      for (var k = 0; k < 2; k++) raised(ctx, star(60 + k * 116, 240, 15, 5.5, 4, -Math.PI / 2), amb, iw * 0.24, 740 + k);
    } };
  });
`,
  prophets_eye: `  add('prophets_eye', 'relic', 'bronze', 0.66, function (ctx, r, rnd, iw) {
    // the prophet's eye in an iron setting with a bronze bezel, ivory sclera, amber iris
    var iron = MAT.iron, iv = MAT.ivory, amb = MAT.amber;
    var casing = Pth();
    casing.moveTo(0, 128);
    casing.bezierCurveTo(40, 20, 216, 20, 256, 128);
    casing.bezierCurveTo(216, 236, 40, 236, 0, 128);
    casing.closePath();
    return { sil: casing, paint: function () {
      body(ctx, r, 25);
      raised(ctx, casing, iron, iw * 0.85, 750);
      raised(ctx, ring(128, 128, 112, 92), r, iw * 0.5, 752);
      recessed(ctx, ring(128, 128, 94, 78), iron, iw * 0.42, 751);
      for (var i = 0; i < 5; i++) {
        var a = -Math.PI + i * Math.PI / 4;
        raised(ctx, circ(128 + Math.cos(a) * 116, 128 + Math.sin(a) * 116 * 0.62, 8), r, iw * 0.24, 760 + i);
      }
      recessed(ctx, ell(128, 128, 92, 70, 0), iv, iw * 0.42, 770);
      glowShape(ctx, ell(128, 128, 44, 58, 0), amb[1], null, 11);
      glowShape(ctx, circ(128, 128, 32), amb[3], rgba(amb[6], 0.92), 8);
      recessed(ctx, ell(128, 128, 12, 32, 0), amb, iw * 0.3, 771);
      glowShape(ctx, circ(118, 116, 8), iv[0], null, 6);
      raisedLine(ctx, line([[20, 128], [38, 88]]), 8, r, iw * 0.3, 772);
    } };
  });
`,
  prophets_eye_plus: `  add('prophets_eye_plus', 'relic', 'bronzeBright', 0.70, function (ctx, r, rnd, iw) {
    // the upgraded eye: gilded setting, brighter amber, a plus mark and gold sparks
    var iron = MAT.iron, iv = MAT.ivory, amb = MAT.amber;
    var casing = Pth();
    casing.moveTo(0, 128);
    casing.bezierCurveTo(40, 18, 214, 18, 254, 128);
    casing.bezierCurveTo(214, 238, 40, 238, 0, 128);
    casing.closePath();
    var plus = plusPath(210, 46, 44, 15);
    var sparks = Pth();
    for (var k = 0; k < 2; k++) sparks.addPath(sparkle(40 + k * 128, 28, 15, 5.5, -Math.PI / 2));
    return { sil: U(casing, plus, sparks), paint: function () {
      body(ctx, r, 26);
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      pool(ctx, 128, 128, 130, r[1], 0.16 * WARM_MUL);
      ctx.restore();
      raised(ctx, casing, r, iw * 0.85, 790);
      raised(ctx, ring(128, 128, 112, 90), amb, iw * 0.5, 792);
      recessed(ctx, ring(128, 128, 92, 78), iron, iw * 0.42, 791);
      for (var i = 0; i < 5; i++) {
        var a = -Math.PI + i * Math.PI / 4;
        raised(ctx, circ(128 + Math.cos(a) * 114, 128 + Math.sin(a) * 114 * 0.62, 8.5), amb, iw * 0.26, 800 + i);
      }
      recessed(ctx, ell(128, 128, 90, 68, 0), iv, iw * 0.42, 810);
      glowShape(ctx, ell(128, 128, 44, 58, 0), amb[1], null, 12);
      glowShape(ctx, circ(128, 128, 33), amb[3], rgba(amb[6], 0.92), 9);
      recessed(ctx, ell(128, 128, 12, 33, 0), amb, iw * 0.3, 811);
      glowShape(ctx, circ(117, 115, 9), iv[0], null, 7);
      raised(ctx, plus, amb, iw * 0.62, 820);
      glowShape(ctx, plusPath(210, 46, 24, 8), amb[1], rgba(amb[0], 0.45), 9);
      for (var k = 0; k < 2; k++) raised(ctx, sparkle(40 + k * 128, 28, 15, 5.5, -Math.PI / 2), amb, iw * 0.26, 830 + k);
    } };
  });
`,
};

let replaced = 0;
for (const b of blocks) {
  if (RELICS[b.name]) { b.text = RELICS[b.name]; replaced++; }
}
src = head + blocks.map(b => b.text).join('');
fs.writeFileSync(FILE, src);
console.log('rebuilt ' + replaced + ' relic blocks; MAT table + WARM_MUL installed');
