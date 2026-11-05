# Blocks a release whose campfire / shop scenes disagree with the combat scene they are generated from.
#
# WHY THIS EXISTS -- the v1.0.6 incident: the creature atlas was re-rendered at 1.5x (frame canvas
# 378x359 -> 570x580, sprite scale 1.2534 -> 0.8878) and only scenes/creature_visuals was rebuilt. The
# rest-site (campfire) and merchant (shop) scenes are GENERATED from it and still carried the old frame
# rects and the old hard-coded sprite placement, so the character was a sliced, mispositioned mess in
# every campfire and shop while combat looked perfect. The in-game QA of that release only looked at
# combat, so it shipped.
#
# The check is structural: every AtlasTexture region in the generated scenes must be identical to a
# region in the creature scene, must fit inside the atlas, and the Sprite2D scale must match the
# creature scene's. Run by package-mod.ps1 (blocking); also usable standalone.
#
# Usage:  python .tools/verify-scene-slicing.py
import io
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "pckproject", "Yetannia")
CREATURE = os.path.join(PROJ, "scenes", "creature_visuals", "yetannia.tscn")
GENERATED = [
    ("rest_site", os.path.join(PROJ, "scenes", "rest_site", "yetannia_rest_site.tscn")),
    ("merchant", os.path.join(PROJ, "scenes", "merchant", "yetannia_merchant.tscn")),
]
ATLAS = os.path.join(PROJ, "images", "creature", "yetannia_atlas_0.png")


def regions(path):
    src = io.open(path, encoding="utf-8").read()
    return [(float(a), float(b), float(c), float(d))
            for a, b, c, d in re.findall(r'region = Rect2\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)', src)]


def sprite_scale(path):
    src = io.open(path, encoding="utf-8").read()
    m = re.search(r'\[node name="Sprite2D"[^\]]*\]\n(?:[^\n]*\n)*?scale = Vector2\(([-0-9.]+),', src)
    return float(m.group(1)) if m else None


def atlas_size(path):
    with open(path, "rb") as fh:
        head = fh.read(33)
    return struct.unpack(">II", head[16:24])


def main() -> int:
    problems = []
    for path in [CREATURE] + [p for _n, p in GENERATED]:
        if not os.path.exists(path):
            problems.append("missing scene: %s" % os.path.relpath(path))
    if problems:
        print("FAIL:\n  - " + "\n  - ".join(problems))
        return 2

    aw, ah = atlas_size(ATLAS)
    creature_regions = set(regions(CREATURE))
    creature_scale = sprite_scale(CREATURE)
    print("atlas %dx%d | creature regions %d | sprite scale %s"
          % (aw, ah, len(creature_regions), creature_scale))

    for name, path in GENERATED:
        regs = regions(path)
        outside = [r for r in regs if r[0] < 0 or r[1] < 0 or r[0] + r[2] > aw + 1 or r[1] + r[3] > ah + 1]
        foreign = [r for r in regs if r not in creature_regions]
        scale = sprite_scale(path)
        print("%-9s regions %3d | outside atlas %d | not-in-creature %d | sprite scale %s"
              % (name, len(regs), len(outside), len(foreign), scale))
        if not regs:
            problems.append("%s: no AtlasTexture regions" % name)
        if outside:
            problems.append("%s: %d region(s) outside the atlas" % (name, len(outside)))
        if foreign:
            problems.append("%s: %d region(s) do not match any creature frame "
                            "(stale frame rects -- rerun build-alt-scenes.py)" % (name, len(foreign)))
        if scale is None or creature_scale is None or abs(scale - creature_scale) > 1e-6:
            problems.append("%s: sprite scale %s != creature %s (stale placement)"
                            % (name, scale, creature_scale))

    if problems:
        print("\nFAIL:\n  - " + "\n  - ".join(problems))
        return 1
    print("\nPASS: campfire and shop scenes slice the same frames as the combat scene, "
          "inside the atlas, at the same sprite scale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
