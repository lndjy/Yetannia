// Side-by-side style comparison: vanilla reference sets vs a produced set.
//
//   node compare.js --a vanilla.power.64 --b mine.power.64 [--a2 ... --b2 ...]
//
// Reads the JSON written by measure.js (`{aggregate, rows}`) out of .tools/art/stats and prints
// a table with the delta, so "did it get closer to the base game" is a number, not an opinion.
'use strict';
const fs = require('fs');
const path = require('path');

const STATS = path.join(__dirname, 'stats');

// The measures that actually decide whether it reads as StS2 art, in priority order.
const KEYS = [
  ['coveragePct',                'alpha coverage % (alpha>=32)'],
  ['meanAlphaPct',               'mean alpha %'],
  ['bbox.fillPct',               'content bbox fill %'],
  ['cornerAlphaPct',             'mean alpha in 4 corner blocks %'],
  ['ringAlphaPct',               'mean alpha in outer ring %'],
  ['centreAlphaPct',             'mean alpha in centre box %'],
  ['shapeIoU.roundedSquare',     'IoU vs ideal rounded square'],
  ['shapeIoU.circle',            'IoU vs ideal circle'],
  ['shapeIoU.square',            'IoU vs ideal square'],
  ['outline.circularity',        'silhouette circularity'],
  ['outline.rimPctOfCovered',    'rim pixels % of covered'],
  ['outline.rimLuma',            'luma of silhouette rim (0=black ink)'],
  ['outline.rimNearBlackPct',    'rim pixels that are near-black %'],
  ['outline.innerRimLuma',       'luma one px inside the rim'],
  ['outline.softAlphaPct',       'soft (partial) alpha % of canvas'],
  ['palette.distinctColors',     'distinct 5-bit colours'],
  ['palette.top1Pct',            'share of most common colour %'],
  ['palette.top5Pct',            'share of top-5 colours %'],
  ['palette.hueBinsAbove1Pct',   'hue families above 1%'],
  ['palette.meanSaturation',     'mean saturation'],
  ['value.mean',                 'mean luma'],
  ['value.median',               'median luma'],
  ['value.std',                  'luma std dev'],
  ['value.p10',                  'luma p10'],
  ['value.p25',                  'luma p25'],
  ['value.p75',                  'luma p75'],
  ['value.p90',                  'luma p90'],
  ['value.darkPct',              'luma<0.20 %'],
  ['value.midPct',               'luma 0.20-0.55 %'],
  ['value.lightPct',             'luma 0.55-0.80 %'],
  ['value.highlightPct',         'luma>0.80 %'],
  ['value.nearBlackPct',         'luma<0.09 % (outline ink)'],
  ['edges.allPct',               'sobel edge density % (whole canvas)'],
  ['edges.interiorPct',          'sobel edge density % (interior only)'],
  ['contrast.darkMassLuma',      'dark mass luma'],
  ['contrast.highlightLuma',     'highlight mass luma'],
  ['contrast.deltaLuma',         'highlight - dark luma'],
  ['contrast.flatWhiteInkPct',   'flat white ink % of covered'],
  ['contrast.highlightChroma',   'highlight chroma (0=grey)'],
];

function load(name) {
  const p = path.join(STATS, name + '.json');
  if (!fs.existsSync(p)) throw new Error('no stats for ' + name + ' (' + p + ')');
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function argPairs(argv) {
  const pairs = [];
  let cur = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--a') { cur = { a: argv[++i] }; pairs.push(cur); }
    else if (argv[i] === '--b') { cur.b = argv[++i]; }
    else if (argv[i] === '--label') { cur.label = argv[++i]; }
  }
  return pairs.filter(p => p.a && p.b);
}

const pairs = argPairs(process.argv.slice(2));
if (!pairs.length) {
  console.error('usage: node compare.js --a <vanillaStatsName> --b <mineStatsName> [--label X] [--a ... --b ...]');
  process.exit(2);
}

const data = pairs.map(p => ({ label: p.label || (p.a + ' vs ' + p.b), A: load(p.a), B: load(p.b) }));

const w = 30, cw = 15;
console.log('STYLE COMPARISON  (A = vanilla reference, B = produced)');
console.log('='.repeat(w + cw * 4 + 10));
for (const d of data) {
  console.log('\n## ' + d.label + '   (nA=' + d.A.aggregate.n + ', nB=' + d.B.aggregate.n + ')');
  console.log('measure'.padEnd(w) + 'A mean'.padStart(cw) + 'B mean'.padStart(cw) +
    'A med'.padStart(cw) + 'B med'.padStart(cw) + '   delta(mean)   B-in-A-p10..p90');
  for (const [k, desc] of KEYS) {
    const a = d.A.aggregate[k], b = d.B.aggregate[k];
    if (!a || !b) { console.log(k.padEnd(w) + '  (missing)'); continue; }
    const delta = +(b.mean - a.mean).toFixed(3);
    const inRange = b.mean >= a.p10 && b.mean <= a.p90;
    console.log(
      k.padEnd(w) +
      String(a.mean).padStart(cw) + String(b.mean).padStart(cw) +
      String(a.median).padStart(cw) + String(b.median).padStart(cw) +
      ('   ' + (delta >= 0 ? '+' : '') + delta).padEnd(14) +
      (inRange ? 'yes' : 'NO') + '   [' + a.p10 + ' .. ' + a.p90 + ']' + (k === '' ? '' : '')
    );
  }
  // pooled hue histogram difference
  const ha = d.A.aggregate.hueHistogram, hb = d.B.aggregate.hueHistogram;
  let l1 = 0;
  for (let i = 0; i < 24; i++) l1 += Math.abs(ha[i] - hb[i]);
  console.log('hue L1 distance (24 bins, pct pts): ' + l1.toFixed(1) + '  (0 = identical hue mix, 200 = disjoint)');
  console.log('  A hue: ' + ha.join(' '));
  console.log('  B hue: ' + hb.join(' '));
}
