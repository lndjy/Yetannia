# model-clip-probe.py — can we actually ANIMATE? Checks that AnimationClip curve data
# (paths + keyframes) is readable, not just present as an opaque type tree.
# usage: python .tools/model-clip-probe.py [bundle.unity3d]
import sys

import UnityPy

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\pet__3015004_prefab.unity3d"

env = UnityPy.load(BUNDLE)
clips = [o.read() for o in env.objects if o.type.name == "AnimationClip"]
print("clips:", len(clips))

for c in clips:
    fc = len(c.m_FloatCurves) if c.m_FloatCurves else 0
    pc = len(c.m_PositionCurves) if c.m_PositionCurves else 0
    qc = len(c.m_RotationCurves) if c.m_RotationCurves else 0
    sc = len(c.m_ScaleCurves) if c.m_ScaleCurves else 0
    stop = "?"
    try:
        stop = round(c.m_MuscleClip.m_Clip.data.m_StopTime, 3)
    except Exception:
        pass
    print(f"  {c.m_Name:22s} float={fc:4d} pos={pc:4d} quat={qc:4d} scale={sc:3d} stop={stop}")

if clips:
    c = clips[0]
    print("--- sample: first float curve ---")
    f = c.m_FloatCurves[0]
    print("  attrs:", [a for a in dir(f) if not a.startswith("_")])
    print("  path :", f.path, "attribute:", f.attribute, "classID:", f.classID)
    keys = f.curve.m_Curve if f.curve else None
    print("  keys :", len(keys) if keys else 0)
    if keys:
        for k in keys[:4]:
            print("   ", k.time, k.value, "in", k.inSlope, "out", k.outSlope)
