// Verification for the v2 Yetannia icon deliverables.
//
//   node verify-v2.js
//
// Asserts, for every produced PNG:
//   * exact dimensions (64 or 256)
//   * 8-bit non-interlaced RGBA (colour type 6, alpha actually present)
//   * non-blank: file size bracket AND alpha-coverage bracket
//   * sha256-distinct from every other produced icon
//   * visually pairwise-distinct: mean premultiplied difference on a 16x16 reduction, with the
//     closest pair reported for the power set and for the whole set
//   * the 64 px file is genuinely a reduction of the matching 256 px file
// and then prints the measured style table against the vanilla reference sets extracted from
// SlayTheSpire2.pck (see ./measure.js and ./compare.js).
//
// This replaces .tools/icongen/verify.js, which is still correct for the v1 file set but hard-codes
// 21 powers and therefore reports starscar_form.png as an unexpected file.
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { decode } = require('./pngio.js');
const { measure, aggregate } = require('./measure.js');

const ROOT = 'D:\\桌面\\sts2mod\\.tools\\pckproject\\Yetannia\\images';
const STATS = path.join(__dirname, 'stats');

const POWERS = [
  'prophet_tally', 'foresight', 'nirvana', 'prophetic_study', 'cycle_of_prophecy',
  'pure_love_form', 'delayed_echo', 'delayed_scry', 'scry_might', 'scry_agility',
  'judgement', 'ember_boon', 'granted_turn', 'insight', 'purify',
  'exhaust_blast', 'free_status', 'double_status', 'status_draw', 'shared_might',
  'steady_agility', 'starscar_form', 'temp_might', 'temp_agility',
];
const RELICS = ['agate_potion_belt', 'foresight_charm', 'prophets_bracelet', 'prophets_eye', 'prophets_eye_plus'];

const SPEC = [
  { dir: 'powers', names: POWERS.map(n => n + '.png'), w: 64, h: 64, minBytes: 900, minCov: 25, maxCov: 92, label: 'powers 64' },
  { dir: 'powers_big', names: POWERS.map(n => n + '.png'), w: 256, h: 256, minBytes: 3000, minCov: 25, maxCov: 92, label: 'powers_big 256' },
  { dir: 'relics', names: RELICS.map(n => n + '.png'), w: 64, h: 64, minBytes: 900, minCov: 20, maxCov: 92, label: 'relics 64' },
  { dir: 'relics_big', names: RELICS.map(n => n + '.png'), w: 256, h: 256, minBytes: 3000, minCov: 20, maxCov: 92, label: 'relics_big 256' },
  { dir: 'ui', names: ['energy_yetannia_small.png'], w: 24, h: 24, minBytes: 300, minCov: 25, maxCov: 92, label: 'ui inline energy glyph 24 (TextEnergyIconPath)' },
  { dir: 'ui', names: ['energy_yetannia.png'], w: 256, h: 256, minBytes: 3000, minCov: 25, maxCov: 92, label: 'ui energy 256' },
  { dir: 'ui', names: ['map_marker_yetannia.png'], w: 49, h: 64, minBytes: 400, minCov: 25, maxCov: 92, label: 'ui map marker 49x64 (CustomMapMarkerPath)' },
];
const SIG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function readIHDR(file) {
  const fd = fs.openSync(file, 'r');
  const buf = Buffer.alloc(33);
  try { fs.readSync(fd, buf, 0, 33, 0); } finally { fs.closeSync(fd); }
  if (!buf.slice(0, 8).equals(SIG)) throw new Error('not a PNG (bad signature)');
  if (buf.toString('ascii', 12, 16) !== 'IHDR') throw new Error('first chunk is not IHDR');
  return {
    width: buf.readUInt32BE(16), height: buf.readUInt32BE(20),
    bitDepth: buf[24], colorType: buf[25], interlace: buf[28],
  };
}

// 16x16 premultiplied-alpha reduction, used for the pairwise distinctness test
function thumb16(file) {
  const img = decode(file);
  const { width: W, height: H, channels: C, pixels: P } = img;
  const out = new Float64Array(16 * 16 * 4);
  const cnt = new Float64Array(16 * 16);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * C;
      const a = C === 4 ? P[i + 3] / 255 : 1;
      const t = Math.floor(y * 16 / H) * 16 + Math.floor(x * 16 / W);
      out[t * 4] += P[i] * a; out[t * 4 + 1] += P[i + 1] * a; out[t * 4 + 2] += P[i + 2] * a;
      out[t * 4 + 3] += a; cnt[t]++;
    }
  }
  for (let t = 0; t < 256; t++) {
    for (let k = 0; k < 4; k++) out[t * 4 + k] /= Math.max(1, cnt[t]);
  }
  return out;
}
function thumbDist(a, b) {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += Math.abs(a[i] - b[i]);
  return s / a.length;   // 0..255
}

// ---------------------------------------------------------------- checks
const failures = [], notes = [];
let checked = 0;
const produced = [];   // {key, dir, name, file, w, h, bytes, coverage, sha}

for (const spec of SPEC) {
  const dir = path.join(ROOT, spec.dir);
  if (!fs.existsSync(dir)) { failures.push('MISSING FOLDER: ' + dir); continue; }
  for (const name of spec.names) {
    const file = path.join(dir, name);
    if (!fs.existsSync(file)) { failures.push('MISSING FILE: ' + spec.dir + '/' + name); continue; }
    checked++;
    const size = fs.statSync(file).size;
    let hdr;
    try { hdr = readIHDR(file); } catch (e) { failures.push('UNREADABLE: ' + name + ' - ' + e.message); continue; }
    if (hdr.width !== spec.w || hdr.height !== spec.h) {
      failures.push(`WRONG SIZE: ${spec.dir}/${name} is ${hdr.width}x${hdr.height}, expected ${spec.w}x${spec.h}`);
    }
    if (hdr.colorType !== 6) failures.push(`NOT RGBA: ${spec.dir}/${name} colour type ${hdr.colorType}`);
    if (hdr.bitDepth !== 8) failures.push(`BAD DEPTH: ${spec.dir}/${name} bit depth ${hdr.bitDepth}`);
    if (hdr.interlace !== 0) failures.push(`INTERLACED: ${spec.dir}/${name}`);
    if (size <= spec.minBytes) failures.push(`BLANK/SMALL: ${spec.dir}/${name} is ${size} bytes (want > ${spec.minBytes})`);

    // alpha-coverage bracket
    const img = decode(file);
    let covered = 0, sumA = 0;
    const N = img.width * img.height;
    for (let i = 0; i < N; i++) {
      const a = img.pixels[i * img.channels + 3];
      sumA += a;
      if (a >= 32) covered++;
    }
    const cov = 100 * covered / N;
    const meanA = 100 * sumA / N / 255;
    if (cov < spec.minCov) failures.push(`TOO SPARSE: ${spec.dir}/${name} coverage ${cov.toFixed(1)}% < ${spec.minCov}%`);
    if (cov > spec.maxCov) failures.push(`TOO SOLID: ${spec.dir}/${name} coverage ${cov.toFixed(1)}% > ${spec.maxCov}%`);
    if (meanA < 15) failures.push(`MOSTLY TRANSPARENT: ${spec.dir}/${name} mean alpha ${meanA.toFixed(1)}%`);

    const sha = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
    produced.push({
      key: (spec.dir === 'ui' ? 'ui/' : spec.dir + '/') + name,
      dir: spec.dir, name, file, w: hdr.width, h: hdr.height, bytes: size,
      coverage: +cov.toFixed(2), meanAlpha: +meanA.toFixed(2), sha,
    });
  }
}

// nothing extra lying around in the deliverable folders
for (const spec of SPEC) {
  const dir = path.join(ROOT, spec.dir);
  if (!fs.existsSync(dir)) continue;
  const expected = new Set(SPEC.filter(s => s.dir === spec.dir).flatMap(s => s.names));
  for (const f of fs.readdirSync(dir)) {
    if (f.toLowerCase().endsWith('.png') && !expected.has(f)) failures.push('UNEXPECTED FILE: ' + spec.dir + '/' + f);
  }
}

// sha256 distinctness
const bySha = new Map();
for (const p of produced) {
  if (bySha.has(p.sha)) failures.push(`DUPLICATE BYTES: ${p.key} is byte-identical to ${bySha.get(p.sha)}`);
  else bySha.set(p.sha, p.key);
}

// pairwise visual distinctness (16x16 premultiplied reduction)
const thumbs = new Map();
for (const p of produced) thumbs.set(p.key, thumb16(p.file));

function closestPairs(keys) {
  const rows = [];
  for (let i = 0; i < keys.length; i++) {
    for (let j = i + 1; j < keys.length; j++) {
      rows.push({ a: keys[i], b: keys[j], d: +thumbDist(thumbs.get(keys[i]), thumbs.get(keys[j])).toFixed(2) });
    }
  }
  rows.sort((x, y) => x.d - y.d);
  return rows;
}
const allKeys = produced.map(p => p.key);
const powerKeys = POWERS.map(n => 'powers/' + n + '.png');
const relicKeys = RELICS.map(n => 'relics/' + n + '.png');
const powerPairs = closestPairs(powerKeys);
const relicPairs = closestPairs(relicKeys);
const allPairs = closestPairs(allKeys);

const DIST_FLOOR = 8.0;
for (const list of [powerPairs, relicPairs]) {
  if (list.length && list[0].d < DIST_FLOOR) {
    failures.push(`NEAR-IDENTICAL ICONS: ${list[0].a} vs ${list[0].b} distance ${list[0].d} < ${DIST_FLOOR}`);
  }
}
// and the 64 px file must be a genuine reduction of the matching 256 px file
for (const n of POWERS.concat(RELICS)) {
  const big = thumbs.get('powers_big/' + n + '.png') || thumbs.get('relics_big/' + n + '.png');
  const small = thumbs.get('powers/' + n + '.png') || thumbs.get('relics/' + n + '.png');
  const d = thumbDist(big, small);
  if (d > 26) failures.push(`64 PX DOES NOT MATCH ITS 256 PX SOURCE: ${n} distance ${d.toFixed(1)}`);
}

// ---------------------------------------------------------------- style comparison
function loadStats(name) {
  const p = path.join(STATS, name + '.json');
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, 'utf8')).aggregate : null;
}
const PAIRS = [
  ['vanilla.power.64', 'mine.power.64', 'POWERS 64 px (vanilla = power_atlas slices, the real in-game art)'],
  ['vanilla.power.256', 'mine.power.256', 'POWERS 256 px (vanilla = images/powers/*.png sources)'],
  ['vanilla.relic.256', 'mine.relic.256', 'RELICS 256 px (vanilla = images/relics/*.png sources)'],
  ['vanilla.relic.64', 'mine.relic.64', 'RELICS 64 px (vanilla = trimmed atlas slices, informational only)'],
];
const KEYS = [
  'coveragePct', 'meanAlphaPct', 'bbox.fillPct', 'cornerAlphaPct', 'ringAlphaPct', 'centreAlphaPct',
  'shapeIoU.roundedSquare', 'shapeIoU.circle', 'shapeIoU.square',
  'outline.circularity', 'outline.rimPctOfCovered', 'outline.rimLuma', 'outline.rimNearBlackPct',
  'outline.innerRimLuma', 'outline.softAlphaPct',
  'palette.distinctColors', 'palette.top1Pct', 'palette.top5Pct', 'palette.hueBinsAbove1Pct', 'palette.meanSaturation',
  'value.mean', 'value.median', 'value.std', 'value.p10', 'value.p25', 'value.p75', 'value.p90',
  'value.darkPct', 'value.midPct', 'value.lightPct', 'value.highlightPct', 'value.nearBlackPct',
  'edges.allPct', 'edges.interiorPct',
  'contrast.darkMassLuma', 'contrast.highlightLuma', 'contrast.deltaLuma', 'contrast.flatWhiteInkPct',
  'contrast.highlightChroma',
];
let outOfBand = 0;
const styleReport = [];
for (const [a, b, label] of PAIRS) {
  const A = loadStats(a), B = loadStats(b);
  if (!A || !B) { styleReport.push({ label, error: 'missing stats' }); continue; }
  const rows = [];
  for (const k of KEYS) {
    const av = A[k], bv = B[k];
    if (!av || !bv) continue;
    const inBand = bv.mean >= av.p10 && bv.mean <= av.p90;
    if (!inBand) outOfBand++;
    rows.push({ k, vanilla: av.mean, mine: bv.mean, delta: +(bv.mean - av.mean).toFixed(3), p10: av.p10, p90: av.p90, inBand });
  }
  let l1 = 0;
  for (let i = 0; i < 24; i++) l1 += Math.abs(A.hueHistogram[i] - B.hueHistogram[i]);
  styleReport.push({ label, nVanilla: A.n, nMine: B.n, rows, hueL1: +l1.toFixed(1) });
}

// ---------------------------------------------------------------- report
console.log('Yetannia icon verification (v2 painted set)');
console.log('===========================================');
console.log('expected files: ' + (POWERS.length * 2 + RELICS.length * 2 + 3));
console.log('files checked : ' + checked);
console.log('distinct sha256: ' + bySha.size + ' / ' + produced.length);
console.log('');
console.log('closest pair, powers (16x16 premultiplied mean abs diff, 0-255):');
powerPairs.slice(0, 5).forEach(p => console.log('   ' + String(p.d).padStart(6) + '   ' + p.a + '  <->  ' + p.b));
console.log('closest pair, relics:');
relicPairs.slice(0, 3).forEach(p => console.log('   ' + String(p.d).padStart(6) + '   ' + p.a + '  <->  ' + p.b));
console.log('closest pair, whole set:');
allPairs.slice(0, 3).forEach(p => console.log('   ' + String(p.d).padStart(6) + '   ' + p.a + '  <->  ' + p.b));
console.log('');

for (const s of styleReport) {
  console.log('## ' + s.label + (s.error ? '  ERROR: ' + s.error : `   (vanilla n=${s.nVanilla}, mine n=${s.nMine})`));
  if (s.error) continue;
  console.log('measure'.padEnd(30) + 'vanilla'.padStart(10) + 'mine'.padStart(10) + 'delta'.padStart(10) + '   vanilla p10..p90            in band');
  for (const r of s.rows) {
    console.log(r.k.padEnd(30) + String(r.vanilla).padStart(10) + String(r.mine).padStart(10) +
      String((r.delta >= 0 ? '+' : '') + r.delta).padStart(10) +
      '   [' + String(r.p10).padStart(7) + ' ..' + String(r.p90).padStart(8) + ']   ' + (r.inBand ? 'yes' : 'NO'));
  }
  console.log('hue L1 distance (24 bins, pct points): ' + s.hueL1 + '   (0 = identical mix, 200 = disjoint)');
  console.log('');
}
console.log('style measures outside vanilla p10..p90, summed over all four tables: ' + outOfBand);
console.log('');

if (failures.length) {
  console.log('FAILURES (' + failures.length + '):');
  for (const f of failures) console.log('  ! ' + f);
  process.exit(1);
}
console.log('PASS');
console.log('  - all ' + checked + ' files present, exact size, 8-bit non-interlaced RGBA');
console.log('  - every file non-blank (size, alpha coverage and mean alpha brackets)');
console.log('  - every file sha256-distinct');
console.log('  - closest power pair distance ' + powerPairs[0].d + ', closest relic pair ' + relicPairs[0].d +
  ' (floor ' + DIST_FLOOR + ')');
console.log('  - every 64 px file is a reduction of its 256 px source');
