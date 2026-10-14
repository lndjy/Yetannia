// One-shot tuning patch #4, driven by comparison round 4:
//   edges.interiorPct 57.8 vs 37.2  -> ~1.55x too busy. The driver is the number of separate
//       outlined interior parts: every rivet/tooth/barb adds two ink edges that survive the 8x
//       downscale. Cut the decorative loops roughly in half, thin the interior ink, and flatten
//       the raised-part gradients (which also lifts top-1 colour share).
//   distinctColors 274 vs 158, top5Pct 34.7 vs 62.0 -> glow/shadow blur ramps and per-part
//       gradients each spread across many 8x8x8 buckets; fewer and tighter ones.
//   innerRimLuma 0.076 vs 0.042 -> the ink band should stay darker a little further in.
// Per-icon edits are scoped to that icon's own block so identical loop headers elsewhere are safe.
// Throwaway tooling - run once with `node _tune4.js`.
'use strict';
const fs = require('fs');
const path = require('path');
const FILE = path.join(__dirname, 'paint.js');
let src = fs.readFileSync(FILE, 'utf8');

// ---- split into per-icon blocks
const marks = [];
const re = /^  add\('/gm;
let m;
while ((m = re.exec(src)) !== null) marks.push(m.index);
marks.push(src.length);
const head = src.slice(0, marks[0]);
let blocks = [];
for (let i = 0; i < marks.length - 1; i++) {
  const text = src.slice(marks[i], marks[i + 1]);
  const nm = /^  add\('([^']+)'/.exec(text)[1];
  blocks.push({ name: nm, text });
}

// name -> [[find, replace], ...]
const EDITS = {
  nirvana: [['for (var i = 0; i < 7; i++) {', 'for (var i = 0; i < 4; i++) {'],
            ['for (var k = 0; k < 4; k++) {', 'for (var k = 0; k < 2; k++) {']],
  foresight: [['for (var i = 0; i < 12; i++) {', 'for (var i = 0; i < 8; i++) {'],
              ['(Math.PI * 1.88 / 11)', '(Math.PI * 1.88 / 7)']],
  cycle_of_prophecy: [['for (var i = 0; i < 9; i++) {', 'for (var i = 0; i < 5; i++) {'],
                      ['(0.07 + i * 0.095)', '(0.10 + i * 0.175)']],
  scry_might: [['for (var i = 0; i < 4; i++) {\n        raised(ctx, ell(86 + i * 36',
                'for (var i = 0; i < 3; i++) {\n        raised(ctx, ell(86 + i * 36'],
               ['for (var k = 0; k < 4; k++) raised(ctx, circ(82 + k * 36, 74, 5.5)',
                'for (var k = 0; k < 2; k++) raised(ctx, circ(96 + k * 64, 74, 5.5)']],
  scry_agility: [['for (var i = 0; i < 11; i++) {', 'for (var i = 0; i < 7; i++) {'],
                 ['var t = 0.08 + i * 0.078;', 'var t = 0.10 + i * 0.125;']],
  steady_agility: [['for (var i = 0; i < 8; i++) {', 'for (var i = 0; i < 5; i++) {'],
                   ['var t = 0.10 + i * 0.10;', 'var t = 0.14 + i * 0.165;']],
  delayed_scry: [['for (var i = 0; i < 5; i++) {', 'for (var i = 0; i < 3; i++) {'],
                 ['for (var k = 0; k < 8; k++) {', 'for (var k = 0; k < 5; k++) {']],
  granted_turn: [['for (var i = 0; i < 5; i++) {', 'for (var i = 0; i < 3; i++) {'],
                 ['for (var k = 0; k < 7; k++) {', 'for (var k = 0; k < 4; k++) {']],
  exhaust_blast: [['for (var k = 0; k < 8; k++) {', 'for (var k = 0; k < 5; k++) {'],
                  ['var aa = k * Math.PI / 4 + 0.2;', 'var aa = k * Math.PI / 2.5 + 0.2;']],
  free_status: [['for (var i = 0; i < 5; i++) raised(ctx, circ(60 + i * 34, 128, 5)',
                 'for (var i = 0; i < 3; i++) raised(ctx, circ(70 + i * 58, 128, 5)']],
  double_status: [['for (var i = 0; i < 4; i++) raised(ctx, circ(94, 58 + i * 46, 4.8)',
                  'for (var i = 0; i < 2; i++) raised(ctx, circ(94, 70 + i * 78, 4.8)']],
  foresight_charm: [['for (var i = 0; i < 12; i++) {', 'for (var i = 0; i < 8; i++) {'],
                    ['var a = i * Math.PI / 6;', 'var a = i * Math.PI / 4;']],
  prophets_bracelet: [['for (var i = 0; i < 9; i++) {', 'for (var i = 0; i < 5; i++) {'],
                      ['var a = -Math.PI * 0.5 + i * (Math.PI * 2 / 9);',
                       'var a = -Math.PI * 0.5 + i * (Math.PI * 2 / 5);'],
                      ['for (var k = 0; k < 4; k++) raised(ctx, star(40 + k * 58, 238, 14, 5, 4, -Math.PI / 2)',
                       'for (var k = 0; k < 2; k++) raised(ctx, star(64 + k * 112, 238, 14, 5, 4, -Math.PI / 2)']],
  prophets_eye: [['for (var i = 0; i < 8; i++) {', 'for (var i = 0; i < 5; i++) {'],
                 ['var a = -Math.PI + i * Math.PI / 7;', 'var a = -Math.PI + i * Math.PI / 4;']],
  prophets_eye_plus: [['for (var i = 0; i < 8; i++) {', 'for (var i = 0; i < 5; i++) {'],
                      ['var a = -Math.PI + i * Math.PI / 7;', 'var a = -Math.PI + i * Math.PI / 4;'],
                      ['for (var k = 0; k < 4; k++) sparks.addPath(sparkle(26 + k * 64, 26 + (k % 2) * 24, 14, 5, -Math.PI / 2));',
                       'for (var k = 0; k < 2; k++) sparks.addPath(sparkle(40 + k * 128, 30, 14, 5, -Math.PI / 2));'],
                      ['for (var k = 0; k < 4; k++) raised(ctx, sparkle(26 + k * 64, 26 + (k % 2) * 24, 14, 5, -Math.PI / 2)',
                       'for (var k = 0; k < 2; k++) raised(ctx, sparkle(40 + k * 128, 30, 14, 5, -Math.PI / 2)']],
  agate_potion_belt: [['for (var i = 0; i < 5; i++) raised(ctx, rr(14 + i * 48, 140, 32, 38, 6)',
                       'for (var i = 0; i < 3; i++) raised(ctx, rr(26 + i * 82, 140, 32, 38, 6)'],
                      ['for (var m = 0; m < 6; m++) raised(ctx, circ(24 + m * 42, 204, 5)',
                       'for (var m = 0; m < 4; m++) raised(ctx, circ(40 + m * 60, 204, 5)']],
  energy_yetannia: [['for (var k = 0; k < 8; k++) {', 'for (var k = 0; k < 5; k++) {'],
                    ['var a = k * Math.PI / 4 + 0.3;', 'var a = k * Math.PI / 2.5 + 0.3;']],
  ember_boon: [['for (var k = 0; k < 6; k++) {', 'for (var k = 0; k < 4; k++) {'],
               ['var sx = 30 + rnd() * 196, sy = 12 + rnd() * 74, s = 9 + rnd() * 8;',
                'var sx = 40 + rnd() * 176, sy = 14 + rnd() * 66, s = 11 + rnd() * 9;']],
  purify: [['for (var k = 0; k < 4; k++) {\n      sparks.addPath', 'for (var k = 0; k < 2; k++) {\n      sparks.addPath']],
  starscar_form: [['for (var k = 0; k < 5; k++) {', 'for (var k = 0; k < 3; k++) {']],
};

let hits = 0, misses = [];
for (const b of blocks) {
  const list = EDITS[b.name];
  if (!list) continue;
  for (const [a, r] of list) {
    if (!b.text.includes(a)) { misses.push(b.name + ' :: ' + a.split('\n')[0].trim().slice(0, 58)); continue; }
    b.text = b.text.replace(a, r); hits++;
  }
}
src = head + blocks.map(b => b.text).join('');
fs.writeFileSync(FILE, src);
console.log('per-icon loop edits applied: ' + hits);
if (misses.length) { console.log('MISSED:'); misses.forEach(x => console.log('  ' + x)); }
