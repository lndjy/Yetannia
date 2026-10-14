// Hue-migrates the base game's energy-counter layer textures into Yetannia's purple.
//
// WHY a hue remap and nothing else: the vanilla counter is a real multi-layer orb (an octagonal
// frame, a flame texture, a hot core, a vein skeleton), and the brief was to keep every bit of that
// structure - highlights, soft glows, the per-layer brightness ladder - and only move the hue. So
// the operation acts pointwise on colour and never on position:
//
//   * HSV (max-based value, not HSL lightness), so VALUE and SATURATION are preserved exactly and
//     the relative brightness between the five layers cannot change;
//   * hue is remapped as  h' = 260 + (h - 5) * 0.55  for warm pixels, which puts the family's mass
//     hue (the red octagon, h ~ 5) exactly on 260 deg - the mass hue measured off
//     images/ui/energy_yetannia.png, rgb(176,144,240) - and squeezes the orange/gold highlights
//     (h 16-40) into 266-279 instead of letting them run off into magenta;
//   * pixels that are not meaningfully saturated (s <= 0.04) or not warm (h outside 0-100/290-360)
//     are copied byte-for-byte, so greys, whites and the black outline are untouched;
//   * ALPHA IS NEVER TOUCHED, so the silhouette of every layer is bit-identical to the source.
//     That is also why rotating layers 2 and 3 cannot band: the recolour is a per-pixel function of
//     colour alone and therefore commutes with rotation, and the alpha (the only thing rotation
//     can smear) is unchanged.
//
// Source: the base game's ironclad_orb_layer_{1..5}.png, recovered losslessly from the .ctex
// payloads in .tools/qa/r28-counter/ctex (Godot stores them as lossless WebP at offset 56; they were
// decoded with the project's own Godot binary into C:\temp\art\counter\src).
//
//   node .tools/art/recolor-counter.js [--src DIR] [--out DIR]
'use strict';
const fs = require('fs');
const path = require('path');
const { decode, savePNG } = require('./pngio.js');

const argv = process.argv.slice(2);
function str(flag, dflt) { const i = argv.indexOf(flag); return i >= 0 ? argv[i + 1] : dflt; }
const SRC = str('--src', 'C:\\temp\\art\\counter\\src');
const OUT = str('--out', path.resolve(__dirname, '..', 'pckproject', 'Yetannia', 'images', 'ui', 'energy_counter'));
const MASS_HUE = 260;   // measured mass hue of images/ui/energy_yetannia.png
const SRC_HUE = 5;      // measured mass hue of the vanilla red octagon
const SQUEEZE = 0.55;   // 1.0 would be a plain rotation; <1 keeps the highlights inside the family

function rgb2hsv(r, g, b) {
  const R = r / 255, G = g / 255, B = b / 255;
  const mx = Math.max(R, G, B), mn = Math.min(R, G, B), d = mx - mn;
  let h = 0;
  if (d > 1e-9) {
    if (mx === R) h = ((G - B) / d) % 6;
    else if (mx === G) h = (B - R) / d + 2;
    else h = (R - G) / d + 4;
    h *= 60; if (h < 0) h += 360;
  }
  const s = mx <= 1e-9 ? 0 : d / mx;
  return [h, s, mx];
}
function hsv2rgb(h, s, v) {
  h = ((h % 360) + 360) % 360;
  const c = v * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = v - c;
  let r = 0, g = 0, b = 0;
  if (h < 60) { r = c; g = x; }
  else if (h < 120) { r = x; g = c; }
  else if (h < 180) { g = c; b = x; }
  else if (h < 240) { g = x; b = c; }
  else if (h < 300) { r = x; b = c; }
  else { r = c; b = x; }
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}

fs.mkdirSync(OUT, { recursive: true });
const report = [];
for (const n of [1, 2, 3, 4, 5]) {
  const src = path.join(SRC, 'ironclad_orb_layer_' + n + '.png');
  const img = decode(src);
  const { width: W, height: H, channels: C, pixels: P } = img;
  const out = Buffer.alloc(W * H * 4);
  let changed = 0, meanIn = 0, wIn = 0, meanOut = 0, alphaSame = true;
  for (let i = 0; i < W * H; i++) {
    const r = P[i * C], g = P[i * C + 1], b = P[i * C + 2], a = P[i * C + 3];
    const [h, s, v] = rgb2hsv(r, g, b);
    let nr = r, ng = g, nb = b;
    const warm = h < 100 || h > 290;
    if (s > 0.04 && warm) {
      const nh = MASS_HUE + (h - SRC_HUE) * SQUEEZE;
      const rgb = hsv2rgb(nh, s, v);
      nr = rgb[0]; ng = rgb[1]; nb = rgb[2];
      changed++;
      meanIn += h; wIn++;
      const [h2] = rgb2hsv(nr, ng, nb);
      meanOut += h2;
    }
    if (a !== P[i * C + 3]) alphaSame = false;
    out[i * 4] = nr; out[i * 4 + 1] = ng; out[i * 4 + 2] = nb; out[i * 4 + 3] = a;
  }
  const dst = path.join(OUT, 'yetannia_orb_layer_' + n + '.png');
  savePNG(dst, W, H, out);
  const rec = {
    layer: n, size: W + 'x' + H,
    recolouredPct: +(100 * changed / (W * H)).toFixed(1),
    meanHueIn: +(meanIn / Math.max(1, wIn)).toFixed(1),
    meanHueOut: +(meanOut / Math.max(1, wIn)).toFixed(1),
    alphaUnchanged: alphaSame,
    out: dst,
  };
  report.push(rec);
  console.log('layer_' + n + '  ' + rec.size + '  recoloured ' + rec.recolouredPct + '% of pixels' +
    '  meanHue ' + rec.meanHueIn + ' -> ' + rec.meanHueOut + '  alpha unchanged: ' + rec.alphaUnchanged);
}
// The report goes to .tools/art/stats/, NOT next to the textures: everything under images/ ends up
// inside the shipped pck.
fs.writeFileSync(path.resolve(__dirname, 'stats', 'counter-recolor-report.json'),
  JSON.stringify(report, null, 2), 'utf8');
console.log('wrote ' + report.length + ' textures -> ' + OUT);
