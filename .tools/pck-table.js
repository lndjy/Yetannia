// pck-table.js -- read a Godot 4.5 .pck DIRECTORY TABLE (no byte-scanning, no extension whitelist).
//
// Why this exists: .tools/pck-extract.js finds entries by scanning every byte offset for a
// length-prefixed ASCII path whose extension is on a small whitelist. That is fine for "pull the
// vanilla PNGs", but it cannot answer "what does res://animations/characters/ironclad/*.tres point
// at?" because .skel / .atlas / .res / .remap are not on the whitelist and byte-scanning 2 GB is
// slow. Godot writes the real table at a known offset, so read it.
//
// Empirically established layout of SlayTheSpire2.pck (1,990,705,700 bytes, godot 4.5.1):
//
//   header, 112 bytes:
//     0x00 u32 magic 'GDPC'
//     0x04 u32 pack_format_version = 3
//     0x08 u32 ver_major=4  0x0c ver_minor=5  0x10 ver_patch=1
//     0x14 u32 pack_flags = 2
//     0x18 u64 file_base = 112        <- first byte of file data
//     0x20 u64 dir_offset = 1989176224 <- ABSOLUTE offset of the directory table, near EOF
//     0x28 u32 reserved[16]
//     0x68 u32[2] zero padding
//
//   directory table at dir_offset:
//     u32 file_count                                        (15890 for this pack)
//     per entry:
//       u32 path_len   (INCLUDES the trailing NULs and is PADDED UP TO A MULTIPLE OF 4)
//       u8  path[path_len]
//       u64 offset     (absolute; verified by md5 below)
//       u64 size
//       u8  md5[16]
//       u32 flags      (1 = PACK_FILE_ENCRYPTED)
//
//   pck-extract.js's old guess (count at 0x60, entries at 0x64, unpadded pascal strings, table
//   directly after the header) is the PCKPacker layout, not this one -- on this pack it reads
//   file_count == 0. Both are implemented here so the tool does not silently do nothing.
//
// usage:
//   node .tools/pck-table.js <pack.pck> list                    > out.txt
//   node .tools/pck-table.js <pack.pck> grep <substring...>
//   node .tools/pck-table.js <pack.pck> extract <substring> <outDir>
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const WINDOW = 1 << 22; // 4 MiB read window

function reader(fd, size) {
  let buf = Buffer.alloc(0);
  let base = 0;
  return {
    // NOTE: reads are NOT monotonic -- the directory table lives at EOF while the payloads it points
    // at live anywhere earlier -- so BOTH ends of the window must be tested. Checking only the end
    // silently returned garbage for any offset below the current window (that bug made every entry
    // look like an md5 mismatch).
    need(start, end) {
      if (start >= base && end <= base + buf.length) return;
      base = Math.max(0, start - WINDOW);
      const len = Math.min(size - base, Math.max(WINDOW * 5, end - base + 1024));
      buf = Buffer.alloc(len);
      fs.readSync(fd, buf, 0, len, base);
    },
    u32(off) { this.need(off, off + 4); return buf.readUInt32LE(off - base); },
    u64(off) { this.need(off, off + 8); return Number(buf.readBigUInt64LE(off - base)); },
    bytes(off, len) { this.need(off, off + len); return buf.slice(off - base, off - base + len); },
    get size() { return size; },
  };
}

function openTable(packPath) {
  const fd = fs.openSync(packPath, 'r');
  const size = fs.fstatSync(fd).size;
  const r = reader(fd, size);
  if (r.bytes(0, 4).toString('latin1') !== 'GDPC') throw new Error('not a Godot .pck (no GDPC magic)');
  const fmt = r.u32(4);
  const ver = `${r.u32(8)}.${r.u32(12)}.${r.u32(16)}`;
  const flags = r.u32(20);
  const fileBase = r.u64(24);
  const dirOffset = r.u64(32);

  if (flags & 4) throw new Error('PACK_DIR_ENCRYPTED: directory table is encrypted, cannot read');

  const cleanPath = (raw) => raw.toString('utf8').replace(/\0+$/, '');
  const entries = [];
  let layout;

  const readEntries = (p, padded, count) => {
    const out = [];
    for (let i = 0; i < count; i++) {
      const plen = r.u32(p); p += 4;
      const name = cleanPath(r.bytes(p, plen)); p += plen;
      const off = r.u64(p); p += 8;
      const sz = r.u64(p); p += 8;
      const md5 = r.bytes(p, 16).toString('hex'); p += 16;
      const ef = r.u32(p); p += 4;
      out.push({ path: name, offset: off, size: sz, md5, flags: ef, encrypted: (ef & 1) !== 0 });
    }
    return out;
  };

  // Layout A (observed on SlayTheSpire2.pck): directory at dir_offset, 4-byte-padded path lengths.
  if (dirOffset > 0 && dirOffset < size) {
    const count = r.u32(dirOffset);
    if (count > 0 && count < 1000000) {
      const got = readEntries(dirOffset + 4, true, Math.min(count, 4));
      const ok = got.every((e) => /^[ -~]+$/.test(e.path) && e.path.includes('/'));
      if (ok) {
        layout = `A (directory near EOF at ${dirOffset}, padded paths)`;
        entries.push(...readEntries(dirOffset + 4, true, count));
      }
    }
  }

  // Layout B: PCKPacker -- directory right after a 100-byte header, unpadded pascal strings.
  if (entries.length === 0) {
    const count = r.u32(96);
    if (count > 0 && count < 1000000) {
      layout = 'B (directory after 100-byte header, unpadded paths)';
      entries.push(...readEntries(100, false, count));
    }
  }

  if (entries.length === 0) throw new Error('no directory table found (both known layouts empty)');

  const resolved = entries.map((e) => {
    const raw = e;
    if (e.offset + e.size <= size && !e.encrypted
        && md5Of(r, e.offset, e.size) === e.md5) return { ...raw, absolute: true };
    if (fileBase + e.offset + e.size <= size && !e.encrypted
        && md5Of(r, fileBase + e.offset, e.size) === e.md5) {
      return { ...raw, offset: fileBase + e.offset, absolute: false };
    }
    return { ...raw, absolute: null };
  });

  return { fd, size, info: { fmt, ver, flags, fileBase, dirOffset, count: entries.length, layout },
           entries: resolved, bytes: (o, l) => r.bytes(o, l) };
}

function md5Of(r, off, len) {
  if (off < 0 || off + len > r.size || len <= 0) return null;
  // hash in 8 MiB slices so a 2 GB pack never needs one giant buffer
  const h = crypto.createHash('md5');
  const SLICE = 8 << 20;
  for (let p = 0; p < len; p += SLICE) {
    const n = Math.min(SLICE, len - p);
    h.update(r.bytes(off + p, n));
  }
  return h.digest('hex');
}

// ------------------------------------------------------------------ cli
const [packPath, cmd, ...rest] = process.argv.slice(2);
if (!packPath || !cmd) {
  console.error('usage: node .tools/pck-table.js <pack.pck> list|grep|extract ...');
  process.exit(2);
}
const h = openTable(packPath);
h.size = fs.fstatSync(h.fd).size;
console.error(`pack    : ${packPath} (${h.size.toLocaleString()} bytes)`);
console.error(`format  : v${h.info.fmt} godot ${h.info.ver} flags=${h.info.flags}` +
  ` file_base=${h.info.fileBase} dir_offset=${h.info.dirOffset}`);
console.error(`table   : layout ${h.info.layout}, ${h.info.count} entries`);

const seen = new Set();
const uniq = h.entries.filter((e) => (seen.has(e.path) ? false : seen.add(e.path)));

if (cmd === 'list') {
  for (const e of uniq) console.log(`${String(e.size).padStart(10)}  ${e.absolute === null ? 'UNVERIFIED' : 'ok'}  ${e.path}`);
} else if (cmd === 'grep') {
  for (const needle of rest) {
    const hits = uniq.filter((e) => e.path.includes(needle));
    console.log(`# "${needle}": ${hits.length} entries`);
    for (const e of hits) {
      console.log(`${String(e.size).padStart(10)}  ${(e.absolute === null ? 'UNVERIFIED' : e.absolute ? 'abs' : 'relbase').padEnd(10)}  ${e.path}`);
    }
  }
} else if (cmd === 'extract') {
  const [needle, outDir] = rest;
  const hits = uniq.filter((e) => e.path.includes(needle));
  fs.mkdirSync(outDir, { recursive: true });
  for (const e of hits) {
    if (e.absolute === null) { console.error(`  SKIP (md5/range) ${e.path}`); continue; }
    const flat = e.path.replace(/^res:\/\//, '').replace(/[/\\]/g, '__');
    fs.writeFileSync(path.join(outDir, flat), h.bytes(e.offset, e.size));
    console.log(`  ${String(e.size).padStart(10)} B  ${e.path}`);
  }
} else {
  console.error(`unknown command ${cmd}`);
  process.exit(2);
}
