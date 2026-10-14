/* Yetannia icon set - all glyphs drawn with canvas vector paths (no emoji, no font glyphs
   except the tiny "2" mark on double_status). Design canvas is 256x256. */
(function () {
  'use strict';

  var GLYPH = '#f2f4f8';
  var DARK = 'rgba(10,12,22,0.46)';
  var DARK_SOFT = 'rgba(10,12,22,0.28)';
  var OUTLINE = 4; // dark outline width for low-contrast (gold/bronze) frames

  // ---------------------------------------------------------------- helpers
  function rr(x, y, w, h, r) {
    r = Math.min(r, Math.min(w, h) / 2);
    var p = new Path2D();
    p.moveTo(x + r, y);
    p.lineTo(x + w - r, y);
    p.arcTo(x + w, y, x + w, y + r, r);
    p.lineTo(x + w, y + h - r);
    p.arcTo(x + w, y + h, x + w - r, y + h, r);
    p.lineTo(x + r, y + h);
    p.arcTo(x, y + h, x, y + h - r, r);
    p.lineTo(x, y + r);
    p.arcTo(x, y, x + r, y, r);
    p.closePath();
    return p;
  }
  function circ(cx, cy, r) {
    var p = new Path2D();
    p.arc(cx, cy, r, 0, Math.PI * 2, false);
    p.closePath();
    return p;
  }
  function ellPath(cx, cy, rx, ry, rot) {
    var p = new Path2D();
    p.ellipse(cx, cy, rx, ry, rot || 0, 0, Math.PI * 2, false);
    p.closePath();
    return p;
  }
  function poly(pts) {
    var p = new Path2D();
    p.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) p.lineTo(pts[i][0], pts[i][1]);
    p.closePath();
    return p;
  }
  function union() {
    var p = new Path2D();
    for (var i = 0; i < arguments.length; i++) p.addPath(arguments[i]);
    return p;
  }
  function ring(cx, cy, rOut, rIn) {
    var p = new Path2D();
    p.arc(cx, cy, rOut, 0, Math.PI * 2, false);
    p.moveTo(cx + rIn, cy);
    p.arc(cx, cy, rIn, 0, Math.PI * 2, true);
    p.closePath();
    return p;
  }
  function starPoly(cx, cy, rOut, rIn, n, rot) {
    var pts = [];
    for (var i = 0; i < n * 2; i++) {
      var a = rot + i * Math.PI / n;
      var r = (i % 2 === 0) ? rOut : rIn;
      pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
    return poly(pts);
  }
  // almond eye: hw = half width, hh = half height
  function almond(cx, cy, hw, hh) {
    var p = new Path2D();
    p.moveTo(cx - hw, cy);
    p.quadraticCurveTo(cx, cy - 2 * hh, cx + hw, cy);
    p.quadraticCurveTo(cx, cy + 2 * hh, cx - hw, cy);
    p.closePath();
    return p;
  }
  function taperRay(bx, by, tx, ty, w0, w1) {
    var dx = tx - bx, dy = ty - by, L = Math.hypot(dx, dy) || 1;
    var px = -dy / L, py = dx / L;
    return poly([
      [bx + px * w0, by + py * w0],
      [tx + px * w1, ty + py * w1],
      [tx - px * w1, ty - py * w1],
      [bx - px * w0, by - py * w0]
    ]);
  }
  function sparkle(cx, cy, rOut, rIn, rot) {
    return starPoly(cx, cy, rOut, rIn, 4, (rot === undefined ? -Math.PI / 2 : rot));
  }
  // plus sign as ONE polygon so an outline stroke never crosses its own middle
  function plusPath(cx, cy, arm, thick) {
    var a = arm, t = thick;
    return poly([
      [cx - t, cy - a], [cx + t, cy - a], [cx + t, cy - t], [cx + a, cy - t],
      [cx + a, cy + t], [cx + t, cy + t], [cx + t, cy + a], [cx - t, cy + a],
      [cx - t, cy + t], [cx - a, cy + t], [cx - a, cy - t], [cx - t, cy - t]
    ]);
  }
  // potion flask (body + neck + cork) as ONE path, same reason
  function flaskPath(cx, baseY) {
    var p = new Path2D();
    p.moveTo(cx - 13, baseY);
    p.quadraticCurveTo(cx - 26, baseY - 4, cx - 24, baseY - 20);
    p.quadraticCurveTo(cx - 22, baseY - 38, cx - 10, baseY - 40);
    p.lineTo(cx - 10, baseY - 58);
    p.lineTo(cx - 13, baseY - 58);
    p.lineTo(cx - 13, baseY - 70);
    p.lineTo(cx + 13, baseY - 70);
    p.lineTo(cx + 13, baseY - 58);
    p.lineTo(cx + 10, baseY - 58);
    p.lineTo(cx + 10, baseY - 40);
    p.quadraticCurveTo(cx + 22, baseY - 38, cx + 24, baseY - 20);
    p.quadraticCurveTo(cx + 26, baseY - 4, cx + 13, baseY);
    p.closePath();
    return p;
  }

  // ---- painting primitives -------------------------------------------------
  // PASS 0 = silhouette pass: every white shape is painted as one opaque dark
  // silhouette that carries the drop shadow; dark details are skipped. PASS 1 =
  // the real paint, with no shadows. Result: one clean shadow behind the whole
  // glyph instead of every element shadowing its neighbours.
  var PASS = 1;
  var SIL = '#0b0d16';
  var SHADOW = { color: 'rgba(0,0,0,0.55)', blur: 11, oy: 5 };

  function white(ctx, path) {
    ctx.save();
    if (PASS === 0) {
      ctx.shadowColor = SHADOW.color;
      ctx.shadowBlur = SHADOW.blur;
      ctx.shadowOffsetY = SHADOW.oy;
      ctx.fillStyle = SIL;
      ctx.strokeStyle = SIL;
      ctx.lineWidth = 4 + OUTLINE;
      ctx.lineJoin = 'round';
      ctx.stroke(path);
      ctx.fill(path);
      ctx.restore();
      return;
    }
    ctx.fillStyle = GLYPH;
    if (OUTLINE) {
      ctx.strokeStyle = 'rgba(12,10,24,0.72)';
      ctx.lineWidth = OUTLINE;
      ctx.lineJoin = 'round';
      ctx.stroke(path);
    }
    ctx.fill(path);
    ctx.restore();
  }
  function whiteStroke(ctx, path, w, cap) {
    ctx.save();
    ctx.lineCap = cap || 'round';
    ctx.lineJoin = 'round';
    if (PASS === 0) {
      ctx.shadowColor = SHADOW.color;
      ctx.shadowBlur = SHADOW.blur;
      ctx.shadowOffsetY = SHADOW.oy;
      ctx.strokeStyle = SIL;
      ctx.lineWidth = w + 4 + OUTLINE;
      ctx.stroke(path);
      ctx.restore();
      return;
    }
    ctx.strokeStyle = GLYPH;
    ctx.lineWidth = w;
    if (OUTLINE) {
      ctx.strokeStyle = 'rgba(12,10,24,0.72)';
      ctx.lineWidth = w + OUTLINE;
      ctx.stroke(path);
      ctx.strokeStyle = GLYPH;
      ctx.lineWidth = w;
    }
    ctx.stroke(path);
    ctx.restore();
  }
  function dark(ctx, path) { if (PASS === 0) return; ctx.fillStyle = DARK; ctx.fill(path); }
  function darkStroke(ctx, path, w, cap) {
    if (PASS === 0) return;
    ctx.strokeStyle = DARK;
    ctx.lineWidth = w;
    ctx.lineCap = cap || 'round';
    ctx.lineJoin = 'round';
    ctx.stroke(path);
  }
  function softDark(ctx, path) { if (PASS === 0) return; ctx.fillStyle = DARK_SOFT; ctx.fill(path); }
  function pupil(ctx, cx, cy, r) { dark(ctx, circ(cx, cy, r)); }

  // reusable hourglass silhouette
  function hourglass(cx, cy, w, h) {
    var L = cx - w / 2, R = cx + w / 2, T = cy - h / 2, B = cy + h / 2;
    var neck = w * 0.16, capH = h * 0.11;
    var p = new Path2D();
    p.moveTo(L, T);
    p.lineTo(R, T);
    p.quadraticCurveTo(R + w * 0.03, T + capH * 0.7, R - w * 0.03, T + capH * 1.5);
    p.bezierCurveTo(R - w * 0.16, T + h * 0.31, cx + neck / 2 + w * 0.12, cy - h * 0.09, cx + neck / 2, cy);
    p.bezierCurveTo(cx + neck / 2 + w * 0.12, cy + h * 0.09, R - w * 0.16, B - h * 0.31, R - w * 0.03, B - capH * 1.5);
    p.quadraticCurveTo(R + w * 0.03, B - capH * 0.7, R, B);
    p.lineTo(L, B);
    p.quadraticCurveTo(L - w * 0.03, B - capH * 0.7, L + w * 0.03, B - capH * 1.5);
    p.bezierCurveTo(L + w * 0.16, B - h * 0.31, cx - neck / 2 - w * 0.12, cy + h * 0.09, cx - neck / 2, cy);
    p.bezierCurveTo(cx - neck / 2 - w * 0.12, cy - h * 0.09, L + w * 0.16, T + h * 0.31, L + w * 0.03, T + capH * 1.5);
    p.quadraticCurveTo(L - w * 0.03, T + capH * 0.7, L, T);
    p.closePath();
    return p;
  }

  // reusable feather, centred at (cx,cy), pointing up-right, scale 1 = ~155px long
  function feather(ctx, cx, cy, scale, rot) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rot === undefined ? 0 : rot);
    ctx.scale(scale, scale);
    // quill
    var quill = new Path2D();
    quill.moveTo(-24, 26);
    quill.lineTo(-82, 84);
    whiteStroke(ctx, quill, 12, 'round');
    // vane
    var vane = new Path2D();
    vane.moveTo(74, -80);
    vane.quadraticCurveTo(88, 35, -28, 32);
    vane.quadraticCurveTo(-21, -64, 74, -80);
    vane.closePath();
    white(ctx, vane);
    // shaft
    var shaft = new Path2D();
    shaft.moveTo(62, -68);
    shaft.lineTo(-18, 26);
    darkStroke(ctx, shaft, 8, 'round');
    ctx.restore();
  }

  // ------------------------------------------------------------------ icons
  var ICONS = [];
  function add(name, group, cat, draw) { ICONS.push({ name: name, group: group, cat: cat, draw: draw }); }

  // ============================ POWERS =====================================

  add('prophet_tally', 'power', 'violet', function (ctx) {
    var eye = almond(128, 96, 74, 42);
    var bars = union(
      rr(88, 152, 14, 54, 4), rr(122, 152, 14, 54, 4), rr(156, 152, 14, 54, 4)
    );
    var slash = new Path2D();
    slash.moveTo(74, 200); slash.lineTo(184, 156);
    white(ctx, union(eye, bars));
    whiteStroke(ctx, slash, 14, 'round');
    pupil(ctx, 128, 96, 25);
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.fill(circ(121, 89, 7));
  });

  add('foresight', 'power', 'violet', function (ctx) {
    var cy = 165, r0 = 86, r1 = 118;
    var rays = new Path2D();
    [50, 70, 90, 110, 130].forEach(function (deg) {
      var a = deg * Math.PI / 180;
      var dx = Math.cos(a), dy = -Math.sin(a);
      rays.addPath(taperRay(128 + dx * r0, cy + dy * r0, 128 + dx * r1, cy + dy * r1, 11, 3.5));
    });
    white(ctx, rays);
    white(ctx, almond(128, cy, 78, 44));
    pupil(ctx, 128, cy, 26);
  });

  add('nirvana', 'power', 'steel', function (ctx) {
    var shield = new Path2D();
    shield.moveTo(64, 72);
    shield.quadraticCurveTo(128, 44, 192, 72);
    shield.lineTo(192, 118);
    shield.quadraticCurveTo(192, 178, 128, 212);
    shield.quadraticCurveTo(64, 178, 64, 118);
    shield.closePath();
    white(ctx, shield);
    dark(ctx, almond(128, 124, 52, 32));
    ctx.fillStyle = GLYPH; ctx.fill(circ(128, 124, 15));
  });

  add('prophetic_study', 'power', 'violet', function (ctx) {
    white(ctx, almond(128, 97, 62, 36));
    pupil(ctx, 128, 97, 22);
    var book = new Path2D();
    book.moveTo(128, 161);
    book.lineTo(196, 145);
    book.quadraticCurveTo(205, 165, 198, 187);
    book.lineTo(128, 199);
    book.closePath();
    book.moveTo(128, 161);
    book.lineTo(60, 145);
    book.quadraticCurveTo(51, 165, 58, 187);
    book.lineTo(128, 199);
    book.closePath();
    white(ctx, book);
    var g = new Path2D(); g.moveTo(128, 165); g.lineTo(128, 196);
    darkStroke(ctx, g, 8, 'butt');
    var l1 = new Path2D(); l1.moveTo(148, 170); l1.lineTo(184, 160);
    var l2 = new Path2D(); l2.moveTo(108, 170); l2.lineTo(72, 160);
    darkStroke(ctx, l1, 6, 'round'); darkStroke(ctx, l2, 6, 'round');
  });

  add('cycle_of_prophecy', 'power', 'violet', function (ctx) {
    var a0 = -Math.PI * 0.36, a1 = Math.PI * 1.36;
    var loop = new Path2D();
    loop.arc(128, 128, 84, a0, a1, false);
    loop.arc(128, 128, 60, a1, a0, true);
    loop.closePath();
    white(ctx, loop);
    var ma = a1, midR = 72;
    var bx = 128 + Math.cos(ma) * midR, by = 128 + Math.sin(ma) * midR;
    var tx = -Math.sin(ma), ty = Math.cos(ma);
    var px = -ty, py = tx, w = 27;
    var head = poly([
      [bx + px * w, by + py * w],
      [bx + tx * 34, by + ty * 34],
      [bx - px * w, by - py * w]
    ]);
    white(ctx, head);
    white(ctx, almond(128, 128, 34, 19));
    pupil(ctx, 128, 128, 11);
  });

  add('pure_love_form', 'power', 'rose', function (ctx) {
    var h = new Path2D();
    h.moveTo(128, 206);
    h.bezierCurveTo(48, 154, 42, 100, 72, 72);
    h.bezierCurveTo(100, 48, 128, 68, 128, 94);
    h.bezierCurveTo(128, 68, 156, 48, 184, 72);
    h.bezierCurveTo(214, 100, 208, 154, 128, 206);
    h.closePath();
    white(ctx, h);
    dark(ctx, sparkle(172, 104, 26, 8));
  });

  add('delayed_echo', 'power', 'gold', function (ctx) {
    function card(cx, cy, rot, withArt) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      var c = rr(-46, -62, 92, 124, 14);
      white(ctx, c);
      ctx.strokeStyle = 'rgba(10,12,22,0.55)';
      ctx.lineWidth = 7;
      ctx.stroke(c);
      if (withArt) { dark(ctx, rr(-33, -49, 66, 52, 8)); dark(ctx, rr(-33, 14, 66, 9, 4)); dark(ctx, rr(-33, 31, 42, 9, 4)); }
      ctx.restore();
    }
    card(116, 104, -0.13, false);
    card(144, 152, 0.10, true);
  });

  add('delayed_scry', 'power', 'gold', function (ctx) {
    white(ctx, hourglass(128, 128, 136, 168));
    dark(ctx, poly([[92, 62], [164, 62], [128, 112]]));
    dark(ctx, almond(128, 176, 40, 22));
    ctx.fillStyle = GLYPH; ctx.fill(circ(128, 176, 13));
  });

  add('scry_might', 'power', 'crimson', function (ctx) {
    var body = union(
      rr(64, 88, 128, 104, 30),
      circ(80, 90, 20), circ(112, 86, 20), circ(144, 86, 20), circ(176, 90, 20)
    );
    white(ctx, body);
    [92, 124, 156].forEach(function (x) { dark(ctx, rr(x - 4, 96, 8, 54, 4)); });
    var thumb = rr(56, 144, 144, 46, 23);
    white(ctx, thumb);
    ctx.strokeStyle = 'rgba(10,12,22,0.50)';
    ctx.lineWidth = 7;
    ctx.stroke(thumb);
  });

  add('scry_agility', 'power', 'emerald', function (ctx) {
    feather(ctx, 128, 128, 1.0, 0);
  });

  add('judgement', 'power', 'violet', function (ctx) {
    white(ctx, circ(128, 52, 12));
    white(ctx, rr(56, 58, 144, 14, 7));
    white(ctx, rr(121, 58, 14, 144, 7));
    white(ctx, rr(84, 190, 88, 18, 9));
    var c1 = new Path2D(); c1.moveTo(72, 72); c1.lineTo(54, 122);
    var c2 = new Path2D(); c2.moveTo(72, 72); c2.lineTo(90, 122);
    var c3 = new Path2D(); c3.moveTo(184, 72); c3.lineTo(166, 122);
    var c4 = new Path2D(); c4.moveTo(184, 72); c4.lineTo(202, 122);
    whiteStroke(ctx, union(c1, c2, c3, c4), 9, 'round');
    var b1 = new Path2D();
    b1.moveTo(46, 118); b1.quadraticCurveTo(72, 180, 98, 118); b1.closePath();
    var b2 = new Path2D();
    b2.moveTo(158, 118); b2.quadraticCurveTo(184, 180, 210, 118); b2.closePath();
    white(ctx, union(b1, b2));
  });

  add('ember_boon', 'power', 'crimson', function (ctx) {
    var f = new Path2D();
    f.moveTo(134, 38);
    f.bezierCurveTo(146, 78, 190, 104, 190, 146);
    f.bezierCurveTo(190, 186, 162, 212, 128, 212);
    f.bezierCurveTo(94, 212, 66, 186, 66, 146);
    f.bezierCurveTo(66, 116, 92, 100, 106, 74);
    f.bezierCurveTo(112, 92, 120, 100, 126, 104);
    f.bezierCurveTo(128, 78, 130, 56, 134, 38);
    f.closePath();
    white(ctx, f);
    var inner = new Path2D();
    inner.moveTo(128, 124);
    inner.bezierCurveTo(140, 148, 156, 158, 156, 178);
    inner.bezierCurveTo(156, 198, 142, 208, 128, 208);
    inner.bezierCurveTo(114, 208, 100, 198, 100, 178);
    inner.bezierCurveTo(100, 158, 116, 148, 128, 124);
    inner.closePath();
    dark(ctx, inner);
  });

  add('granted_turn', 'power', 'gold', function (ctx) {
    white(ctx, hourglass(104, 128, 120, 148));
    dark(ctx, poly([[76, 74], [132, 74], [104, 118]]));
    var plus = plusPath(186, 90, 30, 9);
    white(ctx, plus);
    ctx.strokeStyle = 'rgba(10,12,22,0.55)';
    ctx.lineWidth = 7;
    ctx.lineJoin = 'round';
    ctx.stroke(plus);
  });

  add('insight', 'power', 'violet', function (ctx) {
    white(ctx, starPoly(128, 128, 96, 60, 12, -Math.PI / 2));
    dark(ctx, almond(128, 128, 52, 30));
    ctx.fillStyle = GLYPH; ctx.fill(circ(128, 128, 15));
  });

  add('purify', 'power', 'steel', function (ctx) {
    var d = new Path2D();
    d.moveTo(128, 40);
    d.bezierCurveTo(160, 90, 192, 126, 192, 158);
    d.bezierCurveTo(192, 194, 163, 214, 128, 214);
    d.bezierCurveTo(93, 214, 64, 194, 64, 158);
    d.bezierCurveTo(64, 126, 96, 90, 128, 40);
    d.closePath();
    white(ctx, d);
    dark(ctx, sparkle(128, 154, 44, 12));
    white(ctx, sparkle(188, 74, 20, 6));
  });

  add('exhaust_blast', 'power', 'crimson', function (ctx) {
    var ro = [89, 76, 93, 78, 87, 74, 91, 80, 86, 76, 89, 82];
    var ri = [46, 52, 43, 54, 48, 52, 45, 54, 46, 52, 50, 48];
    var pts = [];
    for (var i = 0; i < 24; i++) {
      var a = -Math.PI / 2 + i * Math.PI / 12;
      var r = (i % 2 === 0) ? ro[(i / 2) | 0] : ri[((i - 1) / 2) | 0];
      pts.push([128 + r * Math.cos(a), 128 + r * Math.sin(a)]);
    }
    white(ctx, poly(pts));
    dark(ctx, circ(128, 128, 40));
    ctx.fillStyle = GLYPH; ctx.fill(circ(128, 128, 17));
  });

  add('free_status', 'power', 'slate', function (ctx) {
    ctx.save();
    ctx.translate(100, 142);
    ctx.rotate(-0.45);
    var sh = new Path2D();
    sh.moveTo(0, 0);
    sh.lineTo(0, -34);
    sh.arc(34, -34, 34, Math.PI, Math.PI * 2, false);
    sh.lineTo(68, 0);
    whiteStroke(ctx, sh, 17, 'butt');
    ctx.restore();
    white(ctx, rr(76, 130, 104, 78, 16));
    dark(ctx, union(circ(128, 158, 15), rr(122, 156, 12, 32, 6)));
  });

  add('double_status', 'power', 'slate', function (ctx) {
    var c1 = new Path2D();
    c1.moveTo(52, 130); c1.lineTo(104, 84); c1.lineTo(156, 130);
    var c2 = new Path2D();
    c2.moveTo(52, 186); c2.lineTo(104, 140); c2.lineTo(156, 186);
    ctx.save();
    ctx.lineJoin = 'miter';
    ctx.miterLimit = 6;
    whiteStroke(ctx, union(c1, c2), 24, 'butt');
    ctx.restore();
    if (PASS === 0) return;
    ctx.save();
    ctx.fillStyle = GLYPH;
    ctx.font = 'bold 62px "Segoe UI", Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('2', 190, 158);
    ctx.restore();
  });

  add('status_draw', 'power', 'slate', function (ctx) {
    var card = rr(46, 72, 82, 116, 12);
    white(ctx, card);
    dark(ctx, rr(58, 84, 58, 92, 7));
    var shaft = new Path2D();
    shaft.moveTo(118, 130); shaft.lineTo(172, 130);
    whiteStroke(ctx, shaft, 20, 'butt');
    white(ctx, poly([[166, 104], [210, 130], [166, 156]]));
  });

  add('shared_might', 'power', 'crimson', function (ctx) {
    var A = circ(104, 128, 44), B = circ(152, 128, 44);
    function ringStroke(p) {
      ctx.save();
      if (PASS === 0) {
        ctx.shadowColor = 'rgba(0,0,0,0.45)';
        ctx.shadowBlur = 10;
        ctx.shadowOffsetY = 4;
      }
      ctx.strokeStyle = 'rgba(10,12,22,0.88)';
      ctx.lineWidth = 31;
      ctx.stroke(p);
      ctx.shadowColor = 'transparent';
      ctx.strokeStyle = GLYPH;
      ctx.lineWidth = 19;
      ctx.stroke(p);
      ctx.restore();
    }
    ringStroke(A);
    ringStroke(B);
    // redraw the lower half of A over B so the rings genuinely interlock
    ctx.save();
    ctx.beginPath(); ctx.arc(104, 128, 60, 0, Math.PI * 2); ctx.clip();
    ctx.beginPath(); ctx.arc(152, 128, 60, 0, Math.PI * 2); ctx.clip();
    ctx.beginPath(); ctx.rect(0, 128, 256, 128); ctx.clip();
    ctx.strokeStyle = 'rgba(10,12,22,0.88)';
    ctx.lineWidth = 31;
    ctx.stroke(A);
    ctx.strokeStyle = GLYPH;
    ctx.lineWidth = 19;
    ctx.stroke(A);
    ctx.restore();
  });

  add('steady_agility', 'power', 'emerald', function (ctx) {
    var shield = new Path2D();
    shield.moveTo(58, 80);
    shield.quadraticCurveTo(128, 50, 198, 80);
    shield.lineTo(198, 124);
    shield.quadraticCurveTo(198, 180, 128, 212);
    shield.quadraticCurveTo(58, 180, 58, 124);
    shield.closePath();
    white(ctx, shield);
    var inset = new Path2D();
    inset.moveTo(78, 92);
    inset.quadraticCurveTo(128, 70, 178, 92);
    inset.lineTo(178, 128);
    inset.quadraticCurveTo(178, 172, 128, 196);
    inset.quadraticCurveTo(78, 172, 78, 128);
    inset.closePath();
    dark(ctx, inset);
    var vane = new Path2D();
    vane.moveTo(128, 88);
    vane.quadraticCurveTo(184, 133, 128, 182);
    vane.quadraticCurveTo(88, 133, 128, 88);
    vane.closePath();
    white(ctx, vane);
    var shaft = new Path2D();
    shaft.moveTo(128, 94); shaft.lineTo(128, 186);
    darkStroke(ctx, shaft, 7, 'round');
    var quill = new Path2D();
    quill.moveTo(128, 176); quill.lineTo(128, 200);
    whiteStroke(ctx, quill, 9, 'round');
  });

  // ============================ RELICS =====================================

  add('agate_potion_belt', 'relic', 'bronze', function (ctx) {
    white(ctx, rr(48, 146, 160, 40, 13));
    var buckle = rr(104, 138, 48, 56, 11);
    white(ctx, buckle);
    dark(ctx, rr(116, 150, 24, 32, 6));
    [82, 174].forEach(function (cx) {
      white(ctx, flaskPath(cx, 138));
      dark(ctx, circ(cx, 122, 11));
    });
  });

  add('foresight_charm', 'relic', 'bronze', function (ctx) {
    whiteStroke(ctx, circ(128, 64, 16), 10, 'round');
    ctx.save();
    ctx.translate(128, 146);
    ctx.rotate(Math.PI / 4);
    white(ctx, rr(-46, -46, 92, 92, 16));
    dark(ctx, rr(-35, -35, 70, 70, 12));
    ctx.restore();
    white(ctx, almond(128, 146, 30, 17));
    pupil(ctx, 128, 146, 10);
  });

  add('prophets_bracelet', 'relic', 'bronze', function (ctx) {
    var p = new Path2D();
    p.ellipse(128, 130, 82, 66, 0, 0, Math.PI * 2, false);
    p.moveTo(128 + 52, 130);
    p.ellipse(128, 130, 52, 42, 0, 0, Math.PI * 2, true);
    p.closePath();
    white(ctx, p);
    dark(ctx, almond(128, 130, 56, 26));
    ctx.fillStyle = GLYPH; ctx.fill(circ(128, 130, 15));
  });

  add('prophets_eye', 'relic', 'bronze', function (ctx) {
    white(ctx, almond(128, 128, 84, 54));
    dark(ctx, almond(128, 128, 64, 40));
    ctx.fillStyle = GLYPH; ctx.fill(circ(128, 128, 28));
    pupil(ctx, 128, 128, 14);
    ctx.fillStyle = GLYPH; ctx.fill(circ(120, 118, 6));
  });

  add('prophets_eye_plus', 'relic', 'bronzeBright', function (ctx) {
    if (PASS === 0) return; // glow + gradient sphere: paint once only
    ctx.save();
    ctx.strokeStyle = 'rgba(255,222,130,0.40)';
    ctx.lineWidth = 10;
    ctx.stroke(circ(128, 128, 100));
    ctx.restore();
    white(ctx, almond(128, 128, 84, 54));
    dark(ctx, almond(128, 128, 64, 40));
    ctx.fillStyle = GLYPH; ctx.fill(circ(128, 128, 28));
    pupil(ctx, 128, 128, 14);
    ctx.fillStyle = GLYPH; ctx.fill(circ(120, 118, 6));
    var plus = plusPath(198, 68, 28, 9);
    white(ctx, plus);
    ctx.strokeStyle = 'rgba(10,12,22,0.55)';
    ctx.lineWidth = 7;
    ctx.lineJoin = 'round';
    ctx.stroke(plus);
  });

  // ============================ ENERGY ORB =================================

  add('energy_yetannia', 'orb', 'orb', function (ctx) {
    if (PASS === 0) return; // the orb paints gradients directly; one pass only
    // soft outer halo
    var halo = ctx.createRadialGradient(128, 128, 40, 128, 128, 128);
    halo.addColorStop(0, 'rgba(186,150,255,0.42)');
    halo.addColorStop(0.62, 'rgba(150,110,240,0.22)');
    halo.addColorStop(1, 'rgba(120,90,220,0)');
    ctx.fillStyle = halo;
    ctx.fillRect(0, 0, 256, 256);
    // sphere
    var g = ctx.createRadialGradient(100, 94, 10, 128, 128, 122);
    g.addColorStop(0, '#efe6ff');
    g.addColorStop(0.16, '#c9a8ff');
    g.addColorStop(0.48, '#7a5cd6');
    g.addColorStop(0.80, '#432b8f');
    g.addColorStop(1, '#241356');
    ctx.fillStyle = g;
    ctx.fill(circ(128, 128, 118));
    // gold rim
    var rim = ctx.createLinearGradient(0, 20, 0, 236);
    rim.addColorStop(0, '#ffe9a0');
    rim.addColorStop(0.5, '#f1c40f');
    rim.addColorStop(1, '#a97f0a');
    ctx.strokeStyle = rim;
    ctx.lineWidth = 7;
    ctx.beginPath(); ctx.arc(128, 128, 114.5, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = 'rgba(255,220,140,0.35)';
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(128, 128, 98, 0, Math.PI * 2); ctx.stroke();
    // inner gold glow
    var glow = ctx.createRadialGradient(128, 128, 10, 128, 128, 96);
    glow.addColorStop(0, 'rgba(255,214,120,0.30)');
    glow.addColorStop(1, 'rgba(255,214,120,0)');
    ctx.fillStyle = glow;
    ctx.fill(circ(128, 128, 96));
    // eye motif
    ctx.save();
    ctx.shadowColor = 'rgba(20,10,50,0.55)';
    ctx.shadowBlur = 14;
    ctx.shadowOffsetY = 4;
    ctx.fillStyle = '#ffe9a8';
    ctx.fill(almond(128, 128, 60, 35));
    ctx.restore();
    ctx.fillStyle = '#2a1a5e';
    ctx.fill(circ(128, 128, 19));
    ctx.fillStyle = '#ffffff';
    ctx.fill(circ(120, 119, 7));
    // specular highlight
    ctx.save();
    ctx.translate(92, 76);
    ctx.rotate(-0.55);
    ctx.beginPath();
    ctx.ellipse(0, 0, 36, 20, 0, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,255,255,0.34)';
    ctx.fill();
    ctx.restore();
  });

  window.ICONS = ICONS;
  window.__COLORS = {
    violet: ['#6b4fc8', '#3b2a7a'],
    crimson: ['#c0392b', '#7b2018'],
    emerald: ['#27ae60', '#14532d'],
    steel: ['#2980b9', '#154360'],
    slate: ['#7f8c8d', '#3b4247'],
    gold: ['#e5b60e', '#7a6000'],
    rose: ['#d1497f', '#5c1a46'],
    bronze: ['#d9a441', '#7a4f16'],
    bronzeBright: ['#ffd76a', '#a9761c'],
    orb: ['#6b4fc8', '#3b2a7a']
  };
  window.__OUTLINE_CATS = { gold: 1, bronze: 1, bronzeBright: 1 };
  // frame first, then the glyph in two passes (silhouette+shadow, then the paint)
  window.__DRAW_ICON = function (ctx, def, colors, outlineCats) {
    OUTLINE = outlineCats[def.cat] ? 4 : 0;
    PASS = 1;
    ctx.clearRect(0, 0, 256, 256);
    if (def.cat !== 'orb') {
      var c = colors[def.cat];
      var g = ctx.createLinearGradient(0, 0, 0, 256);
      g.addColorStop(0, c[0]);
      g.addColorStop(1, c[1]);
      ctx.fillStyle = g;
      ctx.fill(rr(0, 0, 256, 256, 56));
      var gl = ctx.createLinearGradient(0, 0, 0, 150);
      gl.addColorStop(0, 'rgba(255,255,255,0.16)');
      gl.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = gl;
      ctx.fill(rr(0, 0, 256, 256, 56));
      ctx.strokeStyle = 'rgba(255,255,255,0.30)';
      ctx.lineWidth = 2.5;
      ctx.stroke(rr(5, 5, 246, 246, 52));
      ctx.strokeStyle = 'rgba(0,0,0,0.40)';
      ctx.lineWidth = 4;
      ctx.stroke(rr(2, 2, 252, 252, 55));
    }
    PASS = 0;
    def.draw(ctx);
    PASS = 1;
    def.draw(ctx);
    PASS = 1;
    OUTLINE = 0;
  };
})();
