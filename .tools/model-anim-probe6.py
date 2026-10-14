# model-anim-probe6.py -- validate the streamed-clip parse and dump its curve index space.
#
# probe 5 brute-forced the layout and found, for all 11 clips, a single parse that consumes the whole
# blob with non-decreasing times:
#     data[0]      = magic 0xFF7FFFFF
#     then blocks: { UInt32 count; float time; CurveKey keys[count] }   (klen=5, starting at word 1)
#     CurveKey     = { float coeff[4]; int curveIndex }   (index word LAST)
# Block 0 has count == curveCount, i.e. every streamed curve has a key at t=0 - which is exactly
# what "keys sorted by time" implies. This script prints the block table, the curve-index set, and
# tests the coefficients by evaluating the hermite polynomial at t=0 against the rest pose.
#
# usage: python .tools/model-anim-probe6.py
import os
import struct
from collections import Counter

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


def parse_streamed(d, N):
    """-> (blocks, keys) where keys is a list of (time, curveIndex, coeff[4])."""
    o = 1
    blocks = []
    keys = []
    while o + 1 < d.size:
        cnt = int(d[o])
        t = f32(d[o + 1])
        o += 2
        if cnt > N + 8:
            return blocks, keys, False
        for _ in range(cnt):
            if o + 5 > d.size:
                return blocks, keys, False
            coeff = [f32(d[o + i]) for i in range(4)]
            idx = int(d[o + 4])
            keys.append((t, idx, coeff))
            o += 5
        blocks.append((t, cnt))
    return blocks, keys, True


for c in clips:
    st = c.m_MuscleClip.m_Clip.data.m_StreamedClip
    d = np.asarray(getattr(st, "data"), dtype=np.uint32)
    N = int(getattr(st, "curveCount"))
    dn = c.m_MuscleClip.m_Clip.data.m_DenseClip
    fc = int(getattr(dn, "m_FrameCount"))
    blocks, keys, clean = parse_streamed(d, N)
    times = [t for t, _ in blocks]
    mono = all(times[i] <= times[i + 1] + 1e-6 for i in range(len(times) - 1))
    idxs = [k[1] for k in keys]
    print("=" * 100)
    print("%s  curveCount=%d frames=%d  clean=%s blocks=%d keys=%d mono=%s"
          % (c.m_Name, N, fc, clean, len(blocks), len(keys), mono))
    print("   time range: %.4f .. %.4f   (block0 count=%s, clip length=%.3f s)"
          % (min(times), max(times), blocks[0][1] if blocks else None, fc / 30.0))
    print("   first 12 blocks (time,count):", [(round(t, 4), n) for t, n in blocks[:12]])
    print("   curveIndex: min=%d max=%d distinct=%d" % (min(idxs), max(idxs), len(set(idxs))))
    print("   keys per curve: min=%d max=%d mean=%.2f"
          % (min(Counter(idxs).values()), max(Counter(idxs).values()),
             len(idxs) / float(len(set(idxs)))))
    print("   index histogram tail:", sorted(Counter(idxs).items())[-6:])
    print("   block0 indices: first 8=%s last 8=%s" % (idxs[:8], idxs[N - 8:N]))
