# model-anim-probe4.py -- pin down the exact section boundaries + look inside the streamed clip.
#
# probe 3 proved the layout convention from the constant clip of zd_daiji:
#   array = [ localPosition 3*nPos ][ localRotation 4*nRot ][ localScale 3*nScale ]
#   * every "rest localRotation" exact match sat at offsets == 3 (mod 4) -> attribute-MAJOR order,
#   * the matched bones came out in increasing binding order -> filtered binding order inside a
#     section,
#   * for zd_daiji: 3*101 + 4*65 + 3*244 = 303 + 260 + 732 = 1295 = len(constant) exactly,
#     and 3*101 = 303 == 3 (mod 4), 4*65 = 260, 3*244 = 732.
# So a section boundary is detectable from the data alone: the rotation section is the run of
# 4-strided unit quaternions, the scale section the 1.0-ish triples after it.
#
# usage: python .tools/model-anim-probe4.py
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


h = json.load(open(HIER, encoding="utf-8"))
entries = h["hierarchies"][list(h["hierarchies"])[0]]
stack, chains = [], []
for e in entries:
    d = e.get("depth", 0)
    del stack[d:]
    stack.append(e.get("name") or "")
    chains.append(tuple(stack))
tid_of = {}
for e, ch in zip(entries, chains):
    if len(ch) > 2:
        tid_of[crc32u("/".join(ch[2:]))] = e["transform"]

env = UnityPy.load(U3D)
clips = sorted([o.read() for o in env.objects if o.type.name == "AnimationClip"],
               key=lambda c: c.m_Name)


def sections(arr, tag):
    """Find [nPos, nRot, nScale] of a storage array from the data's own structure."""
    L = len(arr)
    # rotation candidates: 4-window that is a unit quaternion in a step-4 lattice
    unit = np.zeros(max(0, L - 3), dtype=bool)
    for j in range(L - 3):
        unit[j] = abs(float(np.linalg.norm(arr[j:j + 4])) - 1.0) < 1e-3
    best_len, best = 0, None
    for p in range(4):
        # longest step-4 run starting at phase p
        j = p
        while j < len(unit):
            if unit[j]:
                k = j
                while k + 4 < len(unit) and unit[k + 4]:
                    k += 4
                if k - j + 1 > best_len:
                    best_len, best = k - j + 1, (j, k)
                j = k + 4
            j += 1
    if best is None:
        return None
    rs, re_ = best
    nRot = (re_ - rs) // 4 + 1
    nPos = rs // 3 if rs % 3 == 0 else None
    tail = L - (rs + 4 * nRot)
    nScale = tail // 3 if tail % 3 == 0 else None
    print("   %-9s len=%5d  rot-section=[%4d,%4d) nRot=%3d | nPos=%s (3*nPos=%s) | tail=%d nScale=%s"
          % (tag, L, rs, rs + 4 * nRot, nRot, nPos, rs, tail, nScale))
    return nPos, nRot, nScale


print("=== section boundaries per clip ===")
for c in clips:
    gb = list(gg(c.m_ClipBindingConstant, "genericBindings", default=[]) or [])
    n = len(set(x.path & 0xFFFFFFFF for x in gb))
    dn = c.m_MuscleClip.m_Clip.data.m_DenseClip
    cn = np.asarray(gg(c.m_MuscleClip.m_Clip.data.m_ConstantClip, "data", default=[]) or [],
                    dtype=np.float64)
    st = c.m_MuscleClip.m_Clip.data.m_StreamedClip
    cc = int(gg(dn, "m_CurveCount", default=0) or 0)
    fc = int(gg(dn, "m_FrameCount", default=0) or 0)
    F = np.asarray(gg(dn, "m_SampleArray", default=[]) or [], dtype=np.float64).reshape(fc, cc)
    print("%s  paths=%d dense=%d frames=%d streamed=%s const=%d T=%d"
          % (c.m_Name, n, cc, fc, gg(st, "curveCount"), cn.size, 10 * n))
    # dense: use frame rows; a column is a rotation column if it is inside the 4-lattice run
    dn_sec = sections(F[0], "dense")
    cn_sec = sections(cn, "const")
    if cn_sec[0] is not None and dn_sec[0] is not None:
        print("      -> implied streamed widths: rot=%d  pos=%d  scale=%d"
              % (n - cn_sec[1] - dn_sec[1], n - cn_sec[0] - dn_sec[0],
                 n - (cn_sec[2] or 0) - (dn_sec[2] or 0)))

print("\n=== streamed clip raw structure ===")
for c in clips[:4]:
    st = c.m_MuscleClip.m_Clip.data.m_StreamedClip
    d = np.asarray(gg(st, "data", default=[]) or [], dtype=np.uint32)
    print("%s words=%d  [0]=0x%08X [1]=%d" % (c.m_Name, d.size, d[0], d[1]))
    # test the 5-word record hypothesis: data[6+5k+1] == k+1
    k = 0
    while 6 + 5 * k + 1 < d.size and d[6 + 5 * k + 1] == k + 1:
        k += 1
    print("   5-word records with index==k+1 : %d  (first failure at word %d)"
          % (k, 6 + 5 * k))
    if 6 + 5 * k + 1 < d.size:
        print("   around failure:", d[max(0, 6 + 5 * k - 5):6 + 5 * k + 25].tolist())
        f = d[6 + 5 * k:6 + 5 * k + 5].tolist()
        print("   failing record words:", f, " as floats:", [np.float32(np.uint32(x)).item()
                                                             for x in f])
    print("   floats of first 3 records:",
          [float(np.float32(np.uint32(x))) for x in d[6:21]])
    print("   tail 24 words:", d[-24:].tolist())
