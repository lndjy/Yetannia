# model-anim-probe9.py -- place the dense and streamed sections exactly.
#
# probe 8 confirmed, for zd_daiji:
#   CONST scale  j <-> binding 0+j     max err 1.1e-06   (all 244 scales are just the rest scales)
#   CONST pos    j <-> binding 163+j   max err 2.7e-02, median 1.2e-07
#   CONST rot    j <-> binding 164+j   median 1.1e-06 (a couple of outliers)
# so the CONSTANT section is the *tail* of each attribute's binding list. The dense+streamed sections
# therefore live in [0, n-nConst). This script scans every contiguous offset for the dense section
# (and for the streamed section, using streamed block 0 = every streamed curve's key at t=0) and
# reports the offset with the smallest rest-pose error.
#
# usage: python .tools/model-anim-probe9.py
import json
import os
import struct
import zlib

import numpy as np
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = os.path.join(HERE, "out", "export", "pet__3015004_prefab")
U3D = os.path.join(BUNDLE_DIR, "pet__3015004_prefab.unity3d")
HIER = os.path.join(BUNDLE_DIR, "hierarchy.json")


def f32(u):
    return struct.unpack("<f", struct.pack("<I", int(u) & 0xFFFFFFFF))[0]


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
tid_of = {crc32u("/".join(ch[2:])): e["transform"] for e, ch in zip(entries, chains) if len(ch) > 2}
name_of_tid = {e["transform"]: (ch[-1] if ch else "?") for e, ch in zip(entries, chains)}
rpos_json = {e["transform"]: np.array([e["local_position"]["x"], e["local_position"]["y"],
                                       e["local_position"]["z"]]) for e in entries}

env = UnityPy.load(U3D)
TR = {}
for o in env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        d = o.read()
        lp, lr, ls = (gg(d, "m_LocalPosition"), gg(d, "m_LocalRotation"), gg(d, "m_LocalScale"))
        TR[o.path_id] = (np.array([lp.x, lp.y, lp.z]) if lp else None,
                         np.array([lr.x, lr.y, lr.z, lr.w]) if lr else None,
                         np.array([ls.x, ls.y, ls.z]) if ls else None)
clips = sorted([o.read() for o in env.objects if o.type.name == "AnimationClip"],
               key=lambda c: c.m_Name)


def sections(arr):
    L = len(arr)
    unit = np.zeros(max(0, L - 3), dtype=bool)
    for j in range(L - 3):
        unit[j] = abs(float(np.linalg.norm(arr[j:j + 4])) - 1.0) < 1e-3
    bl, best = 0, None
    for p in range(4):
        j = p
        while j < len(unit):
            if unit[j]:
                k = j
                while k + 4 < len(unit) and unit[k + 4]:
                    k += 4
                if k - j + 1 > bl:
                    bl, best = k - j + 1, (j, k)
                j = k + 4
            j += 1
    rs, re_ = best
    nRot = (re_ - rs) // 4 + 1
    return rs // 3, nRot


def best_offset(arr, rest, label):
    """arr: (m, w) values, rest: (n, w) table. slide arr over rest, report best offsets."""
    m = len(arr)
    n = len(rest)
    if m == 0:
        return
    errs = []
    for o in range(0, n - m + 1):
        e = np.abs(arr - rest[o:o + m]).max(1)
        errs.append((float(np.median(e)), float(e.max()), o))
    errs.sort()
    print("    %-28s best offsets (median,max,offset): %s" % (
        label, [(round(a, 5), round(b, 4), c) for a, b, c in errs[:3]]))


for c in clips:
    gb = list(gg(c.m_ClipBindingConstant, "genericBindings", default=[]) or [])
    order = {1: [], 2: [], 3: []}
    for x in gb:
        order[x.attribute].append(x.path & 0xFFFFFFFF)
    n = len(order[1])
    dn = c.m_MuscleClip.m_Clip.data.m_DenseClip
    cc, fc = int(dn.m_CurveCount), int(dn.m_FrameCount)
    F = np.asarray(dn.m_SampleArray).reshape(fc, cc)
    cn = np.asarray(c.m_MuscleClip.m_Clip.data.m_ConstantClip.data)
    st = c.m_MuscleClip.m_Clip.data.m_StreamedClip
    d = np.asarray(st.data, dtype=np.uint32)
    N = int(st.curveCount)
    Pd, Rd = sections(F[0])
    Pc, Rc = sections(cn)

    restP = np.stack([rpos_json[tid_of[p]] for p in order[1]])
    restR = np.stack([TR[tid_of[p]][1] for p in order[2]])
    # cross-check hierarchy.json's local_position against the bundle's m_LocalPosition
    restP2 = np.stack([TR[tid_of[p]][0] for p in order[1]])
    print("=" * 100)
    print("%s n=%d  Pd=%d Rd=%d Pc=%d Rc=%d  | cross-check json-vs-bundle localPosition max=%.2e"
          % (c.m_Name, n, Pd, Rd, Pc, Rc, float(np.abs(restP - restP2).max())))

    dp = F[0][:3 * Pd].reshape(-1, 3)
    dr = F[0][3 * Pd:3 * Pd + 4 * Rd].reshape(-1, 4)
    dpm = F[:, :3 * Pd].reshape(fc, -1, 3).mean(0)
    drm = F[:, 3 * Pd:3 * Pd + 4 * Rd].reshape(fc, -1, 4)
    drm = drm / np.maximum(np.linalg.norm(drm, axis=2, keepdims=True), 1e-9)
    drm = drm.mean(0)
    best_offset(dp, restP, "DENSE pos (frame0)")
    best_offset(dpm, restP, "DENSE pos (mean over frames)")
    best_offset(dr, restR, "DENSE rot (frame0)")
    best_offset(drm, restR, "DENSE rot (mean of normalized)")

    # streamed block 0
    o = 1
    cnt = int(d[o]); o += 1
    keys = []
    for j in range(cnt):
        keys.append((int(d[o]), [f32(d[o + k]) for k in range(1, 5)]))
        o += 5
    idx = np.array([k[0] for k in keys])
    val = np.array([k[1][3] for k in keys])
    Ps = n - Pd - Pc
    Rs = n - Rd - Rc
    print("    streamed block0 count=%d  (expect %d = 3*%d + 4*%d)  idx 0..%d increasing=%s"
          % (cnt, 3 * Ps + 4 * Rs, Ps, Rs, idx.max(), bool((np.diff(idx) == 1).all())))
    if 3 * Ps:
        best_offset(val[:3 * Ps].reshape(-1, 3), restP, "STRM pos (t=0)")
    if 4 * Rs and 3 * Ps + 4 * Rs <= val.size:
        best_offset(val[3 * Ps:3 * Ps + 4 * Rs].reshape(-1, 4), restR, "STRM rot (t=0)")
    # nonzero k/30 time words
    tf = np.array([f32(x) for x in d])
    tset = np.array([k / 30.0 for k in range(1, fc + 2)])
    hit = [i for i in range(d.size) if np.min(np.abs(tset - tf[i])) < 1e-7]
    print("    words equal to a NONZERO k/30: %d  first 24: %s" % (len(hit), hit[:24]))
    if len(hit) > 2:
        print("    gaps between first 24:", list(np.diff(hit[:24])))
