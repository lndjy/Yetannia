# model-anim-probe2.py -- column-level structure of the dense clip array.
#
# Established arithmetic (probe 1, all 11 clips, exact):
#     m_DenseClip.m_CurveCount + m_StreamedClip.curveCount + len(m_ConstantClip.data)
#         == numUniqueBindingPaths * 10          (pos 3 + rot 4 + scale 3)
#   zd_daiji 656 + 489 + 1295 = 2440 = 244*10   etc. for every clip.
# So every one of the 2440 float slots of a 244-path clip belongs to exactly ONE of the three
# storages, and ConstantClip.data really is a List[float] (UnityPy: `data: List[float]`), i.e. one
# float per constant slot.
#
# Now: within m_DenseClip.m_SampleArray (frame-major, m_CurveCount floats/frame) which slots are
# they, and in what order? A quaternion's 4 floats are a unit vector, so scanning 4-wide windows
# for |q|==1 over ALL frames is a razor-sharp oracle. This script reports it plus per-column stats.
#
# usage: python .tools/model-anim-probe2.py
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
hash_to_tid, tid_to_name = {}, {}
for e, ch in zip(entries, chains):
    if len(ch) > 2:
        hash_to_tid[crc32u("/".join(ch[2:]))] = e["transform"]
        tid_to_name[e["transform"]] = "/".join(ch[2:])

env = UnityPy.load(U3D)
clips = sorted([o.read() for o in env.objects if o.type.name == "AnimationClip"],
               key=lambda c: c.m_Name)

for c in clips:
    gb = list(gg(c.m_ClipBindingConstant, "genericBindings", default=[]) or [])
    dn = c.m_MuscleClip.m_Clip.data.m_DenseClip
    cc = int(gg(dn, "m_CurveCount", default=0) or 0)
    fc = int(gg(dn, "m_FrameCount", default=0) or 0)
    sa = np.asarray(gg(dn, "m_SampleArray", default=[]) or [], dtype=np.float64)
    cn = np.asarray(gg(c.m_MuscleClip.m_Clip.data.m_ConstantClip, "data", default=[]) or [],
                    dtype=np.float64)
    if cc == 0 or sa.size != cc * fc:
        continue
    F = sa.reshape(fc, cc)
    npaths = len(set(x.path & 0xFFFFFFFF for x in gb))
    attrs = Counter(x.attribute for x in gb)
    print("=" * 108)
    print("%s  paths=%d bindings=%d attrs=%s" % (c.m_Name, npaths, len(gb), dict(attrs)))
    print("  dense cc=%d frames=%d | const floats=%d | sum=%d  T=%d"
          % (cc, fc, cn.size, cc + cn.size, npaths * 10))

    # ---- unit-quaternion windows over every start column
    ok = np.zeros(max(0, cc - 3), dtype=bool)
    dev = np.full(max(0, cc - 3), 9.0)
    for j in range(cc - 3):
        n = np.linalg.norm(F[:, j:j + 4], axis=1)
        dev[j] = float(np.abs(n - 1.0).max())
        ok[j] = dev[j] < 1e-3
    idx = np.where(ok)[0]
    print("  unit-q windows: %d of %d   starts=%s" % (len(idx), len(ok), idx[:24].tolist()))
    if len(idx) > 1:
        d = np.diff(idx)
        print("  start-step histogram: %s" % Counter(d.tolist()).most_common(8))
        print("  near-miss (dev<1e-2) count: %d" % int((dev < 1e-2).sum()))

    # ---- per-column stats
    mn, mx, sd, mean = F.min(0), F.max(0), F.std(0), F.mean(0)
    allzero = np.all(F == 0.0, axis=0)
    near1 = (np.abs(mean - 1.0) < 1e-3) & (sd < 1e-6)
    inrange = (mn >= -1.0001) & (mx <= 1.0001)
    print("  cols: all-zero=%d  const==1.0=%d  all-in[-1,1]=%d" %
          (int(allzero.sum()), int(near1.sum()), int(inrange.sum())))
    # runs of classification
    cls = np.where(allzero, "Z", np.where(near1, "1", np.where(inrange, "u", "P")))
    runs = []
    s = 0
    for i in range(1, cc + 1):
        if i == cc or cls[i] != cls[s]:
            runs.append("%s%d" % (cls[s], i - s))
            s = i
    print("  class runs: %s" % " ".join(runs))

    # ---- constant clip stats
    if cn.size:
        print("  const floats: all==1.0 -> %d ; all==0.0 -> %d ; <0 or >1 -> %d ; sample=%s"
              % (int((cn == 1.0).sum()), int((cn == 0.0).sum()),
                 int(((cn < -1e-6) | (cn > 1 + 1e-6)).sum()), np.round(cn[:16], 5).tolist()))
