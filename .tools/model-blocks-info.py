# model-blocks-info.py — decompress blocksInfo for real and dump the block table + node table.
#
# blocksInfo itself decompresses cleanly, so we can read every block's (usize, csize, flags) and
# the node (file) table. That settles whether the block data is contiguous, whether padding exists,
# and which block first fails -- instead of UnityPy's all-or-nothing LZ4BlockError.
#
# usage: python .tools/model-blocks-info.py <bundle> [xor-hex] [max-blocks]
import struct
import sys

import lz4.block


def parse_header(buf):
    assert buf[:7] == b"UnityFS", buf[:8]
    off = 8
    version = struct.unpack_from(">I", buf, off)[0]; off += 4
    e = buf.index(b"\x00", off); player = buf[off:e].decode(); off = e + 1
    e = buf.index(b"\x00", off); engine = buf[off:e].decode(); off = e + 1
    size = struct.unpack_from(">q", buf, off)[0]; off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    flags = struct.unpack_from(">I", buf, off)[0]; off += 4
    data_off = (off + 15) & ~15
    return dict(version=version, player=player, engine=engine, size=size, cbis=cbis,
                ubis=ubis, flags=flags, hdr_end=off, blocksinfo_off=data_off,
                data_off=data_off + cbis)


def dump(path, xor):
    raw = open(path, "rb").read()
    buf = bytes(b ^ xor for b in raw) if xor else raw
    h = parse_header(buf)
    print(f"===== {path}  ({len(raw)} bytes, xor={xor if xor is None else hex(xor)}) =====")
    print(f"  engine={h['engine']!r} player={h['player']!r} flags=0x{h['flags']:x} "
          f"cbis={h['cbis']} ubis={h['ubis']} declared_size={h['size']}")
    print(f"  header ends {h['hdr_end']}, blocksInfo @ {h['blocksinfo_off']} "
          f"({h['cbis']}B), data @ {h['data_off']}")

    bi = lz4.block.decompress(buf[h['blocksinfo_off']:h['blocksinfo_off'] + h['cbis']],
                             uncompressed_size=h['ubis'])
    print(f"  blocksInfo decompressed: {len(bi)} bytes")
    # blocksInfo layout: uncompressedDataHash[16], blockCount i32, then (usize u32, csize u32, flags u16)
    p = 0
    hsh = bi[p:p + 16]; p += 16
    print(f"  uncompressedDataHash = {hsh.hex()}")
    nblocks = struct.unpack_from("<i", bi, p)[0]; p += 4
    print(f"  blockCount = {nblocks}")
    blocks = []
    for i in range(nblocks):
        usz, csz, fl = struct.unpack_from("<IIH", bi, p); p += 10
        blocks.append((usz, csz, fl))
    nnodes = struct.unpack_from("<i", bi, p)[0]; p += 4
    print(f"  nodeCount = {nnodes}")
    nodes = []
    for i in range(nnodes):
        off_, sz_, fl_ = struct.unpack_from("<qqI", bi, p); p += 20
        e = bi.index(b"\x00", p); name = bi[p:e].decode("utf-8", "replace"); p = e + 1
        nodes.append((off_, sz_, fl_, name))
    print(f"  parsed {p} of {len(bi)} blocksInfo bytes")
    for off_, sz_, fl_, name in nodes:
        print(f"    node off={off_} size={sz_} flags={fl_} path={name!r}")

    tot_c = sum(b[1] for b in blocks)
    tot_u = sum(b[0] for b in blocks)
    print(f"  sum(compressedSize)={tot_c}  sum(uncompressedSize)={tot_u}")
    print(f"  bytes available after blocksInfo = {len(buf) - h['data_off']}  "
          f"(diff = {len(buf) - h['data_off'] - tot_c})")
    print(f"  first 5 non-zero-uncompressed blocks: {[(u, c, f) for u, c, f in blocks if u][:5]}")

    # per-block decompression probe
    pos = h['data_off']
    okc = badc = 0
    first_bad = None
    maxb = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    for i, (usz, csz, fl) in enumerate(blocks):
        blob = buf[pos:pos + csz]
        try:
            out = lz4.block.decompress(blob, uncompressed_size=usz)
            if i < maxb:
                print(f"    block {i:3d} @ {pos} usz={usz} csz={csz} fl={fl} -> OK {len(out)}")
            okc += 1
        except Exception as exc:
            if i < maxb:
                print(f"    block {i:3d} @ {pos} usz={usz} csz={csz} fl={fl} -> "
                      f"{type(exc).__name__} {exc}")
            if first_bad is None:
                first_bad = (i, pos, usz, csz, fl)
            badc += 1
        pos += csz
    print(f"  block decompression: {okc} ok, {badc} bad; first_bad={first_bad}")
    print()


if __name__ == "__main__":
    p = sys.argv[1]
    x = int(sys.argv[2], 16) if len(sys.argv) > 2 and sys.argv[2] not in ("none", "-") else None
    dump(p, x)
