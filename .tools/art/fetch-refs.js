// Extracts vanilla StS2 power/relic icon textures out of SlayTheSpire2.pck.
//
// The pck ships no raw PNGs for these: only `images/powers/<id>.png.import` metadata plus the
// Godot-imported VRAM texture under `.godot/imported/<id>.png-<md5>.bptc.ctex`. So:
//   1. read the pck index,
//   2. pull every `images/{powers,relics}/*.png.import` and parse its `path.bptc=` / `path.s3tc=` line,
//   3. pull those .ctex blobs into an ASCII working dir so Godot can load them as res:// paths.
//
// Usage: node fetch-refs.js [--powers] [--relics] [--limit N]
'use strict';
const fs = require('fs');
const path = require('path');

const PCK = 'D:\\SteamLibrary\\steamapps\\common\\Slay the Spire 2\\SlayTheSpire2.pck';
const WORK = 'C:\\temp\\artref';                       // ASCII: Godot res:// friendly
const OUT_CTEX = path.join(WORK, 'ctex');

const MAGIC = 0x43504447;

function readIndex(file) {
  const fd = fs.openSync(file, 'r');
  const head = Buffer.alloc(256);
  fs.readSync(fd, head, 0, 256, 0);
  let p = 0;
  const u32 = () => ((p += 4), head.readUInt32LE(p - 4));
  const u64 = () => { const v = Number(head.readBigUInt64LE(p)); p += 8; return v; };
  const magic = u32();
  if (magic !== MAGIC) throw new Error('bad magic');
  const formatVersion = u32(); u32(); u32(); u32();
  let fileBase = 0, directoryOffset = 0;
  if (formatVersion >= 2) { u32(); fileBase = u64(); }
  if (formatVersion >= 3) directoryOffset = u64();
  p += 16 * 4;
  let pos, fileCount;
  if (formatVersion >= 3) {
    const dc = Buffer.alloc(4);
    fs.readSync(fd, dc, 0, 4, directoryOffset);
    fileCount = dc.readUInt32LE(0);
    pos = directoryOffset + 4;
  } else { fileCount = u32(); pos = p; }
  const entries = new Map();
  const lenBuf = Buffer.alloc(4);
  for (let i = 0; i < fileCount; i++) {
    fs.readSync(fd, lenBuf, 0, 4, pos);
    const pathLen = lenBuf.readUInt32LE(0);
    pos += 4;
    const pathBytes = Buffer.alloc(pathLen);
    fs.readSync(fd, pathBytes, 0, pathLen, pos);
    pos += pathLen;
    const name = pathBytes.toString('utf8').replace(/\0+$/, '');
    const metaLen = 8 + 8 + 16 + (formatVersion >= 2 ? 4 : 0);
    const meta = Buffer.alloc(metaLen);
    fs.readSync(fd, meta, 0, metaLen, pos);
    pos += metaLen;
    let offset = Number(meta.readBigUInt64LE(0));
    const size = Number(meta.readBigUInt64LE(8));
    const flags = formatVersion >= 2 ? meta.readUInt32LE(32) : 0;
    if (!(flags & 1)) offset += fileBase;
    entries.set(name, { offset, size, flags });
  }
  fs.closeSync(fd);
  return entries;
}

const argv = process.argv.slice(2);
const wantPowers = argv.includes('--powers') || argv.length === 0;
const wantRelics = argv.includes('--relics') || argv.length === 0;
const li = argv.indexOf('--limit');
const limit = li >= 0 ? parseInt(argv[li + 1], 10) : 0;

const idx = readIndex(PCK);
console.log('pck entries:', idx.size);

const fd = fs.openSync(PCK, 'r');
function readEntry(name) {
  const e = idx.get(name);
  if (!e) return null;
  const buf = Buffer.alloc(e.size);
  fs.readSync(fd, buf, 0, e.size, e.offset);
  return buf;
}

fs.mkdirSync(OUT_CTEX, { recursive: true });

const wanted = [];
for (const [name] of idx) {
  let kind = null;
  if (/^images\/powers\/[a-z0-9_]+\.png\.import$/.test(name)) kind = 'power';
  else if (/^images\/relics\/[a-z0-9_]+\.png\.import$/.test(name)) kind = 'relic';
  else continue;
  if (kind === 'power' && !wantPowers) continue;
  if (kind === 'relic' && !wantRelics) continue;
  wanted.push({ name, kind });
}
console.log('candidate .import files:', wanted.length);

const manifest = [];
let missing = 0;
for (const w of wanted) {
  const txt = readEntry(w.name).toString('utf8');
  const id = w.name.replace(/^images\/(powers|relics)\//, '').replace(/\.png\.import$/, '');
  // prefer bptc (cpu-decodable), fall back to s3tc
  const m = /^path\.bptc="res:\/\/(.+?)"\s*$/m.exec(txt) || /^path\.s3tc="res:\/\/(.+?)"\s*$/m.exec(txt);
  if (!m) { missing++; continue; }
  const ctexRes = m[1];
  const blob = readEntry(ctexRes);
  if (!blob) { missing++; console.log('  MISSING ctex', ctexRes); continue; }
  const flat = w.kind + '__' + id + '__' + path.basename(ctexRes);
  fs.writeFileSync(path.join(OUT_CTEX, flat), blob);
  manifest.push({ id, kind: w.kind, ctex: flat, src: ctexRes, bytes: blob.length });
}
fs.closeSync(fd);

if (limit > 0) manifest.length = Math.min(manifest.length, limit);
fs.writeFileSync(path.join(WORK, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
console.log('extracted', manifest.length, 'ctex ->', OUT_CTEX, ' (unresolved ' + missing + ')');
console.log('manifest ->', path.join(WORK, 'manifest.json'));
