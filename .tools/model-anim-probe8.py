# model-anim-probe8.py -- (a) find where the streamed block TIMES live, (b) verify the
# "dense / streamed / constant are three CONTIGUOUS ranges of the binding list" hypothesis.
#
# Established so far (probes 1-4):
#   * every one of the 10*n curve slots (pos 3 + rot 4 + scale 3 per binding) lives in exactly one of
#     {DenseClip, StreamedClip, ConstantClip}:  D + S + len(Constant) == 10*n exactly, 11/11 clips.
#   * inside each storage array the layout is attribute-major:
#         [ localPosition 3*nPos ][ localRotation 4*nRot ][ localScale 3*nScale ]
#     with the entries in binding order. (proved by exact rest-pose matches at offsets == 3 mod 4)
#   * the section sizes are readable from the data itself and they satisfy
#         Pd + Ps + Pc == n,  Rd + Rs + Rc == n,  Sd + Ss + Sc == n.
# Hypothesis H: for each attribute the storage ranges are CONTIGUOUS in the order dense, streamed,
# constant:   dense = [0, Xd),  streamed = [Xd, Xd+Xs),  constant = [Xd+Xs, n).
# H predicts the constant rotation section's j-th quaternion belongs to binding Rd+Rs+j, and the
# probe-3 exact matches did land on consecutive bones for consecutive j - so H looks right. This
# script checks it against the rest pose for all three attributes.
#
# usage: python .tools/model-anim-probe8.py
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
tid_of = {}
for e, ch in zip(entries, chains):
    if len(ch) > 2:
        tid_of[crc32u("/".join(ch[2:]))] = e["transform"]
name_of = {e["transform"]: ch[-1] for e, ch in zip(entries, chains)}
rest_pos = {e["transform"]: np.array([e["local_position"]["x"], e["local_position"]["y"],
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

WANT = "zd_daiji"
for c in clips:
    if c.m_Name != WANT:
        continue
    gb = list(gg(c.m_ClipBindingConstant, "genericBindings", default=[]) or [])
    order = {1: [], 2: [], 3: []}
    for x in gb:
        order[x.attribute].append(x.path & 0xFFFFFFFF)
    n = len(order[1])
    dn = c.m_MuscleClip.m_Clip.data.m_DenseClip
    st = c.m_MuscleClip.m_Clip.data.m_StreamedClip
    cc, fc = int(dn.m_CurveCount), int(dn.m_FrameCount)
    F = np.asarray(dn.m_SampleArray).reshape(fc, cc)
    cn = np.asarray(c.m_MuscleClip.m_Clip.data.m_ConstantClip.data)
    d = np.asarray(st.data, dtype=np.uint32)
    N = int(st.curveCount)
    print("%s: n=%d dense=%d streamed=%d const=%d frames=%d" % (WANT, n, cc, N, cn.size, fc))

    # ---- (a) locate time words = k/30
    tgt = np.array([k / 30.0 for k in range(fc + 2)])
    tf = np.array([f32(x) for x in d])
    hit = [i for i in range(d.size) if np.min(np.abs(tgt - tf[i])) < 1e-6]
    print("\n(a) words whose float value is exactly k/30 : %d of %d" % (len(hit), d.size))
    print("    first 40 positions:", hit[:40])
    print("    gaps:", list(np.diff(hit[:40])))
    print("    last 10 positions:", hit[-10:])

    # ---- (b) rest tables in binding order
    restP = np.stack([rest_pos[tid_of[p]] for p in order[1]])
    restR = np.stack([TR[tid_of[p]][1] for p in order[2]])
    restS = np.stack([TR[tid_of[p]][2] for p in order[3]])

    # section sizes straight from the arrays (probe 4 logic)
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
        nPos = rs // 3
        tail = L - (rs + 4 * nRot)
        return nPos, nRot, tail // 3
    Pd, Rd, _Sd = sections(F[0])
    Pc, Rc, Sc = sections(cn)
    Ps, Rs, Ss = n - Pd - Pc, n - Rd - Rc, n - (Sc or 0)
    print("\n(b) implied partition   pos: dense %d | streamed %d | constant %d" % (Pd, Ps, Pc))
    print("                        rot: dense %d | streamed %d | constant %d" % (Rd, Rs, Rc))
    print("                        scl: dense %d | streamed %d | constant %d" % (0, 0, Sc))

    # ---- dense: frame 0 vs rest, section-aligned
    print("\n(c) hypothesis H checks (max |value - rest|)")
    dp = F[0][:3 * Pd].reshape(-1, 3)
    err = np.abs(dp - restP[:Pd]).max(1)
    print("    DENSE pos  i<->binding i        : n=%d err min=%.2e med=%.2e max=%.2e"
          % (len(err), err.min(), np.median(err), err.max()))
    dr = F[0][3 * Pd:3 * Pd + 4 * Rd].reshape(-1, 4)
    err = np.abs(dr - restR[:Rd]).max(1)
    print("    DENSE rot  i<->binding i        : n=%d err min=%.2e med=%.2e max=%.2e"
          % (len(err), err.min(), np.median(err), err.max()))
    cp = cn[:3 * Pc].reshape(-1, 3)
    base = n - Pc
    err = np.abs(cp - restP[base:]).max(1)
    print("    CONST pos  j<->binding %d+j    : n=%d err min=%.2e med=%.2e max=%.2e"
          % (base, len(err), err.min(), np.median(err), err.max()))
    cr = cn[3 * Pc:3 * Pc + 4 * Rc].reshape(-1, 4)
    base = n - Rc
    err = np.abs(cr - restR[base:]).max(1)
    print("    CONST rot  j<->binding %d+j    : n=%d err min=%.2e med=%.2e max=%.2e"
          % (base, len(err), err.min(), np.median(err), err.max()))
    cs = cn[3 * Pc + 4 * Rc:].reshape(-1, 3)
    base = n - (Sc or 0)
    err = np.abs(cs - restS[base:]).max(1)
    print("    CONST scl  j<->binding %d+j    : n=%d err min=%.2e med=%.2e max=%.2e"
          % (base, len(err), err.min(), np.median(err), err.max()))

    # ---- streamed block 0 under parse A: [count][key{index,c0..c3}]
    o = 1
    cnt = int(d[o]); o += 1
    keys = []
    for j in range(cnt):
        keys.append((int(d[o]), [f32(d[o + k]) for k in range(1, 5)]))
        o += 5
    idx = np.array([k[0] for k in keys])
    val = np.array([k[1][3] for k in keys])
    print("\n(d) streamed block0: count=%d  index range %d..%d  increasing=%s"
          % (cnt, idx.min(), idx.max(), bool((np.diff(idx) == 1).all())))
    print("    values 0..11:", np.round(val[:12], 6).tolist())
    print("    |v|>1 count=%d (position/scale-like), |v|<=1 count=%d (rotation-like)"
          % (int((np.abs(val) > 1).sum()), int((np.abs(val) <= 1).sum())))
    # under attribute-major streamed index space: [pos 3Ps][rot 4Rs][scale 3Ss]
    if Ps and 3 * Ps <= val.size:
        sp = val[:3 * Ps].reshape(-1, 3)
        _, s0 = base, None
        e2 = np.abs(sp - restP[Pd:Pd + Ps]).max(1)
        print("    STRM pos  i<->binding %d+i   : n=%d err med=%.2e max=%.2e"
              % (Pd, len(e2), np.median(e2), e2.max()))
    if Rs:
        sr = val[3 * Ps:3 * Ps + 4 * Rs].reshape(-1, 4)
        e2 = np.abs(sr - restR[Rd:Rd + Rs]).max(1)
        print("    STRM rot  i<->binding %d+i   : n=%d err med=%.2e max=%.2e"
              % (Rd, len(e2), np.median(e2), e2.max()))
