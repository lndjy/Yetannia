# model-clip-probe3.py — last feasibility gate: is the clip data decodable and generic-mapped?
# Unity 2019 stores non-legacy clips in m_Clip.data as one of {StreamedClip, DenseClip, ConstantClip}.
# We need: (a) which one is populated, (b) whether m_ClipBindingConstant maps curves to Transform
# paths (generic) rather than to humanoid muscle indices (which would need Unity's muscle solver).
# usage: python .tools/model-clip-probe3.py [bundle.unity3d]
import sys

import UnityPy

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\pet__3015004_prefab.unity3d"

ANIM_TYPE = {0: "Legacy", 1: "Generic", 2: "Humanoid"}


def g(obj, *names, default=0):
    """UnityPy's generated structs are inconsistent about the m_ prefix; try both."""
    for n in names:
        if obj is not None and hasattr(obj, n):
            v = getattr(obj, n)
            if v is not None:
                return v
    return default


def size(v):
    if v is None:
        return 0
    if isinstance(v, (bytes, bytearray, list)):
        return len(v)
    return v


env = UnityPy.load(BUNDLE)
clips = [x.read() for x in env.objects if x.type.name == "AnimationClip"]

d0 = clips[0].m_MuscleClip.m_Clip.data
for name in ("StreamedClip", "DenseClip", "ConstantClip"):
    sub = g(d0, "m_" + name, name, default=None)
    print(f"{name} attrs:", sorted(a for a in dir(sub) if not a.startswith("_")) if sub else None)
print()

for c in clips:
    d = c.m_MuscleClip.m_Clip.data
    st = g(d, "m_StreamedClip", "StreamedClip", default=None)
    dn = g(d, "m_DenseClip", "DenseClip", default=None)
    cn = g(d, "m_ConstantClip", "ConstantClip", default=None)
    bind = c.m_ClipBindingConstant
    nb = len(bind.genericBindings) if bind and g(bind, "genericBindings", default=None) else 0
    print(f"{c.m_Name:20s} type={ANIM_TYPE.get(c.m_AnimationType, c.m_AnimationType)} "
          f"rate={c.m_SampleRate} stop={round(c.m_MuscleClip.m_StopTime, 2)} bindings={nb} "
          f"| streamed curves={size(g(st, 'curveCount', 'm_CurveCount'))} data={size(g(st, 'data', 'm_Data'))} "
          f"| dense curves={g(dn, 'curveCount', 'm_CurveCount')} frames={g(dn, 'frameCount', 'm_FrameCount')} "
          f"samples={size(g(dn, 'sampleArray', 'm_SampleArray'))} "
          f"| constant={size(g(cn, 'data', 'm_Data'))}")

print("--- first clip bindings ---")
b = clips[0].m_ClipBindingConstant
print("bind attrs:", sorted(a for a in dir(b) if not a.startswith("_")))
for gb in (g(b, "genericBindings", default=[]) or [])[:6]:
    print("  ", "attrs:", sorted(a for a in dir(gb) if not a.startswith("_")))
    print("   path", getattr(gb, "path", None), "attribute", getattr(gb, "attribute", None),
          "classID", getattr(gb, "classID", None), "customType", getattr(gb, "customType", None))
