# model-probe-cliphash.py -- bounded de-risk for the NEXT phase (animation).
# Question: are AnimationClip genericBindings path hashes resolvable to hierarchy.json transform
# paths via Unity's Animator.StringToHash, i.e. hash = c + (hash<<6) + (hash<<16) - hash?
# Also reports the dense-clip sampling layout so the frame->curve indexing can be trusted.
import json
import os

import UnityPy

BASE = r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab"
BUNDLE = os.path.join(BASE, "pet__3015004_prefab.unity3d")


def gg(o, *names, **kw):
    for n in names:
        v = getattr(o, n, None)
        if v is not None:
            return v
    return kw.get("default")


def pid(x):
    if x is None:
        return None
    v = getattr(x, "m_PathID", None)
    if v is not None:
        return v
    i = getattr(x, "component", None)
    if i is not None:
        return getattr(i, "m_PathID", None)
    try:
        return int(x)
    except Exception:
        return None


def string_to_hash(s):
    h = 0
    for ch in s:
        h = (ord(ch) + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


env = UnityPy.load(BUNDLE)

# ---- build every transform path string the same way Unity builds binding paths
trs, name, father = {}, {}, {}
for o in env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        d = o.read()
        trs[o.path_id] = d
        go = gg(d, "m_GameObject")
        name[o.path_id] = gg(go.read(), "m_Name") if go else "?"
        father[o.path_id] = pid(gg(d, "m_Father"))


def path_of(t):
    parts = []
    while t in trs:
        parts.append(name[t])
        t = father.get(t)
    return "/".join(reversed(parts))


paths = {}
for t in trs:
    if father.get(t) in trs:          # binding paths are relative to the animator root
        p = path_of(t)
        paths.setdefault(p, t)
hashes = {}
for p, t in paths.items():
    hashes[string_to_hash(p)] = p
print("built %d relative transform paths -> %d unique hashes" % (len(paths), len(hashes)))

# ---- clips
clips = [o for o in env.objects if o.type.name == "AnimationClip"]
print("clips: %d" % len(clips))
tot = hit = 0
for co in clips:
    d = co.read()
    nm = gg(d, "m_Name")
    cb = gg(d, "m_ClipBindingConstant")
    gb = gg(cb, "genericBindings") if cb is not None else None
    gb = gb or []
    got = 0
    for b in gb:
        p = gg(b, "path", "m_Path")
        if p is None:
            continue
        tot += 1
        if int(p) in hashes:
            hit += 1
            got += 1
    # dense clip layout
    mc = gg(d, "m_MuscleClip")
    dense = gg(mc, "m_DenseClip") if mc is not None else None
    streamed = gg(mc, "m_StreamedClip") if mc is not None else None
    n = None; cc = None; fps = None; dur = None
    if dense is not None:
        n = gg(dense, "m_FrameCount", "frameCount")
        cc = gg(dense, "m_CurveCount", "curveCount")
        sr = gg(dense, "m_SampleRate", "sampleRate")
        sa = gg(dense, "m_SampleArray", "sampleArray")
        fps = sr
        print("  %-34s bindings=%3d resolved=%3d | dense frameCount=%s curveCount=%s rate=%s "
              "samples=%s" % (nm[:34], len(gb), got, n, cc, sr,
                              (len(sa) if sa is not None else None)))
    if streamed is not None:
        print("       streamed curveCount=%s (streamed curves need the packed-bit reader)"
              % gg(streamed, "curveCount"))

print("\nTOTAL genericBindings=%d  resolved-to-hierarchy-path=%d (%.1f%%)"
      % (tot, hit, (100.0 * hit / tot) if tot else 0.0))
