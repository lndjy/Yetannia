# model-anim-probe7.py -- decisive dump of the streamed blob for one small clip.
# usage: python .tools/model-anim-probe7.py [clipName] [start] [count]
import os
import struct
import sys

import numpy as np
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
U3D = os.path.join(HERE, "out", "export", "pet__3015004_prefab",
                   "pet__3015004_prefab.unity3d")
WANT = sys.argv[1] if len(sys.argv) > 1 else "zd_jn_01_xl"
S = int(sys.argv[2]) if len(sys.argv) > 2 else 0
C = int(sys.argv[3]) if len(sys.argv) > 3 else 40


def f32(u):
    return struct.unpack("<f", struct.pack("<I", int(u) & 0xFFFFFFFF))[0]


env = UnityPy.load(U3D)
c = [o.read() for o in env.objects if o.type.name == "AnimationClip"
     and o.read().m_Name == WANT][0]
st = c.m_MuscleClip.m_Clip.data.m_StreamedClip
d = np.asarray(getattr(st, "data"), dtype=np.uint32)
N = int(getattr(st, "curveCount"))
print("%s words=%d curveCount=%d" % (WANT, d.size, N))
print("\nwords[%d:%d] as (int, float):" % (S, S + C))
for i in range(S, min(S + C, d.size)):
    print("   [%5d] %10d   %+.8g" % (i, int(d[i]), f32(d[i])))

print("\n--- parse A: block = [count][keys], key = {index, c0,c1,c2,c3} (index first) ---")
o = 1
blocks = []
ok = True
while o < d.size:
    cnt = int(d[o])
    o += 1
    if cnt > N + 4 or o + 5 * cnt > d.size + 0:
        ok = False
        print("   FAIL at word %d: count=%d" % (o - 1, cnt))
        break
    idxs = [int(d[o + 5 * j]) for j in range(cnt)]
    blocks.append((o - 1, cnt, idxs))
    o += 5 * cnt
print("   clean=%s consumed=%d/%d blocks=%d" % (ok, o, d.size, len(blocks)))
for b, (w, cnt, idxs) in enumerate(blocks[:14]):
    inc = all(idxs[i] < idxs[i + 1] for i in range(len(idxs) - 1))
    print("   block %3d @word %6d count=%4d idx[0..3]=%s idx[-2:]=%s increasing=%s inrange=%s"
          % (b, w, cnt, idxs[:4], idxs[-2:], inc, all(0 <= x < N for x in idxs)))
if len(blocks) > 14:
    print("   ...")
    for b in range(max(14, len(blocks) - 4), len(blocks)):
        w, cnt, idxs = blocks[b]
        print("   block %3d @word %6d count=%4d idx[0..3]=%s idx[-2:]=%s"
              % (b, w, cnt, idxs[:4], idxs[-2:]))

print("\n--- parse B: block = [count][time][keys], key={index,c0..c3} ---")
o = 1
blocks2 = []
ok2 = True
while o + 1 < d.size:
    cnt = int(d[o])
    t = f32(d[o + 1])
    o += 2
    if cnt > N + 4 or o + 5 * cnt > d.size:
        ok2 = False
        print("   FAIL at word %d: count=%d time=%g" % (o - 2, cnt, t))
        break
    idxs = [int(d[o + 5 * j]) for j in range(cnt)]
    blocks2.append((t, cnt, idxs))
    o += 5 * cnt
print("   clean=%s consumed=%d/%d blocks=%d" % (ok2, o, d.size, len(blocks2)))
for b, (t, cnt, idxs) in enumerate(blocks2[:14]):
    print("   block %3d time=%+.6f count=%4d idx[0..3]=%s idx[-2:]=%s"
          % (b, t, cnt, idxs[:4], idxs[-2:]))

print("\n--- parse C: block = [time][count][keys], key={index,c0..c3} ---")
o = 1
blocks3 = []
ok3 = True
while o + 1 < d.size:
    t = f32(d[o])
    cnt = int(d[o + 1])
    o += 2
    if cnt > N + 4 or o + 5 * cnt > d.size:
        ok3 = False
        print("   FAIL at word %d: time=%g count=%d" % (o - 2, t, cnt))
        break
    idxs = [int(d[o + 5 * j]) for j in range(cnt)]
    blocks3.append((t, cnt, idxs))
    o += 5 * cnt
print("   clean=%s consumed=%d/%d blocks=%d" % (ok3, o, d.size, len(blocks3)))
for b, (t, cnt, idxs) in enumerate(blocks3[:14]):
    print("   block %3d time=%+.6f count=%4d idx[0..3]=%s idx[-2:]=%s"
          % (b, t, cnt, idxs[:4], idxs[-2:]))
