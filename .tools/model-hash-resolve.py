# model-hash-resolve.py — reverse the generic-clip binding path hashes to real bones.
#
# Why this file exists: an earlier agent tested 4 hash functions against the hierarchy paths,
# got 0/245, and concluded the clips were "humanoid muscle-space retargeted through an Avatar".
# That conclusion is wrong, and the binding table itself disproves it:
#   * typeID == 4 (Transform) for ALL bindings,
#   * attribute takes exactly 3 values (1,2,3) = localPosition/localRotation/localScale,
#   * 244 paths x 3 channels, so every path is distinct,
#   * NO Avatar exists in ANY bundle (Animator.m_Avatar is NULL everywhere), so a humanoid
#     retarget is not merely unnecessary, it is impossible.
# => these ARE generic per-transform TRS curves and the hash MUST be reversible.
#
# Two things that made the earlier attempt fail:
#   1. hierarchy.json has no parent links, only a `depth` per entry in traversal order, so path
#      strings were unbuildable; a depth stack fixes it.
#   2. the clip paths are relative to the Animator root (mx_3015004_01), NOT the prefab root
#      (3015004_prefab) — two levels must be stripped.
# Also: Unity's StringToHash returns a signed int while the serialized path reads as uint, so
# everything is masked to 32 bits on both sides.
#
# usage: python .tools/model-hash-resolve.py
import json
import os
import sys
import zlib
from collections import Counter

import UnityPy

# Derive every path from __file__. Never hardcode a non-ASCII path literal in a source file that
# a Windows shell might round-trip through the ANSI codepage (that mangles it irreversibly).
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "out", "export")
BUNDLE = os.path.join(ROOT, "pet__3015004_prefab")
U3D = os.path.join(BUNDLE, "pet__3015004_prefab.unity3d")
HIER = os.path.join(BUNDLE, "hierarchy.json")


def unity_hash(s, utf8=False):
    """UnityEngine.Animator.StringToHash — uint32, FNV-ish."""
    h = 0
    units = list(s.encode("utf-8")) if utf8 else [ord(c) for c in s]
    for u in units:
        h = (u + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


def crc32_hash(s):
    return zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF


# ---------------------------------------------------------------- hierarchy
if not os.path.exists(HIER):
    sys.exit(f"missing {HIER} — run .tools/model-export-hierarchy.py first")

with open(HIER, encoding="utf-8") as fh:
    h = json.load(fh)
entries = h["hierarchies"][list(h["hierarchies"])[0]]
print("hierarchy entries:", len(entries))
print("entry fields:", sorted(entries[0].keys()))

depth_field = next((k for k in ("depth", "m_Depth", "level") if k in entries[0]), None)
print("depth field:", depth_field)
print("first 8:", [(e.get(depth_field), e.get("name")) for e in entries[:8]])


def build_chains():
    """{full_chain_tuple: [indices]} rebuilt from the depth stack."""
    out = {}
    stack = []
    for i, e in enumerate(entries):
        d = e.get(depth_field, 0)
        del stack[d:]
        stack.append(e.get("name") or "")
        out.setdefault(tuple(stack), []).append(i)
    return out


chains = build_chains()
print("distinct chains:", len(chains))

# ---------------------------------------------------------------- bindings
env = UnityPy.load(U3D)
clips = [o.read() for o in env.objects if o.type.name == "AnimationClip"]
wanted = set()
for c in clips:
    for gb in (c.m_ClipBindingConstant.genericBindings or []):
        wanted.add(gb.path & 0xFFFFFFFF)
print(f"\nunique binding path hashes across {len(clips)} clips: {len(wanted)}")

# ---------------------------------------------------------------- sweep
HASHES = {"crc32": crc32_hash, "unity": unity_hash,
          "unity-utf8": lambda s: unity_hash(s, True)}
FALLBACKS = {"ident": lambda s: s, "lower": str.lower}

print("\n=== coverage sweep: hash x strip-depth x case ===")
best = None
for hname, hf in HASHES.items():
    for strip in range(0, 4):
        for fbname, fb in FALLBACKS.items():
            table = {}
            for chain in chains:
                sub = chain[strip:]
                if not sub:
                    continue
                table.setdefault(hf(fb("/".join(sub))) & 0xFFFFFFFF, "/".join(sub))
            hit = len(set(table) & wanted)
            if hit:
                print(f"  {hname:11s}/{fbname:5s}/strip{strip}  candidates={len(table):4d} "
                      f"matched={hit}")
            if best is None or hit > best[1]:
                best = (f"{hname}|{fbname}|{strip}", hit)

print(f"\nbest: {best[0]} -> {best[1]}/{len(wanted)}")
if best[1] == 0:
    sys.exit("no variant matched — the hash scheme is something else")

hname, fbname, strip_s = best[0].split("|")
hf, fb, strip_n = HASHES[hname], FALLBACKS[fbname], int(strip_s)
table = {}
for chain in chains:
    sub = chain[strip_n:]
    if sub:
        table.setdefault(hf(fb("/".join(sub))) & 0xFFFFFFFF, "/".join(sub))
resolved = {k: table[k] for k in wanted if k in table}
print(f"resolved {len(resolved)}/{len(wanted)} binding hashes to real paths")

print("\n--- animated transforms ---")
for k in sorted(resolved, key=lambda x: resolved[x]):
    print("   ", resolved[k])

per_bone = {}
for c in clips:
    for gb in (c.m_ClipBindingConstant.genericBindings or []):
        p = resolved.get(gb.path & 0xFFFFFFFF)
        if p:
            per_bone.setdefault(p, set()).add(gb.attribute)
print(f"\nanimated transforms: {len(per_bone)}")
print("attribute legend: 1=localPosition 2=localRotation 3=localScale")
print("channel mix:", Counter(tuple(sorted(v)) for v in per_bone.values()))
print("\nRESULT: clips map to", len(per_bone), "real bones; hash =", hname,
      "of the path relative to the Animator root, strip", strip_n)
