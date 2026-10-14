# model-diag.py — why do 301500401_prefab.data and tadatas.data differ from their manifest CRCs?
#
# usage: python .tools/model-diag.py
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


def diag(path):
    raw = open(path, "rb").read()
    buf = mva.decrypt(raw)
    data_off, blks, nodes = mva.parse(buf)
    print(f"--- {os.path.basename(path)}  len={len(raw)} data_off={data_off}")
    print(f"    blocks={len(blks)} sum(csz)={sum(b[1] for b in blks)} avail={len(buf) - data_off} "
          f"sum(usz)={sum(b[0] for b in blks)} sum(node size)={sum(n[1] for n in nodes)}")
    print(f"    last 3 blocks (usz,csz,flags): {blks[-3:]}")
    print(f"    nodes: {[(n[3], n[1], n[2]) for n in nodes]}")
    pos = data_off
    parts = []
    for i, (u, c, f) in enumerate(blks):
        try:
            parts.append(lz4.block.decompress(buf[pos:pos + c], uncompressed_size=u))
        except Exception as exc:
            print(f"    block {i}: {type(exc).__name__} usz={u} csz={c} filepos={pos} "
                  f"end={pos + c} (file len {len(buf)})")
        pos += c
    data = b"".join(parts)
    print(f"    decompressed {len(data)} of {sum(b[0] for b in blks)} bytes")
    print(f"    crc32(all data) = {zlib.crc32(data) & 0xffffffff}   manifest = {mva.manifest_crc(path + '.manifest')}")
    if nodes:
        n0 = nodes[0][1]
        print(f"    crc32(node0)={zlib.crc32(data[:n0]) & 0xffffffff} "
              f"crc32(node1)={zlib.crc32(data[n0:]) & 0xffffffff}")
    print(f"    crc32(decrypted bundle file) = {zlib.crc32(buf) & 0xffffffff}")
    # where does the last (failing) block start in the raw file?
    pos = data_off
    for i, (u, c, f) in enumerate(blks):
        if i == len(blks) - 1:
            print(f"    last block spans file bytes {pos}..{pos + c}")
        pos += c
    print()


for p in (r"D:\桌面\sts2mod\model\pet\301500401_prefab.data",
          r"D:\桌面\sts2mod\model\tadatas.data",
          r"D:\桌面\sts2mod\model\pet\3015004_prefab.data"):
    diag(p)
