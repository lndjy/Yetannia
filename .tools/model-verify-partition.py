# model-verify-partition.py — independent check of the one identity the whole
# animation decode rests on.
#
# Claim (from the animation subagent): the clip's "slot space" is 10 floats per animated
# transform (pos3 + rot4 quaternion + scl3), and the three storage partitions exactly
# divide it:
#     len(DenseClip.m_SampleArray) + StreamedClip.curveCount + len(ConstantClip.data) == 10 * n
# where n = number of distinct animated transforms = len(genericBindings)/3.
#
# This is structural, not statistical, so it is a real falsification test: if it holds for
# 11/11 clips with exact equality, the layout claim is almost certainly right (a wrong layout
# would have to coincidentally satisfy exact integer equality eleven times).
#
# Also checks the claim that genericBindings are grouped attribute-major:
# all attribute==1, then all 2, then all 3.
#
# usage: python .tools/model-verify-partition.py
import glob
import os
from collections import Counter

import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "out", "export")

ok = bad = 0
for d in sorted(glob.glob(os.path.join(ROOT, "*"))):
    u3d = glob.glob(os.path.join(d, "*.unity3d"))
    if not u3d:
        continue
    env = UnityPy.load(u3d[0])
    clips = [o.read() for o in env.objects if o.type.name == "AnimationClip"]
    if not clips:
        continue
    print(f"\n=== {os.path.basename(d)} ===")
    for c in clips:
        gb = list(c.m_ClipBindingConstant.genericBindings or [])
        attrs = [g.attribute for g in gb]
        n = len(gb) // 3
        # attribute-major grouping: the attribute sequence must be non-decreasing 1..3
        grouped = attrs == sorted(attrs) and set(attrs) <= {1, 2, 3}

        data = c.m_MuscleClip.m_Clip.data
        dense = len(data.m_DenseClip.m_SampleArray)
        streamed = data.m_StreamedClip.curveCount
        constant = len(data.m_ConstantClip.data)
        total = dense + streamed + constant
        want = 10 * n
        hit = total == want
        ok, bad = (ok + 1, bad) if hit else (ok, bad + 1)
        print(f"  {c.m_Name:20s} n={n:3d} bindings={len(gb):3d} grouped={grouped!s:5s} "
              f"dense={dense:4d} streamed={streamed:4d} constant={constant:4d} "
              f"sum={total:5d} 10n={want:5d}  {'MATCH' if hit else '*** MISMATCH ***'} "
              f"attrs={sorted(Counter(attrs).items())}")

print(f"\n{ok} match / {bad} mismatch")
