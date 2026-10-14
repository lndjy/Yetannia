# model-anim-probe5.py -- brute-force the streamed clip's byte layout.
#
# Unity 4.3 source (Runtime/mecanim/animation/streamedclip.h) documents the SEMANTICS exactly:
#     struct CurveTimeData { float time; UInt32 count; };            // 8 bytes
#     struct CurveKey      { int curveIndex; float coeff[4]; };      // 20 bytes
#     stream = CurveTimeData followed by count CurveKey, repeated; keys sorted by time.
# The 2019 blob additionally starts with magic 0xFF7FFFFF then curveCount, and is NOT plain floats
# (total bytes / (curves*frames) is ~2.5, so it is quantised/packed). This script brute-forces the
# layout: try every start offset, both field orders, several CurveKey layouts, and score each parse
# by how much of the blob it consumes with non-decreasing times.
#
# usage: python .tools/model-anim-probe5.py
import os
import struct

import numpy as np
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
U3D = os.path.join(HERE, "out", "export", "pet__3015004_prefab",
                   "pet__3015004_prefab.unity3d")


def f32(u):
    return struct.unpack("<f", struct.pack("<I", int(u) & 0xFFFFFFFF))[0]


env = UnityPy.load(U3D)
clips = sorted([o.read() for o in env.objects if o.type.name == "AnimationClip"],
               key=lambda c: c.m_Name)

for c in clips:
    st = c.m_MuscleClip.m_Clip.data.m_StreamedClip
    d = np.asarray(getattr(st, "data"), dtype=np.uint32)
    N = int(getattr(st, "curveCount"))
    print("=" * 100)
    print("%s words=%d curveCount=%d  (bytes=%d)" % (c.m_Name, d.size, N, d.size * 4))
    print("  words[0:24]:", d[:24].tolist())
    print("  as float32 :", [round(f32(x), 6) for x in d[:24]])

    # --- parse attempt: header words H, then blocks [t][c][keys...]
    best = []
    for H in range(0, 8):
        for order in ("tc", "ct"):
            for klen in (5, 4, 6):
                o = H
                times = []
                nkeys = 0
                nblocks = 0
                ok = True
                while o + 1 < d.size:
                    a, b = int(d[o]), int(d[o + 1])
                    t = f32(a) if order == "tc" else f32(b)
                    cnt = b if order == "tc" else a
                    if cnt < 0 or cnt > N + 8 or not np.isfinite(t):
                        ok = False
                        break
                    if times and t < times[-1] - 1e-4:
                        ok = False
                        break
                    times.append(t)
                    nkeys += cnt
                    nblocks += 1
                    o += 2 + klen * cnt
                    if o > d.size:
                        ok = False
                        break
                best.append((o, ok, nblocks, nkeys, H, order, klen))
    best.sort(key=lambda x: -x[0])
    print("  best parses (words-consumed, clean, blocks, keys, header, order, keylen):")
    for b in best[:6]:
        print("     consumed=%5d/%5d clean=%-5s blocks=%5d keys=%5d H=%d order=%s klen=%d"
              % (b[0], d.size, b[1], b[2], b[3], b[4], b[5], b[6]))
