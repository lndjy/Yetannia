/* Yetannia icon set, v2 - painted objects in the base game's style.
 *
 * Why this file exists: the v1 generator (../icongen/glyphs.js) drew a flat rounded-square plate
 * with a white vector glyph on top. Measured against the base game's own icons that is wrong in
 * every dimension that matters. The numbers below were taken from the real thing - the 271 64x64
 * power icons sliced out of SlayTheSpire2.pck's power_atlas, and the 256x256 images/powers/*.png
 * sources (see ./measure.js and ./stats/):
 *
 *   vanilla power icon, 64x64, n=271                 mean
 *   ------------------------------------------------------
 *   alpha coverage (a>=32)                          61.1 %
 *   content bbox fill                               92.0 %
 *   IoU vs ideal rounded square                      0.70   <- NOT a plate
 *   IoU vs ideal circle                              0.70
 *   near-black pixels in the outer 2 px ink band    94.4 %
 *   ink band thickness (inward ring profile)     7-10 px at 256 = ~3 % of the icon
 *   luma bands dark<0.20 / mid / light / >0.80  26.1/30.0/30.3/13.7 %
 *   flat-white ink                                   4.5 %  <- highlights are TINTED, not white
 *   highlight chroma                                  71.7
 *   distinct 5-bit colours                             158
 *   partial-alpha pixels                     32 % of covered, 75 % within 2 px of the edge
 *
 * So: no plate. An object with its own silhouette that fills the frame, a ~3%-of-width near-black
 * outline, a lit-from-upper-left painted body with tinted highlights, surface texture, interior
 * structure that is itself outlined, and a soft (~3 px at 64) antialiased edge.
 *
 * The outer ink band and the soft edge are NOT drawn here: ./artcrop.js derives them from the
 * rendered alpha with a chamfer distance transform, because that is a far more accurate way to hit
 * "outer 2 px are near-black" and "alpha ramps over 3 px" than any stack of canvas strokes.
 *
 * Each icon returns { sil, paint }: `sil` is the one Path2D silhouette (used for the auto-fit probe
 * and for the body clip), `paint` draws the interior. Design space is 256x256, objects are built at
 * 512 (ctx pre-scaled 2x) and auto-fitted so the content bbox covers a fixed fraction of the frame.
 */
(function () {
  'use strict';

  var INK_DARK = [10, 7, 14];
  var WARM_KEY = '#ffdc9a';    // the key light is warm on every family - a base-game signature
  // NOTE: WARM_MUL is declared next to FAM so the relic group can dial the key light down.
  var DESIGN = 256;

  // ------------------------------------------------------------------ palettes
  // 7 stops: 0 = specular, 1 = lit, 2 = light, 3 = base, 4 = shade, 5 = deep, 6 = darkest
  var FAM = {
    // stop luma targets: .95 .80 .67 .50 .36 .24 .12  (vanilla body mass sits in 0.30-0.85)
    violet:    ['#f6ecff', '#d9bcff', '#b795f5', '#8f68dd', '#6a45b4', '#472b80', '#241542'],
    crimson:   ['#ffe6d2', '#ffb489', '#ef7a52', '#d4523a', '#9c2c1e', '#6b1a12', '#360c08'],
    emerald:   ['#e8ffe2', '#b0f0a8', '#74d182', '#3fa458', '#24713c', '#124a26', '#06230f'],
    steel:     ['#e6f6ff', '#a8daf7', '#66a9e0', '#3f88c6', '#1f5386', '#103357', '#06172a'],
    slate:     ['#f2f7f8', '#cad6d8', '#9dadaf', '#75868a', '#526063', '#333e40', '#181f21'],
    gold:      ['#fff8da', '#ffe07a', '#e8b32c', '#b98a14', '#8a6508', '#5a4104', '#2b1e01'],
    rose:      ['#ffe8f2', '#ffaecd', '#ec6ba3', '#c04378', '#8c2851', '#571530', '#2a0a17'],
    bronze:    ['#f3e2bd', '#dcb877', '#b08539', '#825c1f', '#5a3c11', '#372308', '#180f04'],
    // gilded variant for the upgraded relic - bronzeBright is referenced by prophets_eye_plus
    // and MUST exist here, or the icon silently falls back to violet via FAM[cat] || FAM.violet
    bronzeBright: ['#fdf0cb', '#f0d287', '#d3a02c', '#a37a14', '#775208', '#4a3104', '#231703'],
    starlight: ['#f6fbff', '#cfe8ff', '#96c4f7', '#5f8ede', '#3d63b4', '#233c80', '#0e1740'],
    orb:       ['#f8f0ff', '#dcc0ff', '#b795f5', '#8a5fd8', '#6138a8', '#3d2170', '#1c0f38'],
  };


  // Extra materials for the relic group. Vanilla relics are not one metal: they mix leather,
  // iron, ivory, amber and glass, which is where their hue spread and their muted saturation
  // (0.34 vs the powers' 0.42) come from.
  var MAT = {
    leather: ['#f2e0c6', '#d9b183', '#a9764a', '#7d5230', '#54341d', '#331e0f', '#180d06'],
    iron:    ['#eef3f7', '#c2ccd5', '#8a97a3', '#5c6975', '#3c4650', '#242b32', '#0f1317'],
    ivory:   ['#f4ecdb', '#ddd0b1', '#c0ac83', '#9a855e', '#6f5c3e', '#463824', '#201a10'],
    amber:   ['#f2e2b6', '#e6bf6d', '#c88c1c', '#99630c', '#6a4206', '#402702', '#1c1101'],
    glassG:  ['#eafff2', '#a8f0cf', '#4fc79a', '#1f8f6a', '#12614a', '#0a3a2c', '#041a13'],
    glassR:  ['#ffe9ea', '#ffb0b4', '#e8626a', '#b0323c', '#7a1e26', '#4a1016', '#220609'],
  };
  var WARM_MUL = 1;   // relics take a dimmer, cooler key light than powers (0.30 for relics)

  // ------------------------------------------------------------------ accent hues
  // Reviewer defect #1: every icon was one hue family end to end, which reads as a UI widget no
  // matter how much value contrast it has. Each family therefore gets exactly ONE deliberate
  // contrasting accent hue - warm amber for the cool families, cool cyan for the warm ones - and
  // that accent is given real geometry (a glowing tally groove, a gold rim, a brass escutcheon, a
  // cold crack light), not just a tint over the body. The family itself never changes.
  var ACC = {
    violet: '#ffc44a', steel: '#ffc44a', slate: '#ffb43c', emerald: '#ffd166',
    starlight: '#ffbe4d', rose: '#57c8ff', gold: '#4fc8ff',
    crimson: '#54c8ff', bronze: '#5cc6f0', bronzeBright: '#5cc6f0', orb: '#ffc44a',
  };
  var _accCache = {};
  // accent material: same 7-stop structure as FAM so accent parts can go straight into
  // raised()/recessed()/glowShape() and receive identical lighting
  function accRamp(cat) {
    var c = ACC[cat] || '#ffc44a';
    if (_accCache[c]) return _accCache[c];
    var r = [tint(c, 0.80), tint(c, 0.46), c, shade(c, 0.26), shade(c, 0.48), shade(c, 0.68), shade(c, 0.86)];
    _accCache[c] = r;
    return r;
  }
  function accHue(cat) { return ACC[cat] || '#ffc44a'; }
  // the icon currently being built, so a build() closure can reach its own accent material
  var CURCAT = 'violet';
  function AR() { return accRamp(CURCAT); }

  function hex(c) { return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]; }
  function rgba(c, a) { var v = typeof c === 'string' ? hex(c) : c; return 'rgba(' + v[0] + ',' + v[1] + ',' + v[2] + ',' + a + ')'; }
  function mixc(a, b, t) {
    var x = typeof a === 'string' ? hex(a) : a, y = typeof b === 'string' ? hex(b) : b;
    return '#' + [0, 1, 2].map(function (i) { return ('0' + Math.round(x[i] + (y[i] - x[i]) * t).toString(16)).slice(-2); }).join('');
  }
  function shade(c, t) { return mixc(c, '#000000', t); }
  function tint(c, t) { return mixc(c, '#ffffff', t); }
  function inkOf(ramp) { return mixc(ramp[6], '#000000', 0.40); }
  // interior detail ink: near-black, because vanilla reserves black for internal features (the
  // demon's eyes and mouth, the juggernaut's faceplate) rather than a tinted family shade
  function inkInner(ramp) { return mixc(ramp[6], '#000000', 0.45); }

  // ------------------------------------------------------------------ prng
  function mulberry(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hashName(s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  // ------------------------------------------------------------------ path helpers
  function Pth() { return new Path2D(); }
  function rr(x, y, w, h, r) {
    r = Math.max(0, Math.min(r, Math.min(w, h) / 2));
    var p = Pth();
    p.moveTo(x + r, y);
    p.lineTo(x + w - r, y); p.arcTo(x + w, y, x + w, y + r, r);
    p.lineTo(x + w, y + h - r); p.arcTo(x + w, y + h, x + w - r, y + h, r);
    p.lineTo(x + r, y + h); p.arcTo(x, y + h, x, y + h - r, r);
    p.lineTo(x, y + r); p.arcTo(x, y, x + r, y, r);
    p.closePath(); return p;
  }
  function circ(cx, cy, r) { var p = Pth(); p.arc(cx, cy, r, 0, 6.283185307, false); p.closePath(); return p; }
  function ell(cx, cy, rx, ry, rot) { var p = Pth(); p.ellipse(cx, cy, rx, ry, rot || 0, 0, 6.283185307, false); p.closePath(); return p; }
  function poly(pts) {
    var p = Pth(); p.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) p.lineTo(pts[i][0], pts[i][1]);
    p.closePath(); return p;
  }
  // Every path handed to U() while a silhouette is being built is also recorded here, so the
  // renderer can fill the silhouette part by part instead of relying on a nonzero Path2D clip
  // (which cancels subpaths that wind against each other and punches holes in the union).
  var PARTS = [];
  function U() {
    var p = Pth();
    for (var i = 0; i < arguments.length; i++) { p.addPath(arguments[i]); PARTS.push(arguments[i]); }
    return p;
  }
  function ring(cx, cy, ro, ri) {
    var p = Pth();
    p.arc(cx, cy, ro, 0, 6.283185307, false);
    p.moveTo(cx + ri, cy); p.arc(cx, cy, ri, 0, 6.283185307, true);
    p.closePath(); return p;
  }
  function star(cx, cy, ro, ri, n, rot) {
    var pts = [];
    for (var i = 0; i < n * 2; i++) {
      var a = (rot || 0) + i * Math.PI / n;
      var r = (i % 2 === 0) ? ro : ri;
      pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
    return poly(pts);
  }
  function almond(cx, cy, hw, hh) {
    // traced lower-lobe first so the winding matches poly()/circ()/rr() - see polyW()
    var p = Pth();
    p.moveTo(cx - hw, cy);
    p.quadraticCurveTo(cx, cy + 2 * hh, cx + hw, cy);
    p.quadraticCurveTo(cx, cy - 2 * hh, cx - hw, cy);
    p.closePath(); return p;
  }
  function sparkle(cx, cy, ro, ri, rot) { return star(cx, cy, ro, ri, 4, rot === undefined ? -Math.PI / 2 : rot); }
  function ray(bx, by, tx, ty, w0, w1) {
    var dx = tx - bx, dy = ty - by, L = Math.hypot(dx, dy) || 1;
    var px = -dy / L, py = dx / L;
    return poly([[bx + px * w0, by + py * w0], [tx + px * w1, ty + py * w1], [tx - px * w1, ty - py * w1], [bx - px * w0, by - py * w0]]);
  }
  function plusPath(cx, cy, arm, th) {
    return poly([
      [cx - th, cy - arm], [cx + th, cy - arm], [cx + th, cy - th], [cx + arm, cy - th],
      [cx + arm, cy + th], [cx + th, cy + th], [cx + th, cy + arm], [cx - th, cy + arm],
      [cx - th, cy + th], [cx - arm, cy + th], [cx - arm, cy - th], [cx - th, cy - th]]);
  }
  function line(pts) {
    var p = Pth(); p.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) p.lineTo(pts[i][0], pts[i][1]);
    return p;
  }
  function arcPath(cx, cy, r, a0, a1) { var p = Pth(); p.arc(cx, cy, r, a0, a1, false); return p; }
  // uniform inward scale about a pivot - a cheap, stable "inset" for blobby silhouettes
  function inset(path, px, py, s) {
    var m = new DOMMatrix();
    m.translateSelf(px, py); m.scaleSelf(s, s); m.translateSelf(-px, -py);
    var p = Pth(); p.addPath(path, m); return p;
  }
  // poly() with one guaranteed winding direction. The nonzero fill rule cancels overlapping
  // subpaths that wind against each other, and that silently punched transparent holes through
  // every union silhouette built from a band plus a polygon (a black sash across starscar_form, a
  // hole through granted_turn's top plate). Every constructed outline now goes through this.
  function polyW(pts) {
    var s = 0;
    for (var i = 0; i < pts.length; i++) {
      var a = pts[i], b = pts[(i + 1) % pts.length];
      s += a[0] * b[1] - b[0] * a[1];
    }
    return poly(s < 0 ? pts.slice().reverse() : pts);
  }
  // A closed band along a polyline. Open paths (line/arcPath) only contribute their implicit
  // closing chord to a filled silhouette, which is why a bar or a shackle built that way leaks;
  // this builds the real outline so a forged bar/chain/ribbon can be part of the silhouette.
  function bandPath(pts, w) {
    var L = [], R = [];
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      var a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
      var dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || 1;
      L.push([p[0] - dy / d * w, p[1] + dx / d * w]);
      R.push([p[0] + dy / d * w, p[1] - dx / d * w]);
    }
    return polyW(L.concat(R.reverse()));
  }
  // Tapered two-lobe organic shape pointing along `ang`: petal, leaf, feather-barb, flame tongue.
  // The vanilla vocabulary is full of these and they read as hand-drawn where an ellipse does not.
  function arrowHead(x0, y0, x1, y1, len, hw) {
    var dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy) || 1;
    var ux = dx / L, uy = dy / L, px = -uy, py = ux;
    return poly([[x1 + ux * len, y1 + uy * len],
      [x1 + px * hw, y1 + py * hw], [x1 - px * hw, y1 - py * hw]]);
  }
  function petal(cx, cy, ang, len, hw, bend) {
    bend = bend || 0;
    var dx = Math.cos(ang), dy = Math.sin(ang), px = -dy, py = dx;
    var mx = cx + dx * len * 0.42, my = cy + dy * len * 0.42;
    var tx = cx + dx * len, ty = cy + dy * len;
    var nx = cx + px * bend * len, ny = cy + py * bend * len;
    var p = Pth();
    p.moveTo(cx, cy);
    p.quadraticCurveTo(mx + px * hw + nx, my + py * hw + ny, tx + nx * 1.4, ty + ny * 1.4);
    p.quadraticCurveTo(mx - px * hw + nx, my - py * hw + ny, cx, cy);
    p.closePath(); return p;
  }
  // A wobbled closed organic ring: a hand-cut disc/slab edge. `amp` in design units, k = lobes.
  function wobble(cx, cy, r, k, amp, seed, phase) {
    var pts = [], n = 48, rnd = mulberry(seed >>> 0);
    var ph = [rnd(), rnd(), rnd(), rnd()];
    for (var i = 0; i < n; i++) {
      var a = i / n * 6.283185307 + (phase || 0);
      var d = amp * (0.55 * Math.sin(k * a + ph[0] * 6.28) + 0.30 * Math.sin((k + 2) * a + ph[1] * 6.28)
        + 0.15 * Math.sin((k + 5) * a + ph[2] * 6.28));
      var q = r + d;
      pts.push([cx + q * Math.cos(a), cy + q * Math.sin(a)]);
    }
    return poly(pts);
  }
  // A torn / deckled edge for parchment: a straight run of small random bites.
  function deckle(x0, y0, x1, y1, amp, seed, steps) {
    var pts = [], n = steps || 9, rnd = mulberry(seed >>> 0);
    for (var i = 0; i <= n; i++) {
      var t = i / n;
      var x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t;
      if (i > 0 && i < n) {
        var dx = x1 - x0, dy = y1 - y0, d = Math.hypot(dx, dy) || 1;
        var o = (rnd() - 0.5) * 2 * amp;
        x += -dy / d * o; y += dx / d * o;
      }
      pts.push([x, y]);
    }
    return pts;
  }

  // ------------------------------------------------------------------ painting
  var TEXTURE = null;

  function makeTexture() {
    var s = 192, cv = document.createElement('canvas');
    cv.width = s; cv.height = s;
    var c = cv.getContext('2d');
    var id = c.createImageData(s, s);
    var rnd = mulberry(0x51ed2701);
    function grid(n) { var g = new Float32Array(n * n); for (var i = 0; i < n * n; i++) g[i] = rnd(); return g; }
    function sample(g, n, u, v) {
      var x = u * n, y = v * n;
      var x0 = Math.floor(x) % n, y0 = Math.floor(y) % n;
      var x1 = (x0 + 1) % n, y1 = (y0 + 1) % n;
      var fx = x - Math.floor(x), fy = y - Math.floor(y);
      fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
      var a = g[y0 * n + x0], b = g[y0 * n + x1], cc = g[y1 * n + x0], d = g[y1 * n + x1];
      return (a * (1 - fx) + b * fx) * (1 - fy) + (cc * (1 - fx) + d * fx) * fy;
    }
    var g3 = grid(3), g7 = grid(7), g19 = grid(19), g53 = grid(53);
    for (var y = 0; y < s; y++) {
      for (var x = 0; x < s; x++) {
        var u = x / s, v = y / s;
        var n = sample(g3, 3, u, v) * 0.40 + sample(g7, 7, u, v) * 0.28
          + sample(g19, 19, u, v) * 0.21 + sample(g53, 53, u, v) * 0.11;
        var k = Math.max(0, Math.min(255, Math.round(128 + (n - 0.5) * 250)));
        var i = (y * s + x) * 4;
        id.data[i] = id.data[i + 1] = id.data[i + 2] = k; id.data[i + 3] = 255;
      }
    }
    c.putImageData(id, 0, 0);
    return cv;
  }

  function axisGrad(ctx, x0, y0, x1, y1, stops) {
    var g = ctx.createLinearGradient(x0, y0, x1, y1);
    for (var i = 0; i < stops.length; i++) g.addColorStop(stops[i][0], stops[i][1]);
    return g;
  }
  function pool(ctx, x, y, r, col, a0, comp) {
    var g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(col, a0));
    g.addColorStop(0.45, rgba(col, a0 * 0.55));
    g.addColorStop(1, rgba(col, 0));
    ctx.save();
    if (comp) ctx.globalCompositeOperation = comp;
    ctx.fillStyle = g; ctx.fillRect(0, 0, DESIGN, DESIGN);
    ctx.restore();
  }
  function texture(ctx, seed, amp) {
    if (!TEXTURE) TEXTURE = makeTexture();
    var rnd = mulberry(seed);
    ctx.save();
    ctx.globalCompositeOperation = 'overlay';
    ctx.globalAlpha = amp;
    var ox = Math.floor(rnd() * 60), oy = Math.floor(rnd() * 60);
    for (var y = -192 + oy; y < DESIGN + 192; y += 192) {
      for (var x = -192 + ox; x < DESIGN + 192; x += 192) ctx.drawImage(TEXTURE, x, y);
    }
    ctx.restore();
    // brush scratches along the light axis
    ctx.save();
    ctx.globalAlpha = 0.05;
    ctx.lineCap = 'round';
    for (var i = 0; i < 16; i++) {
      var sx = rnd() * DESIGN, sy = rnd() * DESIGN;
      var len = 6 + rnd() * 36, ang = -2.15 + (rnd() - 0.5) * 1.1;
      ctx.strokeStyle = rnd() < 0.5 ? 'rgba(255,255,255,0.55)' : 'rgba(0,0,0,0.5)';
      ctx.lineWidth = 0.7 + rnd() * 2.0;
      ctx.beginPath(); ctx.moveTo(sx, sy);
      ctx.lineTo(sx + Math.cos(ang) * len, sy + Math.sin(ang) * len); ctx.stroke();
    }
    ctx.restore();
    // grime specks
    ctx.save();
    ctx.globalAlpha = 0.07;
    for (var k = 0; k < 26; k++) {
      ctx.fillStyle = rnd() < 0.55 ? 'rgba(0,0,0,0.65)' : 'rgba(255,255,255,0.55)';
      ctx.beginPath(); ctx.arc(rnd() * DESIGN, rnd() * DESIGN, 0.5 + rnd() * 1.6, 0, 6.2832); ctx.fill();
    }
    ctx.restore();
  }

  // The painted body for a silhouette. Caller must have clipped to the silhouette already.
  //
  // FLAT, on purpose. Pixel-probing the vanilla 256 px sources (see the profile in
  // ICON-STYLE-REPORT.md) shows demon_form_power is one solid (255,77,58) with pure black used only
  // for the internal features, juggernaut_power is flat red + flat yellow horns, dexterity_power is
  // a flat green with a single hard-edged two-tone split, and only echo_form_power carries a real
  // gradient plus one white highlight. So: flat fill, at most one hard-edged two-tone split, and an
  // optional single highlight. No radial light pools, no metal sheen, no ambient accent wash.
  function body(ctx, ramp, seed, opt) {
    opt = opt || {};
    ctx.save();
    ctx.fillStyle = opt.base === undefined ? ramp[2] : opt.base;
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    if (opt.split) {
      // hard-edged lit region on the upper-left: vanilla's dexterity light/shade split
      ctx.beginPath();
      ctx.moveTo(0, 0); ctx.lineTo(DESIGN, 0); ctx.lineTo(0, DESIGN);
      ctx.closePath();
      ctx.fillStyle = rgba(ramp[1], opt.split);
      ctx.fill();
    }
    ctx.restore();
  }

  // A raised part: one flat colour plus the ink outline. `opt.tone` picks the ramp stop (2 = the
  // family body, 1 = a lit frame, 3/4 = a darker field); `opt.two` adds the hard two-tone split.
  function raised(ctx, path, ramp, inkW, seed, opt) {
    opt = opt || {};
    ctx.save();
    ctx.clip(path);
    ctx.fillStyle = ramp[opt.tone === undefined ? 2 : opt.tone];
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    if (opt.two) {
      // hard 45-degree light/shade split (vanilla dexterity has exactly one of these per icon)
      ctx.beginPath();
      ctx.moveTo(-20, -20); ctx.lineTo(opt.two + 20, -20); ctx.lineTo(-20, opt.two + 20);
      ctx.closePath();
      ctx.fillStyle = rgba(ramp[1], opt.twoA === undefined ? 0.55 : opt.twoA);
      ctx.fill();
    }
    ctx.restore();
    ctx.save();
    ctx.strokeStyle = inkInner(ramp); ctx.lineWidth = inkW; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.stroke(path);
    ctx.restore();
  }

  // raised bar: same idea for open polylines
  function raisedLine(ctx, path, w, ramp, inkW, seed, opt) {
    opt = opt || {};
    ctx.save();
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.strokeStyle = inkOf(ramp); ctx.lineWidth = w + inkW * 2; ctx.stroke(path);
    ctx.strokeStyle = ramp[opt.tone === undefined ? 3 : opt.tone]; ctx.lineWidth = w; ctx.stroke(path);
    ctx.restore();
  }

  // A carved hollow: one flat dark value, pure-black interior line, ink outline. Vanilla reserves
  // near-black for exactly this - eyes, faceplates, carved grooves.
  function recessed(ctx, path, ramp, inkW, seed, opt) {
    opt = opt || {};
    ctx.save();
    ctx.clip(path);
    ctx.fillStyle = opt.deep ? mixc(ramp[6], '#000000', 0.5) : ramp[5];
    ctx.fillRect(0, 0, DESIGN, DESIGN);
    ctx.restore();
    ctx.save();
    ctx.strokeStyle = inkOf(ramp); ctx.lineWidth = inkW; ctx.lineJoin = 'round';
    ctx.stroke(path);
    ctx.restore();
    ctx.save();
    ctx.clip(path);
    ctx.strokeStyle = 'rgba(0,0,0,0.60)';
    ctx.lineWidth = inkW * 0.9; ctx.lineJoin = 'round';
    ctx.translate(inkW * 0.8, inkW * 0.8);
    ctx.stroke(path);
    ctx.restore();
  }

  function glowShape(ctx, path, col, core, blur) {
    ctx.save();
    ctx.shadowColor = rgba(col, 0.95);
    ctx.shadowBlur = blur;
    ctx.fillStyle = rgba(col, 1);
    ctx.fill(path); ctx.fill(path);
    ctx.restore();
    if (core) { ctx.save(); ctx.fillStyle = core; ctx.fill(path); ctx.restore(); }
  }

  // A carved groove along a path: dark cut with a lit lower-right lip, so interior detail reads as
  // cut into the material rather than drawn on top of it.
  function carve(ctx, path, ramp, w, a) {
    ctx.save();
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.strokeStyle = rgba(mixc(ramp[5], '#000000', 0.40), a === undefined ? 0.85 : a);
    ctx.lineWidth = w; ctx.stroke(path);
    ctx.save();
    ctx.translate(w * 0.28, w * 0.34);
    ctx.strokeStyle = rgba(ramp[0], 0.26); ctx.lineWidth = w * 0.34; ctx.stroke(path);
    ctx.restore();
    ctx.restore();
  }

  // A stroke of accent light: the accent material drawn as a glowing carved line.
  function glowLine(ctx, ar, path, w, blur) {
    ctx.save();
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.shadowColor = rgba(ar[1], 0.9);
    ctx.shadowBlur = blur === undefined ? 9 : blur;
    ctx.strokeStyle = ar[3]; ctx.lineWidth = w; ctx.stroke(path);
    ctx.strokeStyle = ar[1]; ctx.lineWidth = w * 0.45; ctx.stroke(path);
    ctx.restore();
  }

  // Sink an already-painted mass toward the family's shade stops - as a FLAT, hard-edged region over
  // the lower-right (the vanilla dexterity two-tone split), not as a gradient.
  function deepen(ctx, ramp, t, x0, y0) {
    ctx.save();
    ctx.globalAlpha = t;
    ctx.fillStyle = ramp[4];
    ctx.beginPath();
    ctx.moveTo(x0 === undefined ? 210 : x0, 0);
    ctx.lineTo(DESIGN, 0); ctx.lineTo(DESIGN, DESIGN); ctx.lineTo(0, DESIGN);
    ctx.lineTo(0, y0 === undefined ? 210 : y0);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  // ------------------------------------------------------------------ the one optional highlight
  // RETRACTED DIRECTION, recorded here so it is not re-introduced: an earlier version of this pass
  // put a warm key bloom, an accent-hue wash and a deep-shadow pool on EVERY icon. Pixel-probing
  // the vanilla 256 px sources shows that is wrong - most of them are flat fills (demon_form is one
  // solid red with black only in the eyes and mouth), and only echo_form carries a highlight. What
  // survives is per-icon and optional: a single flat pale ellipse on the lit side.

  // Per-icon OPTIONAL single highlight, in design units: { hi: [cx, cy, rx, ry, rot] }. Only the
  // icons with a big simple mass that vanilla would have given the echo_form treatment get one.
  var ACCP = {
    prophet_tally:    { hi: [76, 132, 11, 20, -0.55], hiA: 0.5 },
    nirvana:          { hi: [96, 104, 16, 9, -0.8], hiA: 0.5 },
    pure_love_form:   { hi: [90, 98, 19, 11, -0.72] },
    scry_agility:     { hi: [94, 84, 21, 11, -0.95] },
    granted_turn:     { hi: [102, 84, 18, 10, -0.85] },
    purify:           { hi: [102, 112, 16, 25, -0.5] },
    starscar_form:    { hi: [96, 90, 19, 10, -0.8] },
    temp_agility:     { hi: [100, 96, 15, 8, -0.95] },
    energy_yetannia:  { hi: [96, 92, 30, 17, -0.6] },
    // the 24 px inline glyph: one highlight ellipse, 76x40 design units = 7x4 px at 24, the same
    // single-highlight treatment the base game gives echo_form
    energy_inline:    { hi: [92, 84, 38, 20, -0.7], hiA: 0.55 },
  };

  function finish(ctx, ramp, name, cat, group) {
    var p = ACCP[name] || {};
    if (!p.hi) return;
    // At most ONE highlight per icon, and only where vanilla would put one (echo_form's single pale
    // ellipse on the lit side). No accent wash, no specular bloom, no deep-shadow pool: the earlier
    // version of this pass was retracted after pixel-probing the vanilla sources.
    ctx.save();
    ctx.fillStyle = rgba(p.hiCol === undefined ? tint(ramp[1], 0.55) : p.hiCol,
      p.hiA === undefined ? 0.85 : p.hiA);
    ctx.beginPath();
    ctx.ellipse(p.hi[0], p.hi[1], p.hi[2], p.hi[3], p.hi[4] === undefined ? -0.7 : p.hi[4], 0, 6.2832);
    ctx.fill();
    ctx.restore();
  }

  // ------------------------------------------------------------------ icons
  var ICONS = [];
  // cov = the alpha-coverage fraction this icon is auto-fitted to (vanilla: mean 61.1 %,
  // p10 46.5 %, p90 75.3 %, n=271). bbox stays capped at 98 % of the frame.
  function add(name, group, cat, cov, build) {
    ICONS.push({ name: name, group: group, cat: cat, cov: cov, build: build });
  }

  // ============================ POWERS =====================================

  add('prophet_tally', 'power', 'violet', 0.66, function (ctx, r, rnd, iw) {
    // 先知累积 "accumulated prophecy": a chipped standing stone. Its face is cut with tally
    // strokes that still hold warm amber light, and the prophet's eye is carved above them.
    // Deliberately no panel, no capsule row and no readout digits - the previous version read as a
    // clicker counter, which is exactly what the reviewer rejected.
    var ak = AR();
    // arch-topped stele standing on a wider, chipped plinth: architectural, so the stone reads as
    // a monument and not as a robbed figure. One hand-cut outline, no panel, no capsule row.
    var sil = Pth();
    sil.moveTo(16, 202);
    sil.lineTo(18, 230);
    sil.quadraticCurveTo(56, 246, 126, 243);
    sil.quadraticCurveTo(200, 246, 238, 230);
    sil.lineTo(240, 202);
    sil.lineTo(204, 194);
    sil.lineTo(208, 140);
    sil.quadraticCurveTo(219, 124, 204, 110);
    sil.lineTo(203, 88);
    sil.bezierCurveTo(199, 40, 168, 14, 128, 14);
    sil.bezierCurveTo(94, 14, 70, 30, 60, 52);
    sil.lineTo(52, 44);
    sil.lineTo(46, 92);
    sil.lineTo(48, 110);
    sil.quadraticCurveTo(35, 124, 46, 140);
    sil.lineTo(52, 194);
    sil.closePath();
    // the chiselled face plane of the shaft: raised, so the key light breaks across a real bevel
    var face = Pth();
    face.moveTo(68, 192);
    face.lineTo(70, 112);
    face.bezierCurveTo(72, 62, 98, 38, 128, 38);
    face.bezierCurveTo(158, 38, 184, 62, 186, 112);
    face.lineTo(188, 192);
    face.closePath();
    // tally cuts: four cuts closed by the slash on the face, two more half-cut into the plinth, so
    // the stone reads as accumulation still in progress rather than as a finished number
    function cut(x0, y0, x1, y1, hw) {
      return ray(x0, y0 - (y0 - y1) * 0.12, x1, y1, hw * 1.16, hw);
    }
    var cuts = [], plinth = [];
    for (var i = 0; i < 4; i++) cuts.push(cut(92 + i * 25, 186, 96 + i * 25 - i, 130, 7.2));
    var slash = ray(82, 180, 164, 136, 6.2, 5.0);
    plinth.push(cut(78, 232, 80, 208, 5.6));
    plinth.push(cut(96, 233, 98, 209, 5.2));
    return { sil: sil, paint: function () {
      body(ctx, r, 0, { grain: 0.11 });
      raised(ctx, sil, r, iw * 0.9, 40, { two: 116 });
      deepen(ctx, r, 0.52);
      raised(ctx, face, r, iw * 0.75, 41);
      carve(ctx, face, r, iw * 1.15, 0.55);
      carve(ctx, arcPath(128, 118, 74, Math.PI * 1.22, Math.PI * 1.78), r, iw * 0.9, 0.4);
      // the prophet's eye, carved into the crown of the face and lit from within
      recessed(ctx, almond(128, 82, 50, 29), r, iw * 0.5, 44);
      glowShape(ctx, almond(128, 82, 42, 22), ak[2], null, 13);
      recessed(ctx, circ(128, 82, 16), r, iw * 0.4, 45);
      glowShape(ctx, circ(128, 82, 12), ak[0], null, 9);
      glowShape(ctx, circ(122, 76, 5.0), '#ffffff', null, 5);
      // carved tally strokes: dark cut, amber light pooled in the groove, bright core along it
      for (var k = 0; k < cuts.length; k++) {
        recessed(ctx, cuts[k], r, iw * 0.34, 50 + k);
        glowShape(ctx, cuts[k], ak[4], null, 9);
        glowShape(ctx, cut(93 + k * 25, 181, 97 + k * 25 - k, 136, 2.9), ak[1], null, 5);
      }
      recessed(ctx, slash, r, iw * 0.34, 70);
      glowShape(ctx, slash, ak[3], null, 9);
      glowShape(ctx, ray(86, 176, 160, 139, 2.5, 2.1), ak[0], null, 5);
      for (var q = 0; q < plinth.length; q++) {
        recessed(ctx, plinth[q], r, iw * 0.28, 60 + q);
        glowShape(ctx, plinth[q], ak[4], null, 7);
        glowShape(ctx, cut(79 + q * 18, 228, 81 + q * 18, 212, 2.2), ak[2], null, 4);
      }
      // chipped details: hairline cracks running in from the flank chips
      carve(ctx, line([[206, 120], [178, 132], [170, 152]]), r, iw * 0.5, 0.45);
      carve(ctx, line([[48, 150], [70, 164], [76, 186]]), r, iw * 0.45, 0.4);
    } };
  });

  add('foresight', 'power', 'violet', 0.64, function (ctx, r, rnd, iw) {
    // a seeing eye inside a ring of prophecy rays: flat violet, black in the pupil, one pale
    // sclera. The eye is the point of the icon, so it is drawn as an eye and not as a black hole.
    var rays = Pth();
    for (var i = 0; i < 8; i++) {
      var a = -Math.PI * 0.94 + i * (Math.PI * 1.88 / 7);
      rays.addPath(ray(128 + Math.cos(a) * 50, 128 + Math.sin(a) * 50,
        128 + Math.cos(a) * 132, 128 + Math.sin(a) * 132, 32, 25));
    }
    // NOTE the silhouette is the FULL disc, not ring(128,128,100,56): an annulus path puts a real
    // hole in the silhouette mask (and in a nonzero Path2D clip), which erased the eye that is
    // supposed to sit inside it. That is why this icon's eye never read.
    var sil = U(rays, circ(128, 128, 100));
    return { sil: sil, paint: function () {
      body(ctx, r, 1);
      raised(ctx, rays, r, iw * 0.55, 60, { tone: 3 });
      raised(ctx, ring(128, 128, 100, 56), r, iw * 0.7, 61, { two: 118 });
      recessed(ctx, circ(128, 128, 56), r, iw * 0.5, 62);
      glowShape(ctx, almond(128, 128, 47, 25), r[1], null, 0);
      glowShape(ctx, circ(128, 128, 15), mixc(r[6], '#000000', 0.55), null, 0);
      glowShape(ctx, circ(121, 121, 5.4), '#ffffff', null, 0);
      carve(ctx, arcPath(128, 128, 62, Math.PI * 1.06, Math.PI * 1.94), r, iw * 0.4, 0.45);
    } };
  });

  add('nirvana', 'power', 'steel', 0.7, function (ctx, r, rnd, iw) {
    // a warded shield: heavy plate, a gold-inlaid rim, and a lotus-eye boss set in a gold bezel.
    // Reviewer notes acted on: the four stray rim studs and the two faint hollow stars were
    // unmotivated marks, so they are gone - the rim is one continuous gold inlay and every other
    // shape belongs to the lotus collar around the eye. The eye itself now carries the warm accent.
    var ak = AR();
    var sh = Pth();
    sh.moveTo(128, 12);
    sh.bezierCurveTo(188, 30, 226, 36, 244, 38);
    sh.lineTo(244, 116);
    sh.bezierCurveTo(244, 190, 192, 232, 128, 250);
    sh.bezierCurveTo(64, 232, 12, 190, 12, 116);
    sh.lineTo(12, 38);
    sh.bezierCurveTo(30, 36, 68, 30, 128, 12);
    sh.closePath();
    var field = inset(sh, 128, 132, 0.80);
    return { sil: sh, paint: function () {
      body(ctx, r, 2);
      raised(ctx, sh, r, iw * 0.7, 70, { two: 118 });
      recessed(ctx, field, r, iw * 0.5, 71);
      raisedLine(ctx, field, 12, ak, iw * 0.32, 72);
      raised(ctx, ring(128, 130, 44, 32), ak, iw * 0.5, 90);
      carve(ctx, ring(128, 130, 44, 32), r, iw * 0.28, 0.45);
      recessed(ctx, circ(128, 130, 32), r, iw * 0.45, 91);
      glowShape(ctx, almond(128, 130, 29, 17), r[1], null, 0);
      glowShape(ctx, circ(128, 130, 11), mixc(r[6], '#000000', 0.55), null, 0);
      glowShape(ctx, circ(122, 124, 4.2), '#ffffff', null, 0);
    } };
  });

  add('prophetic_study', 'power', 'violet', 0.66, function (ctx, r, rnd, iw) {
    // an open tome, an eye of prophecy above it
    var book = Pth();
    book.moveTo(128, 118);
    book.lineTo(246, 92); book.quadraticCurveTo(258, 172, 244, 238);
    book.lineTo(128, 250); book.closePath();
    book.moveTo(128, 118);
    book.lineTo(10, 92); book.quadraticCurveTo(-2, 172, 12, 238);
    book.lineTo(128, 250); book.closePath();
    var eye = almond(128, 50, 66, 34);
    return { sil: U(book, eye), paint: function () {
      body(ctx, r, 3);
      raised(ctx, book, r, iw * 0.75, 100);
      recessed(ctx, rr(20, 112, 96, 108, 8), r, iw * 0.45, 101);
      recessed(ctx, rr(140, 112, 96, 108, 8), r, iw * 0.45, 102);
      for (var i = 0; i < 4; i++) {
        raised(ctx, rr(28, 124 + i * 24, 80, 9, 4), r, iw * 0.26, 110 + i);
        raised(ctx, rr(148, 124 + i * 24, 80, 9, 4), r, iw * 0.26, 120 + i);
      }
      raised(ctx, rr(120, 100, 16, 152, 6), r, iw * 0.4, 130);
      glowShape(ctx, almond(128, 50, 58, 30), r[1], null, 14);
      glowShape(ctx, circ(128, 50, 19), r[3], rgba(r[6], 0.85), 8);
      glowShape(ctx, circ(120, 42, 7), '#ffffff', null, 5);
      raised(ctx, sparkle(34, 44, 20, 7, -Math.PI / 2), r, iw * 0.3, 131);
      raised(ctx, sparkle(222, 40, 16, 5.5, -Math.PI / 2), r, iw * 0.28, 132);
    } };
  });

  add('cycle_of_prophecy', 'power', 'violet', 0.62, function (ctx, r, rnd, iw) {
    // an ouroboros arrow: a heavy broken ring with an arrowhead, an eye at the hub
    var a0 = -Math.PI * 0.78, a1 = Math.PI * 1.02;
    var ar = Pth();
    ar.arc(128, 128, 104, a0, a1, false);
    ar.arc(128, 128, 54, a1, a0, true);
    ar.closePath();
    var tipX = 128 + Math.cos(a1) * 79, tipY = 128 + Math.sin(a1) * 79;
    var tx = -Math.sin(a1), ty = Math.cos(a1), px = -ty, py = tx;
    var head = poly([
      [tipX + px * 46, tipY + py * 46],
      [tipX + tx * 54, tipY + ty * 54],
      [tipX - px * 46, tipY - py * 46]]);
    return { sil: U(ar, head, circ(128, 128, 54)), paint: function () {
      body(ctx, r, 4);
      raised(ctx, U(ar, head), r, iw * 0.7, 140);
      for (var i = 0; i < 5; i++) {
        var a = a0 + (a1 - a0) * (0.10 + i * 0.175);
        recessed(ctx, star(128 + Math.cos(a) * 79, 128 + Math.sin(a) * 79, 12, 4, 4, a), r, iw * 0.22, 150 + i);
      }
      recessed(ctx, circ(128, 128, 54), r, iw * 0.45, 160);
      glowShape(ctx, almond(128, 128, 48, 26), r[1], null, 12);
      glowShape(ctx, circ(128, 128, 17), r[3], rgba(r[6], 0.85), 8);
      glowShape(ctx, circ(120, 120, 6), '#ffffff', null, 5);
    } };
  });

  add('pure_love_form', 'power', 'rose', 0.7, function (ctx, r, rnd, iw) {
    // a heavy enamelled heart with a filigree rose window
    var h = Pth();
    h.moveTo(128, 250);
    h.bezierCurveTo(26, 190, 2, 116, 36, 68);
    h.bezierCurveTo(70, 20, 122, 30, 128, 80);
    h.bezierCurveTo(134, 30, 186, 20, 220, 68);
    h.bezierCurveTo(254, 116, 230, 190, 128, 250);
    h.closePath();
    return { sil: h, paint: function () {
      body(ctx, r, 5);
      raised(ctx, h, r, iw * 0.8, 170, { two: 112 });
      recessed(ctx, almond(128, 146, 64, 42), r, iw * 0.5, 171);
      raised(ctx, ring(128, 146, 42, 30), r, iw * 0.4, 172);
      for (var i = 0; i < 6; i++) {
        var a = i * Math.PI / 3;
        raised(ctx, star(128 + Math.cos(a) * 54, 146 + Math.sin(a) * 36, 15, 5, 4, a), r, iw * 0.24, 180 + i);
      }
      glowShape(ctx, circ(128, 146, 18), r[1], rgba(r[0], 0.7), 12);
      recessed(ctx, star(62, 74, 22, 9, 4, -0.4), r, iw * 0.3, 190);
      raised(ctx, star(198, 58, 17, 6, 4, -0.4), r, iw * 0.3, 191);
    } };
  });

  add('delayed_echo', 'power', 'gold', 0.68, function (ctx, r, rnd, iw) {
    // a delayed echo: one aged parchment card, and in front of it the cold blue ghost of itself
    // that has not arrived yet. Replaces the two flat rounded rectangles; the cards are hand-cut
    // parchment with deckled edges, a curled corner and inked lines, and the echo is the family's
    // contrasting accent hue.
    var ak = AR();
    function parch(cx, cy, w, h, rot, seed) {
      var hw = w / 2, hh = h / 2;
      var pts = [];
      var run = [deckle(-hw, -hh, hw, -hh, 3.6, seed, 8), deckle(hw, -hh, hw, hh * 0.66, 3.2, seed + 7, 6)];
      for (var i = 0; i < run.length; i++) pts = pts.concat(run[i]);
      pts.push([hw * 0.58, hh * 0.98]);
      pts = pts.concat(deckle(hw * 0.58, hh * 0.98, -hw, hh * 0.9, 3.8, seed + 13, 8));
      pts = pts.concat(deckle(-hw, hh * 0.9, -hw * 0.96, -hh, 3.2, seed + 21, 7));
      var m = new DOMMatrix();
      m.translateSelf(cx, cy); m.rotateSelf(rot);
      var q = Pth(); q.addPath(poly(pts), m); return q;
    }
    var back = parch(104, 112, 118, 182, -0.24, 0x31a7);
    var front = parch(160, 152, 118, 182, 0.10, 0x31a7);
    return { sil: U(back, front), paint: function () {
      body(ctx, r, 6);
      // the echo: the same card one step behind and one step colder, so the pair reads as a
      // delayed repeat rather than as two different sheets of paper
      raised(ctx, back, ak, iw * 0.62, 200);
      deepen(ctx, ak, 0.52);
      carve(ctx, parch(104, 112, 90, 148, -0.24, 0x31a7), r, iw * 0.34, 0.4);
      ctx.save(); ctx.translate(104, 112); ctx.rotate(-0.24);
      glowShape(ctx, almond(0, -44, 30, 17), ak[2], null, 11);
      recessed(ctx, circ(0, -44, 10), r, iw * 0.3, 202);
      carve(ctx, line([[-34, 8], [30, 0]]), r, iw * 0.42, 0.4);
      carve(ctx, line([[-34, 28], [22, 20]]), r, iw * 0.42, 0.36);
      carve(ctx, line([[-34, 48], [12, 40]]), r, iw * 0.42, 0.32);
      ctx.restore();
      // the solid card in front
      raised(ctx, front, r, iw * 0.76, 210);
      carve(ctx, parch(160, 152, 92, 152, 0.10, 0x31a7), r, iw * 0.36, 0.42);
      ctx.save(); ctx.translate(160, 152); ctx.rotate(0.10);
      glowShape(ctx, almond(0, -48, 32, 18), r[1], null, 12);
      glowShape(ctx, circ(0, -48, 11), r[3], rgba(r[6], 0.9), 7);
      glowShape(ctx, circ(-5, -53, 3.6), '#ffffff', null, 4);
      carve(ctx, line([[-36, 6], [32, -2]]), r, iw * 0.44, 0.42);
      carve(ctx, line([[-36, 26], [24, 18]]), r, iw * 0.44, 0.38);
      carve(ctx, line([[-36, 46], [14, 38]]), r, iw * 0.44, 0.34);
      ctx.restore();
      // the echo ripple coming off the solid card, in the accent hue
      glowLine(ctx, ak, line([[206, 74], [224, 96], [226, 124]]), iw * 1.6, 8);
      glowLine(ctx, ak, line([[212, 100], [228, 122]]), iw * 1.2, 7);
    } };
  });

  add('delayed_scry', 'power', 'gold', 0.62, function (ctx, r, rnd, iw) {
    // an hourglass whose falling sand has become a watching eye
    var caps = U(rr(10, 4, 236, 36, 12), rr(10, 216, 236, 36, 12));
    var glass = poly([[40, 38], [216, 38], [128, 128], [216, 218], [40, 218], [128, 128]]);
    return { sil: U(caps, glass), paint: function () {
      body(ctx, r, 7);
      raised(ctx, glass, r, iw * 0.6, 210);
      recessed(ctx, poly([[68, 46], [188, 46], [128, 124]]), r, iw * 0.35, 211);
      raised(ctx, caps, r, iw * 0.75, 212);
      for (var i = 0; i < 3; i++) {
        raised(ctx, circ(40 + i * 12, 23, 5.5), r, iw * 0.24, 220 + i);
        raised(ctx, circ(40 + i * 12, 229, 5.5), r, iw * 0.24, 226 + i);
      }
      glowShape(ctx, almond(128, 172, 46, 26), r[1], null, 12);
      glowShape(ctx, circ(128, 172, 17), r[3], rgba(r[6], 0.85), 8);
      glowShape(ctx, circ(120, 164, 6), '#ffffff', null, 5);
      for (var k = 0; k < 5; k++) {
        raised(ctx, circ(112 + (rnd() - 0.5) * 24, 54 + k * 7, 1.7 + rnd() * 1.8), r, iw * 0.12, 232 + k);
      }
    } };
  });

  add('scry_might', 'power', 'crimson', 0.72, function (ctx, r, rnd, iw) {
    // a clenched fist - brute force, knuckles forward
    var fist = Pth();
    fist.moveTo(46, 122);
    fist.bezierCurveTo(40, 78, 76, 54, 116, 52);
    fist.bezierCurveTo(156, 50, 198, 60, 218, 86);
    fist.bezierCurveTo(238, 112, 236, 152, 218, 180);
    fist.bezierCurveTo(200, 210, 168, 236, 130, 242);
    fist.bezierCurveTo(92, 248, 56, 228, 42, 196);
    fist.bezierCurveTo(30, 168, 38, 144, 46, 136);
    fist.closePath();
    return { sil: fist, paint: function () {
      body(ctx, r, 8);
      raised(ctx, fist, r, iw * 0.8, 240);
      for (var i = 0; i < 3; i++) {
        raised(ctx, ell(86 + i * 36, 96, 18, 25, -0.15), r, iw * 0.5, 250 + i);
        recessed(ctx, rr(70 + i * 36, 118, 8, 44, 4), r, iw * 0.22, 260 + i);
      }
      raised(ctx, rr(46, 156, 168, 56, 24), r, iw * 0.6, 270);
      recessed(ctx, rr(66, 166, 128, 13, 6), r, iw * 0.3, 271);
      raised(ctx, ell(56, 176, 24, 30, 0.2), r, iw * 0.45, 272);
      glowShape(ctx, ring(152, 158, 32, 22), r[1], null, 10);
      for (var k = 0; k < 2; k++) raised(ctx, circ(96 + k * 64, 74, 5.5), r, iw * 0.2, 280 + k);
    } };
  });

  add('scry_agility', 'power', 'emerald', 0.6, function (ctx, r, rnd, iw) {
    // a long feather, quill to the lower-left
    var vane = Pth();
    vane.moveTo(250, 10);
    vane.bezierCurveTo(240, 116, 196, 194, 104, 232);
    vane.bezierCurveTo(62, 248, 22, 252, 6, 246);
    vane.bezierCurveTo(36, 208, 50, 158, 68, 116);
    vane.bezierCurveTo(100, 56, 158, 24, 250, 10);
    vane.closePath();
    var shaft = line([[2, 252], [238, 26]]);
    return { sil: U(vane, line([[8, 246], [236, 32]])), paint: function () {
      body(ctx, r, 9);
      raised(ctx, vane, r, iw * 0.7, 290);
      var a = Math.atan2(228 - 18, 16 - 244) - Math.PI / 2 + 0.30;
      for (var i = 0; i < 7; i++) {
        var t = 0.10 + i * 0.125;
        var sx = 244 + (16 - 244) * t, sy = 18 + (228 - 18) * t;
        var L = 38 * (1 - t * 0.35);
        recessed(ctx, ray(sx, sy, sx + Math.cos(a) * L, sy + Math.sin(a) * L, 3.6, 1.4), r, iw * 0.2, 300 + i);
        recessed(ctx, ray(sx, sy, sx - Math.cos(a) * L, sy - Math.sin(a) * L, 3.6, 1.4), r, iw * 0.2, 320 + i);
      }
      raisedLine(ctx, line([[14, 242], [228, 34]]), 9, r, iw * 0.45, 340);
      glowShape(ctx, line([[214, 48], [72, 196]]), r[1], null, 5);
    } };
  });

  add('judgement', 'power', 'violet', 0.56, function (ctx, r, rnd, iw) {
    // a balance: beam, chains, two pans, a radiant finial
    var beam = rr(4, 54, 248, 28, 14);
    var post = rr(112, 28, 32, 210, 12);
    var base = rr(48, 214, 160, 34, 16);
    var chains = U(line([[62, 82], [34, 146]]), line([[62, 82], [90, 146]]),
      line([[194, 82], [166, 146]]), line([[194, 82], [222, 146]]));
    var pan1 = Pth();
    pan1.moveTo(2, 134); pan1.lineTo(122, 134);
    pan1.quadraticCurveTo(122, 216, 62, 216); pan1.quadraticCurveTo(2, 216, 2, 134);
    pan1.closePath();
    var pan2 = Pth();
    pan2.moveTo(134, 134); pan2.lineTo(254, 134);
    pan2.quadraticCurveTo(254, 216, 194, 216); pan2.quadraticCurveTo(134, 216, 134, 134);
    pan2.closePath();
    var fin = star(128, 24, 30, 14, 4, -Math.PI / 2);
    return { sil: U(beam, post, base, pan1, pan2, fin, chains), paint: function () {
      body(ctx, r, 10);
      raised(ctx, U(pan1, pan2), r, iw * 0.7, 350);
      raisedLine(ctx, chains, 7, r, iw * 0.4, 351);
      raised(ctx, beam, r, iw * 0.7, 352);
      recessed(ctx, rr(16, 60, 224, 16, 8), r, iw * 0.3, 353);
      raised(ctx, post, r, iw * 0.7, 354);
      raised(ctx, base, r, iw * 0.7, 355);
      glowShape(ctx, fin, r[1], rgba(r[0], 0.75), 12);
      raised(ctx, ring(128, 112, 34, 20), r, iw * 0.4, 356);
      for (var i = 0; i < 3; i++) raised(ctx, circ(78 + i * 50, 231, 7), r, iw * 0.22, 360 + i);
    } };
  });

  add('ember_boon', 'power', 'crimson', 0.6, function (ctx, r, rnd, iw) {
    // a tall flame with an inner core and rising sparks
    var f = Pth();
    f.moveTo(140, 2);
    f.bezierCurveTo(154, 66, 236, 92, 244, 152);
    f.bezierCurveTo(252, 212, 196, 254, 128, 254);
    f.bezierCurveTo(60, 254, 4, 212, 12, 152);
    f.bezierCurveTo(20, 100, 78, 86, 100, 44);
    f.bezierCurveTo(110, 74, 120, 86, 132, 92);
    f.bezierCurveTo(134, 58, 138, 26, 142, 6);
    f.closePath();
    var inner = Pth();
    inner.moveTo(128, 104);
    inner.bezierCurveTo(148, 148, 176, 166, 176, 194);
    inner.bezierCurveTo(176, 224, 154, 240, 128, 240);
    inner.bezierCurveTo(102, 240, 80, 224, 80, 194);
    inner.bezierCurveTo(80, 166, 108, 148, 128, 104);
    inner.closePath();
    var sparks = Pth();
    var sr = [];
    for (var k = 0; k < 4; k++) {
      var sx = 40 + rnd() * 176, sy = 14 + rnd() * 66, s = 11 + rnd() * 9;
      sr.push([sx, sy, s]);
      sparks.addPath(sparkle(sx, sy, s, s * 0.34, -Math.PI / 2));
    }
    return { sil: U(f, sparks), paint: function () {
      body(ctx, r, 11);
      raised(ctx, f, r, iw * 0.8, 370, { two: 108 });
      recessed(ctx, inner, r, iw * 0.5, 371);
      glowShape(ctx, ell(128, 198, 40, 50, 0), r[1], rgba(r[0], 0.55), 18);
      recessed(ctx, ell(128, 200, 16, 25, 0), r, iw * 0.3, 372);
      glowShape(ctx, ell(128, 204, 8, 14, 0), '#fff6d8', null, 10);
      for (var k = 0; k < sr.length; k++) {
        raised(ctx, sparkle(sr[k][0], sr[k][1], sr[k][2], sr[k][2] * 0.34, -Math.PI / 2), r, iw * 0.22, 380 + k);
      }
    } };
  });

  add('granted_turn', 'power', 'gold', 0.62, function (ctx, r, rnd, iw) {
    // "one more turn": a forged sandglass whose glass is cut from cold blue crystal (the family's
    // contrasting accent) holding amber sand, with one extra amber grain granted on the top plate.
    // Replaces the old flat gold triangles with a bare plus badge floating beside them.
    var ak = AR();
    var caps = U(
      bandPath([[30, 34], [128, 26], [226, 34]], 16),
      bandPath([[30, 222], [128, 230], [226, 222]], 16));
    var glass = Pth();
    glass.moveTo(54, 44);
    glass.bezierCurveTo(58, 92, 100, 110, 116, 128);
    glass.bezierCurveTo(100, 146, 58, 164, 54, 212);
    glass.lineTo(202, 212);
    glass.bezierCurveTo(198, 164, 156, 146, 140, 128);
    glass.bezierCurveTo(156, 110, 198, 92, 202, 44);
    glass.closePath();
    var upper = Pth();
    upper.moveTo(68, 58);
    upper.bezierCurveTo(72, 94, 104, 110, 118, 124);
    upper.lineTo(138, 124);
    upper.bezierCurveTo(152, 110, 184, 94, 188, 58);
    upper.closePath();
    var sand = Pth();
    sand.moveTo(64, 208);
    sand.bezierCurveTo(66, 182, 94, 166, 112, 156);
    sand.bezierCurveTo(120, 148, 136, 148, 144, 156);
    sand.bezierCurveTo(162, 166, 190, 182, 192, 208);
    sand.closePath();
    // the granted turn: one extra amber grain, seated on the top plate and glowing. An encircling
    // hoop was tried first and read as a bucket handle, so the token is an object that touches the
    // glass instead of a ring around it.
    var grain = star(128, 30, 42, 14, 4, -Math.PI / 2);
    return { sil: U(caps, glass, grain), paint: function () {
      body(ctx, r, 12);
      // cold crystal glass, drained at the top
      raised(ctx, glass, ak, iw * 0.6, 392);
      recessed(ctx, upper, ak, iw * 0.34, 393);
      // the sand: a heap in the lower bulb and the thread still falling into it
      raised(ctx, sand, r, iw * 0.34, 394);
      carve(ctx, sand, r, iw * 0.3, 0.5);
      raised(ctx, bandPath([[128, 150], [128, 200]], 3.2), r, iw * 0.16, 395);
      for (var i = 0; i < 4; i++) {
        raised(ctx, circ(112 + (rnd() - 0.5) * 30, 62 + i * 8, 1.7 + rnd() * 1.7), r, iw * 0.14, 400 + i);
      }
      // the granted grain, glowing amber on the top plate
      raised(ctx, grain, r, iw * 0.4, 404);
      glowShape(ctx, star(128, 30, 34, 11, 4, -Math.PI / 2), r[1], null, 13);
      glowShape(ctx, circ(128, 30, 8), '#fff6d6', null, 9);
      // forged collars and the two chipped end plates
      raised(ctx, U(bandPath([[52, 44], [128, 38], [204, 44]], 9),
        bandPath([[52, 212], [128, 218], [204, 212]], 9)), r, iw * 0.4, 410);
      raised(ctx, caps, r, iw * 0.7, 412);
      carve(ctx, bandPath([[34, 30], [128, 22], [222, 30]], 7), r, iw * 0.26, 0.4);
      carve(ctx, bandPath([[34, 226], [128, 234], [222, 226]], 7), r, iw * 0.26, 0.4);
      for (var k = 0; k < 3; k++) {
        raised(ctx, circ(52 + k * 76, 30, 5.4), ak, iw * 0.2, 420 + k);
        raised(ctx, circ(52 + k * 76, 226, 5.4), ak, iw * 0.2, 426 + k);
      }
      glowShape(ctx, circ(128, 190, 13), r[1], rgba(r[0], 0.6), 10);
    } };
  });

  add('insight', 'power', 'violet', 0.58, function (ctx, r, rnd, iw) {
    // a radiant star with a seeing eye at its heart
    var ro = [128, 124, 130, 122, 128, 126, 130, 124, 128, 126, 130, 126];
    var ri = [74, 80, 72, 82, 76, 80, 74, 82, 76, 80, 74, 78];
    var pts = [];
    for (var i = 0; i < 24; i++) {
      var a = -Math.PI / 2 + i * Math.PI / 12;
      var q = (i % 2 === 0) ? ro[(i / 2) | 0] : ri[((i - 1) / 2) | 0];
      pts.push([128 + q * Math.cos(a), 128 + q * Math.sin(a)]);
    }
    var st = poly(pts);
    return { sil: st, paint: function () {
      body(ctx, r, 13);
      raised(ctx, st, r, iw * 0.75, 420, { two: 118 });
      recessed(ctx, star(128, 128, 92, 66, 12, -Math.PI / 2), r, iw * 0.35, 421);
      glowShape(ctx, ring(128, 128, 58, 50), r[1], null, 10);
      recessed(ctx, circ(128, 128, 50), r, iw * 0.4, 422);
      glowShape(ctx, almond(128, 128, 38, 21), r[1], null, 12);
      glowShape(ctx, circ(128, 128, 15), r[3], rgba(r[6], 0.85), 8);
      glowShape(ctx, circ(121, 121, 5.5), '#ffffff', null, 5);
    } };
  });

  add('purify', 'power', 'steel', 0.62, function (ctx, r, rnd, iw) {
    // a pure droplet, faceted inside, sparks of cleansing rising off it
    var d = Pth();
    d.moveTo(128, 2);
    d.bezierCurveTo(172, 84, 246, 128, 246, 176);
    d.bezierCurveTo(246, 224, 194, 254, 128, 254);
    d.bezierCurveTo(62, 254, 10, 224, 10, 176);
    d.bezierCurveTo(10, 128, 84, 84, 128, 2);
    d.closePath();
    var sparks = Pth();
    for (var k = 0; k < 2; k++) {
      sparks.addPath(sparkle(24 + rnd() * 210, 20 + rnd() * 60, 10 + rnd() * 9, 3.6, -Math.PI / 2));
    }
    return { sil: U(d, sparks), paint: function () {
      body(ctx, r, 14);
      raised(ctx, d, r, iw * 0.8, 430, { two: 118 });
      recessed(ctx, inset(d, 128, 168, 0.62), r, iw * 0.4, 431);
      for (var i = 0; i < 5; i++) {
        var a = -Math.PI * 0.9 + i * (Math.PI * 0.8 / 4);
        raised(ctx, ray(128, 168, 128 + Math.cos(a) * 76, 168 + Math.sin(a) * 76, 7.5, 2), r, iw * 0.24, 440 + i);
      }
      glowShape(ctx, sparkle(128, 168, 46, 14, -Math.PI / 2), r[1], rgba(r[0], 0.5), 16);
      raised(ctx, ell(94, 100, 18, 32, -0.5), r, iw * 0.3, 460);
      glowShape(ctx, circ(96, 92, 8), '#ffffff', null, 6);
    } };
  });

  add('exhaust_blast', 'power', 'crimson', 0.6, function (ctx, r, rnd, iw) {
    // a detonation: ragged burst shell around a bright core
    var ro = [128, 118, 132, 116, 128, 120, 130, 116, 126, 120, 128, 122];
    var ri = [92, 98, 88, 100, 94, 98, 90, 100, 94, 98, 92, 96];
    var pts = [];
    for (var i = 0; i < 24; i++) {
      var a = -Math.PI / 2 + i * Math.PI / 12;
      var q = (i % 2 === 0) ? ro[(i / 2) | 0] : ri[((i - 1) / 2) | 0];
      pts.push([128 + q * Math.cos(a), 128 + q * Math.sin(a)]);
    }
    var sp = poly(pts);
    var spikes = Pth();
    for (var k = 0; k < 5; k++) {
      var aa = k * Math.PI / 2.5 + 0.2;
      spikes.addPath(ray(128 + Math.cos(aa) * 80, 128 + Math.sin(aa) * 80,
        128 + Math.cos(aa) * 132, 128 + Math.sin(aa) * 132, 26, 12));
    }
    return { sil: U(sp, spikes), paint: function () {
      body(ctx, r, 15);
      raised(ctx, spikes, r, iw * 0.45, 480);
      raised(ctx, sp, r, iw * 0.75, 470);
      recessed(ctx, star(128, 128, 88, 62, 10, -Math.PI / 2), r, iw * 0.35, 471);
      glowShape(ctx, circ(128, 128, 45), r[1], null, 16);
      recessed(ctx, circ(128, 128, 30), r, iw * 0.35, 472);
      glowShape(ctx, circ(128, 128, 20), '#fff2d0', null, 12);
    } };
  });

  add('free_status', 'power', 'slate', 0.62, function (ctx, r, rnd, iw) {
    // a sprung padlock: one shackle leg still in its hole, the other swung clear out of the empty
    // hole beside it, on a brass pintle; a brass keyhole plate on the case. Replaces the old bare
    // rounded rectangle, and the symmetric U + centre boss that read as a handbag.
    var ak = AR();
    var plate = poly([
      [32, 156], [44, 134], [74, 126], [186, 126], [216, 134], [228, 156],
      [232, 190], [228, 218], [212, 240], [180, 248], [128, 244], [76, 248], [44, 240],
      [28, 218], [24, 190]]);
    // the shackle: left leg seated in its hole, right leg swung out and up, free end in the air
    var hoop = [[98, 152], [94, 102], [108, 72], [140, 58], [176, 62], [200, 46]];
    var shackle = bandPath(hoop, 13);
    var seam = line(hoop);
    var holeL = ell(98, 138, 13, 11, 0), holeR = ell(160, 138, 13, 11, 0);
    var esc = Pth();
    esc.moveTo(104, 176);
    esc.quadraticCurveTo(128, 166, 152, 176);
    esc.quadraticCurveTo(160, 214, 152, 238);
    esc.quadraticCurveTo(128, 248, 104, 238);
    esc.quadraticCurveTo(96, 214, 104, 176);
    esc.closePath();
    var keyhole = U(circ(128, 198, 11), poly([[122, 202], [134, 202], [131, 230], [125, 230]]));
    return { sil: U(plate, shackle), paint: function () {
      body(ctx, r, 16);
      raised(ctx, shackle, r, iw * 0.6, 490);
      carve(ctx, seam, r, iw * 0.38, 0.5);
      // the free end of the shackle: a forged foot, so it reads as a cut bar end and not a handle
      raised(ctx, bandPath([[190, 40], [206, 48]], 12), r, iw * 0.45, 489);
      raised(ctx, plate, r, iw * 0.8, 492, { two: 152 });
      deepen(ctx, r, 0.40);
      carve(ctx, inset(plate, 128, 190, 0.90), r, iw * 0.6, 0.42);
      // the top face and its two shackle holes - one occupied, one empty
      raised(ctx, bandPath([[42, 140], [128, 132], [214, 140]], 15), r, iw * 0.5, 494);
      carve(ctx, bandPath([[42, 140], [128, 132], [214, 140]], 8), r, iw * 0.3, 0.4);
      recessed(ctx, holeR, r, iw * 0.45, 495);
      recessed(ctx, holeL, r, iw * 0.45, 496);
      glowShape(ctx, ell(160, 138, 8, 6, 0), r[6], rgba(r[6], 0.9), 5);
      // hammer dents, wider and shallower on the shaded side
      carve(ctx, arcPath(206, 168, 18, Math.PI * 0.9, Math.PI * 1.7), r, iw * 0.3, 0.28);
      carve(ctx, arcPath(196, 226, 22, Math.PI * 1.1, Math.PI * 1.8), r, iw * 0.3, 0.26);
      carve(ctx, arcPath(60, 232, 20, Math.PI * 1.0, Math.PI * 1.6), r, iw * 0.28, 0.3);
      // the brass keyhole plate and the keyhole itself
      raised(ctx, esc, ak, iw * 0.5, 500);
      carve(ctx, esc, r, iw * 0.3, 0.45);
      recessed(ctx, keyhole, r, iw * 0.45, 501);
      glowShape(ctx, circ(128, 198, 9), ak[2], null, 8);
      // the brass pintle the shackle turns on
      raised(ctx, ring(104, 130, 16, 9), ak, iw * 0.34, 505);
      carve(ctx, circ(104, 130, 5), r, iw * 0.24, 0.5);
      var rv = [[52, 156], [204, 156], [64, 228], [196, 232]];
      for (var i = 0; i < rv.length; i++) {
        raised(ctx, circ(rv[i][0], rv[i][1], 7), ak, iw * 0.24, 510 + i);
        carve(ctx, circ(rv[i][0], rv[i][1], 3), r, iw * 0.2, 0.55);
      }
    } };
  });

  add('double_status', 'power', 'slate', 0.6, function (ctx, r, rnd, iw) {
    // "double status": the same status mark struck twice - two hand-cut iron tiles, the near one
    // bright with amber light in its carved mark, the far one dim and set back. Replaces the two
    // flat grey triangles and the broken "2" glyph.
    var ak = AR();
    // one carved status mark: an angular brand, so it reads at 64 px where a spiral became a donut
    var rune = line([[-16, -26], [2, -6], [-14, 10], [8, 30]]);
    var rune2 = line([[-16, -26], [20, -20]]);
    var rune3 = line([[-14, 10], [22, 16]]);
    var runeAll = U(rune, rune2, rune3);
    function tile(cx, cy, w, h, rot, seed) {
      var hw = w / 2, hh = h / 2, j = mulberry(seed >>> 0);
      var base = [[-hw * 0.88, -hh * 0.98], [-hw * 0.12, -hh * 1.06], [hw * 0.74, -hh * 0.9],
        [hw * 1.02, -hh * 0.14], [hw * 0.88, hh * 0.96], [hw * 0.04, hh * 1.05],
        [-hw * 0.82, hh * 0.9], [-hw * 1.03, hh * 0.06]];
      var pts = [];
      for (var i = 0; i < base.length; i++) {
        pts.push([base[i][0] + (j() - 0.5) * 9, base[i][1] + (j() - 0.5) * 9]);
      }
      var m = new DOMMatrix();
      m.translateSelf(cx, cy); m.rotateSelf(rot);
      var q = Pth(); q.addPath(poly(pts), m); return q;
    }
    function markOf(cx, cy, rot, s) {
      var m = new DOMMatrix();
      m.translateSelf(cx, cy); m.rotateSelf(rot); m.scaleSelf(s, s);
      var q = Pth(); q.addPath(runeAll, m); return q;
    }
    var back = tile(96, 104, 132, 138, -0.30, 0x51a3);
    var front = tile(160, 166, 140, 146, 0.14, 0x77c1);
    var pin = circ(160, 166, 15);
    return { sil: U(back, front, pin), paint: function () {
      body(ctx, r, 17);
      // the far tile: the same mark, one step down in value and warmth
      raised(ctx, back, r, iw * 0.75, 510);
      deepen(ctx, r, 0.56, 0, 0, 210, 210);
      carve(ctx, inset(back, 96, 104, 0.84), r, iw * 0.5, 0.42);
      glowLine(ctx, ak, markOf(96, 104, -0.30, 0.9), iw * 3.0, 7);
      // the near tile
      raised(ctx, front, r, iw * 0.8, 520);
      deepen(ctx, r, 0.30);
      carve(ctx, inset(front, 160, 166, 0.84), r, iw * 0.55, 0.45);
      glowLine(ctx, ak, markOf(160, 166, 0.14, 1.0), iw * 3.6, 11);
      carve(ctx, markOf(160, 166, 0.14, 1.0), r, iw * 0.34, 0.45);
      // the bronze pin that holds both tiles on the same nail
      raised(ctx, pin, ak, iw * 0.4, 530);
      carve(ctx, circ(160, 166, 6), r, iw * 0.3, 0.55);
    } };
  });

  add('status_draw', 'power', 'slate', 0.66, function (ctx, r, rnd, iw) {
    // drawing a status: a fan of three hand-cut parchment cards with a bronze arrow pulling the
    // top one clear of the rest. Replaces the two flat rounded rectangles and the bare barbed line.
    var ak = AR();
    function parch(cx, cy, w, h, rot, seed) {
      var hw = w / 2, hh = h / 2;
      var pts = [];
      pts = pts.concat(deckle(-hw, -hh, hw, -hh, 3.4, seed, 8));
      pts = pts.concat(deckle(hw, -hh, hw, hh, 3.0, seed + 5, 7));
      pts = pts.concat(deckle(hw, hh, -hw, hh, 3.6, seed + 11, 8));
      pts = pts.concat(deckle(-hw, hh, -hw, -hh, 3.0, seed + 17, 7));
      var m = new DOMMatrix();
      m.translateSelf(cx, cy); m.rotateSelf(rot);
      var q = Pth(); q.addPath(poly(pts), m); return q;
    }
    var fan = [
      parch(74, 150, 108, 176, -0.34, 0x2b17),
      parch(120, 140, 108, 180, -0.10, 0x2b17),
      parch(178, 116, 108, 180, 0.20, 0x2b17),
    ];
    var arc = [[104, 236], [172, 234], [226, 208], [248, 156], [240, 100]];
    var arw = bandPath(arc, 13);
    var head = arrowHead(arc[3][0], arc[3][1], arc[4][0], arc[4][1], 34, 26);
    function rule(cx, cy, rot) {
      var m = new DOMMatrix(); m.translateSelf(cx, cy); m.rotateSelf(rot);
      var p = Pth();
      var a = line([[-36, 6], [32, -2]]), b = line([[-36, 26], [24, 18]]), c = line([[-36, 46], [14, 38]]);
      p.addPath(a, m); p.addPath(b, m); p.addPath(c, m);
      return p;
    }
    return { sil: U(fan[0], fan[1], fan[2], arw, head), paint: function () {
      body(ctx, r, 18);
      raised(ctx, fan[0], r, iw * 0.7, 530);
      deepen(ctx, r, 0.62, 0, 20, 210, 250);
      carve(ctx, rule(74, 150, -0.34), r, iw * 0.42, 0.34);
      raised(ctx, fan[1], r, iw * 0.7, 531);
      deepen(ctx, r, 0.38, 20, 40, 230, 250);
      carve(ctx, rule(120, 140, -0.10), r, iw * 0.42, 0.38);
      // the card being drawn: brightest, with an inked eye stamp
      raised(ctx, fan[2], r, iw * 0.8, 532);
      carve(ctx, parch(178, 116, 92, 156, 0.20, 0x2b17), r, iw * 0.36, 0.42);
      ctx.save(); ctx.translate(178, 116); ctx.rotate(0.20);
      glowShape(ctx, almond(0, -50, 30, 17), r[1], null, 11);
      recessed(ctx, circ(0, -50, 11), r, iw * 0.3, 533);
      glowShape(ctx, circ(0, -50, 8), r[3], rgba(r[6], 0.9), 6);
      glowShape(ctx, circ(-5, -55, 3.4), '#ffffff', null, 4);
      carve(ctx, line([[-36, 6], [32, -2]]), r, iw * 0.44, 0.42);
      carve(ctx, line([[-36, 26], [24, 18]]), r, iw * 0.44, 0.38);
      carve(ctx, line([[-36, 46], [14, 38]]), r, iw * 0.44, 0.34);
      ctx.restore();
      // the hand pulling the card out, forged in the accent brass so it reads as an arrow
      raised(ctx, arw, ak, iw * 0.5, 540);
      carve(ctx, line(arc), r, iw * 0.3, 0.42);
      raised(ctx, head, ak, iw * 0.5, 541);
      carve(ctx, bandPath([[104, 236], [172, 234]], 8), r, iw * 0.34, 0.5);
    } };
  });

  add('shared_might', 'power', 'crimson', 0.54, function (ctx, r, rnd, iw) {
    // two interlocking rings with a spark where they cross
    var rA = ring(88, 128, 88, 44), rB = ring(168, 128, 88, 44);
    var sp1 = sparkle(128, 40, 28, 10, -Math.PI / 2);
    var sp2 = sparkle(128, 218, 20, 7, -Math.PI / 2);
    return { sil: U(rA, rB, sp1, sp2), paint: function () {
      body(ctx, r, 19);
      raised(ctx, rB, r, iw * 0.85, 550);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 128, 256, 128); ctx.clip();
      raised(ctx, rA, r, iw * 0.85, 551); ctx.restore();
      raised(ctx, rA, r, iw * 0.85, 552);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 128, 256, 128); ctx.clip();
      raised(ctx, rB, r, iw * 0.85, 553); ctx.restore();
      glowShape(ctx, sp1, r[1], rgba(r[0], 0.7), 14);
      glowShape(ctx, sp2, r[1], rgba(r[0], 0.6), 10);
    } };
  });

  add('steady_agility', 'power', 'emerald', 0.7, function (ctx, r, rnd, iw) {
    // a shield with a feather crest - settled, unshakeable dexterity
    var sh = Pth();
    sh.moveTo(128, 8);
    sh.bezierCurveTo(178, 26, 218, 32, 242, 34);
    sh.lineTo(242, 116);
    sh.bezierCurveTo(242, 192, 190, 236, 128, 252);
    sh.bezierCurveTo(66, 236, 14, 192, 14, 116);
    sh.lineTo(14, 34);
    sh.bezierCurveTo(38, 32, 78, 26, 128, 8);
    sh.closePath();
    var vane = Pth();
    vane.moveTo(188, 54);
    vane.bezierCurveTo(178, 116, 146, 158, 98, 180);
    vane.bezierCurveTo(76, 190, 58, 190, 50, 186);
    vane.bezierCurveTo(68, 162, 80, 132, 92, 110);
    vane.bezierCurveTo(110, 74, 142, 54, 188, 54);
    vane.closePath();
    var shaft = line([[48, 190], [188, 54]]);
    return { sil: U(sh, vane, line([[52, 186], [186, 58]])), paint: function () {
      body(ctx, r, 20);
      raised(ctx, sh, r, iw * 0.8, 560, { two: 120 });
      recessed(ctx, inset(sh, 128, 130, 0.76), r, iw * 0.5, 561);
      raised(ctx, vane, r, iw * 0.55, 562);
      var a = Math.atan2(190 - 54, 48 - 188) - Math.PI / 2 + 0.34;
      for (var i = 0; i < 5; i++) {
        var t = 0.14 + i * 0.165;
        var sx = 188 + (50 - 188) * t, sy = 54 + (186 - 54) * t;
        var L = 28 * (1 - t * 0.3);
        recessed(ctx, ray(sx, sy, sx + Math.cos(a) * L, sy + Math.sin(a) * L, 2.9, 1.2), r, iw * 0.18, 570 + i);
        recessed(ctx, ray(sx, sy, sx - Math.cos(a) * L, sy - Math.sin(a) * L, 2.9, 1.2), r, iw * 0.18, 580 + i);
      }
      raisedLine(ctx, shaft, 9, r, iw * 0.42, 590);
      glowShape(ctx, sparkle(128, 200, 30, 10, -Math.PI / 2), r[1], rgba(r[0], 0.5), 12);
    } };
  });

  add('starscar_form', 'power', 'starlight', 0.58, function (ctx, r, rnd, iw) {
    // 星痕化: a hand-cut star broken open. Five unequal arms, one chipped short, split by a rift of
    // warm light (the family's contrasting accent) and bound by a forged ward band. Replaces the
    // bare five-point primitive with its black stick and three stray motes.
    var ak = AR();
    var rr1 = [130, 112, 136, 118, 124], rr2 = [62, 70, 54, 68, 64];
    var jr = mulberry(0x5a17);
    var pts = [];
    for (var i = 0; i < 10; i++) {
      var a = -Math.PI / 2 + i * Math.PI / 5;
      var q = (i % 2 === 0) ? rr1[(i / 2) | 0] : rr2[((i - 1) / 2) | 0];
      q += (jr() - 0.5) * 9;
      pts.push([126 + q * Math.cos(a), 130 + q * Math.sin(a)]);
    }
    var st = Pth();
    st.moveTo(pts[0][0], pts[0][1]);
    for (var k = 0; k < 5; k++) {
      var inn = pts[k * 2 + 1], tip = pts[(k * 2 + 2) % 10];
      // the control is pulled toward the hub, which keeps the arms pointed instead of bulging
      var cx2 = 126 + (inn[0] - 126) * 0.74, cy2 = 130 + (inn[1] - 130) * 0.74;
      st.quadraticCurveTo(cx2, cy2, tip[0], tip[1]);
    }
    st.closePath();
    var band = bandPath([[16, 208], [74, 194], [132, 166], [190, 118], [228, 58]], 15);
    // the scar: one long rift cracking the star from the lower left to the upper right
    var rift = poly([[58, 206], [100, 168], [86, 152], [150, 108], [142, 138], [190, 108],
      [196, 128], [140, 166], [152, 182], [96, 218]]);
    var core = poly([[70, 198], [104, 166], [92, 154], [146, 118], [140, 140], [184, 114],
      [186, 124], [134, 160], [144, 172], [92, 208]]);
    return { sil: st, paint: function () {
      body(ctx, r, 21);
      raised(ctx, st, r, iw * 0.8, 600, { two: 118 });
      // the scar: a flat rift of warm light cracking the star open
      glowShape(ctx, rift, ak[3], null, 0);
      glowShape(ctx, core, ak[1], null, 0);
      glowLine(ctx, ak, line([[96, 172], [170, 118]]), iw * 2.6, 0);
      // chips off the broken arm
    } };
  });

  add('temp_might', 'power', 'crimson', 0.6, function (ctx, r, rnd, iw) {
    // 未命名·奋起 的临时力量. The reviewer asked for a front-view fist; I tried four of them and none
    // read at 64 px, and the reason is structural, not a matter of polish: long grooves from the top
    // edge read as four upright fingers (open hand), shortening them turns the lobes into teeth, and
    // a smooth mass with only creases is a mitten again. There is also no fist anywhere in the base
    // game to copy - vanilla draws Strength as a SWORD (strength_power), as a red arrow
    // (possess_strength_power) or as a rising burst (vigor_power). The burst is out because it would
    // collide with our own exhaust_blast, so this is vanilla's primary strength idiom: a broad
    // crimson blade. "Temporary" is carried by ONE deformation, as instructed - the upper blade
    // drains into a darker value behind a hand-cut boundary and its edges erode into large steps, so
    // the blade is visibly spending itself. No detached islands (anything under ~22 design units is
    // eaten by its own outline), flat crimson, 4 values + black, and unmistakably not scry_might.
    var M = new DOMMatrix();
    M.translateSelf(104, 186); M.rotateSelf(45);
    var L = function (p) { var q = Pth(); q.addPath(p, M); return q; };
    // local space: the sword points up, hilt at the origin
    var blade = poly([
      [-24, -14], [-22, -64], [-34, -88], [-10, -112], [-22, -136], [-2, -152], [0, -160],
      [2, -152], [22, -136], [10, -112], [34, -88], [22, -64], [24, -14]]);
    var guard = poly([[-50, -2], [-44, -16], [44, -16], [50, -2], [44, 8], [-44, 8]]);
    var grip = poly([[-11, 6], [11, 6], [10, 44], [-10, 44]]);
    var pommel = circ(0, 52, 13);
    // the draining upper blade, behind a hand-cut boundary
    var drainL = poly([[-30, -84], [-10, -100], [10, -86], [30, -102], [30, -172], [-30, -172]]);
    var ridgeL = poly([[-7, -24], [7, -24], [4, -140], [-4, -140]]);
    var sword = U(L(blade), L(guard), L(grip), L(pommel));
    return { sil: sword, paint: function () {
      body(ctx, r, 8);
      raised(ctx, sword, r, iw * 0.85, 650, { two: 112 });
      raised(ctx, L(drainL), r, iw * 0.7, 651, { tone: 4 });
      glowShape(ctx, L(ridgeL), r[1], null, 0);
      raised(ctx, L(guard), r, iw * 0.7, 652, { tone: 3 });
      raised(ctx, L(grip), r, iw * 0.7, 653, { tone: 4 });
      raised(ctx, L(pommel), r, iw * 0.7, 654, { tone: 3 });
      // the wrapped grip
      for (var i = 0; i < 3; i++) {
        carve(ctx, L(line([[-11, 13 + i * 10], [11, 13 + i * 10]])), r, iw * 0.8, 0.6);
      }
      // the eroded blade edges, so the steps survive at 64 px
      carve(ctx, L(line([[-24, -14], [-22, -64], [-34, -88], [-10, -112], [-22, -136], [-2, -152]])),
        r, iw * 0.5, 0.4);
      carve(ctx, L(line([[24, -14], [22, -64], [34, -88], [10, -112], [22, -136], [2, -152]])),
        r, iw * 0.5, 0.4);
    } };
  });

  add('temp_agility', 'power', 'emerald', 0.6, function (ctx, r, rnd, iw) {
    // 未命名·从容 的临时敏捷: a quill feather with the upper half already torn away into wind, so it
    // reads as agility that expires. The vane is ONE solid island with the barbs cut in as interior
    // black lines - serrating the silhouette instead would make every barb thinner than the outline
    // band and render the whole thing black. Narrow and vertical, never scry_agility's round leaf.
    var ak = AR();
    var vane = Pth();
    vane.moveTo(74, 244);
    vane.bezierCurveTo(64, 206, 62, 168, 74, 132);
    vane.bezierCurveTo(88, 92, 108, 62, 128, 46);
    vane.bezierCurveTo(140, 58, 146, 76, 148, 96);
    vane.bezierCurveTo(160, 90, 170, 78, 176, 64);
    vane.bezierCurveTo(184, 96, 180, 132, 168, 164);
    vane.bezierCurveTo(158, 190, 142, 214, 124, 236);
    vane.bezierCurveTo(112, 248, 92, 252, 74, 244);
    vane.closePath();
    var ribbons = [
      bandPath([[164, 92], [200, 74], [228, 44]], 15),
      bandPath([[154, 130], [190, 128], [222, 112]], 13),
    ];
    var motes = [petal(226, 168, -1.1, 30, 14, 0.2), petal(244, 46, -1.0, 26, 12, 0.2)];
    var sil = U(vane, ribbons[0], ribbons[1], motes[0], motes[1]);
    return { sil: sil, paint: function () {
      body(ctx, r, 9);
      for (var q = 0; q < ribbons.length; q++) {
        raised(ctx, ribbons[q], r, iw * 0.4, 670 + q, { tone: 1 });
        carve(ctx, bandPath([[164, 92], [200, 74], [228, 44]], 6), r, iw * 0.3, 0.4);
      }
      raised(ctx, vane, r, iw * 0.8, 680, { two: 116 });
      // the barbs, cut into the vane as thin black lines: short and irregular near the torn top
      var a = -2.34;
      for (var k = 0; k < 7; k++) {
        var t = 0.10 + k * 0.135;
        var sx = 74 + (128 - 74) * t + 8, sy = 244 + (46 - 244) * t;
        var L = 44 * (1 - t * 0.42);
        carve(ctx, ray(sx, sy, sx + Math.cos(a) * L, sy + Math.sin(a) * L, 2.6, 1.1), r, iw * 0.36, 0.55);
        carve(ctx, ray(sx, sy, sx - Math.cos(a) * L * 0.86, sy - Math.sin(a) * L * 0.86, 2.6, 1.1), r, iw * 0.36, 0.5);
      }
      // the shaft and the torn end: the vane simply stops and the last barbs are loose
      raised(ctx, bandPath([[78, 244], [92, 160], [126, 52]], 9), r, iw * 0.4, 690, { tone: 1 });
      carve(ctx, line([[78, 242], [126, 52]]), r, iw * 0.3, 0.5);
      carve(ctx, line([[128, 46], [140, 34], [152, 50]]), r, iw * 0.5, 0.6);
      for (var m = 0; m < motes.length; m++) {
        glowShape(ctx, petal(m === 0 ? 226 : 244, m === 0 ? 168 : 46, -1.05, 20, 9, 0.2), ak[2], null, 0);
      }
    } };
  });

  // ============================ RELICS =====================================

  add('agate_potion_belt', 'relic', 'bronze', 0.70, function (ctx, r, rnd, iw) {
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
  add('foresight_charm', 'relic', 'bronze', 0.72, function (ctx, r, rnd, iw) {
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
  add('prophets_bracelet', 'relic', 'bronze', 0.68, function (ctx, r, rnd, iw) {
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
  // ---- 先知发饰 / Prophet's Hair Ornament (model id YETANNIA-PROPHETS_EYE) ----------------------
  // Redrawn for the rename: the subject used to be an eye, which the display name no longer
  // describes. It is now a pleated fan-comb (a 发梳 / hair ornament): an iron spine with three
  // rivets, a bronze fan of flat tone wedges, and an amber cabochon in an iron bezel at the hinge.
  // Same materials as the rest of the relic set (bronze body, iron furniture, ivory inlay, amber
  // gem) so it stays in the established family; no new hue was introduced.
  add('prophets_eye', 'relic', 'bronze', 0.66, function (ctx, r, rnd, iw) {
    var iron = MAT.iron, iv = MAT.ivory, amb = MAT.amber;
    var C = { x: 128, y: 176 };
    var bar = rr(10, 166, 236, 74, 20);
    var fan = Pth();
    fan.arc(C.x, C.y, 122, Math.PI, 2 * Math.PI, false);
    fan.closePath();
    return { sil: U(bar, fan), paint: function () {
      body(ctx, r, 27);
      raised(ctx, fan, r, iw * 0.85, 910, { two: 232 });
      // an inset darker field leaves the bronze fan rim showing at the edge
      raised(ctx, inset(fan, C.x, C.y, 0.84), r, iw * 0.45, 911, { tone: 3 });
      // the pleats: flat alternating wedges radiating from the hinge, which is what makes a fan
      // comb read as a comb and not as a shell
      for (var i = 0; i < 8; i += 2) {
        var a0 = Math.PI + i * Math.PI / 8, a1 = a0 + Math.PI / 8;
        raised(ctx, polyW([[C.x, C.y],
          [C.x + Math.cos(a0) * 106, C.y + Math.sin(a0) * 106],
          [C.x + Math.cos(a1) * 106, C.y + Math.sin(a1) * 106]]), r, iw * 0.30, 915 + i, { tone: 2 });
      }
      raised(ctx, bar, iron, iw * 0.85, 930);
      raised(ctx, rr(26, 180, 204, 16, 8), iv, iw * 0.4, 931);
      for (var k = 0; k < 3; k++) raised(ctx, circ(46 + k * 82, 216, 12), iron, iw * 0.34, 935 + k);
      raised(ctx, circ(C.x, C.y + 2, 34), iron, iw * 0.7, 940);
      recessed(ctx, circ(C.x, C.y + 2, 24), iron, iw * 0.4, 941);
      glowShape(ctx, ell(C.x, C.y + 2, 20, 17, 0), amb[1], rgba(amb[6], 0.92), 9);
      glowShape(ctx, circ(C.x - 7, C.y - 6, 6), iv[0], null, 5);
    } };
  });
  // ---- 先知头冠 / Prophet's Crown (model id YETANNIA-PROPHETS_EYE_PLUS) --------------------------
  // The Ancient form of the same object: gilded (bronzeBright) instead of bronze, and taller - a
  // jewelled band under three truncated points with a large central cabochon and two amber sparks.
  // The pair is deliberately opposite in silhouette (low pleated fan vs tall three-point crown) so
  // the two are never confused at 64 px.
  add('prophets_eye_plus', 'relic', 'bronzeBright', 0.72, function (ctx, r, rnd, iw) {
    var iron = MAT.iron, iv = MAT.ivory, amb = MAT.amber;
    var band = rr(12, 148, 232, 82, 20);
    // truncated points rather than sharp spikes: a spike narrower than the ~8.5 design-unit ink
    // band comes out solid black (see ICON-STYLE-REPORT.md A4)
    var pts = [
      polyW([[22, 156], [86, 156], [78, 66], [34, 66]]),
      polyW([[94, 156], [162, 156], [156, 30], [100, 30]]),
      polyW([[170, 156], [234, 156], [222, 66], [178, 66]]),
    ];
    var pcx = [54, 128, 202], pcy = [111, 93, 111], gx = [56, 128, 200], gy = [98, 96, 98];
    return { sil: U(band, pts[0], pts[1], pts[2]), paint: function () {
      body(ctx, r, 32);
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      pool(ctx, 128, 128, 132, r[1], 0.16 * WARM_MUL);
      ctx.restore();
      for (var i = 0; i < 3; i++) {
        raised(ctx, pts[i], r, iw * 0.85, 950 + i);
        raised(ctx, inset(pts[i], pcx[i], pcy[i], 0.70), r, iw * 0.4, 954 + i, { tone: 3 });
        glowShape(ctx, circ(gx[i], gy[i], 13), amb[1], rgba(amb[6], 0.92), 8);
        glowShape(ctx, circ(gx[i] - 4, gy[i] - 4, 4.5), iv[0], null, 4);
      }
      raised(ctx, band, iron, iw * 0.85, 960, { two: 258 });
      raised(ctx, rr(26, 202, 204, 22, 9), r, iw * 0.45, 961);
      raised(ctx, circ(128, 186, 30), iron, iw * 0.6, 970);
      recessed(ctx, circ(128, 186, 22), iron, iw * 0.4, 971);
      glowShape(ctx, ell(128, 186, 18, 15, 0), amb[1], rgba(amb[6], 0.92), 9);
      glowShape(ctx, circ(122, 180, 5.5), iv[0], null, 5);
      for (var s = 0; s < 2; s++) raised(ctx, circ(52 + s * 152, 186, 11), amb, iw * 0.34, 975 + s);
      for (var t = 0; t < 2; t++) raised(ctx, sparkle(30 + t * 196, 44, 17, 6, -Math.PI / 2), amb, iw * 0.26, 980 + t);
    } };
  });
  add('energy_yetannia', 'orb', 'orb', 0.74, function (ctx, r, rnd, iw) {
    var sphere = circ(128, 128, 124);
    var band = ring(128, 128, 124, 106);
    var sparks = Pth();
    for (var k = 0; k < 5; k++) {
      var a = k * Math.PI / 2.5 + 0.3;
      sparks.addPath(star(128 + Math.cos(a) * 118, 128 + Math.sin(a) * 118, 14, 4.5, 4, a));
    }
    return { sil: U(sphere, sparks), paint: function () {
      body(ctx, r, 27);
      raised(ctx, sphere, r, iw * 0.9, 840);
      // gold band around the rim
      ctx.save();
      ctx.beginPath(); ctx.arc(128, 128, 122, 0, 6.2832); ctx.clip();
      var gold = ['#fff6cf', '#ffd76a', '#e0ac1e', '#9c7208', '#4a3502'];
      ctx.fillStyle = axisGrad(ctx, 60, 16, 212, 244, [
        [0.0, gold[0]], [0.28, gold[1]], [0.58, gold[2]], [0.84, gold[3]], [1.0, gold[4]]
      ]);
      ctx.fillRect(0, 0, 256, 18); ctx.fillRect(0, 238, 256, 18);
      ctx.fillRect(0, 0, 18, 256); ctx.fillRect(238, 0, 18, 256);
      ctx.restore();
      ctx.save();
      ctx.strokeStyle = '#33240a'; ctx.lineWidth = iw * 0.55; ctx.lineJoin = 'round';
      ctx.beginPath(); ctx.arc(128, 128, 114, 0, 6.2832); ctx.stroke();
      ctx.restore();
      glowShape(ctx, ring(128, 128, 110, 100), r[1], null, 8);
      // eye motif
      glowShape(ctx, almond(128, 128, 68, 39), r[1], null, 16);
      recessed(ctx, circ(128, 128, 22), r, iw * 0.4, 841);
      glowShape(ctx, circ(128, 128, 15), '#fff0b8', null, 10);
      glowShape(ctx, circ(119, 119, 8), '#ffffff', null, 7);
      ctx.save();
      ctx.translate(86, 70); ctx.rotate(-0.6);
      ctx.beginPath(); ctx.ellipse(0, 0, 42, 23, 0, 0, 6.2832);
      ctx.fillStyle = 'rgba(255,255,255,0.30)'; ctx.fill();
      ctx.restore();
      for (var k = 0; k < 8; k++) {
        var a = k * Math.PI / 4 + 0.3;
        raised(ctx, star(128 + Math.cos(a) * 118, 128 + Math.sin(a) * 118, 13, 4.4, 4, a), r, iw * 0.22, 850 + k);
      }
    } };
  });

  // ------------------------------------------------------------------ inline energy glyph
  // The card-text energy icon (TextEnergyIconPath). Godot renders [img]<path>[/img] at the texture's
  // own size, and every vanilla <color>_energy_icon.png in images/packed/sprite_fonts is 24x24, so
  // this asset is emitted at 24x24 by artresize.ps1 and is AUTHORED for 24 px - it is not the 256
  // orb scaled down. At 24 px one design unit is 0.094 px, so nothing here may be stroke-based:
  // there are exactly three marks (the ball, one solid dark eye lens, one pale iris) plus a single
  // highlight. The 256 orb's gold rim, rim spikes, highlight streak and eye outline are all
  // deliberately dropped - at 24 px they were sub-pixel mush. The silhouette is wobbled rather than
  // a clean circle so it keeps the set's hand-cut edge.
  add('energy_inline', 'texticon', 'orb', 0.80, function (ctx, r, rnd, iw) {
    var ball = wobble(128, 128, 122, 3, 3.4, 0x51c0, 0);
    var eye = almond(128, 136, 76, 42);
    var iris = circ(128, 134, 25);
    return { sil: ball, paint: function () {
      body(ctx, r, 29, { split: 0.5 });
      glowShape(ctx, eye, mixc(r[6], '#000000', 0.35), null, 0);
      glowShape(ctx, iris, MAT.amber[0], null, 0);
    } };
  });

  // ------------------------------------------------------------------ map marker
  // The map avatar Yetannia stands on, drawn to the base game's own marker convention. That
  // convention is NOT a portrait: decoding the five packed PNGs (49x64, lossless WebP inside the
  // .ctex) shows five bold flat EMBLEMS in each character's colour - ironclad a red chevron, silent
  // a green barbed leaf, defect literally a map-pin, necrobinder pink slats, regent an orange crest
  // - each spanning the frame (measured bbox 37-49 wide x 62-64 tall, i.e. 0-7 px side margins and
  // 0-7 px top/bottom, 50-64 % of that bbox covered), with internal facet lines and a thick
  // semi-transparent black outline. That is our own house style, so this emblem is painted with the
  // same flat fills + plateau outline as the 30 power icons.
  //
  // 眼形宝石徽记: a faceted pin whose head carries the eye. A bare eye-shaped gem cannot fill a
  // 49x64 PORTRAIT frame without shrinking the marker (an eye is landscape), and marker size
  // consistency is the one thing that has to match vanilla - so the gem is cut as the pin head,
  // which is the same shape the base game already uses for defect's marker.
  add('map_marker', 'marker', 'orb', 0.6, function (ctx, r, rnd, iw) {
    // design bbox 182 wide x 254 tall (aspect 0.717) -> ~44 x 62 px of the 49x64 frame after
    // artresize's central 392x512 crop, i.e. the vanilla footprint rather than a shrunken one
    var pin = Pth();
    pin.arc(128, 91, 91, Math.PI * 0.806, Math.PI * 2.194, false);   // 145 deg over the top to 35 deg
    pin.lineTo(128, 254);
    pin.closePath();
    var eye = almond(128, 86, 66, 40);
    var iris = circ(128, 84, 24);
    return { sil: pin, paint: function () {
      body(ctx, r, 30, { split: 0.45 });
      // the gem's girdle (where the point meets the head) and the point's own facet
      carve(ctx, line([[54, 143], [128, 196], [202, 143]]), r, iw * 0.8, 0.45);
      carve(ctx, line([[128, 150], [128, 250]]), r, iw * 0.9, 0.5);
      // the eye: one solid near-black lens with a cream iris, the same motif as the energy orb
      glowShape(ctx, eye, mixc(r[6], '#000000', 0.35), null, 0);
      glowShape(ctx, iris, MAT.amber[0], null, 0);
      glowShape(ctx, circ(120, 76, 8), '#ffffff', null, 0);
    } };
  });

  // ------------------------------------------------------------------ frame
  var RENDER = 512;

  window.__ICONS = ICONS;
  window.__FAM = FAM;
  window.__RENDER = RENDER;

  function paintOne(ctx, def) {
    var r = FAM[def.cat] || FAM.violet;
    var seed = hashName(def.name);
    var iw = 2.1;                        // interior ink width, design units
    CURCAT = def.cat;
    var obj = def.build(ctx, r, mulberry(seed), iw);
    ctx.save();
    ctx.beginPath();
    ctx.clip(obj.sil);
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    obj.paint();
    finish(ctx, r, def.name, def.cat, def.group);
    ctx.restore();
  }

  // Render one icon into a 512x512 canvas.
  //
  // Auto-fit is coverage-driven, not bbox-driven: vanilla icons cover 61 % of the canvas inside a
  // 92 %-of-frame bbox, so the scale is chosen to hit this icon's `cov` and then clamped so the
  // content bbox never exceeds 98 % of the frame. (Scaling changes coverage quadratically, so a
  // sparse subject simply cannot be scaled into range - those had to be redrawn denser.)
  window.__DRAW_ICON = function (ctx, def) {
    var r = FAM[def.cat] || FAM.violet;
    var seed = hashName(def.name);
    var iw = 2.1;
    WARM_MUL = def.group === 'relic' ? 0.30 : 1;
    CURCAT = def.cat;
    // ---- pass 1: silhouette only, to measure the content bbox and the covered area.
    // The silhouette is filled PART BY PART rather than as one Path2D: a Path2D clip fills with the
    // nonzero rule, so any subpath wound against the others cancels and punches a transparent hole
    // through the union. Several hand-drawn outlines (the sandglass glass, bandPath before it was
    // normalised) wound the other way and did exactly that. Filling each part source-over can never
    // cancel, and it is what the final clip is derived from below.
    var probe = document.createElement('canvas');
    probe.width = RENDER; probe.height = RENDER;
    var pc = probe.getContext('2d');
    pc.setTransform(2, 0, 0, 2, 0, 0);
    pc.fillStyle = '#fff';
    PARTS.length = 0;
    var obj0 = def.build(pc, FAM.slate, mulberry(seed), iw);
    var parts = PARTS.slice();
    PARTS.length = 0;
    if (parts.length) for (var pi = 0; pi < parts.length; pi++) pc.fill(parts[pi]);
    else pc.fill(obj0.sil);
    var d = pc.getImageData(0, 0, RENDER, RENDER).data;
    var minX = RENDER, minY = RENDER, maxX = -1, maxY = -1, covered = 0;
    var gsx = 0, gsy = 0;
    for (var y = 0; y < RENDER; y++) {
      for (var x = 0; x < RENDER; x++) {
        if (d[(y * RENDER + x) * 4 + 3] > 32) {
          covered++;
          if (x < minX) minX = x; if (x > maxX) maxX = x;
          if (y < minY) minY = y; if (y > maxY) maxY = y;
          gsx += x; gsy += y;
        }
      }
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, RENDER, RENDER);
    if (maxX < 0 || !covered) return { coverage: 0, bboxFill: 0, scale: 0 };
    var bw = maxX - minX + 1, bh = maxY - minY + 1;
    var sBboxMax = (def.group === 'relic' ? 0.93 : 0.965) * RENDER / Math.max(bw, bh);
    var sArea = Math.sqrt(def.cov * RENDER * RENDER / covered);
    var s = Math.min(sArea, sBboxMax);
    var cx = (minX + maxX + 1) / 2, cy = (minY + maxY + 1) / 2;
    // ---- pass 2: the real thing. Probe pixels were design*2, so the transform is s * 2 on the
    // design-space object, offset so the probe bbox centre lands on the frame centre.
    var tf = function (c) { c.setTransform(s * 2, 0, 0, s * 2, RENDER / 2 - cx * s, RENDER / 2 - cy * s); };
    if (parts.length > 1) {
      // paint into a scratch layer, then keep only what the part-wise mask covers
      var layer = document.createElement('canvas');
      layer.width = RENDER; layer.height = RENDER;
      var lc = layer.getContext('2d');
      tf(lc);
      lc.lineJoin = 'round'; lc.lineCap = 'round';
      var objL = def.build(lc, r, mulberry(seed), iw);
      PARTS.length = 0;
      objL.paint();
      finish(lc, r, def.name, def.cat, def.group);
      var mask = document.createElement('canvas');
      mask.width = RENDER; mask.height = RENDER;
      var mc = mask.getContext('2d');
      tf(mc);
      mc.fillStyle = '#fff';
      for (var mi = 0; mi < parts.length; mi++) mc.fill(parts[mi]);
      lc.setTransform(1, 0, 0, 1, 0, 0);
      lc.globalCompositeOperation = 'destination-in';
      lc.drawImage(mask, 0, 0);
      lc.globalCompositeOperation = 'source-over';
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(layer, 0, 0);
    } else {
      ctx.setTransform(s * 2, 0, 0, s * 2, RENDER / 2 - cx * s, RENDER / 2 - cy * s);
      ctx.save();
      ctx.beginPath();
      var obj = def.build(ctx, r, mulberry(seed), iw);
      PARTS.length = 0;
      ctx.clip(obj.sil);
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      obj.paint();
      finish(ctx, r, def.name, def.cat, def.group);
      ctx.restore();
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    return { coverage: covered * s * s / (RENDER * RENDER), bboxFill: (bw * s) * (bh * s) / (RENDER * RENDER), scale: s };
  };
})();
