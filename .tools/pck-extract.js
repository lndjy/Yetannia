// pck-extract.js — dump resources out of a Godot .pck by path substring.
//
// The directory-entry parsing is the same one r27-pckdiff.js needed for the byte-level pck comparison,
// kept here so the next "what does the base game actually ship for X" question does not have to be
// answered by guessing. Godot's PackedSourcePCK directory entry is:
//   u32 pathLength, path bytes (length-prefixed INCLUDING a trailing NUL), u64 offset, u64 size,
//   u8 md5[16], u32 flags
// and with flags & 0x2 (PACK_REL_FILEBASE) the offset is relative to file_base at header+24.
//
// usage: node .tools/pck-extract.js <pack.pck> <path-substring> <outDir>
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const EXT = /\.(png|ctex|import|json|txt|tres|tscn|exr|md5|cfg|remap|po|translation)$/;

function entriesOf(buf) {
  const found = new Map();
  const fileBase = Number(buf.readBigUInt64LE(24));   // flags 0x2 = PACK_REL_FILEBASE
  const relBase = (buf.readUInt32LE(20) & 0x2) !== 0;
  for (let p = 8; p + 40 < buf.length; p++) {
    const len = buf.readUInt32LE(p);
    if (len < 6 || len > 400) continue;
    const end = p + 4 + len;
    if (end + 36 > buf.length) continue;
    const full = buf.slice(p + 4, end).toString('utf8');
    const name = full.replace(/\0+$/, '');
    if (!/^[\x20-\x7e]+$/.test(name) || !name.includes('/') || !EXT.test(name)) continue;
    const rawOffset = Number(buf.readBigUInt64LE(end));
    const size = Number(buf.readBigUInt64LE(end + 8));
    if (size <= 0 || rawOffset <= 0) continue;
    const md5 = buf.slice(end + 16, end + 32).toString('hex');

    // The table carries the md5 of the payload it points at, so a wrong layout cannot pass this.
    const digestAt = (off) => {
      if (off <= 0 || off + size > buf.length) return null;
      return crypto.createHash('md5').update(buf.slice(off, off + size)).digest('hex');
    };
    let offset = null;
    if (digestAt(rawOffset) === md5) offset = rawOffset;
    else if (relBase && digestAt(fileBase + rawOffset) === md5) offset = fileBase + rawOffset;
    if (offset === null) continue;

    if (!found.has(name)) found.set(name, { path: name, offset, size, md5 });
  }
  return found;
}

const [packPath, needle, outDir] = process.argv.slice(2);
if (!packPath || !needle || !outDir) {
  console.error('usage: node .tools/pck-extract.js <pack.pck> <path-substring> <outDir>');
  process.exit(2);
}

const buf = fs.readFileSync(packPath);
const entries = entriesOf(buf);
const hits = [...entries.values()].filter((e) => e.path.includes(needle));

console.log(`pack      : ${packPath} (${buf.length} bytes)`);
console.log(`entries   : ${entries.size}`);
console.log(`matching  : ${hits.length} for "${needle}"`);

fs.mkdirSync(outDir, { recursive: true });
for (const e of hits) {
  // Flatten the pack path into a single filename so nested groups stay distinguishable.
  const flat = e.path.replace(/^res:\/\//, '').replace(/[\/\\]/g, '__');
  const dest = path.join(outDir, flat);
  fs.writeFileSync(dest, buf.slice(e.offset, e.offset + e.size));
  console.log(`  ${e.size.toString().padStart(8)} B  ${e.path}`);
}
