# model-boundary-scan.py — locate where the 0x7b XOR stops being correct.
#
# Block 0 decodes 1229 perfectly-valid SerializedFile bytes (type tree with 'm_ExecutionOrder',
# 'Hash128') and then hits a back-reference of 31599 with only 1229 bytes of history. Everything is
# right up to that point, so either a boundary or a local corruption starts there. Scan both.
#
# usage: python .tools/model-boundary-scan.py <bundle>
import struct
import sys

import lz4.block

sys.path.insert(0, r"D:\桌面\sts2mod\.tools")


def parse(raw):
    body = bytes(b ^ 0x7B for b in raw)
    off = 8 + 4
    e = body.index(b"\x00", off); off = e + 1
    e = body.index(b"\x00", off); off = e + 1
    off += 8
    cbis = struct.unpack_from(">I", body, off)[0]; off += 4
    ubis = struct.unpack_from(">I", body, off)[0]; off += 4
    off += 4
    bio = (off + 15) & ~15
    bi = lz4.block.decompress(body[bio:bio + cbis], uncompressed_size=ubis)
    p = 16
    n = struct.unpack_from(">i", bi, p)[0]; p += 4
    blks = []
    for _ in range(n):
        u, c, f = struct.unpack_from(">IIH", bi, p); p += 10
        blks.append((u, c, f))
    return bio + cbis, blks


def try_dec(blob, usz):
    try:
        return len(lz4.block.decompress(blob, uncompressed_size=usz))
    except Exception:
        return None


def main():
    path = sys.argv[1]
    raw = open(path, "rb").read()
    data_off, blks = parse(raw)
    print(f"data_off={data_off} blocks={len(blks)}")

    print("\n== A: per-block, XOR-0x7b vs plain ==")
    pos = data_off
    xorok = plainok = 0
    for i, (usz, csz, fl) in enumerate(blks):
        seg = raw[pos:pos + csz]
        if try_dec(bytes(b ^ 0x7B for b in seg), usz) is not None:
            xorok += 1
        if try_dec(seg, usz) is not None:
            plainok += 1
        pos += csz
    print(f"   whole-block: xor7b ok={xorok}/{len(blks)}, plain ok={plainok}/{len(blks)}")

    # ---- block 0 boundary scans ----
    usz0, csz0, _ = blks[0]
    s, e = data_off, data_off + csz0
    print(f"\n== B: block 0 boundary scan (block bytes {s}..{e}, usz={usz0}) ==")

    print("   B1: plain for [s,N), xor7b for [N,e)")
    hits = []
    for N in range(s, e + 1, 1):
        blob = raw[s:N] + bytes(b ^ 0x7B for b in raw[N:e])
        if try_dec(blob, usz0) is not None:
            hits.append(N)
    print(f"   -> {len(hits)} hits: {hits[:10]}")

    print("   B2: xor7b for [s,N), plain for [N,e)")
    hits = []
    for N in range(s, e + 1, 1):
        blob = bytes(b ^ 0x7B for b in raw[s:N]) + raw[N:e]
        if try_dec(blob, usz0) is not None:
            hits.append(N)
    print(f"   -> {len(hits)} hits: {hits[:10]}")

    print("   B3: xor7b for [s,N), xor k for [N,e)  -- which k? at candidate N near 1011")
    for N in (data_off + 482, data_off + 483, data_off + 484, data_off + 512,
              data_off + 1024, data_off + 443):
        good = [k for k in range(256)
                if try_dec(bytes(b ^ 0x7B for b in raw[s:N]) + bytes(b ^ k for b in raw[N:e]),
                           usz0) is not None]
        print(f"     N={N} (rel {N - s}): keys {good}")

    # ---- where exactly does a single-byte repair fix it? ----
    print("\n== C: single-byte repair scan around the failure ==")
    base = bytes(b ^ 0x7B for b in raw[s:e])
    found = []
    for p in range(400, 600):
        for v in range(256):
            if v == base[p]:
                continue
            cand = base[:p] + bytes([v]) + base[p + 1:]
            if try_dec(cand, usz0) is not None:
                found.append((p, base[p], v))
    print(f"   single-byte repairs that make block 0 fully valid: {found[:20]}")


if __name__ == "__main__":
    main()
