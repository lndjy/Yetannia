// Verification for the Yetannia icon deliverables.
//   node verify.js
// Asserts: exact file set (54), exact dimensions from each PNG IHDR, non-blankness by size.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = 'D:\\桌面\\sts2mod\\.tools\\pckproject\\Yetannia\\images';

const POWERS = [
  'prophet_tally', 'foresight', 'nirvana', 'prophetic_study', 'cycle_of_prophecy',
  'pure_love_form', 'delayed_echo', 'delayed_scry', 'scry_might', 'scry_agility',
  'judgement', 'ember_boon', 'granted_turn', 'insight', 'purify',
  'exhaust_blast', 'free_status', 'double_status', 'status_draw', 'shared_might',
  'steady_agility',
];
const RELICS = ['agate_potion_belt', 'foresight_charm', 'prophets_bracelet', 'prophets_eye', 'prophets_eye_plus'];

// group folder -> [expected width, expected height, min bytes]
const SPEC = [
  { dir: 'powers', names: POWERS.map(n => n + '.png'), w: 64, h: 64, min: 1536, label: 'powers (64x64)' },
  { dir: 'powers_big', names: POWERS.map(n => n + '.png'), w: 256, h: 256, min: 4096, label: 'powers_big (256x256)' },
  { dir: 'relics', names: RELICS.map(n => n + '.png'), w: 64, h: 64, min: 1536, label: 'relics (64x64)' },
  { dir: 'relics_big', names: RELICS.map(n => n + '.png'), w: 256, h: 256, min: 4096, label: 'relics_big (256x256)' },
  { dir: 'ui', names: ['energy_yetannia_small.png'], w: 64, h: 64, min: 1536, label: 'ui energy small (64x64)' },
  { dir: 'ui', names: ['energy_yetannia.png'], w: 256, h: 256, min: 4096, label: 'ui energy orb (256x256)' },
];

const SIG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

// Reads width/height/colour-type/bit-depth straight out of the IHDR chunk.
function readIHDR(file) {
  const fd = fs.openSync(file, 'r');
  const buf = Buffer.alloc(33);
  try { fs.readSync(fd, buf, 0, 33, 0); } finally { fs.closeSync(fd); }
  if (!buf.slice(0, 8).equals(SIG)) throw new Error('not a PNG (bad signature)');
  if (buf.toString('ascii', 12, 16) !== 'IHDR') throw new Error('first chunk is not IHDR');
  return {
    width: buf.readUInt32BE(16),
    height: buf.readUInt32BE(20),
    bitDepth: buf[24],
    colorType: buf[25],
    interlace: buf[28],
  };
}

const failures = [];
const notes = [];
let checked = 0;
const perFolder = {};

for (const spec of SPEC) {
  const dir = path.join(ROOT, spec.dir);
  if (!fs.existsSync(dir)) { failures.push('MISSING FOLDER: ' + dir); continue; }
  let n = 0;
  for (const name of spec.names) {
    const file = path.join(dir, name);
    if (!fs.existsSync(file)) { failures.push('MISSING FILE: ' + path.join(spec.dir, name)); continue; }
    n++; checked++;
    const size = fs.statSync(file).size;
    let hdr;
    try { hdr = readIHDR(file); } catch (e) { failures.push('UNREADABLE: ' + name + ' - ' + e.message); continue; }
    if (hdr.width !== spec.w || hdr.height !== spec.h) {
      failures.push(`WRONG SIZE: ${spec.dir}/${name} is ${hdr.width}x${hdr.height}, expected ${spec.w}x${spec.h}`);
    }
    if (size <= spec.min) {
      failures.push(`BLANK/SMALL: ${spec.dir}/${name} is ${size} bytes, expected > ${spec.min}`);
    }
    if (hdr.colorType !== 6) {
      failures.push(`NOT RGBA: ${spec.dir}/${name} colour type ${hdr.colorType} (want 6)`);
    }
    if (hdr.bitDepth !== 8) {
      failures.push(`BAD DEPTH: ${spec.dir}/${name} bit depth ${hdr.bitDepth} (want 8)`);
    }
    if (hdr.interlace !== 0) {
      failures.push(`INTERLACED: ${spec.dir}/${name}`);
    }
    notes.push(`  ${(spec.dir + '/' + name).padEnd(34)} ${String(hdr.width + 'x' + hdr.height).padStart(9)}  ${String(size).padStart(7)} bytes`);
  }
  perFolder[spec.dir + ' ' + spec.w + 'x' + spec.h] = n;
}

// nothing extra lying around in the deliverable folders
for (const spec of SPEC) {
  const dir = path.join(ROOT, spec.dir);
  if (!fs.existsSync(dir)) continue;
  const expected = new Set(spec.names);
  for (const f of fs.readdirSync(dir)) {
    if (f.toLowerCase().endsWith('.png') && !expected.has(f)) {
      // a file may legitimately be expected by the other spec entry for the same folder
      const other = SPEC.filter(s => s.dir === spec.dir).some(s => s.names.includes(f));
      if (!other) failures.push('UNEXPECTED FILE: ' + path.join(spec.dir, f));
    }
  }
}

const EXPECTED_TOTAL = POWERS.length * 2 + RELICS.length * 2 + 2; // 21*2 + 5*2 + 2 = 54

console.log('Yetannia icon verification');
console.log('==========================');
console.log(notes.join('\n'));
console.log('');
console.log('expected files: ' + EXPECTED_TOTAL);
console.log('files checked : ' + checked);
console.log('');
if (failures.length) {
  console.log('FAILURES (' + failures.length + '):');
  for (const f of failures) console.log('  ! ' + f);
  process.exit(1);
}
if (checked !== EXPECTED_TOTAL) {
  console.log('FAIL: checked ' + checked + ' but expected ' + EXPECTED_TOTAL);
  process.exit(1);
}
console.log('PASS');
console.log('  - all ' + EXPECTED_TOTAL + ' files present');
console.log('  - powers/*.png, relics/*.png, ui/energy_yetannia_small.png are exactly 64x64');
console.log('  - powers_big/*.png, relics_big/*.png, ui/energy_yetannia.png are exactly 256x256');
console.log('  - every file > 1.5 KB and every 256x256 file > 4 KB (nothing blank)');
console.log('  - all files are 8-bit non-interlaced RGBA (colour type 6, alpha present)');
