// One-shot shape patcher: makes the sparse subjects dense enough that the coverage-driven
// auto-fit can actually reach the vanilla band (61 % +/- , p10 46.5). Vanilla power icons are
// solid masses; thin ray/ring/star subjects simply cannot be scaled into range.
// Throwaway tooling - run once with `node _fatten.js`.
'use strict';
const fs = require('fs');
const p = require('path').join(__dirname, 'paint.js');
let t = fs.readFileSync(p, 'utf8');
const R = [
  // ---- foresight: 9 hair-thin rays -> 12 blunt rays merged into a thick corona
  [`    var rays = Pth();
    for (var i = 0; i < 9; i++) {
      var a = -Math.PI * 0.94 + i * (Math.PI * 1.88 / 8);
      rays.addPath(ray(128 + Math.cos(a) * 72, 128 + Math.sin(a) * 72,
        128 + Math.cos(a) * 126, 128 + Math.sin(a) * 126, 14, 4.5));
    }
    var sil = U(rays, ring(128, 128, 84, 60));`,
   `    var rays = Pth();
    for (var i = 0; i < 12; i++) {
      var a = -Math.PI * 0.94 + i * (Math.PI * 1.88 / 11);
      rays.addPath(ray(128 + Math.cos(a) * 50, 128 + Math.sin(a) * 50,
        128 + Math.cos(a) * 130, 128 + Math.sin(a) * 130, 31, 15));
    }
    var sil = U(rays, ring(128, 128, 100, 56));`],
  [`      raised(ctx, ring(128, 128, 84, 60), r, iw * 0.7, 61);
      recessed(ctx, circ(128, 128, 60), r, iw * 0.5, 62);`,
   `      raised(ctx, ring(128, 128, 100, 56), r, iw * 0.7, 61);
      recessed(ctx, circ(128, 128, 56), r, iw * 0.5, 62);`],

  // ---- judgement: a real balance with deep solid bowls instead of thin wire pans
  [`    var beam = rr(12, 58, 232, 22, 11);
    var post = rr(118, 34, 20, 200, 9);
    var base = rr(58, 216, 140, 28, 13);
    var chains = U(line([[60, 82], [40, 142]]), line([[60, 82], [80, 142]]),
      line([[196, 82], [176, 142]]), line([[196, 82], [216, 142]]));
    var pan1 = Pth();
    pan1.moveTo(14, 142); pan1.quadraticCurveTo(60, 202, 106, 142); pan1.closePath();
    var pan2 = Pth();
    pan2.moveTo(150, 142); pan2.quadraticCurveTo(196, 202, 242, 142); pan2.closePath();
    var fin = star(128, 26, 24, 10, 4, -Math.PI / 2);`,
   `    var beam = rr(4, 54, 248, 28, 14);
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
    var fin = star(128, 24, 30, 14, 4, -Math.PI / 2);`],
  [`      raised(ctx, ring(128, 128, 28, 16), r, iw * 0.4, 356);
      for (var i = 0; i < 3; i++) raised(ctx, circ(64 + i * 64, 230, 6), r, iw * 0.22, 360 + i);`,
   `      raised(ctx, ring(128, 112, 34, 20), r, iw * 0.4, 356);
      for (var i = 0; i < 3; i++) raised(ctx, circ(78 + i * 50, 231, 7), r, iw * 0.22, 360 + i);`],
  [`      recessed(ctx, rr(24, 62, 208, 14, 7), r, iw * 0.3, 353);`,
   `      recessed(ctx, rr(16, 60, 224, 16, 8), r, iw * 0.3, 353);`],

  // ---- insight: fatter star points
  [`    var ro = [126, 118, 128, 114, 124, 120, 130, 116, 126, 120, 128, 122];
    var ri = [50, 57, 48, 59, 52, 57, 50, 59, 52, 57, 50, 55];`,
   `    var ro = [128, 124, 130, 122, 128, 126, 130, 124, 128, 126, 130, 126];
    var ri = [74, 80, 72, 82, 76, 80, 74, 82, 76, 80, 74, 78];`],
  [`      recessed(ctx, star(128, 128, 86, 47, 12, -Math.PI / 2), r, iw * 0.35, 421);
      glowShape(ctx, ring(128, 128, 53, 45), r[1], null, 10);
      recessed(ctx, circ(128, 128, 45), r, iw * 0.4, 422);`,
   `      recessed(ctx, star(128, 128, 92, 66, 12, -Math.PI / 2), r, iw * 0.35, 421);
      glowShape(ctx, ring(128, 128, 58, 50), r[1], null, 10);
      recessed(ctx, circ(128, 128, 50), r, iw * 0.4, 422);`],

  // ---- exhaust_blast: shallower interstices, blunter spikes
  [`    var ro = [128, 108, 132, 104, 126, 112, 130, 106, 124, 110, 128, 116];
    var ri = [66, 75, 62, 79, 68, 73, 64, 77, 68, 75, 66, 71];`,
   `    var ro = [128, 118, 132, 116, 128, 120, 130, 116, 126, 120, 128, 122];
    var ri = [92, 98, 88, 100, 94, 98, 90, 100, 94, 98, 92, 96];`],
  [`      spikes.addPath(ray(128 + Math.cos(aa) * 86, 128 + Math.sin(aa) * 86,
        128 + Math.cos(aa) * 130, 128 + Math.sin(aa) * 130, 13, 4));`,
   `      spikes.addPath(ray(128 + Math.cos(aa) * 80, 128 + Math.sin(aa) * 80,
        128 + Math.cos(aa) * 132, 128 + Math.sin(aa) * 132, 26, 12));`],
  [`      recessed(ctx, star(128, 128, 78, 45, 10, -Math.PI / 2), r, iw * 0.35, 471);`,
   `      recessed(ctx, star(128, 128, 88, 62, 10, -Math.PI / 2), r, iw * 0.35, 471);`],

  // ---- shared_might: heavier rings
  [`    var rA = ring(92, 128, 76, 52), rB = ring(164, 128, 76, 52);`,
   `    var rA = ring(88, 128, 88, 44), rB = ring(168, 128, 88, 44);`],
  [`      raised(ctx, rB, r, iw * 0.8, 550);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 128, 256, 128); ctx.clip();
      raised(ctx, rA, r, iw * 0.8, 551); ctx.restore();
      raised(ctx, rA, r, iw * 0.8, 552);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 128, 256, 128); ctx.clip();
      raised(ctx, rB, r, iw * 0.8, 553); ctx.restore();`,
   `      raised(ctx, rB, r, iw * 0.85, 550);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 128, 256, 128); ctx.clip();
      raised(ctx, rA, r, iw * 0.85, 551); ctx.restore();
      raised(ctx, rA, r, iw * 0.85, 552);
      ctx.save(); ctx.beginPath(); ctx.rect(0, 128, 256, 128); ctx.clip();
      raised(ctx, rB, r, iw * 0.85, 553); ctx.restore();`],

  // ---- cycle_of_prophecy: thicker annulus
  [`    ar.arc(128, 128, 98, a0, a1, false);
    ar.arc(128, 128, 60, a1, a0, true);`,
   `    ar.arc(128, 128, 104, a0, a1, false);
    ar.arc(128, 128, 54, a1, a0, true);`],
  [`    var head = poly([
      [tipX + px * 38, tipY + py * 38],
      [tipX + tx * 46, tipY + ty * 46],
      [tipX - px * 38, tipY - py * 38]]);
    return { sil: U(ar, head, circ(128, 128, 60)), paint: function () {`,
   `    var head = poly([
      [tipX + px * 46, tipY + py * 46],
      [tipX + tx * 54, tipY + ty * 54],
      [tipX - px * 46, tipY - py * 46]]);
    return { sil: U(ar, head, circ(128, 128, 54)), paint: function () {`],
  [`      recessed(ctx, circ(128, 128, 60), r, iw * 0.45, 160);`,
   `      recessed(ctx, circ(128, 128, 54), r, iw * 0.45, 160);`],

  // ---- starscar_form: fatter star, heavier ward arcs
  [`    var st = star(126, 130, 122, 52, 5, -Math.PI / 2);`,
   `    var st = star(126, 130, 126, 76, 5, -Math.PI / 2);`],
  [`      raisedLine(ctx, wardA, 13, r, iw * 0.6, 602);
      raisedLine(ctx, wardB, 13, r, iw * 0.6, 603);`,
   `      raisedLine(ctx, wardA, 19, r, iw * 0.6, 602);
      raisedLine(ctx, wardB, 19, r, iw * 0.6, 603);`],

  // ---- double_status: heavier chevrons, fatter 2
  [`    two.moveTo(172, 76);
    two.bezierCurveTo(196, 26, 254, 34, 254, 84);
    two.bezierCurveTo(254, 120, 218, 148, 180, 190);
    two.lineTo(180, 236);
    two.lineTo(254, 236);`,
   `    two.moveTo(168, 74);
    two.bezierCurveTo(194, 20, 256, 30, 256, 84);
    two.bezierCurveTo(256, 122, 216, 150, 178, 192);
    two.lineTo(178, 238);
    two.lineTo(256, 238);`],
  [`      raisedLine(ctx, c1, 30, r, iw * 0.6, 510);
      raisedLine(ctx, c2, 30, r, iw * 0.6, 511);`,
   `      raisedLine(ctx, c1, 44, r, iw * 0.6, 510);
      raisedLine(ctx, c2, 44, r, iw * 0.6, 511);`],

  // ---- scry_agility: fuller vane
  [`    vane.moveTo(244, 18);
    vane.bezierCurveTo(232, 112, 184, 178, 100, 214);
    vane.bezierCurveTo(62, 230, 30, 234, 16, 228);
    vane.bezierCurveTo(44, 196, 62, 154, 80, 120);
    vane.bezierCurveTo(108, 68, 158, 30, 244, 18);`,
   `    vane.moveTo(250, 10);
    vane.bezierCurveTo(240, 116, 196, 194, 104, 232);
    vane.bezierCurveTo(62, 248, 22, 252, 6, 246);
    vane.bezierCurveTo(36, 208, 50, 158, 68, 116);
    vane.bezierCurveTo(100, 56, 158, 24, 250, 10);`],
  [`    var shaft = line([[10, 246], [232, 30]]);
    return { sil: U(vane, line([[16, 240], [230, 36]])), paint: function () {`,
   `    var shaft = line([[2, 252], [238, 26]]);
    return { sil: U(vane, line([[8, 246], [236, 32]])), paint: function () {`],

  // ---- ember_boon: wider flame body
  [`    f.moveTo(142, 6);
    f.bezierCurveTo(152, 64, 222, 96, 228, 154);
    f.bezierCurveTo(234, 210, 190, 250, 128, 250);
    f.bezierCurveTo(66, 250, 22, 210, 28, 154);
    f.bezierCurveTo(34, 106, 82, 90, 102, 50);`,
   `    f.moveTo(140, 2);
    f.bezierCurveTo(154, 66, 236, 92, 244, 152);
    f.bezierCurveTo(252, 212, 196, 254, 128, 254);
    f.bezierCurveTo(60, 254, 4, 212, 12, 152);
    f.bezierCurveTo(20, 100, 78, 86, 100, 44);`],
  [`      glowShape(ctx, ell(128, 196, 32, 42, 0), r[1], rgba(r[0], 0.55), 18);`,
   `      glowShape(ctx, ell(128, 198, 40, 50, 0), r[1], rgba(r[0], 0.55), 18);`],

  // ---- hourglasses: fatter glass and caps
  [`    var caps = U(rr(10, 16, 184, 28, 10), rr(10, 212, 184, 28, 10));
    var glass = poly([[38, 44], [166, 44], [102, 128], [166, 212], [38, 212], [102, 128]]);
    var plus = plusPath(200, 64, 56, 18);`,
   `    var caps = U(rr(4, 10, 196, 34, 12), rr(4, 212, 196, 34, 12));
    var glass = poly([[30, 42], [174, 42], [102, 128], [174, 214], [30, 214], [102, 128]]);
    var plus = plusPath(202, 60, 60, 20);`],
  [`    var caps = U(rr(20, 8, 216, 30, 10), rr(20, 214, 216, 30, 10));
    var glass = poly([[56, 38], [200, 38], [128, 128], [200, 218], [56, 218], [128, 128]]);`,
   `    var caps = U(rr(10, 4, 236, 36, 12), rr(10, 216, 236, 36, 12));
    var glass = poly([[40, 38], [216, 38], [128, 128], [216, 218], [40, 218], [128, 128]]);`],

  // ---- purify: fuller droplet
  [`    d.moveTo(128, 6);
    d.bezierCurveTo(170, 88, 232, 130, 232, 176);
    d.bezierCurveTo(232, 222, 186, 250, 128, 250);
    d.bezierCurveTo(70, 250, 24, 222, 24, 176);
    d.bezierCurveTo(24, 130, 86, 88, 128, 6);`,
   `    d.moveTo(128, 2);
    d.bezierCurveTo(172, 84, 246, 128, 246, 176);
    d.bezierCurveTo(246, 224, 194, 254, 128, 254);
    d.bezierCurveTo(62, 254, 10, 224, 10, 176);
    d.bezierCurveTo(10, 128, 84, 84, 128, 2);`],
];
let n = 0, miss = [];
for (const [a, b] of R) {
  if (!t.includes(a)) { miss.push(a.split('\n')[0].trim().slice(0, 60)); continue; }
  t = t.replace(a, b); n++;
}
fs.writeFileSync(p, t);
console.log('patched ' + n + '/' + R.length);
if (miss.length) { console.log('MISSED:'); miss.forEach(m => console.log('  ' + m)); }
