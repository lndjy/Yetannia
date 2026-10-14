# model-transform-hunt.py — try every plausible body transform on data block 0.
#
# We know: header (0..50) and blocksInfo (64..529) are correct under XOR 0x7b, and blocksInfo yields a
# self-consistent table. Block 0 under XOR 0x7b decodes a perfect SerializedFile header then breaks.
# So the body transform is *almost* XOR 0x7b. Enumerate the near misses.
#
# usage: python .tools/model-transform-hunt.py <bundle>
import lzma
import struct
import sys
import zlib

import lz4.block

sys.path.insert(0, r"D:\桌面\sts2mod\.tools")
from importlib import import_module


def parse(buf):
    off = 8
    off += 4
    e = buf.index(b"\x00", off); off = e + 1
    e = buf.index(b"\x00", off); off = e + 1
    off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    off += 4
    bio = (off + 15) & ~15
    bi = lz4.block.decompress(buf[bio:bio + cbis], uncompressed_size=ubis)
    p = 16
    n = struct.unpack_from(">i", bi, p)[0]; p += 4
    blks = []
    for _ in range(n):
        u, c, f = struct.unpack_from(">IIH", bi, p); p += 10
        blks.append((u, c, f))
    return bio + cbis, blks


def main():
    path = sys.argv[1]
    raw = open(path, "rb").read()
    body = bytes(b ^ 0x7B for b in raw)          # the XOR-0x7b interpretation
    data_off, blks = parse(body)
    usz, csz, fl = blks[0]
    print(f"block0: usz={usz} csz={csz} fl={fl} @{data_off}")
    ct = body[data_off:data_off + csz]           # ciphertext-as-if-whole-file-xor
    ctr = raw[data_off:data_off + csz]           # raw stored bytes

    def try_lz4(label, blob):
        try:
            out = lz4.block.decompress(blob, uncompressed_size=usz)
            print(f"  [LZ4    ] {label}: OK {len(out)} bytes")
            return out
        except Exception as exc:
            print(f"  [LZ4    ] {label}: {type(exc).__name__}")
            return None

    def try_other(label, blob):
        hits = []
        for nm, fn in (("lzma", lambda b: lzma.decompress(b)),
                       ("lzma_raw", lambda b: lzma.LZMADecompressor().decompress(b)),
                       ("zlib", lambda b: zlib.decompress(b)),
                       ("raw-deflate", lambda b: zlib.decompress(b, -15)),
                       ("bz2", lambda b: __import__("bz2").decompress(b))):
            try:
                out = fn(blob)
                hits.append((nm, len(out)))
            except Exception:
                pass
        try:
            import brotli
            hits.append(("brotli", len(brotli.decompress(blob))))
        except Exception:
            pass
        try:
            import zstandard
            hits.append(("zstd", len(zstandard.ZstdDecompressor().decompress(blob))))
        except Exception:
            pass
        print(f"  [other  ] {label}: {hits if hits else 'no codec accepts it'}")

    print("\n-- A: whole-file XOR 0x7b (known)", )
    try_lz4("xor7b", ct)
    print("-- B: body left plain (header+blocksInfo only XORed)")
    try_lz4("plain", ctr)
    print("-- C: per-block single-byte key")
    wins = []
    for k in range(256):
        cand = bytes(b ^ k for b in ctr)
        try:
            out = lz4.block.decompress(cand, uncompressed_size=usz)
            wins.append((k, len(out)))
        except Exception:
            pass
    print(f"   single-byte keys that decompress block0: {wins}")

    print("-- D: block0 under XOR 0x7b, other codecs")
    try_other("xor7b", ct)
    try_other("plain", ctr)

    print("-- E: skip-zero XOR variants on raw")
    def skipzero_enc(b):
        return bytes((x ^ 0x7B) if x else 0 for x in b)

    def skipzero_dec(b):
        return bytes((x ^ 0x7B) if x else 0 for x in b)
    try_lz4("skipzero", skipzero_dec(ctr))

    print("-- F: how far does xor7b block0 get, and is the output sane?")
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "mbp", r"D:\桌面\sts2mod\.tools\model-block-probe.py")
    mbp = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(mbp)
    out, status, fail = mbp.lz4_decode(ct)
    print(f"   produced {len(out)}/{usz}; died rel {fail}; {status}")
    print(f"   input abs die = {data_off + fail}")
    open(r"D:\桌面\sts2mod\.tools\out\block0_partial.bin", "wb").write(out)
    for i in range(0, min(len(out), 1229), 16):
        chunk = out[i:i + 16]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"   {i:05x}  {hx:<47}  {asc}")
    # find where readable strings stop appearing
    printable_runs = []
    cur = b""
    start = 0
    for i, b in enumerate(out):
        if 32 <= b < 127:
            if not cur:
                start = i
            cur += bytes([b])
        else:
            if len(cur) >= 5:
                printable_runs.append((start, cur.decode()))
            cur = b""
    print(f"   readable strings in partial output: {printable_runs[:60]}")


if __name__ == "__main__":
    main()
