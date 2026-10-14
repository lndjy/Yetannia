# model-cab-dump.py — decrypt with a prefix-XOR boundary, decompress every block, and read the CAB.
#
# usage: python .tools/model-cab-dump.py <bundle.data> <prefixN|auto>
import os
import re
import struct
import sys

import lz4.block

OUT = r"D:\桌面\sts2mod\.tools\out"


def parse_and_decompress(raw, n):
    buf = bytes(b ^ 0x7B for b in raw[:n]) + raw[n:]
    off = 8 + 4
    e = buf.index(b"\x00", off); off = e + 1
    e = buf.index(b"\x00", off); off = e + 1
    size = struct.unpack_from(">q", buf, off)[0]; off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    flags = struct.unpack_from(">I", buf, off)[0]; off += 4
    bio = (off + 15) & ~15
    bi = lz4.block.decompress(buf[bio:bio + cbis], uncompressed_size=ubis)
    p = 16
    nblk = struct.unpack_from(">i", bi, p)[0]; p += 4
    blks = []
    for _ in range(nblk):
        u, c, f = struct.unpack_from(">IIH", bi, p); p += 10
        blks.append((u, c, f))
    nn = struct.unpack_from(">i", bi, p)[0]; p += 4
    nodes = []
    for _ in range(nn):
        o_, s_, f_ = struct.unpack_from(">qqI", bi, p); p += 20
        e = bi.index(b"\x00", p); nodes.append((o_, s_, f_, bi[p:e].decode())); p = e + 1
    pos = bio + cbis
    parts = []
    for (u, c, f) in blks:
        parts.append(lz4.block.decompress(buf[pos:pos + c], uncompressed_size=u))
        pos += c
    return b"".join(parts), blks, nodes, buf


def strings(data, minlen=4, limit=400):
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, data):
        out.append((m.start(), m.group().decode()))
        if len(out) >= limit:
            break
    return out


def main():
    path = sys.argv[1]
    n = int(sys.argv[2]) if sys.argv[2] != "auto" else 1000
    raw = open(path, "rb").read()
    os.makedirs(OUT, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]

    data, blks, nodes, buf = parse_and_decompress(raw, n)
    print(f"N={n}: total data {len(data)} bytes (sum usz={sum(b[0] for b in blks)})")
    for o_, s_, f_, nm in nodes:
        print(f"  node off={o_} size={s_} flags={f_} path={nm!r}")
        blob = data[o_:o_ + s_]
        open(os.path.join(OUT, f"{stem}.{nm.split('.')[-1]}.bin"), "wb").write(blob)

    cab = data[:nodes[0][1]]
    # SerializedFile header (UnityFS serialized files are BIG-endian too)
    print("\n-- SerializedFile header (BE) --")
    for endian, tag in ((">", "BE"), ("<", "LE")):
        h = struct.unpack_from(endian + "IIII", cab, 0)
        print(f"  [{tag}] metadataSize={h[0]} fileSize={h[1]} version={h[2]} dataOffset={h[3]}")
    st = cab.index(b"\x00", 16)
    print(f"  unityVersion@{16 + 0}={cab[16:st]!r}")
    q = st + 1
    print(f"  targetPlatform={struct.unpack_from('>i', cab, q)[0]}  "
          f"enableTypeTree={cab[q + 4]}")
    print(f"  bytes after header: {cab[q + 5:q + 21].hex(' ')}")

    print(f"\n-- printable strings in CAB (first 120) --")
    for off_, s in strings(cab, 4, 120):
        print(f"   {off_:08x}  {s!r}")


if __name__ == "__main__":
    main()
