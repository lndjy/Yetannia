# model-clip-probe2.py — where do the AnimationClip curves actually live?
# All four classic curve lists are empty, so the curve data must be in the compressed
# (dense) representation. Find it and see whether it is decodable.
# usage: python .tools/model-clip-probe2.py [bundle.unity3d]
import sys

import UnityPy

BUNDLE = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\pet__3015004_prefab.unity3d"

env = UnityPy.load(BUNDLE)
objs = [o for o in env.objects if o.type.name == "AnimationClip"]
print("clips:", len(objs))
c = objs[0].read()
print("attrs:", sorted(a for a in dir(c) if not a.startswith("_")))

mc = getattr(c, "m_MuscleClip", None)
print("m_MuscleClip:", type(mc).__name__ if mc is not None else None)
if mc is not None:
    print("  muscle attrs:", sorted(a for a in dir(mc) if not a.startswith("_")))
    clip = getattr(mc, "m_Clip", None)
    print("  m_Clip:", type(clip).__name__ if clip is not None else None)
    if clip is not None:
        print("  clip attrs:", sorted(a for a in dir(clip) if not a.startswith("_")))
        d = getattr(clip, "data", None)
        print("  data:", type(d).__name__ if d is not None else None)
        if d is not None:
            print("  data attrs:", sorted(a for a in dir(d) if not a.startswith("_")))
            for name in ("m_CompressedData", "m_Streams", "m_StopTime", "m_SampleRate"):
                v = getattr(d, name, "<none>")
                if isinstance(v, (bytes, bytearray)):
                    print(f"    {name}: {len(v)} bytes")
                elif isinstance(v, list):
                    print(f"    {name}: list[{len(v)}]")
                else:
                    print(f"    {name}: {v!r}")

# Also look at the raw type tree so we know exactly which nodes exist.
tt = getattr(objs[0], "type_tree", None) or getattr(objs[0], "serialized_type", None)
print("--- serialized type tree (top level) ---")
try:
    nodes = tt.m_Nodes
    for n in nodes[:60]:
        print(f"  L{n.m_Level} {n.m_Type} {n.m_Name}")
except Exception as exc:
    print("  no type tree:", type(exc).__name__, exc)
