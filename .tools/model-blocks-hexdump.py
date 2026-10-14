# model-blocks-hexdump.py — print the whole decompressed blocksInfo and locate the embedded paths.
#
# My first guess (LE fields) produced nonsense, while reading the voice's count big-endian gives 1.
# Find where "CAB-" lives in the blob: that pins the node-table offset and therefore the endianness.
#
# usage: python .tools/model-blocks-hexdump.py <bundle> [xor-hex|none]
import struct
import sys

import lz4.block


def parse_header(buf):
    off = 8
    version = struct.unpack_from(">I", buf, off)[0]; off += 4
    e = buf.index(b"\x00", off); player = buf[off:e].decode(); off = e + 1
    e = buf.index(b"\x00", off); engine = buf[off:e].decode(); off = e + 1
    off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    flags = struct.unpack_from(">I", buf, off)[0]; off += 4
    return dict(version=version, player=player, engine=engine, cbis=cbis, ubis=ubis,
                flags=flags, hdr_end=off, blocksinfo_off=(off + 15) & ~15)


def hexdump(data, base=0):
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"  {base + i:06x}  {hx:<47}  {asc}")


def dump(path, xor):
    raw = open(path, "rb").read()
    buf = bytes(b ^ xor for b in raw) if xor else raw
    h = parse_header(buf)
    bi = lz4.block.decompress(buf[h['blocksinfo_off']:h['blocksinfo_off'] + h['cbis']],
                             uncompressed_size=h['ubis'])
    print(f"===== {path}  engine={h['engine']!r} cbis={h['cbis']} ubis={h['ubis']} "
          f"blocksInfo@{h['blocksinfo_off']} -> {len(bi)} bytes =====")
    hexdump(bi)
    for tag, endian in (("BE", ">"), ("LE", "<")):
        p = 16
        n = struct.unpack_from(endian + "i", bi, p)[0]
        print(f"  [{tag}] blockCount@{p} = {n}   (sane if 1..200)")
        if 0 < n < 200:
            q = p + 4
            blks = []
            for _ in range(n):
                u, c, f = struct.unpack_from(endian + "IIH", bi, q); q += 10
                blks.append((u, c, f))
            nn = struct.unpack_from(endian + "i", bi, q)[0]
            print(f"  [{tag}] sum(usz)={sum(b[0] for b in blks)} sum(csz)={sum(b[1] for b in blks)} "
                  f"nodeCount@{q}={nn}")
            if 0 < nn < 50:
                r = q + 4
                for _ in range(nn):
                    o_, s_, f_ = struct.unpack_from(endian + "qqI", bi, r); r += 20
                    e = bi.index(b"\x00", r)
                    print(f"  [{tag}]   node off={o_} size={s_} flags={f_} "
                          f"path={bi[r:e].decode('utf-8', 'replace')!r}")
                    r = e + 1
            print(f"  [{tag}] block[0..3]={blks[:4]}")
    print(f"  'CAB-' at offsets: {[i for i in range(len(bi)) if bi.startswith(b'CAB-', i)]}")
    print()


if __name__ == "__main__":
    x = int(sys.argv[2], 16) if len(sys.argv) > 2 and sys.argv[2] != "none" else None
    dump(sys.argv[1], x)
