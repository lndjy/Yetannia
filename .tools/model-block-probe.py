# model-block-probe.py — with the true (big-endian) block table, test every data block individually.
#
# The block table is self-consistent (sum of compressed sizes == bytes after blocksInfo, and the two
# node sizes sum to the sum of uncompressed sizes), so the only open question is what transform the
# block payloads carry. This reports, per block, whether plain XOR-0x7b already yields a valid LZ4
# block, and for the first failures where exactly the stream breaks.
#
# usage: python .tools/model-block-probe.py <bundle> [xor-hex|none] [--blocks 0,1,2]
import struct
import sys

import lz4.block


def parse_header(buf):
    off = 8
    version = struct.unpack_from(">I", buf, off)[0]; off += 4
    e = buf.index(b"\x00", off); player = buf[off:e].decode(); off = e + 1
    e = buf.index(b"\x00", off); engine = buf[off:e].decode(); off = e + 1
    size = struct.unpack_from(">q", buf, off)[0]; off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    flags = struct.unpack_from(">I", buf, off)[0]; off += 4
    return dict(version=version, player=player, engine=engine, size=size, cbis=cbis, ubis=ubis,
                flags=flags, hdr_end=off, blocksinfo_off=(off + 15) & ~15)


def load_table(buf, h):
    bi = lz4.block.decompress(buf[h['blocksinfo_off']:h['blocksinfo_off'] + h['cbis']],
                             uncompressed_size=h['ubis'])
    p = 16
    n = struct.unpack_from(">i", bi, p)[0]; p += 4
    blocks = []
    for _ in range(n):
        u, c, f = struct.unpack_from(">IIH", bi, p); p += 10
        blocks.append((u, c, f))
    nn = struct.unpack_from(">i", bi, p)[0]; p += 4
    nodes = []
    for _ in range(nn):
        o_, s_, f_ = struct.unpack_from(">qqI", bi, p); p += 20
        e = bi.index(b"\x00", p); nodes.append((o_, s_, f_, bi[p:e].decode())); p = e + 1
    return blocks, nodes, p, len(bi)


def lz4_decode(src, verbose=False):
    """Raw LZ4 block decode; returns (out, status, fail_rel_off)."""
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        tok_off = i
        token = src[i]; i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                if i >= n:
                    return bytes(out), "truncated litlen", tok_off
                b = src[i]; i += 1; lit += b
                if b != 255:
                    break
        if i + lit > n:
            return bytes(out), f"literals past end (want {lit})", tok_off
        out += src[i:i + lit]; i += lit
        if i == n:
            return bytes(out), "ok", tok_off
        if i + 2 > n:
            return bytes(out), "truncated offset", tok_off
        offset = src[i] | (src[i + 1] << 8); i += 2
        ml = token & 0x0F
        if ml == 15:
            while True:
                if i >= n:
                    return bytes(out), "truncated matchlen", tok_off
                b = src[i]; i += 1; ml += b
                if b != 255:
                    break
        ml += 4
        if offset == 0 or offset > len(out):
            return bytes(out), f"bad backref offset={offset} history={len(out)}", tok_off
        for _ in range(ml):
            out.append(out[-offset])
    return bytes(out), "ran out of input", i


def main():
    path = sys.argv[1]
    x = int(sys.argv[2], 16) if len(sys.argv) > 2 and sys.argv[2] != "none" else None
    only = None
    if "--blocks" in sys.argv:
        only = {int(v) for v in sys.argv[sys.argv.index("--blocks") + 1].split(",")}

    raw = open(path, "rb").read()
    buf = bytes(b ^ x for b in raw) if x else raw
    h = parse_header(buf)
    blocks, nodes, used, bilen = load_table(buf, h)
    data_off = h['blocksinfo_off'] + h['cbis']
    print(f"===== {path} engine={h['engine']!r}")
    print(f"  blocksInfo {bilen}B (parsed {used}), {len(blocks)} blocks, data @ {data_off}, "
          f"sum(csz)={sum(b[1] for b in blocks)}, avail={len(buf) - data_off}")
    for o_, s_, f_, nm in nodes:
        print(f"    node off={o_} size={s_} flags={f_} path={nm!r}")

    pos = data_off
    ok = bad = 0
    bad_list = []
    for i, (usz, csz, fl) in enumerate(blocks):
        blob = buf[pos:pos + csz]
        if only is None or i in only:
            try:
                out = lz4.block.decompress(blob, uncompressed_size=usz)
                ok += 1
                if i < 4 or (only and i in only):
                    print(f"  block {i:3d} @{pos} usz={usz} csz={csz} fl={fl} -> OK {len(out)}")
            except Exception as exc:
                bad += 1
                out, status, fail = lz4_decode(blob)
                bad_list.append(i)
                if len(bad_list) <= 8:
                    print(f"  block {i:3d} @{pos} usz={usz} csz={csz} fl={fl} -> BAD "
                          f"({type(exc).__name__}); manual: {len(out)}/{usz} bytes, "
                          f"died in input byte {pos + fail} (rel {fail}), reason: {status}")
                    print(f"      input around die: {blob[max(0, fail - 12):fail + 12].hex(' ')}")
                    print(f"      out head: {out[:40].hex(' ')}")
                    asc = "".join(chr(b) if 32 <= b < 127 else "." for b in out[:64])
                    print(f"      out ascii: {asc!r}")
        pos += csz
    print(f"  TOTAL: {ok} ok / {bad} bad of {len(blocks)}; first bad blocks: {bad_list[:12]}")


if __name__ == "__main__":
    main()
