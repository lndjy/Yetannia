# model-anim-clip.py -- decode the pet bundle's AnimationClips into per-frame bone TRS.
#
# ============================ HOW THE CLIP FORMAT WORKS (solved) ============================
# An AnimationClip here is a NON-legacy, Generic clip (no Avatar exists in any bundle, so nothing is
# humanoid-retargeted). Its curves are plain per-Transform TRS curves addressed by a 32-bit path:
#
#   * path hash = zlib.crc32(path string, case sensitive) of the transform path RELATIVE TO THE
#     ANIMATOR ROOT `mx_3015004_01` (i.e. drop the first two segments of the depth-built path:
#     `3015004_prefab` then `mx_3015004_01`). 245/245 binding hashes resolve. (../model-hash-resolve.py)
#   * `m_ClipBindingConstant.genericBindings` is grouped ATTRIBUTE-MAJOR: every typeID==4 binding with
#     attribute==1 (localPosition) first, then every attribute==2 (localRotation), then every
#     attribute==3 (localScale). Within a group the order is the CURVE ORDER.
#   * the curve space has 10 float slots per path: pos 3 + rot 4 (quaternion xyzw) + scale 3, and
#     every slot belongs to exactly ONE of three storages:
#         DenseClip.m_SampleArray   frame-major, m_CurveCount floats/frame
#         StreamedClip              keys sorted by time, hermite coefficients
#         ConstantClip.data         one float per constant slot
#     `len(dense) + streamed.curveCount + len(constant) == 10 * numPaths` EXACTLY for all 11 clips
#     (e.g. zd_daiji 656 + 489 + 1295 = 2440 = 244*10).
#   * inside each storage the layout is also attribute-major:
#         [localPosition 3*nPos][localRotation 4*nRot][localScale 3*nScale]
#     with the entries in binding order (proved by exact rest-pose matches: constant scales map to
#     binding 0+j with error 1e-06, and the dense quaternion groups only land on unit 4-vectors when
#     the rotation section is placed at 3*nPos).
#   * THE PARTITION (the thing that was missing): for each attribute the three storages take
#     CONTIGUOUS ranges of the binding list, in the order
#              STREAMED = [0, Xs)   DENSE = [Xs, Xs+Xd)   CONSTANT = [Xs+Xd, n)
#     Evidence: sliding the dense section over the rest-pose table finds its best alignment at offset
#     Ps for every clip with median error 0.0 (zd_daiji Ps=23 -> offset 23; zd_chuchang 100 -> 100;
#     zd_jn_01 98 -> 98; zd_jn_01_xl 82 -> 82; zd_jn_02 59 -> 59; ...), and the constant section's
#     exact rest matches land on the tail at n-nConst+j.
#
#   * StreamedClip blob layout (verified byte-for-byte, matches Unity 4.3
#     Runtime/mecanim/animation/streamedclip.h):
#         stream   = CurveTimeData*         terminated by a {+inf, 0} entry
#         CurveTimeData = { float time; UInt32 count; CurveKey keys[count]; }
#         CurveKey = { int curveIndex; float coeff[4]; }
#     The first entry has time = -FLT_MAX (0xFF7FFFFF, the "magic") and count == curveCount, i.e.
#     every streamed curve's initial state. The streamed curve index space is attribute-major too:
#     [pos 3*Ps][rot 4*Rs][scale 3*Ss] -> bindings [0,Ps)/[0,Rs)/[0,Ss).
#     A key is evaluated as  dt = t - keyTime;  v = dt*(dt*(dt*c0 + c1) + c2) + c3.
#
# usage: python .tools/model-anim-clip.py            (validate every clip in the bundle)
#        python .tools/model-anim-clip.py zd_daiji   (detail for one clip)
import json
import os
import struct
import sys
import zlib
from collections import Counter

import numpy as np
import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = os.path.join(HERE, "out", "export", "pet__3015004_prefab")
U3D = os.path.join(BUNDLE_DIR, "pet__3015004_prefab.unity3d")
HIER = os.path.join(BUNDLE_DIR, "hierarchy.json")

ATTR = {1: "localPosition", 2: "localRotation", 3: "localScale"}
WIDTH = {1: 3, 2: 4, 3: 3}
POS, ROT, SCL = 1, 2, 3


def crc32u(s):
    return zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF


def f32(u):
    return struct.unpack("<f", struct.pack("<I", int(u) & 0xFFFFFFFF))[0]


def gg(o, *names, **kw):
    d = kw.get("default")
    for n in names:
        v = getattr(o, n, None)
        if v is not None:
            return v
    return d


# ------------------------------------------------------------------ hierarchy / hash resolution
def load_hierarchy():
    h = json.load(open(HIER, encoding="utf-8"))
    entries = h["hierarchies"][list(h["hierarchies"])[0]]
    stack, chains = [], []
    for e in entries:
        depth = e.get("depth", 0)
        del stack[depth:]
        stack.append(e.get("name") or "")
        chains.append(tuple(stack))
    hash_to_tid, tid_to_chain = {}, {}
    for e, ch in zip(entries, chains):
        if len(ch) > 2:                      # strip '3015004_prefab' + 'mx_3015004_01'
            hash_to_tid[crc32u("/".join(ch[2:]))] = e["transform"]
            tid_to_chain[e["transform"]] = "/".join(ch[2:])
    return hash_to_tid, tid_to_chain


# ------------------------------------------------------------------ section detection
def _detect_rot_run(arr, L=None):
    """Longest 4-strided run of unit quaternions -> (start, nRot) or None."""
    arr = np.asarray(arr, dtype=np.float64)
    L = len(arr) if L is None else L
    unit = np.zeros(max(0, L - 3), dtype=bool)
    for j in range(L - 3):
        unit[j] = abs(float(np.linalg.norm(arr[j:j + 4])) - 1.0) < 1e-3
    best_len, best = 0, None
    for p in range(4):
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
    return best


def dense_sections(sample_frame, curve_count):
    """[nPos, nRot, nScale] of a DenseClip. The position section is 3*nPos long and the rotation
    section is the 4-strided unit-quaternion run that follows it, so nPos = runStart/3."""
    run = _detect_rot_run(sample_frame, curve_count)
    if run is None:
        return None
    rs, re_ = run
    if rs % 3:
        return None
    n_pos = rs // 3
    n_rot = (re_ - rs) // 4 + 1
    tail = curve_count - (rs + 4 * n_rot)
    if tail < 0 or tail % 3:
        return None
    return n_pos, n_rot, tail // 3


def solve_layout(n, dense_count, const_count, streamed_count, pd_hint, pc_hint):
    """Pick the exact (Ps,Pd,Pc),(Rs,Rd,Rc),(Ss,Sd,Sc) partition.

    The dense sections are reliable (3*Pd + 4*Rd + 3*Sd == dense_count pins them). The constant
    array's rotation run can be one quaternion long or short because near-identity quaternions are
    everywhere, so Rc is solved for instead of measured: the storage identities
        3*Pc + 4*Rc + 3*Sc == len(constant)     and
        3*Ps + 4*Rs + 3*Ss == streamed.curveCount
    with  Pd+Pc+Ps == Rd+Rc+Rs == Sd+Sc+Ss == n
    leave a tiny search space; the candidate closest to pc_hint wins.
    """
    sd = dense_count - 3 * pd_hint
    if sd < 0 or sd % 4:
        return None
    rd = sd // 4
    best = None
    for pc in range(0, n + 1):
        for rc in range(0, n + 1):
            rem = const_count - 3 * pc - 4 * rc
            if rem < 0 or rem % 3:
                continue
            sc = rem // 3
            if sc < 0:
                continue
            ps, rs_, ss = n - pd_hint - pc, n - rd - rc, n - 0 - sc
            if min(ps, rs_, ss) < 0:
                continue
            if 3 * ps + 4 * rs_ + 3 * ss != streamed_count:
                continue
            score = abs(pc - pc_hint) + abs(rc - (n - rd - rs_)) * 0.01
            if best is None or score < best[0]:
                best = (score, (ps, pd_hint, pc), (rs_, rd, rc), (ss, 0, sc))
    return None if best is None else best[1:]


# ------------------------------------------------------------------ streamed clip
def parse_streamed(data):
    """-> list of (time, [(curveIndex, coeff0..3), ...]) for one StreamedClip.data array."""
    d = np.asarray(data, dtype=np.uint32)
    o = 0
    blocks = []
    while o + 1 < d.size:
        t = f32(d[o])
        cnt = int(d[o + 1])
        o += 2
        if not np.isfinite(t) and t > 0:      # +inf terminator
            break
        if cnt < 0 or o + 5 * cnt > d.size:
            raise ValueError("streamed parse desync at word %d (count=%d)" % (o - 2, cnt))
        keys = []
        for j in range(cnt):
            keys.append((int(d[o + 5 * j]), [f32(d[o + 5 * j + k]) for k in range(1, 5)]))
        o += 5 * cnt
        blocks.append((t, keys))
    return blocks


def _keys_from_blocks(blocks, n_curves):
    """-> list over curve index of (times float64[K], coeffs float64[K,4])."""
    acc = [[] for _ in range(n_curves)]
    for t, keys in blocks:
        tc = 0.0 if t < -1e30 else t          # the -FLT_MAX "magic" first entry == start of clip
        for idx, c in keys:
            if 0 <= idx < n_curves:
                acc[idx].append((tc, c))
    out = []
    for lst in acc:
        lst.sort(key=lambda x: x[0])
        if not lst:
            out.append(None)
            continue
        ts = np.array([x[0] for x in lst], dtype=np.float64)
        cs = np.array([x[1] for x in lst], dtype=np.float64)
        out.append((ts, cs))
    return out


def _eval_keys(entry, times):
    """Hermite evaluation of one streamed curve at an array of sample times."""
    ts, cs = entry
    idx = np.searchsorted(ts, times, side="right") - 1
    idx[idx < 0] = 0
    dt = times - ts[idx]
    c = cs[idx]
    return dt * (dt * (dt * c[:, 0] + c[:, 1]) + c[:, 2]) + c[:, 3]


# ------------------------------------------------------------------ one clip
class ClipAnim(object):
    def __init__(self, clip, hash_to_tid, tid_to_chain):
        self.name = clip.m_Name
        self.rate = float(gg(clip, "m_SampleRate", default=30.0) or 30.0)
        dn = clip.m_MuscleClip.m_Clip.data.m_DenseClip
        self.curve_count = int(dn.m_CurveCount)
        self.frame_count = int(dn.m_FrameCount)
        self.begin_time = float(dn.m_BeginTime)
        self.samples = np.asarray(dn.m_SampleArray, dtype=np.float64).reshape(
            self.frame_count, self.curve_count)
        self.constant = np.asarray(
            clip.m_MuscleClip.m_Clip.data.m_ConstantClip.data, dtype=np.float64)
        st = clip.m_MuscleClip.m_Clip.data.m_StreamedClip
        self.streamed_curve_count = int(st.curveCount)
        self.blocks = parse_streamed(st.data)
        self.stop_time = float(clip.m_MuscleClip.m_StopTime)

        # ---- binding order, attribute major
        gb = list(gg(clip.m_ClipBindingConstant, "genericBindings", default=[]) or [])
        self.attr_paths = {POS: [], ROT: [], SCL: []}
        for b in gb:
            if b.attribute in self.attr_paths:
                self.attr_paths[b.attribute].append(b.path & 0xFFFFFFFF)
        self.n = len(self.attr_paths[POS])
        self.attr_tid = {a: [hash_to_tid.get(p) for p in self.attr_paths[a]]
                         for a in self.attr_paths}
        self.unresolved = [p for a in self.attr_paths for p in self.attr_paths[a]
                           if p not in hash_to_tid]

        # ---- section sizes
        sec = dense_sections(self.samples[0], self.curve_count)
        if sec is None:
            raise ValueError("%s: dense section detection failed" % self.name)
        self.Pd, self.Rd, self.Sd = sec
        crun = _detect_rot_run(self.constant, len(self.constant))
        pc_hint = (crun[0] // 3) if (crun and crun[0] % 3 == 0) else 0
        solved = solve_layout(self.n, self.curve_count, len(self.constant),
                              self.streamed_curve_count, self.Pd, pc_hint)
        if solved is None:
            raise ValueError("%s: no consistent 3-storage partition found" % self.name)
        (self.Ps, self.Pd, self.Pc), (self.Rs, self.Rd, self.Rc), \
            (self.Ss, self.Sd, self.Sc) = solved

        # ---- decode
        self.times = self.begin_time + np.arange(self.frame_count) / self.rate
        nF = self.frame_count
        self.pos = np.zeros((nF, self.n, 3))
        self.rot = np.zeros((nF, self.n, 4))
        self.rot[..., 3] = 1.0
        self.scl = np.ones((nF, self.n, 3))

        # positions
        if self.Ps:
            ent = _keys_from_blocks(self.blocks, self.streamed_curve_count)
            rows = [ent[3 * i + c] for i in range(self.Ps) for c in range(3)]
            assert all(r is not None for r in rows)
            for i in range(self.Ps):
                for c in range(3):
                    self.pos[:, i, c] = _eval_keys(rows[3 * i + c], self.times)
        col = 0
        self.pos[:, self.Ps:self.Ps + self.Pd] = self.samples[:, col:col + 3 * self.Pd].reshape(
            nF, self.Pd, 3)
        col = 0
        self.pos[:, self.Ps + self.Pd:] = self.constant[col:col + 3 * self.Pc].reshape(
            self.Pc, 3)[None].repeat(nF, 0)

        # rotations
        if self.Rs:
            ent = _keys_from_blocks(self.blocks, self.streamed_curve_count)
            for i in range(self.Rs):
                for c in range(4):
                    self.rot[:, i, c] = _eval_keys(ent[3 * self.Ps + 4 * i + c], self.times)
        col = 3 * self.Pd
        self.rot[:, self.Rs:self.Rs + self.Rd] = self.samples[
            :, col:col + 4 * self.Rd].reshape(nF, self.Rd, 4)
        col = 3 * self.Pc
        self.rot[:, self.Rs + self.Rd:] = self.constant[col:col + 4 * self.Rc].reshape(
            self.Rc, 4)[None].repeat(nF, 0)

        # scales
        if self.Ss:
            ent = _keys_from_blocks(self.blocks, self.streamed_curve_count)
            for i in range(self.Ss):
                for c in range(3):
                    self.scl[:, i, c] = _eval_keys(
                        ent[3 * self.Ps + 4 * self.Rs + 3 * i + c], self.times)
        col = 3 * self.Pd + 4 * self.Rd
        if self.Sd:
            self.scl[:, self.Ss:self.Ss + self.Sd] = self.samples[
                :, col:col + 3 * self.Sd].reshape(nF, self.Sd, 3)
        col = 3 * self.Pc + 4 * self.Rc
        self.scl[:, self.Ss + self.Sd:] = self.constant[col:col + 3 * self.Sc].reshape(
            self.Sc, 3)[None].repeat(nF, 0)

        # normalise quaternions defensively (they should already be unit)
        self.rot_norm_err = float(np.abs(np.linalg.norm(self.rot, axis=2) - 1.0).max())

    # ---- reporting
    def layout_str(self):
        f = lambda a, d, c: "%s: streamed %d | dense %d | constant %d (sum %s)" % (
            a, d[0], d[1], d[2], d[0] + d[1] + d[2])
        return "\n".join([
            "  n paths = %d, frames = %d @ %.1f fps, stop = %.3f s" % (
                self.n, self.frame_count, self.rate, self.stop_time),
            "  pos  " + f("pos", (self.Ps, self.Pd, self.Pc), None),
            "  rot  " + f("rot", (self.Rs, self.Rd, self.Rc), None),
            "  scl  " + f("scl", (self.Ss, self.Sd, self.Sc), None),
            "  dense floats = 3*%d + 4*%d + 3*%d = %d (header says %d)" % (
                self.Pd, self.Rd, self.Sd, 3 * self.Pd + 4 * self.Rd + 3 * self.Sd,
                self.curve_count),
            "  streamed curveCount = %d (expect %d)" % (
                self.streamed_curve_count, 3 * self.Ps + 4 * self.Rs + 3 * self.Ss),
            "  constant floats = %d (expect %d)" % (
                len(self.constant), 3 * self.Pc + 4 * self.Rc + 3 * self.Sc),
            "  max |q|-1 over all frames/bones = %.2e" % self.rot_norm_err,
        ])

    def pose(self, frame):
        """-> {transform path_id: (pos3, quat4, scale3)} for one frame index."""
        out = {}
        for a, arr, w in ((POS, self.pos, 3), (ROT, self.rot, 4), (SCL, self.scl, 3)):
            tids = self.attr_tid[a]
            vals = arr[frame]
            for i, tid in enumerate(tids):
                if tid is None:
                    continue
                cur = out.get(tid)
                v = vals[i]
                if a == POS:
                    out[tid] = (v, cur[1] if cur else None, cur[2] if cur else None)
                elif a == ROT:
                    out[tid] = (cur[0] if cur else None, v, cur[2] if cur else None)
                else:
                    out[tid] = (cur[0] if cur else None, cur[1] if cur else None, v)
        return out


def load_clips(bundle=U3D):
    hash_to_tid, tid_to_chain = load_hierarchy()
    env = UnityPy.load(bundle)
    out = {}
    for o in env.objects:
        if o.type.name != "AnimationClip":
            continue
        c = o.read()
        out[c.m_Name] = ClipAnim(c, hash_to_tid, tid_to_chain)
    return out, hash_to_tid, tid_to_chain


# ------------------------------------------------------------------ validation
def main():
    which = sys.argv[1] if len(sys.argv) > 1 else None
    clips, hash_to_tid, tid_to_chain = load_clips()
    hash_to_tid2, tid_to_chain2 = load_hierarchy()
    # rest pose from the prefab hierarchy
    env = UnityPy.load(U3D)
    rest = {}
    for o in env.objects:
        if o.type.name in ("Transform", "RectTransform"):
            d = o.read()
            lp, lr, ls = gg(d, "m_LocalPosition"), gg(d, "m_LocalRotation"), gg(d, "m_LocalScale")
            rest[o.path_id] = (np.array([lp.x, lp.y, lp.z]) if lp else np.zeros(3),
                               np.array([lr.x, lr.y, lr.z, lr.w]) if lr else np.array([0, 0, 0, 1.0]),
                               np.array([ls.x, ls.y, ls.z]) if ls else np.ones(3))
    names = [which] if which else sorted(clips)
    for nm in names:
        cl = clips[nm]
        print("=" * 100)
        print(nm)
        print(cl.layout_str())
        # rest comparison, binding by binding
        for a, arr, ri in ((POS, cl.pos, 0), (ROT, cl.rot, 1), (SCL, cl.scl, 2)):
            tids = cl.attr_tid[a]
            tbl = np.stack([rest[t][ri] for t in tids])
            e0 = np.abs(arr[0] - tbl).max(1)
            em = np.abs(arr.mean(0) - tbl).max(1)
            allf = np.abs(arr - tbl[None]).max(2)
            print("   binding-vs-rest %-14s frame0: med %.2e p95 %.2e max %.2e | "
                  "any-frame max %.2e | worst bones %s" % (
                      ATTR[a], np.median(e0), np.percentile(e0, 95), e0.max(), allf.max(),
                      [tid_to_chain.get(tids[i], "?").split("/")[-1]
                       for i in np.argsort(-e0)[:3]]))
        # frame-to-frame motion: how much does the pose actually MOVE?
        d = np.abs(np.diff(cl.rot, axis=0)).reshape(cl.frame_count - 1, -1).max(1)
        dp = np.abs(np.diff(cl.pos, axis=0)).reshape(cl.frame_count - 1, -1).max(1)
        print("   frame-to-frame max |dq| mean %.3e max %.3e | max |dpos| mean %.3e max %.3e"
              % (d.mean(), d.max(), dp.mean(), dp.max()))
        moving = np.abs(cl.rot - cl.rot[0][None]).reshape(cl.frame_count, -1).max(0)
        print("   bones with any rotation change > 1e-3: %d / %d"
              % (int((moving > 1e-3).sum()), cl.n * 4))
        if cl.unresolved:
            print("   !! unresolved binding paths: %d" % len(cl.unresolved))


if __name__ == "__main__":
    main()
