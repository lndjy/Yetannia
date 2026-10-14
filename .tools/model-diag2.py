# model-diag2.py — handle per-block flags (0 = stored uncompressed) and re-solve tadatas.
#
# 301500401_prefab.data: last block is (usz=5700, csz=5700, flags=0) -> stored raw, not LZ4.
#   That was my decoder's bug, not a decryption failure.
# tadatas.data: every block decodes but crc32 != manifest; scan the prefix length for a CRC match.
#
# usage: python .tools/model-diag2.py
import importlib.util
import os
import struct
import sys
import zlib

import lz4.block

_spec = importlib.util.spec_from_file_location(
    "mva", r"D:\桌面\sts2mod\.tools\model-verify-all.py")
mva = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mva)


def block_data(blob, usz, flags):
    comp = flags & 0x3F
    if comp == 0:
        return bytes(blob[:usz])
    return lz4.block.decompress(bytes(blob), uncompressed_size=usz)


def full(path, n):
    raw = open(path, "rb").read()
    buf = mva.decrypt(raw, n)
    data_off, blks, nodes = mva.parse(buf)
    pos = data_off
    parts = []
    for (u, c, f) in blks:
        parts.append(block_data(buf[pos:pos + c], u, f))
        pos += c
    return b"".join(parts), blks, nodes, buf


print("=== 301500401_prefab.data with per-block flags honoured ===")
p = r"D:\桌面\sts2mod\model\pet\301500401_prefab.data"
data, blks, nodes, buf = full(p, 1000)
crc = zlib.crc32(data) & 0xFFFFFFFF
print(f"  data={len(data)} sum(usz)={sum(b[0] for b in blks)}")
print(f"  crc32(all data)={crc}  manifest={mva.manifest_crc(p + '.manifest')}  "
      f"{'MATCH' if crc == mva.manifest_crc(p + '.manifest') else 'DIFF'}")

print("\n=== tadatas.data prefix scan ===")
p2 = r"D:\桌面\sts2mod\model\tadatas.data"
want = mva.manifest_crc(p2 + ".manifest")
print(f"  manifest CRC = {want}")
raw = open(p2, "rb").read()
for n in (272, 273, 300, 512, 529, 700, 999, 1000, 1001, 1024, 1100, 2000, 4096):
    try:
        data, blks, nodes, buf = full(p2, n)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        print(f"  N={n:5d}: data={len(data):9d} crc={crc:10d} "
              f"{'<<<<< MATCH' if crc == want else ''}")
    except Exception as exc:
        print(f"  N={n:5d}: {type(exc).__name__}: {exc}")
