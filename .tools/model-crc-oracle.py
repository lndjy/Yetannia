# model-crc-oracle.py — use the .manifest CRC as a ground-truth oracle for the decryption.
#
# The manifest is plaintext and carries 'CRC: <n>', which Unity computes over the bundle's
# uncompressed contents. If some CRC32 convention matches, the decryption is provably byte-exact
# and the exact prefix length N is pinned (all other N must mismatch).
#
# usage: python .tools/model-crc-oracle.py <bundle.data> <crc> [nlo nhi]
import os
import struct
import sys
import zlib

import lz4.block


def decompress(raw, n):
    buf = bytes(b ^ 0x7B for b in raw[:n]) + raw[n:]
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
    return b"".join(parts), nodes, buf


def candidates(data, nodes, buf, raw):
    cab = data[:nodes[0][1]] if nodes else data
    res = data[nodes[0][1]:] if len(nodes) > 1 else b""
    cand = {
        "data(all blocks concat)": data,
        "node0 only": cab,
        "node1 only": res,
        "decrypted bundle file": buf,
        "raw file": raw,
    }
    return cand


def main():
    path = sys.argv[1]
    want = int(sys.argv[2])
    nlo = int(sys.argv[3]) if len(sys.argv) > 3 else 974
    nhi = int(sys.argv[4]) if len(sys.argv) > 4 else 1013
    raw = open(path, "rb").read()
    print(f"target CRC = {want}  ({os.path.basename(path)})")
    for n in range(nlo, nhi):
        data, nodes, buf = decompress(raw, n)
        for name, blob in candidates(data, nodes, buf, raw).items():
            c = zlib.crc32(blob) & 0xFFFFFFFF
            flag = "   <<<<< MATCH" if c == want else ""
            if flag or n == nlo:
                print(f"  N={n:5d} {name:26s} crc={c:10d}{flag}")
            if flag:
                return


if __name__ == "__main__":
    main()
