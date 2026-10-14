// Minimal Godot 4 PCK reader (pack format v1 / v2 / v3).
// Usage:
//   node pck.js list    <pack.pck> [substringFilter]
//   node pck.js extract <pack.pck> <outDir> [substringFilter]
//
// Header: u32 magic 'GDPC', u32 format_version, u32 ver_major, u32 ver_minor, u32 ver_patch,
//         u32 pack_flags (v2+), u64 file_base (v2+), u64 directory_offset (v3+),
//         16 * u32 reserved, u32 file_count (v1/v2 only)
// Entry:  u32 path_len, path[path_len] (NUL padded), u64 offset, u64 size,
//         byte[16] md5, u32 flags (v2+)
const fs = require("fs");
const path = require("path");

const MAGIC = 0x43504447; // 'GDPC'
const FILE_ENCRYPTED = 1;

function readIndex(file) {
  const fd = fs.openSync(file, "r");
  const head = Buffer.alloc(256);
  fs.readSync(fd, head, 0, 256, 0);

  let p = 0;
  const u32 = () => ((p += 4), head.readUInt32LE(p - 4));
  const u64 = () => {
    const v = Number(head.readBigUInt64LE(p));
    p += 8;
    return v;
  };

  const magic = u32();
  if (magic !== MAGIC) throw new Error("bad magic 0x" + magic.toString(16) + " (expected GDPC)");
  const formatVersion = u32();
  const verMajor = u32();
  const verMinor = u32();
  u32(); // patch

  let packFlags = 0;
  let fileBase = 0;
  let directoryOffset = 0;
  if (formatVersion >= 2) {
    packFlags = u32();
    fileBase = u64();
  }
  if (formatVersion >= 3) {
    directoryOffset = u64();
  }
  p += 16 * 4; // reserved

  let pos;
  let fileCount;
  if (formatVersion >= 3) {
    const dc = Buffer.alloc(4);
    fs.readSync(fd, dc, 0, 4, directoryOffset);
    fileCount = dc.readUInt32LE(0);
    pos = directoryOffset + 4;
  } else {
    fileCount = u32();
    pos = p;
  }

  const entries = [];
  const lenBuf = Buffer.alloc(4);
  for (let i = 0; i < fileCount; i++) {
    fs.readSync(fd, lenBuf, 0, 4, pos);
    const pathLen = lenBuf.readUInt32LE(0);
    pos += 4;
    const pathBytes = Buffer.alloc(pathLen);
    fs.readSync(fd, pathBytes, 0, pathLen, pos);
    pos += pathLen;
    const name = pathBytes.toString("utf8").replace(/\0+$/, "");

    const metaLen = 8 + 8 + 16 + (formatVersion >= 2 ? 4 : 0);
    const meta = Buffer.alloc(metaLen);
    fs.readSync(fd, meta, 0, metaLen, pos);
    pos += metaLen;

    let offset = Number(meta.readBigUInt64LE(0));
    const size = Number(meta.readBigUInt64LE(8));
    const flags = formatVersion >= 2 ? meta.readUInt32LE(32) : 0;
    if (!(flags & FILE_ENCRYPTED)) offset += fileBase;
    entries.push({ name, offset, size, flags });
  }
  fs.closeSync(fd);
  return { formatVersion, verMajor, verMinor, packFlags, fileBase, directoryOffset, entries };
}

function main() {
  const [, , cmd, pack, arg3, arg4] = process.argv;
  if (!cmd || !pack) {
    console.error("usage: node pck.js list|extract <pack.pck> [outDir] [filter]");
    process.exit(2);
  }
  const index = readIndex(pack);
  console.error(
    `pck format v${index.formatVersion} (godot ${index.verMajor}.${index.verMinor}.x), ${index.entries.length} files`
  );

  if (cmd === "list") {
    const filter = arg3;
    for (const e of index.entries) {
      if (!filter || e.name.includes(filter)) console.log(String(e.size).padStart(10), e.name);
    }
    return;
  }

  if (cmd === "extract") {
    const outDir = arg3;
    const filter = arg4;
    const fd = fs.openSync(pack, "r");
    let n = 0;
    for (const e of index.entries) {
      if (filter && !e.name.includes(filter)) continue;
      if (e.flags & FILE_ENCRYPTED) {
        console.error("skipping encrypted file " + e.name);
        continue;
      }
      const target = path.join(outDir, e.name);
      fs.mkdirSync(path.dirname(target), { recursive: true });
      const buf = Buffer.alloc(e.size);
      fs.readSync(fd, buf, 0, e.size, e.offset);
      fs.writeFileSync(target, buf);
      n++;
    }
    fs.closeSync(fd);
    console.error(`extracted ${n} files to ${outDir}`);
    return;
  }

  console.error("unknown command " + cmd);
  process.exit(2);
}

main();
