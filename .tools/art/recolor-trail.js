// Generates Yetannia's card-play trail scene from the base game's ironclad one.
//
// WHY nothing else changed: all five vanilla card_trail_*.tscn reference the SAME five textures
// (images/packed/vfx/trail.png, trail2.png, images/vfx/brush_particle_2.png,
// images/packed/vfx/small_card_silhouette.png, images/vfx/vfx_ghostly_power_up/sparkle.png) and the
// SAME shared CanvasItemMaterial (themes/canvas_item_material_additive_shared.tres). The per
// character identity is therefore entirely in the scene's COLOUR SLOTS, so this produces one scene
// and zero new textures.
//
// Migrated (hue only): OuterTrail.modulate, InnerTrail.modulate, BigSparks.color_ramp (4 stops),
// Sprite2D2.modulate, Sprite2D3.modulate.
// Deliberately NOT touched:
//   * Line2D width_curve (Curve_0ojw2 / Curve_eaky7) - shape of the trail, not colour;
//   * the two Line2D gradients - they are greyscale (0,0,0,0 / .25,.25,.25,.306 / 1,1,1,1), so a hue
//     migration is a no-op on them anyway;
//   * LittleSparks.color_ramp - byte-identical across all five characters, i.e. it is a shared
//     neutral warm-white spark, not a character colour;
//   * every particle parameter, width and script path.
//
// Hue mapping: h' = 260 + (h - 5) * 0.55, the same one used for the energy counter. It puts the
// family's mass hue (the pure red slots, h=0) on 257 deg - the measured mass hue of
// images/ui/energy_yetannia.png - and squeezes the yellow-orange slots (h up to 50) into 257-285,
// so the relative ordering of the stops survives: the slot that was "hotter/more yellow" stays the
// more magenta one. Saturation, value and alpha are preserved exactly, which is what keeps the
// trail's brightness and its fade curves intact.
//
//   node .tools/art/recolor-trail.js
'use strict';
const fs = require('fs');
const path = require('path');

const SRC = 'C:\\temp\\art\\trail\\scenes__vfx__card_trail_ironclad.tscn';
const OUT = path.resolve(__dirname, '..', 'pckproject', 'Yetannia', 'scenes', 'vfx', 'card_trail_yetannia.tscn');
const MASS_HUE = 260, SRC_HUE = 5, SQUEEZE = 0.55;

function rgb2hsv(r, g, b) {
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  let h = 0;
  if (d > 1e-9) {
    if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4;
    h *= 60; if (h < 0) h += 360;
  }
  return [h, mx <= 1e-9 ? 0 : d / mx, mx];
}
function hsv2rgb(h, s, v) {
  h = ((h % 360) + 360) % 360;
  const c = v * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = v - c;
  let r = 0, g = 0, b = 0;
  if (h < 60) { r = c; g = x; } else if (h < 120) { r = x; g = c; } else if (h < 180) { g = c; b = x; }
  else if (h < 240) { g = x; b = c; } else if (h < 300) { r = x; b = c; } else { r = c; b = x; }
  return [r + m, g + m, b + m];
}
function f(n) {                       // Godot writes compact floats; keep it readable and stable
  const s = n.toFixed(6).replace(/0+$/, '').replace(/\.$/, '.0');
  return s === '-0.0' ? '0.0' : s;
}
// one RGBA stop -> purple, value+alpha preserved
function stop(r, g, b, a) {
  const [h, s, v] = rgb2hsv(r, g, b);
  if (s <= 0.04) return [r, g, b, a, h, s, v, 'left (unsaturated)'];
  const nh = MASS_HUE + (h - SRC_HUE) * SQUEEZE;
  const rgb = hsv2rgb(nh, s, v);
  return [rgb[0], rgb[1], rgb[2], a, h, s, v, nh];
}
// "Color(r, g, b, a)" -> "Color(r', g', b', a)"   (alpha untouched)
function migrateColor(text) {
  const m = /^Color\(([^)]*)\)$/.exec(text);
  if (!m) throw new Error('not a Color(): ' + text);
  const p = m[1].split(',').map(x => parseFloat(x.trim()));
  const o = stop(p[0], p[1], p[2], p[3] === undefined ? 1 : p[3]);
  return { text: 'Color(' + f(o[0]) + ', ' + f(o[1]) + ', ' + f(o[2]) + ', ' + f(o[3]) + ')',
    from: text, hueIn: o[4], sat: o[5], val: o[6], hueOut: o[7] };
}
function migrateColorArray(text) {
  const m = /^PackedColorArray\(([^)]*)\)$/.exec(text);
  if (!m) throw new Error('not a PackedColorArray(): ' + text);
  const p = m[1].split(',').map(x => parseFloat(x.trim()));
  const out = [], rows = [];
  for (let i = 0; i < p.length; i += 4) {
    const o = stop(p[i], p[i + 1], p[i + 2], p[i + 3]);
    out.push(f(o[0]), f(o[1]), f(o[2]), f(o[3]));
    rows.push({ hueIn: +o[4].toFixed(1), sat: +o[5].toFixed(3), val: +o[6].toFixed(3), hueOut: o[7] === 'left (unsaturated)' ? o[7] : +o[7].toFixed(1), alpha: p[i + 3] });
  }
  return { text: 'PackedColorArray(' + out.join(', ') + ')', rows };
}

let s = fs.readFileSync(SRC, 'utf8').replace(/^\uFEFF/, '');
const log = [];
const EDITS = [
  'modulate = Color(1, 0.168627, 0, 0.752941)',                     // OuterTrail
  'modulate = Color(1, 0.827451, 0, 0.501961)',                     // InnerTrail
  'colors = PackedColorArray(1, 0.258824, 0.2, 1, 0.811499, 0.184938, 0, 0.447059, 0.59509, 2.32231e-06, 4.81308e-08, 0.482353, 0.639216, 0, 0, 0)', // BigSparks ramp
  'modulate = Color(0.972549, 0.176471, 0, 0.752941)',              // Sprite2D2
  'modulate = Color(0.901961, 0.490196, 0, 0.501961)',              // Sprite2D3
];
for (const edit of EDITS) {
  const count = s.split(edit).length - 1;
  if (count !== 1) throw new Error('expected exactly 1 occurrence, found ' + count + ': ' + edit);
  const rhs = edit.replace(/^(modulate = |colors = )/, '');
  const head = edit.slice(0, edit.length - rhs.length);
  if (rhs.startsWith('Color(')) {
    const r = migrateColor(rhs);
    s = s.replace(edit, head + r.text);
    log.push(head.trim() + ': hue ' + r.hueIn.toFixed(1) + ' (s ' + r.sat.toFixed(2) + ', v ' + r.val.toFixed(2) + ') -> ' + r.hueOut.toFixed(1));
  } else {
    const r = migrateColorArray(rhs);
    s = s.replace(edit, head + r.text);
    for (const row of r.rows) log.push('BigSparks stop: hue ' + row.hueIn + ' (s ' + row.sat + ', v ' + row.val + ', a ' + row.alpha + ') -> ' + row.hueOut);
  }
}
// the root node name is cosmetic, but name it after us so the scene is self-describing
if (s.includes('[node name="CardTrailIronclad" type="Node2D"]')) {
  s = s.replace('[node name="CardTrailIronclad" type="Node2D"]', '[node name="CardTrailYetannia" type="Node2D"]');
  log.push('root node renamed CardTrailIronclad -> CardTrailYetannia');
} else throw new Error('root node name not found');

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, s, 'utf8');
console.log('colour slots migrated:');
for (const l of log) console.log('  ' + l);
console.log('wrote ' + OUT + ' (' + Buffer.byteLength(s) + ' bytes)');
