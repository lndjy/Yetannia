# model-anim-probe.py -- crack the dense/streamed/constant clip layout for the pet clips.
#
# Question: m_DenseClip.m_CurveCount (656 for zd_daiji) does NOT equal
# sum-over-bindings of channel width (245 paths x 10 = 2450). So where do the curves live?
#
# Method 1 (the sharp oracle): a quaternion is a unit 4-vector. If the dense sample array packs
#   [pos(3) rot(4) scale(3)] per animated binding then, inside one frame, the offsets that start a
#   quaternion are periodic with period 10 and phase 3. Any wrong layout grabs arbitrary floats and
#   their 4-norm is not 1. So: scan every offset in a frame, print |q|-1, and read off the period.
# Method 2: decode the StreamedClip's explicit curve indices to learn the curve-index space.
#
# usage: python .tools/model-anim-probe.py
import json
import os
import zlib
from collections import Counter

import numpy as np
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = os.path.join(HERE, "out", "export", "pet__3015004_prefab")
U3D = os.path.join(BUNDLE_DIR, "pet__3015004_prefab.unity3d")
HIER = os.path.join(BUNDLE_DIR, "hierarchy.json")


def crc32u(s):
    return zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF


def gg(o, *names, **kw):
    d = kw.get("default")
    for n in names:
        v = getattr(o, n, None)
        if v is not None:
            return v
    return d


# ---------------------------------------------------------------- hierarchy chains
h = json.load(open(HIER, encoding="utf-8"))
entries = h["hierarchies"][list(h["hierarchies"])[0]]
stack, chains = [], []
for e in entries:
    d = e.get("depth", 0)
    del stack[d:]
    stack.append(e.get("name") or "")
    chains.append(tuple(stack))

hash_to_chain, hash_to_tid = {}, {}
for e, ch in zip(entries, chains):
    sub = ch[2:]                      # strip '3015004_prefab' and 'mx_3015004_01'
    if sub:
        hash_to_chain[crc32u("/".join(sub))] = "/".join(sub)
        hash_to_tid[crc32u("/".join(sub))] = e["transform"]
print("hierarchy: %d entries, %d usable chains" % (len(entries), len(hash_to_chain)))

env = UnityPy.load(U3D)
clips = [o.read() for o in env.objects if o.type.name == "AnimationClip"]
clips.sort(key=lambda c: c.m_Name)


def dense_of(c):
    return c.m_MuscleClip.m_Clip.data.m_DenseClip


def streamed_of(c):
    return c.m_MuscleClip.m_Clip.data.m_StreamedClip


def constant_of(c):
    return c.m_MuscleClip.m_Clip.data.m_ConstantClip


print("\n=== per-clip geometry ===")
for c in clips:
    b = c.m_ClipBindingConstant
    gb = list(gg(b, "genericBindings", default=[]) or [])
    attrs = Counter(x.attribute for x in gb)
    paths = set(x.path & 0xFFFFFFFF for x in gb)
    dn, st, cn = dense_of(c), streamed_of(c), constant_of(c)
    sa = np.asarray(gg(dn, "m_SampleArray", default=[]) or [], dtype=np.float64)
    print("%-16s bindings=%4d uniqPaths=%4d attrs=%s" % (c.m_Name, len(gb), len(paths),
                                                          dict(sorted(attrs.items()))))
    print("      dense  curves=%5s frames=%5s rate=%s begin=%s samples=%7d  (curves*frames=%s)"
          % (gg(dn, "m_CurveCount"), gg(dn, "m_FrameCount"), gg(dn, "m_SampleRate"),
             gg(dn, "m_BeginTime"), len(sa), gg(dn, "m_CurveCount") * gg(dn, "m_FrameCount")))
    print("      stream curves=%s discrete=%s datalen=%s | const datalen=%s"
          % (gg(st, "curveCount"), gg(st, "discreteCurveCount"),
             len(gg(st, "data", default=[]) or []), len(gg(cn, "data", default=[]) or [])))
    unres = [p & 0xFFFFFFFF for p in paths if (p & 0xFFFFFFFF) not in hash_to_chain]
    print("      unresolved paths: %d" % len(unres))

# ---------------------------------------------------------------- unit-quaternion scan
print("\n=== unit-quaternion scan on dense frame 0 (period + phase of rotation blocks) ===")
for c in clips:
    dn = dense_of(c)
    cc = int(gg(dn, "m_CurveCount", default=0) or 0)
    fc = int(gg(dn, "m_FrameCount", default=0) or 0)
    sa = np.asarray(gg(dn, "m_SampleArray", default=[]) or [], dtype=np.float64)
    if cc == 0 or sa.size != cc * fc:
        print("%-16s skipped (cc=%d fc=%d size=%d)" % (c.m_Name, cc, fc, sa.size))
        continue
    F = sa.reshape(fc, cc)
    hits = []
    for f in (0, fc // 3, fc - 1):
        row = F[f]
        for o in range(0, cc - 3):
            n = float(np.linalg.norm(row[o:o + 4]))
            if abs(n - 1.0) < 2e-3:
                hits.append((f, o))
    offs = sorted(set(o for _f, o in hits))
    if not offs:
        print("%-16s cc=%4d NO unit-quaternion offsets in any sampled frame" % (c.m_Name, cc))
        continue
    dif = np.diff(offs)
    per = Counter(dif.tolist()).most_common(4)
    print("%-16s cc=%4d unit-offsets=%3d first=%s last=%s  step-histogram=%s"
          % (c.m_Name, cc, len(offs), offs[:6], offs[-3:], per))

# ---------------------------------------------------------------- streamed curve ids
print("\n=== streamed clip curve-ID space ===")
for c in clips:
    st = streamed_of(c)
    dat = gg(st, "data", default=[]) or []
    if not dat:
        continue
    arr = np.asarray(dat, dtype=np.uint32)
    print("%-16s curveCount=%s discrete=%s  uint32-words=%d  max=%d  min=%d"
          % (c.m_Name, gg(st, "curveCount"), gg(st, "discreteCurveCount"), arr.size,
             int(arr.max()), int(arr.min())))
    print("      first 40 words:", arr[:40].tolist() if arr.size >= 40 else arr.tolist())

# ---------------------------------------------------------------- binding order
print("\n=== binding order sanity (zd_daiji) ===")
c = [x for x in clips if x.m_Name == "zd_daiji"][0]
gb = list(gg(c.m_ClipBindingConstant, "genericBindings", default=[]) or [])
print("first 12 bindings (path->chain, attribute):")
for x in gb[:12]:
    p = x.path & 0xFFFFFFFF
    print("   %-10d attr=%d typeID=%s classID=%s customType=%s  %s"
          % (p, x.attribute, getattr(x, "typeID", None), getattr(x, "classID", None),
             getattr(x, "customType", None), hash_to_chain.get(p, "UNRESOLVED")))
seq = [(x.path & 0xFFFFFFFF, x.attribute) for x in gb]
print("is sorted by (path,attr)?", seq == sorted(seq))
print("first 20 (path,attr):", seq[:20])
