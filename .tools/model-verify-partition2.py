# model-verify-partition2.py — corrected independent check of the animation decode's core identity.
#
# Fixing my own bug from v1: the identity is
#     DenseClip.m_CurveCount + StreamedClip.curveCount + len(ConstantClip.data) == 10 * n
# NOT len(DenseClip.m_SampleArray), which is frame_count * curve_count (zd_daiji: 62 * 656 = 40672).
# v1 therefore reported a false 0/60. Using the wrong field is exactly the mistake this script exists
# to catch, so it is recorded here rather than quietly fixed.
#
# v1 also reported that genericBindings are NOT attribute-major (attrs == sorted(attrs) was False),
# which contradicts the decoder's claim of "all pos, then all rot, then all scale". This script
# prints the raw sequence so that conflict is settled by inspection rather than by argument.
#
# usage: python .tools/model-verify-partition2.py
import glob
import os
from collections import Counter

import UnityPy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "out", "export")

identity_ok = identity_bad = 0
gen_ok = gen_bad = 0
grouped_ok = grouped_bad = 0
printed_pattern = False

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

        seq = attrs == sorted(attrs)
        interleaved = attrs[:3] == [1, 2, 3] if len(attrs) >= 3 else False
        if seq:
            grouped_ok += 1
        else:
            grouped_bad += 1

        data = c.m_MuscleClip.m_Clip.data
        dense = data.m_DenseClip.m_CurveCount      # <-- the fix
        frames = data.m_DenseClip.m_FrameCount
        samples = len(data.m_DenseClip.m_SampleArray)
        streamed = data.m_StreamedClip.curveCount
        constant = len(data.m_ConstantClip.data)
        total = dense + streamed + constant

        # The decoder's headline form is "== 10 * n", which silently assumes each attribute has the
        # same number of bones. Many clips do NOT: e.g. 301500401/zd_shengli has
        # pos=251, rot=253, scale=251 (2 extra rotation bindings), so 10n is wrong there.
        # The general slot-space size is 3*nPos + 4*nRot + 3*nScale.
        n_pos = sum(1 for a in attrs if a == 1)
        n_rot = sum(1 for a in attrs if a == 2)
        n_scl = sum(1 for a in attrs if a == 3)
        want_unit = 10 * n
        want_gen = 3 * n_pos + 4 * n_rot + 3 * n_scl
        hit = total == want_unit
        hit_gen = total == want_gen
        if hit:
            identity_ok += 1
        else:
            identity_bad += 1
        if hit_gen:
            gen_ok += 1
        else:
            gen_bad += 1
        fc_ok = samples == frames * dense

        flag = "10n MATCH" if hit else ("10n no, gen YES" if hit_gen else "*** BOTH FAIL ***")
        print(f"  {c.m_Name:20s} n={n:3d} pos/rot/scl={n_pos}/{n_rot}/{n_scl} "
              f"dense={dense:4d}(f={frames:3d}{'=f*c' if fc_ok else ' !=f*c ***'}) "
              f"streamed={streamed:4d} const={constant:4d} sum={total:5d} "
              f"10n={want_unit:5d} gen={want_gen:5d} | {flag} | attrSeq={seq}")

        if not printed_pattern and len(gb) > 30:
            printed_pattern = True
            print(f"    first 12 (attribute, path): {[(g.attribute, g.path) for g in gb[:12]]}")
            print(f"    attr pattern first 30     : {attrs[:30]}")
            print(f"    attr counts               : {sorted(Counter(attrs).items())}")

print(f"\nidentity  10n form (assumes equal per-attribute counts): {identity_ok} match / {identity_bad} mismatch")
print(f"identity  general form 3nPos+4nRot+3nScl          : {gen_ok} match / {gen_bad} mismatch")
print(f"grouping (bindings non-decreasing 1,1,..,2,2,..,3,3):        "
      f"{grouped_ok} grouped / {grouped_bad} NOT grouped")
