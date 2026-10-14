# model-clip-space.py — decide the ONE thing that blocks animation:
# are these clips generic per-transform curves, or humanoid muscle-space retargeted via an Avatar?
#
# The previous agent tested 4 hash functions against the hierarchy paths and got 0/245 matches,
# and concluded "humanoid muscle-space". That conclusion is checkable directly:
#   * generic  => `attribute` takes only a handful of values (position/rotation/scale DoF) and
#                 every binding path is distinct.
#   * humanoid => `attribute` is a muscle index, so it ranges widely (~0..200) and MANY bindings
#                 share the same path (or the path is the root/empty).
# Also checks whether ANY Avatar exists to retarget through.
# usage: python .tools/model-clip-space.py
import glob
import os
from collections import Counter

import UnityPy

ROOT = r"D:\桌面\sts2mod\.tools\out\export"

print("=== Avatars / Animators anywhere? ===")
for d in sorted(glob.glob(os.path.join(ROOT, "*"))):
    u = glob.glob(os.path.join(d, "*.unity3d"))
    if not u:
        continue
    env = UnityPy.load(u[0])
    avatars = [o for o in env.objects if o.type.name == "Avatar"]
    anims = [o for o in env.objects if o.type.name == "Animator"]
    line = f"{os.path.basename(d):42s} avatars={len(avatars)} animators={len(anims)}"
    for a in anims:
        ar = a.read()
        av = getattr(ar, "m_Avatar", None)
        ctrl = getattr(ar, "m_Controller", None)
        line += f" | m_Avatar={'set' if av else 'NULL'} m_Controller={'set' if ctrl else 'NULL'}"
    print(line)

print()
print("=== clip binding space ===")
B = os.path.join(ROOT, "pet__3015004_prefab", "pet__3015004_prefab.unity3d")
env = UnityPy.load(B)

# AnimatorController: which clips does it drive?
for o in env.objects:
    if o.type.name == "AnimatorController":
        ac = o.read()
        print("AnimatorController:", getattr(ac, "m_Name", "?"),
              "attrs:", sorted(a for a in dir(ac) if not a.startswith("_"))[:18])
        for cp in (getattr(ac, "m_Controller", None) or {}).get("m_Clips", []) if isinstance(
                getattr(ac, "m_Controller", None), dict) else []:
            print("   clip:", cp)
        break

ANIM_TYPE = {0: "Legacy", 1: "Generic", 2: "Humanoid"}
for o in [x for x in env.objects if x.type.name == "AnimationClip"]:
    c = o.read()
    raw_type = getattr(c, "m_AnimationType", "<missing>")
    b = c.m_ClipBindingConstant
    gb = list(getattr(b, "genericBindings", None) or [])
    attrs = Counter(x.attribute for x in gb)
    tids = Counter(x.typeID for x in gb)
    paths = Counter(x.path for x in gb)
    uniq = len(paths)
    top = paths.most_common(3)
    print(f"\n{c.m_Name:20s} m_AnimationType={raw_type!r} ({ANIM_TYPE.get(raw_type,'?')}) "
          f"bindings={len(gb)} uniquePaths={uniq}")
    print(f"   attribute values : {sorted(attrs.items())[:12]}{' ...' if len(attrs) > 12 else ''}"
          f"  (distinct={len(attrs)})")
    print(f"   typeIDs          : {dict(tids)}")
    print(f"   most repeated paths: {top}")
    dense = c.m_MuscleClip.m_Clip.data.m_DenseClip
    print(f"   dense: curves={dense.m_CurveCount} frames={dense.m_FrameCount} "
          f"rate={dense.m_SampleRate} samples={len(dense.m_SampleArray)}")
