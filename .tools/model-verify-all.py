# model-verify-all.py — the definitive check: N=1000 prefix XOR, then LZ4, then manifest CRC, then UnityPy.
#
# The cipher is: XOR the first 1000 bytes with 0x7b, leave every other byte alone.
# Evidence:
#   * blocksInfo decompresses only for a prefix end in [523..529] (3015004) / [1000..1003] (301500401),
#     i.e. ~1000, never 0, never 1024, never "whole file".
#   * crc32(concatenated decompressed blocks) == the .manifest CRC exactly, at N=1000 and nowhere else.
#
# usage: python .tools/model-verify-all.py [root]
import glob
import os
import re
import struct
import sys
import zlib

import lz4.block
import UnityPy

KEY = 0x7B
N = 1000
OUT = r"D:\桌面\sts2mod\.tools\out"


def decrypt(raw, n=N):
    return bytes(b ^ KEY for b in raw[:n]) + raw[n:]


def parse(buf):
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
    return bio + cbis, blks, nodes


def manifest_crc(p):
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    m = re.search(r"^CRC:\s*(\d+)", t, re.M)
    return int(m.group(1)) if m else None


def run(path, root):
    rel = os.path.relpath(path, root)
    raw = open(path, "rb").read()
    want = manifest_crc(path + ".manifest")
    rec = {"file": rel, "bytes": len(raw), "manifest_crc": want}
    try:
        buf = decrypt(raw)
        data_off, blks, nodes = parse(buf)
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
        return rec, None
    rec["blocks"] = len(blks)
    rec["nodes"] = [n[3] for n in nodes]
    pos = data_off
    parts, bad = [], []
    for i, (u, c, f) in enumerate(blks):
        # flags low 6 bits = compression: 0 = stored, 1 = LZMA, 2 = LZ4, 3 = LZ4HC.
        # 301500401_prefab's LAST block is flags=0 (5700/5700 stored) — feeding it to
        # lz4.block raises LZ4BlockError and loses 5700 bytes, which silently breaks the CRC.
        comp = f & 0x3F
        try:
            if comp == 0:
                assert c == u, f"stored block {i} c={c} != u={u}"
                parts.append(buf[pos:pos + c])
            elif comp == 2 or comp == 3:
                parts.append(lz4.block.decompress(buf[pos:pos + c], uncompressed_size=u))
            else:
                raise ValueError(f"unsupported compression {comp}")
        except Exception as exc:
            bad.append((i, type(exc).__name__))
        pos += c
    rec["bad_blocks"] = bad
    data = b"".join(parts)
    rec["data_bytes"] = len(data)
    crc = zlib.crc32(data) & 0xFFFFFFFF
    rec["crc"] = crc
    rec["crc_match"] = (want is None or crc == want)
    os.makedirs(OUT, exist_ok=True)
    dec = os.path.join(OUT, os.path.basename(path).replace(".data", "") + ".decrypted.unity3d")
    open(dec, "wb").write(buf)
    rec["decrypted"] = dec
    if not bad:
        try:
            env = UnityPy.load(dec)
            kinds = {}
            for o in env.objects:
                kinds[o.type.name] = kinds.get(o.type.name, 0) + 1
            rec["objects"] = len(env.objects)
            rec["kinds"] = kinds
        except Exception as exc:
            rec["unitypy_error"] = f"{type(exc).__name__}: {exc}"
    return rec, (buf if not bad else None)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else r"D:\桌面\sts2mod\model"
    files = sorted(glob.glob(os.path.join(root, "**", "*.data"), recursive=True))
    print(f"{'file':50s} {'crc':>6s} {'blocks':>7s} {'objs':>6s}  detail")
    for path in files:
        rec, _ = run(path, root)
        ok = "OK " if rec.get("crc_match") and not rec.get("bad_blocks") else "!! "
        print(f"{ok}{rec['file']:47s} "
              f"{'match' if rec.get('crc_match') else 'DIFF':>6s} "
              f"{rec.get('blocks', '-'):>7} {rec.get('objects', '-'):>6}  "
              f"{rec.get('nodes', rec.get('error', ''))}")
        if rec.get("bad_blocks"):
            print(f"      bad blocks: {rec['bad_blocks'][:6]}")
        if rec.get("unitypy_error"):
            print(f"      UnityPy: {rec['unitypy_error']}")


if __name__ == "__main__":
    main()
