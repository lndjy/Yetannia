# model-batch-crack.py — verify the "XOR first 1000 bytes with 0x7b" rule against every manifest CRC.
#
# Each .data has a plaintext .manifest carrying the CRC Unity computed over the uncompressed bundle
# contents. Matching that CRC proves the decryption is byte-exact, so this doubles as the regression
# test for the whole set and as a check that no file uses a different prefix length.
#
# usage: python .tools/model-batch-crack.py [root]
import glob
import os
import re
import struct
import sys
import zlib

import lz4.block


def decompress(buf):
    off = 8 + 4
    e = buf.index(b"\x00", off); off = e + 1
    e = buf.index(b"\x00", off); off = e + 1
    off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    off += 4
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
    return b"".join(parts), nodes


def decrypt(raw, n):
    return bytes(b ^ 0x7B for b in raw[:n]) + raw[n:]


def manifest_crc(path):
    try:
        txt = open(path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    m = re.search(r"^CRC:\s*(\d+)", txt, re.M)
    return int(m.group(1)) if m else None


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else r"D:\桌面\sts2mod\model"
    files = sorted(glob.glob(os.path.join(root, "**", "*.data"), recursive=True))
    print(f"{len(files)} .data files\n")
    for path in files:
        raw = open(path, "rb").read()
        want = manifest_crc(path + ".manifest")
        rel = os.path.relpath(path, root)
        found = None
        for n in (1000,):
            try:
                data, nodes = decompress(decrypt(raw, n))
            except Exception as exc:
                print(f"{rel:52s} N={n} FAILED {type(exc).__name__}: {exc}")
                continue
            got = zlib.crc32(data) & 0xFFFFFFFF
            if want is not None and got == want:
                found = (n, len(data), nodes)
                break
            print(f"{rel:52s} N={n} crc {got} != {want}")
        if found:
            n, dlen, nodes = found
            print(f"{rel:52s} OK  N={n}  data={dlen}B  nodes={[x[3] for x in nodes]}")
        elif want is None:
            print(f"{rel:52s} no manifest CRC to check against")


if __name__ == "__main__":
    main()
