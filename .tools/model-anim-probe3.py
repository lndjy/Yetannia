# model-anim-probe3.py -- identify the constant clip's contents by matching the KNOWN rest pose.
#
# probe 1 gave the partition identity  dense + streamed + len(constant) == paths*10  exactly for all
# 11 clips, so each of the 10*n float slots (pos 3 + rot 4 + scale 3 per path) belongs to exactly one
# storage. probe 2 showed the dense array contains long 4-stride runs of unit quaternions, i.e. the
# partition is per-BINDING (a whole position/rotation/scale channel moves as a unit) and the storage
# arrays are ordered by binding order (attribute-major: all positions, then rotations, then scales).
#
# This script proves the ordering using data we already trust:
#   * the rest local position of every bone is in hierarchy.json (exact),
#   * the rest local rotation/scale of every bone is in the bundle's Transform objects,
#   * a CONSTANT curve must equal its rest-ish value at every frame, and for positions/scales the
#     constant IS the rest value to float32 exactness.
# So: slide a 3-wide window over the constant array and see which rest-position triples it hits, in
# what order. Same for 4-wide quaternion windows and 3-wide scale windows.
#
# usage: python .tools/model-anim-probe3.py [clipName]
import json
import os
import sys
import zlib

import numpy as np
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = os.path.join(HERE, "out", "export", "pet__3015004_prefab")
U3D = os.path.join(BUNDLE_DIR, "pet__3015004_prefab.unity3d")
HIER = os.path.join(BUNDLE_DIR, "hierarchy.json")
WANT = sys.argv[1] if len(sys.argv) > 1 else "zd_daiji"


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
name_of_tid = {e["transform"]: (ch[-1] if ch else "?") for e, ch in zip(entries, chains)}
rest_pos = {e["transform"]: np.array([e["local_position"]["x"], e["local_position"]["y"],
                                      e["local_position"]["z"]], dtype=np.float64)
            for e in entries}

env = UnityPy.load(U3D)
transforms = {}
for o in env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        d = o.read()
        lp = gg(d, "m_LocalPosition", default=None)
        lr = gg(d, "m_LocalRotation", default=None)
        ls = gg(d, "m_LocalScale", default=None)
        transforms[o.path_id] = (
            np.array([lp.x, lp.y, lp.z], dtype=np.float64) if lp else None,
            np.array([lr.x, lr.y, lr.z, lr.w], dtype=np.float64) if lr else None,
            np.array([ls.x, ls.y, ls.z], dtype=np.float64) if ls else None,
        )

clips = {o.read().m_Name: o.read() for o in env.objects if o.type.name == "AnimationClip"}
c = clips[WANT]
gb = list(gg(c.m_ClipBindingConstant, "genericBindings", default=[]) or [])
dn = c.m_MuscleClip.m_Clip.data.m_DenseClip
cn = np.asarray(gg(c.m_MuscleClip.m_Clip.data.m_ConstantClip, "data", default=[]) or [],
                dtype=np.float64)
cc = int(gg(dn, "m_CurveCount", default=0) or 0)
fc = int(gg(dn, "m_FrameCount", default=0) or 0)
sa = np.asarray(gg(dn, "m_SampleArray", default=[]) or [], dtype=np.float64)
F = sa.reshape(fc, cc)

# binding order, split by attribute
order = {1: [], 2: [], 3: []}
for x in gb:
    order[x.attribute].append(x.path & 0xFFFFFFFF)
n = len(order[1])
print("clip %s: n paths=%d  dense=%d  frames=%d  const=%d  (T=%d)"
      % (WANT, n, cc, fc, cn.size, 10 * n))
print("attribute-major binding order assumed: [pos(3) x %d][rot(4) x %d][scale(3) x %d]"
      % (n, n, n))

# ---------------------------------------------------------------- rest tables in binding order
restP = np.stack([rest_pos[tid_of[p]] for p in order[1]])
restR = np.stack([transforms[tid_of[p]][1] for p in order[2]])
restS = np.stack([transforms[tid_of[p]][2] for p in order[3]])
print("rest rotation: quaternion-norm deviation max %.3e ; rest scale==1 for %d/%d bones"
      % (float(np.abs(np.linalg.norm(restR, axis=1) - 1).max()),
         int((np.abs(restS - 1) < 1e-6).all(1).sum()), n))


def match_triples(arr, table, tol, label):
    """slide 3-wide window over arr, report which table rows it hits (exact-ish)."""
    key = {}
    for i, v in enumerate(table):
        key.setdefault(tuple(np.round(v, 6)), []).append(i)
    hits = []
    for o in range(len(arr) - 2):
        k = tuple(np.round(arr[o:o + 3], 6))
        if k in key:
            hits.append((o, key[k][0], float(np.abs(arr[o:o + 3] - table[key[k][0]]).max())))
    print("\n-- %s: %d/3-aligned hits (offset, boneIndex, err) --" % (label, len(hits)))
    for o, bi, e in hits[:40]:
        print("   off=%5d bone[%3d] %-22s err=%.2e" % (o, bi, name_of_tid[tid_of[order[1][bi]]], e))
    if len(hits) > 40:
        print("   ... %d more" % (len(hits) - 40))
    print("   offsets mod 3:", sorted(set(o % 3 for o, _b, _e in hits)))
    print("   boneIndex sequence monotone-increasing?",
          all(hits[i][1] < hits[i + 1][1] for i in range(len(hits) - 1)) if len(hits) > 1 else None)
    return hits


def match_quats(arr, table, tol, label):
    key = {}
    for i, v in enumerate(table):
        key.setdefault(tuple(np.round(v, 5)), []).append(i)
    hits = []
    for o in range(len(arr) - 3):
        k = tuple(np.round(arr[o:o + 4], 5))
        if k in key:
            hits.append((o, key[k][0], float(np.abs(arr[o:o + 4] - table[key[k][0]]).max())))
    print("\n-- %s: %d 4-aligned quaternion hits --" % (label, len(hits)))
    for o, bi, e in hits[:30]:
        print("   off=%5d bone[%3d] %-22s err=%.2e" % (o, bi, name_of_tid[tid_of[order[2][bi]]], e))
    print("   offsets mod 4:", sorted(set(o % 4 for o, _b, _e in hits)))
    return hits


match_triples(cn, restP, 1e-5, "CONSTANT array vs rest localPosition")
# also: how many exact 1.0s and where
ones = np.where(np.abs(cn - 1.0) < 1e-9)[0]
print("\nconst exact 1.0 count=%d  first=%s last=%s  contiguous tail? %s"
      % (len(ones), ones[:8].tolist(), ones[-8:].tolist() if len(ones) else [],
         bool(len(ones) and ones.min() > cn.size - len(ones) - 5)))
match_quats(cn, restR, 1e-5, "CONSTANT array vs rest localRotation")

# ---------------------------------------------------------------- dense frame 0 vs rest
print("\n=== DENSE frame 0 windows: which rest triple/quat do they match? ===")
f0 = F[0]
hitsP = []
for o in range(cc - 2):
    d = np.abs(restP - f0[o:o + 3]).max(1)
    j = int(np.argmin(d))
    if d[j] < 0.5:
        hitsP.append((o, j, float(d[j])))
print("frame0 3-window near a rest position (err<0.5): %d" % len(hitsP))
for o, j, e in hitsP[:25]:
    print("   off=%4d bone[%3d] %-24s err=%.4f" % (o, j, name_of_tid[tid_of[order[1][j]]], e))
print("   offsets mod 3:", sorted(set(o % 3 for o, _j, _e in hitsP)))

hitsQ = []
for o in range(cc - 3):
    q = f0[o:o + 4]
    nq = np.linalg.norm(q)
    if abs(nq - 1) < 1e-3:
        d = np.abs(restR - q).max(1)
        j = int(np.argmin(d))
        hitsQ.append((o, j, float(d[j]), nq))
print("frame0 unit-quaternions: %d ; of those, nearest rest rotation err<0.2: %d"
      % (len(hitsQ), sum(1 for x in hitsQ if x[2] < 0.2)))
for o, j, e, nq in hitsQ[:25]:
    print("   off=%4d bone[%3d] %-24s err=%.4f |q|=%.6f" % (o, j, name_of_tid[tid_of[order[2][j]]], e, nq))
print("   offsets mod 4:", sorted(set(o % 4 for o, _j, _e, _n in hitsQ)))
