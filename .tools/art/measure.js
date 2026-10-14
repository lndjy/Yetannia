// Style measurement for StS2 icons.
//
// Everything here exists to answer one question mechanically: "does this set of PNGs have the
// same palette / value structure / edge density / silhouette as the base game's own icons?"
//
// Measures (all computed identically for vanilla and for the mod, so the comparison is fair):
//   palette      distinct 5-bit RGB buckets, top-colour share, hue histogram over 24 bins,
//                mean saturation, hue-bin count above 1%, chroma spread
//   value        mean/median/std luma, p10..p90, dark/mid/light/highlight fractions,
//                near-black outline fraction
//   edges        sobel gradient density: whole canvas (incl. silhouette boundary) and
//                interior-only (busy-ness of the shapes themselves)
//   silhouette   coverage, mean alpha, bbox fill, corner/border/centre alpha,
//                IoU against ideal rounded-square / circle / square of equal area,
//                8-bin radial alpha profile
//   contrast     dark-mass luma vs highlight luma, flat-white-ink fraction,
//                highlight chroma (vanilla highlights are tinted, not white)
//
// Usage:
//   node measure.js <file-or-dir> [...] [--label NAME] [--json out.json] [--quiet]
'use strict';
const fs = require('fs');
const path = require('path');
const { decode } = require('../icongen/pngread.js');

const COVER_A = 32;    // alpha at/above which a pixel counts as "covered"
const INK_A = 128;     // alpha at/above which a pixel counts as "solid ink"

function luma(r, g, b) { return 0.299 * r + 0.587 * g + 0.114 * b; }

// ---------------------------------------------------------------- silhouette models
function roundedRectMask(n, radiusFrac, area) {
  const m = new Uint8Array(n * n);
  const r = Math.max(1, radiusFrac * n);
  let inside = 0;
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const cx = Math.min(Math.max(x + 0.5, r), n - r);
      const cy = Math.min(Math.max(y + 0.5, r), n - r);
      const d = Math.hypot(x + 0.5 - cx, y + 0.5 - cy);
      if (d <= r) { m[y * n + x] = 1; inside++; }
    }
  }
  // scale to the requested area by shrinking toward the centre
  const target = Math.round(area);
  if (inside === 0) return m;
  const s = Math.sqrt(target / inside);
  const out = new Uint8Array(n * n);
  const c = n / 2;
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const sx = Math.round((x + 0.5 - c) / s + c - 0.5);
      const sy = Math.round((y + 0.5 - c) / s + c - 0.5);
      if (sx >= 0 && sy >= 0 && sx < n && sy < n && m[sy * n + sx]) out[y * n + x] = 1;
    }
  }
  return out;
}
function circleMask(n, area) {
  const m = new Uint8Array(n * n);
  const r = Math.sqrt(area / Math.PI);
  const c = n / 2;
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    if (Math.hypot(x + 0.5 - c, y + 0.5 - c) <= r) m[y * n + x] = 1;
  }
  return m;
}
function squareMask(n, area) {
  const m = new Uint8Array(n * n);
  const s = Math.sqrt(area);
  const x0 = Math.round((n - s) / 2), y0 = Math.round((n - s) / 2);
  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    if (x >= x0 && y >= y0 && x < x0 + s && y < y0 + s) m[y * n + x] = 1;
  }
  return m;
}
function iou(a, b) {
  let inter = 0, uni = 0;
  for (let i = 0; i < a.length; i++) {
    const x = a[i], y = b[i];
    if (x && y) inter++;
    if (x || y) uni++;
  }
  return uni ? inter / uni : 0;
}

// ---------------------------------------------------------------- main measure
function measure(file) {
  const img = decode(file);
  const { width: W, height: H, channels: C, pixels: P } = img;
  const N = W * H;
  const get = (x, y) => {
    const i = (y * W + x) * C;
    return [P[i], P[i + 1], P[i + 2], C === 4 ? P[i + 3] : 255];
  };

  // ---- pass 1: raster stats
  const colors = new Map();          // 5-bit RGB bucket -> count
  const hues = new Float64Array(24);
  let hueWeight = 0;
  let satSum = 0, satN = 0;
  const lumaHist = new Float64Array(64);
  let covered = 0, solid = 0, sumAlpha = 0;
  let lumSum = 0, lumSum2 = 0;
  const lumList = [];
  // sobel accumulators
  let edgeAll = 0, edgeInk = 0, edgeInkDen = 0;
  // dark mass / highlight mass
  let darkSum = 0, darkN = 0, hiSum = 0, hiN = 0;
  let flatWhite = 0, hiChromaSum = 0;
  let minX = W, minY = H, maxX = -1, maxY = -1;
  // radial profile
  const radial = new Float64Array(8), radialN = new Float64Array(8);
  const lum = new Float64Array(N);

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      const [r, g, b, a] = get(x, y);
      const L = luma(r, g, b);
      lum[i] = L;
      sumAlpha += a;
      const cov = a >= COVER_A;
      if (cov) {
        covered++;
        if (x < minX) minX = x; if (x > maxX) maxX = x;
        if (y < minY) minY = y; if (y > maxY) maxY = y;
        const key = ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3);
        colors.set(key, (colors.get(key) || 0) + 1);
        // HSV-ish
        const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
        const chroma = mx - mn;
        const sat = mx === 0 ? 0 : chroma / mx;
        satSum += sat; satN++;
        if (chroma > 8) {
          let hdeg;
          if (mx === r) hdeg = 60 * (((g - b) / chroma) % 6);
          else if (mx === g) hdeg = 60 * ((b - r) / chroma + 2);
          else hdeg = 60 * ((r - g) / chroma + 4);
          if (hdeg < 0) hdeg += 360;
          const bin = Math.floor(hdeg / 15) % 24;
          const wgt = (a / 255) * (chroma / 255);
          hues[bin] += wgt; hueWeight += wgt;
        }
        lumaHist[Math.min(63, Math.floor(L / 4))]++;
        lumSum += L; lumSum2 += L * L;
        lumList.push(L);
        if (L < 0.10 * 255) darkSum += L, darkN++;
        if (a >= INK_A && L < 0.10 * 255) darkSum = darkSum; // (kept simple: dark mass below)
        if (L > 0.72 * 255) { hiSum += L; hiN++; hiChromaSum += chroma; }
        if (L > 0.88 * 255 && chroma < 26) flatWhite++;
        // radial
        const dx = (x + 0.5) / W - 0.5, dy = (y + 0.5) / H - 0.5;
        const rn = Math.min(7, Math.floor(Math.hypot(dx, dy) / 0.7071 * 8));
        radial[rn] += a / 255; radialN[rn]++;
      } else {
        lum[i] = 0;
      }
    }
  }

  // ---- pass 2: sobel (needs neighbours)
  for (let y = 1; y < H - 1; y++) {
    for (let x = 1; x < W - 1; x++) {
      const i = y * W + x;
      const gx = -lum[i - W - 1] - 2 * lum[i - 1] - lum[i + W - 1]
        + lum[i - W + 1] + 2 * lum[i + 1] + lum[i + W + 1];
      const gy = -lum[i - W - 1] - 2 * lum[i - W] - lum[i - W + 1]
        + lum[i + W - 1] + 2 * lum[i + W] + lum[i + W + 1];
      const mag = Math.hypot(gx, gy) / (4 * 255);
      if (mag > 0.10) edgeAll++;
      const a = P[i * C + 3];
      const aN = P[(i - 1) * C + 3] >= INK_A && P[(i + 1) * C + 3] >= INK_A
        && P[(i - W) * C + 3] >= INK_A && P[(i + W) * C + 3] >= INK_A;
      if (a >= INK_A && aN) { edgeInkDen++; if (mag > 0.10) edgeInk++; }
    }
  }

  // ---- value structure
  lumList.sort((a, b) => a - b);
  const q = (p) => lumList.length ? lumList[Math.min(lumList.length - 1, Math.floor(p * lumList.length))] : 0;
  const mean = covered ? lumSum / covered : 0;
  const std = covered ? Math.sqrt(Math.max(0, lumSum2 / covered - mean * mean)) : 0;
  const bands = { dark: 0, mid: 0, light: 0, highlight: 0, nearBlack: 0 };
  for (const L of lumList) {
    if (L < 0.20 * 255) bands.dark++;
    if (L >= 0.20 * 255 && L < 0.55 * 255) bands.mid++;
    if (L >= 0.55 * 255 && L < 0.80 * 255) bands.light++;
    if (L >= 0.80 * 255) bands.highlight++;
    if (L < 0.09 * 255) bands.nearBlack++;
  }
  const pct = (n) => covered ? +(100 * n / covered).toFixed(2) : 0;

  // ---- palette
  const sorted = [...colors.entries()].sort((a, b) => b[1] - a[1]);
  const hueTotal = hueWeight || 1;
  const hueBins = [...hues].map(v => +(100 * v / hueTotal).toFixed(2));
  const hueFamilies = hueBins.filter(v => v >= 1.0).length;

  // ---- silhouette
  const bboxW = maxX < 0 ? 0 : maxX - minX + 1, bboxH = maxY < 0 ? 0 : maxY - minY + 1;
  const bin = new Uint8Array(N);
  for (let i = 0; i < N; i++) bin[i] = P[i * C + 3] >= COVER_A ? 1 : 0;
  const area = covered;
  const rr = roundedRectMask(W, 0.24, area);
  const ci = circleMask(W, area);
  const sq = squareMask(W, area);
  const corner = Math.max(4, Math.round(W * 0.25));
  let cornerSum = 0, cornerN = 0;
  for (const [cx0, cy0] of [[0, 0], [W - corner, 0], [0, H - corner], [W - corner, H - corner]]) {
    for (let y = cy0; y < cy0 + corner; y++) for (let x = cx0; x < cx0 + corner; x++) {
      cornerSum += P[(y * W + x) * C + 3] / 255; cornerN++;
    }
  }
  const ring = Math.max(1, Math.round(W / 32));
  let ringSum = 0, ringN = 0, centreSum = 0, centreN = 0;
  const q0 = Math.round(W * 0.25), q1 = Math.round(W * 0.75);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const a = P[(y * W + x) * C + 3] / 255;
      if (x < ring || y < ring || x >= W - ring || y >= H - ring) { ringSum += a; ringN++; }
      if (x >= q0 && x < q1 && y >= q0 && y < q1) { centreSum += a; centreN++; }
    }
  }

  // ---- pass 3: rim / outline / perimeter
  // rim pixel = covered pixel with a 4-neighbour that is not covered -> the silhouette boundary
  let rimN = 0, rimLumaSum = 0, rimDark = 0;
  let rim2N = 0, rim2LumaSum = 0;          // one pixel further in
  let perim = 0;
  let softAlpha = 0;
  for (let y = 1; y < H - 1; y++) {
    for (let x = 1; x < W - 1; x++) {
      const i = y * W + x;
      const a = P[i * C + 3];
      if (a > 0 && a < 255) softAlpha++;
      const cov = a >= COVER_A;
      if (!cov) continue;
      const nCov = (P[(i - 1) * C + 3] >= COVER_A ? 1 : 0) + (P[(i + 1) * C + 3] >= COVER_A ? 1 : 0)
        + (P[(i - W) * C + 3] >= COVER_A ? 1 : 0) + (P[(i + W) * C + 3] >= COVER_A ? 1 : 0);
      if (nCov < 4) { perim += 4 - nCov; }
      if (nCov < 4) { rimN++; rimLumaSum += lum[i]; if (lum[i] < 0.10 * 255) rimDark++; }
      else {
        // interior pixel adjacent to a rim pixel?
        const inner = (P[(i - 1) * C + 3] >= COVER_A && P[(i - 2) * C + 3] < COVER_A)
          || (P[(i + 1) * C + 3] >= COVER_A && P[(i + 2) * C + 3] < COVER_A)
          || (P[(i - W) * C + 3] >= COVER_A && P[(i - 2 * W) * C + 3] < COVER_A)
          || (P[(i + W) * C + 3] >= COVER_A && P[(i + 2 * W) * C + 3] < COVER_A);
        if (inner) { rim2N++; rim2LumaSum += lum[i]; }
      }
    }
  }
  const circularity = perim > 0 ? Math.min(1.5, 4 * Math.PI * covered / (perim * perim)) : 0;

  // ---- pass 4: inward band profile
  // Erode the silhouette repeatedly; ring k = layer k-1 minus layer k. Tells us how thick the
  // near-black ink band is (vanilla power icons are outlined in ~black, several px thick).
  let layer = bin;
  const bandLuma = [], bandNearBlack = [], bandW = [];
  for (let k = 0; k < 6; k++) {
    const next = new Uint8Array(N);
    let n = 0, ls = 0, nb = 0;
    for (let y = 1; y < H - 1; y++) {
      for (let x = 1; x < W - 1; x++) {
        const i = y * W + x;
        if (!layer[i]) continue;
        if (layer[i - 1] && layer[i + 1] && layer[i - W] && layer[i + W]) { next[i] = 1; continue; }
        n++; ls += lum[i];
        if (lum[i] < 0.10 * 255) nb++;
      }
    }
    bandLuma.push(n ? +(ls / n / 255).toFixed(3) : null);
    bandNearBlack.push(n ? +(100 * nb / n).toFixed(1) : null);
    bandW.push(n);
    layer = next;
  }

  return {
    file: path.basename(file), W, H,
    bytes: fs.statSync(file).size,
    coveragePct: +(100 * covered / N).toFixed(2),
    solidPct: +(100 * solid / N).toFixed(2),
    meanAlphaPct: +(100 * sumAlpha / N / 255).toFixed(2),
    bbox: { w: bboxW, h: bboxH, fillPct: +(100 * bboxW * bboxH / N).toFixed(1) },
    cornerAlphaPct: +(100 * cornerSum / cornerN).toFixed(2),
    ringAlphaPct: +(100 * ringSum / ringN).toFixed(2),
    centreAlphaPct: +(100 * centreSum / centreN).toFixed(2),
    radial: [...radial].map((v, i) => +(100 * v / Math.max(1, radialN[i])).toFixed(1)),
    shapeIoU: {
      roundedSquare: +iou(bin, rr).toFixed(3),
      circle: +iou(bin, ci).toFixed(3),
      square: +iou(bin, sq).toFixed(3),
    },
    outline: {
      rimPctOfCovered: covered ? +(100 * rimN / covered).toFixed(2) : 0,
      rimLuma: rimN ? +(rimLumaSum / rimN / 255).toFixed(3) : 0,
      rimNearBlackPct: rimN ? +(100 * rimDark / rimN).toFixed(1) : 0,
      innerRimLuma: rim2N ? +(rim2LumaSum / rim2N / 255).toFixed(3) : 0,
      softAlphaPct: +(100 * softAlpha / N).toFixed(2),
      perimeterPx: perim,
      circularity: +circularity.toFixed(3),
      bandLuma: bandLuma,
      bandNearBlackPct: bandNearBlack,
      bandWidthPx: bandW,
    },
    palette: {
      distinctColors: colors.size,
      top1Pct: covered ? +(100 * sorted[0][1] / covered).toFixed(2) : 0,
      top5Pct: covered ? +(100 * sorted.slice(0, 5).reduce((s, e) => s + e[1], 0) / covered).toFixed(2) : 0,
      hueBinsAbove1Pct: hueFamilies,
      hueHistogram: hueBins,
      meanSaturation: satN ? +(satSum / satN).toFixed(3) : 0,
      topColors: sorted.slice(0, 8).map(([k, v]) => ({
        rgb: [((k >> 10) & 31) << 3, ((k >> 5) & 31) << 3, (k & 31) << 3],
        pct: +(100 * v / covered).toFixed(2),
      })),
    },
    value: {
      mean: +(mean / 255).toFixed(3),
      median: +(q(0.5) / 255).toFixed(3),
      std: +(std / 255).toFixed(3),
      p10: +(q(0.10) / 255).toFixed(3), p25: +(q(0.25) / 255).toFixed(3),
      p75: +(q(0.75) / 255).toFixed(3), p90: +(q(0.90) / 255).toFixed(3),
      darkPct: pct(bands.dark), midPct: pct(bands.mid),
      lightPct: pct(bands.light), highlightPct: pct(bands.highlight),
      nearBlackPct: pct(bands.nearBlack),
    },
    edges: {
      allPct: +(100 * edgeAll / N).toFixed(2),
      interiorPct: edgeInkDen ? +(100 * edgeInk / edgeInkDen).toFixed(2) : 0,
    },
    contrast: {
      darkMassLuma: darkN ? +(darkSum / darkN / 255).toFixed(3) : 0,
      highlightLuma: hiN ? +(hiSum / hiN / 255).toFixed(3) : 0,
      deltaLuma: hiN && darkN ? +((hiSum / hiN - darkSum / darkN) / 255).toFixed(3) : 0,
      flatWhiteInkPct: pct(flatWhite),
      highlightChroma: hiN ? +(hiChromaSum / hiN).toFixed(1) : 0,
    },
  };
}

// ---------------------------------------------------------------- aggregation
const SUM_KEYS = [
  ['coveragePct'], ['meanAlphaPct'], ['bbox', 'fillPct'], ['cornerAlphaPct'], ['ringAlphaPct'],
  ['centreAlphaPct'], ['shapeIoU', 'roundedSquare'], ['shapeIoU', 'circle'], ['shapeIoU', 'square'],
  ['outline', 'rimPctOfCovered'], ['outline', 'rimLuma'], ['outline', 'rimNearBlackPct'],
  ['outline', 'innerRimLuma'], ['outline', 'softAlphaPct'], ['outline', 'circularity'],
  ['palette', 'distinctColors'], ['palette', 'top1Pct'], ['palette', 'top5Pct'],
  ['palette', 'hueBinsAbove1Pct'], ['palette', 'meanSaturation'],
  ['value', 'mean'], ['value', 'median'], ['value', 'std'],
  ['value', 'p10'], ['value', 'p25'], ['value', 'p75'], ['value', 'p90'],
  ['value', 'darkPct'], ['value', 'midPct'], ['value', 'lightPct'], ['value', 'highlightPct'],
  ['value', 'nearBlackPct'],
  ['edges', 'allPct'], ['edges', 'interiorPct'],
  ['contrast', 'darkMassLuma'], ['contrast', 'highlightLuma'], ['contrast', 'deltaLuma'],
  ['contrast', 'flatWhiteInkPct'], ['contrast', 'highlightChroma'],
];
function dig(o, p) { return p.reduce((a, k) => (a == null ? a : a[k]), o); }

function aggregate(rows) {
  const out = { n: rows.length };
  for (const p of SUM_KEYS) {
    const vals = rows.map(r => dig(r, p)).filter(v => typeof v === 'number' && isFinite(v));
    if (!vals.length) { out[p.join('.')] = null; continue; }
    vals.sort((a, b) => a - b);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    out[p.join('.')] = {
      mean: +mean.toFixed(3),
      median: +vals[Math.floor(vals.length / 2)].toFixed(3),
      p10: +vals[Math.floor(vals.length * 0.10)].toFixed(3),
      p90: +vals[Math.min(vals.length - 1, Math.floor(vals.length * 0.90))].toFixed(3),
    };
  }
  // pooled hue histogram
  const hue = new Array(24).fill(0);
  for (const r of rows) for (let i = 0; i < 24; i++) hue[i] += r.palette.hueHistogram[i];
  const tot = hue.reduce((a, b) => a + b, 0) || 1;
  out.hueHistogram = hue.map(v => +(100 * v / tot).toFixed(2));
  out.hueBinsAbove1PctPooled = out.hueHistogram.filter(v => v >= 1).length;
  return out;
}

function walk(p, acc) {
  const st = fs.statSync(p);
  if (st.isDirectory()) { for (const f of fs.readdirSync(p).sort()) walk(path.join(p, f), acc); }
  else if (p.toLowerCase().endsWith('.png')) acc.push(p);
  return acc;
}

if (require.main === module) {
  const argv = process.argv.slice(2);
  const inputs = [];
  let jsonOut = null;
  const quiet = argv.includes('--quiet');
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--json') { jsonOut = argv[++i]; continue; }
    if (argv[i] === '--label') { i++; continue; }
    if (argv[i] === '--quiet') continue;
    inputs.push(argv[i]);
  }
  const files = [];
  for (const i of inputs) walk(i, files);
  const rows = files.map(measure);
  const agg = aggregate(rows);
  if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify({ aggregate: agg, rows }, null, 2), 'utf8');
  if (!quiet) {
    console.log('files: ' + rows.length);
    for (const r of rows) {
      console.log('  ' + r.file.padEnd(34) +
        ' cov=' + String(r.coveragePct).padStart(6) +
        ' aMean=' + String(r.meanAlphaPct).padStart(6) +
        ' L=' + String(r.value.mean).padStart(5) +
        ' Lsd=' + String(r.value.std).padStart(5) +
        ' dark=' + String(r.value.darkPct).padStart(5) +
        ' hi=' + String(r.value.highlightPct).padStart(5) +
        ' cols=' + String(r.palette.distinctColors).padStart(5) +
        ' edge=' + String(r.edges.allPct).padStart(5) +
        ' iouRR=' + String(r.shapeIoU.roundedSquare).padStart(5));
    }
    console.log('\nAGGREGATE (n=' + agg.n + ')');
    for (const k of Object.keys(agg)) {
      if (k === 'n' || k === 'hueHistogram') continue;
      const v = agg[k];
      console.log('  ' + k.padEnd(36) + ' mean=' + String(v.mean).padStart(8) +
        ' median=' + String(v.median).padStart(8) + ' p10=' + String(v.p10).padStart(8) + ' p90=' + String(v.p90).padStart(8));
    }
    console.log('  hueHistogram(24x15deg, % of chroma): ' + agg.hueHistogram.join(' '));
  }
  if (jsonOut) console.log('json -> ' + jsonOut);
}

module.exports = { measure, aggregate, walk, luma };
