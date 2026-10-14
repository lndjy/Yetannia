# model-solve-prefix.py — find the XOR prefix length for any bundle, verified by its manifest CRC.
#
# The rule found on 3015004_prefab.data is "XOR the first 1000 bytes with 0x7b". Not every file need
# use the same length, so solve it per file:
#   1. Decrypt with N = end of blocksInfo (the header/table region is always XORed) to learn the block
#      table.
#   2. Slide N through block 0 (O(1) byte update) and keep the N for which block 0 still decompresses
#      to its declared size. Those bytes are LZ4 *literals*, so the surviving range is a superset.
#   3. Disambiguate with crc32(concatenated decompressed blocks) == manifest CRC.
#
# usage: python .tools/model-solve-prefix.py <bundle.data> [extraBlocks]
import os
import re
import struct
import sys
import zlib

import lz4.block

KEY = 0x7B
OUT = r"D:\桌面\sts2mod\.tools\out"


def parse_table(buf):
    off = 8 + 4
    e = buf.index(b"\x00", off); off = e + 1
    e = buf.index(b"\x00", off); off = e + 1
    size = struct.unpack_from(">q", buf, off)[0]; off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    flags = struct.unpack_from(">I", buf, off)[0]; off += 4
    bio = (off + 15) & ~15
    if size != len(buf):
        raise ValueError(f"declared size {size} != file size {len(buf)}")
    bi = lz4.block.decompress(bytes(buf[bio:bio + cbis]), uncompressed_size=ubis)
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
    data_off = bio + cbis
    assert sum(b[1] for b in blks) == len(buf) - data_off, "compressed sizes do not fill the file"
    assert sum(b[0] for b in blks) == sum(n[1] for n in nodes), "node sizes != block sizes"
    return data_off, blks, nodes


def block_offsets(data_off, blks):
    pos = data_off
    out = []
    for (u, c, f) in blks:
        out.append((pos, u, c, f))
        pos += c
    return out


def crc_of(buf, offs, upto=None):
    parts = []
    for (pos, u, c, f) in offs:
        parts.append(lz4.block.decompress(bytes(buf[pos:pos + c]), uncompressed_size=u))
    return zlib.crc32(b"".join(parts)) & 0xFFFFFFFF


def manifest_crc(p):
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    m = re.search(r"^CRC:\s*(\d+)", t, re.M)
    return int(m.group(1)) if m else None


def solve(path, extra_blocks=0):
    raw = open(path, "rb").read()
    want = manifest_crc(path + ".manifest")
    n0 = None
    # step 1: find a prefix long enough to cover header+blocksInfo
    for probe in (64, 529, 2048, 4096, 65536):
        buf = bytearray(bytes(b ^ KEY for b in raw[:probe]) + raw[probe:])
        try:
            data_off, blks, nodes = parse_table(buf)
        except Exception:
            continue
        # blocksInfo starts at data_off - cbis; ensure probe >= that
        n0 = probe
        break
    if n0 is None:
        print(f"{os.path.basename(path)}: cannot even parse the header/table")
        return None
    offs = block_offsets(data_off, blks)
    print(f"{os.path.basename(path)}: {len(raw)}B, {len(blks)} blocks, data@{data_off}, "
          f"manifest CRC={want}")

    # step 2: slide N through block 0 (optionally further).
    # Invariant at the top of each iteration: buf == decrypt(raw, n) == raw[:n]^KEY + raw[n:].
    # Moving n -> n+1 only xors byte n, so the update is O(1) instead of rebuilding a 6 MB buffer.
    last = 0
    limit = offs[min(len(offs) - 1, extra_blocks)][0] + offs[min(len(offs) - 1, extra_blocks)][2]
    buf = bytearray(bytes(b ^ KEY for b in raw[:data_off]) + raw[data_off:])
    cands = []
    for n in range(data_off, min(limit, len(raw))):
        # test every block that straddles the boundary (blocks fully after n are untouched)
        ok = True
        for (pos, u, c, f) in offs:
            if pos >= n:
                break
            try:
                lz4.block.decompress(bytes(buf[pos:pos + c]), uncompressed_size=u)
            except Exception:
                ok = False
                break
        if ok:
            cands.append(n)
        if n + 1 < len(raw):
            buf[n] = raw[n] ^ KEY             # byte n becomes xored -> decrypt(raw, n+1)
    print(f"  candidate N (all blocks to the boundary decompress): "
          f"{cands[0] if cands else None}..{cands[-1] if cands else None} ({len(cands)} values)")

    # step 3: CRC disambiguation
    for n in cands:
        b2 = bytes(b ^ KEY for b in raw[:n]) + raw[n:]
        crc = crc_of(b2, offs)
        if want is None or crc == want:
            print(f"  *** N={n} CRC {'MATCH' if want is not None else '(no manifest)'} crc={crc}")
            if want is not None:
                out = os.path.join(OUT, os.path.splitext(os.path.basename(path))[0] +
                                   ".decrypted.unity3d")
                os.makedirs(os.path.dirname(out), exist_ok=True)
                open(out, "wb").write(b2)
                print(f"      wrote {out}")
            return n
    print(f"  no CRC match among candidates (checked {len(cands)})")
    return None


if __name__ == "__main__":
    solve(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0)
