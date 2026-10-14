# build-alt-scenes.py -- generate the rest-site (campfire) and merchant scenes for Yetannia.
#
# WHY THESE ARE GENERATED RATHER THAN HAND-WRITTEN
#   Both scenes must animate a Sprite2D through a flipbook, which means ~30 AtlasTexture sub-resources
#   and an Animation whose track is a list of SubResource references. Hand-editing that is how you get
#   a stale frame list; instead this reads the ALREADY-VERIFIED creature scene
#   (.tools/pckproject/Yetannia/scenes/creature_visuals/yetannia.tscn, produced by
#   build-creature-anim.py) and re-emits the same atlas regions and the same frame timings. Re-run it
#   after any creature rebuild.
#
# VRAM: both scenes reference res://Yetannia/images/creature/yetannia_atlas_0.png -- the SAME texture
#   the in-combat flipbook uses -- so they add ZERO texture memory. Only sub-resources (AtlasTexture
#   regions, an Animation and an AnimationLibrary) are added, which is metadata, not pixels. That is
#   why no new frames are rendered for them: the source bundles contain no sitting/merchant animation,
#   and adding a second atlas for a slightly different idle would cost a full extra page.
#
# POSE IS AN APPROXIMATION AND LABELLED AS ONE: the only usable clip is the standing idle. There is no
#   authored "sitting at a campfire" or "shopkeeper" motion in the source data (the sibling
#   *_richang bundles have rc_daiji / rc_chumo_*, but using them means rendering and shipping another
#   atlas page; see the report).
#
# BASE-LIB CONTRACTS (from .tools/out/charselect/TASK_C_FINDINGS.md, all cited there):
#   rest site -- NRestSiteCharacterFactory has FlexibleStructure == false because it declares
#     NodeInfo<Control>("ControlRoot", MakeNameUnique: false). So the scene ROOT is discarded and its
#     children are re-parented onto a freshly built NRestSiteCharacter; the root's Scale is copied
#     only if the root is a Node2D (NodeFactory.cs:342-352) but its Position is later zeroed by
#     NRestSiteRoom.cs:339. Two nodes are MANDATORY: a direct child Control named exactly
#     "ControlRoot", and a Control named "Hitbox" anywhere in the subtree (a Marker2D named Hitbox
#     throws in NodeFactory.ConvertNodeType). SelectionReticle / ThoughtBubbleLeft / ThoughtBubbleRight
#     are generated from Hitbox.
#   merchant -- NMerchantCharacterFactory passes an EMPTY node list, so FlexibleStructure == true and
#     the whole scene root is kept as child #0 of the new NMerchantCharacter (NodeFactory.cs:506) --
#     AND ConvertScene has already copied that root's Scale onto the generated node (:342-352, :452-492).
#     A scale on the merchant root is therefore applied twice; see node_blocks() for the fix and the
#     measurement. No named nodes are required. NMerchantCharacter._Ready does `new MegaSprite(GetChild(0))`,
#     which throws unless child #0 is a SpineSprite (MegaSpineBinding.cs:119-143) -- stock Godot has no
#     SpineSprite, so YetanniaPatches kills that call and drives our own AnimationPlayer instead.
#
# usage: python .tools/build-alt-scenes.py [--rest-scale 2.0] [--merchant-scale 2.01] [--dry-run]
import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "pckproject", "Yetannia")
CREATURE = os.path.join(PROJ, "scenes", "creature_visuals", "yetannia.tscn")
ATLAS = "res://Yetannia/images/creature/yetannia_atlas_0.png"
OUT_REST = os.path.join(PROJ, "scenes", "rest_site", "yetannia_rest_site.tscn")
OUT_MERCH = os.path.join(PROJ, "scenes", "merchant", "yetannia_merchant.tscn")

# The verified in-combat sprite placement (QA round 38 re-measured it in game:
# globalScale (1.2534,1.2534), live Bounds 276.42x284.06, offset_bottom 0.00, idle union silhouette
# 221 atlas px * 1.2534 = 277.00 design px = -0.4 % of the Ironclad's 278). Copied verbatim so the
# rest-site and merchant figures are the same size as the in-combat one instead of a second guess.
SPRITE_POS = (-186.4506, -403.5928)
SPRITE_SCALE = 1.2534
# Root-local silhouette box of that sprite config, from the creature scene's own Bounds node.
BOUNDS = (-91.5311, -284.0566, 184.8924, 0.0)
SIL_W, SIL_H = BOUNDS[2] - BOUNDS[0], BOUNDS[3] - BOUNDS[1]      # 276.42 x 284.06


def parse_creature(path):
    src = io.open(path, encoding="utf-8").read()
    regions = {}
    for m in re.finditer(r'\[sub_resource type="AtlasTexture" id="(AtlasTexture_\d+)"\]\s*\n'
                         r'atlas = ExtResource\("([^"]+)"\)\s*\n'
                         r'region = Rect2\(([^)]*)\)', src):
        regions[m.group(1)] = tuple(float(v) for v in m.group(3).split(","))
    anims = {}
    for m in re.finditer(r'\[sub_resource type="Animation" id="(Anim_\w+)"\]\s*\n(.*?)(?=\n\[)',
                         src, re.S):
        body = m.group(2)
        name = re.search(r'resource_name = "([^"]+)"', body)
        length = re.search(r'length = ([\d.]+)', body)
        loop = re.search(r'loop_mode = (\d+)', body)
        path_ = re.search(r'tracks/0/path = NodePath\("([^"]+)"\)', body)
        times = re.search(r'"times": PackedFloat32Array\(([^)]*)\)', body)
        values = re.search(r'"values": \[([^\]]*)\]', body)
        if not (name and times and values):
            continue
        anims[name.group(1)] = dict(
            length=float(length.group(1)) if length else 1.0,
            loop=int(loop.group(1)) if loop else 0,
            track=path_.group(1) if path_ else "Sprite2D:texture",
            times=[t.strip() for t in times.group(1).split(",") if t.strip()],
            # the values list is `SubResource("AtlasTexture_12"),...`; keep only the inner id
            values=[re.search(r'SubResource\("([^"]+)"\)', v).group(1)
                    for v in values.group(1).split(",")
                    if re.search(r'SubResource\("([^"]+)"\)', v)])
    atlas_res = re.search(r'\[ext_resource type="Texture2D" path="([^"]+)" id="([^"]+)"\]', src)
    return regions, anims, (atlas_res.group(1), atlas_res.group(2)) if atlas_res else (ATLAS, "tex0")


PROSE = '''[gd_scene load_steps={steps} format=3]

; {title}
; Generated by .tools/build-alt-scenes.py -- do not hand-edit; retune the script instead.
;
; {notes}
;
; The atlas is the SAME texture the in-combat flipbook uses, so this scene adds no texture memory;
; it only adds AtlasTexture regions and an Animation.

[ext_resource type="Texture2D" path="{atlas}" id="tex0"]

'''


def emit(atlas, regions, anims, want, title, notes):
    """Build the .tscn text for one scene. `want` = list of animation names to include."""
    out = []
    used = []           # atlas region ids in first-use order -> renumbered locally
    ren = {}

    def rid(old):
        if old not in ren:
            ren[old] = "AtlasTexture_%d" % len(used)
            used.append(old)
        return ren[old]

    anim_blocks = []
    for aname in want:
        a = anims[aname]
        vals = [rid(v) for v in a["values"]]
        anim_blocks.append((aname, a, vals))

    steps = 1 + 1 + len(used) + len(anim_blocks) + 1
    txt = PROSE.format(steps=steps, title=title, notes=notes, atlas=atlas)
    for old in used:
        x, y, w, h = regions[old]
        txt += ('[sub_resource type="AtlasTexture" id="%s"]\n'
                'atlas = ExtResource("tex0")\n'
                'region = Rect2(%s, %s, %s, %s)\n\n'
                % (ren[old], g(x), g(y), g(w), g(h)))
    for aname, a, vals in anim_blocks:
        txt += '[sub_resource type="Animation" id="Anim_%s"]\n' % aname
        txt += 'resource_name = "%s"\n' % aname
        txt += 'length = %s\n' % g(a["length"])
        if a["loop"]:
            txt += 'loop_mode = %d\n' % a["loop"]
        txt += 'tracks/0/type = "value"\n'
        txt += 'tracks/0/imported = false\n'
        txt += 'tracks/0/enabled = true\n'
        txt += 'tracks/0/path = NodePath("Sprite2D:texture")\n'
        txt += 'tracks/0/interp = 1\n'
        txt += 'tracks/0/loop_wrap = true\n'
        txt += 'tracks/0/keys = {\n'
        txt += '"times": PackedFloat32Array(%s),\n' % ",".join(a["times"])
        txt += '"transitions": PackedFloat32Array(%s),\n' % ",".join(["1"] * len(a["times"]))
        txt += '"update": 1,\n'
        txt += '"values": [%s]\n' % ",".join('SubResource("%s")' % v for v in vals)
        txt += '}\n\n'
    txt += '[sub_resource type="AnimationLibrary" id="AnimationLibrary_yetannia_alt"]\n'
    txt += '_data = {\n'
    for aname, _a, _v in anim_blocks:
        txt += '&"%s": SubResource("Anim_%s"),\n' % (aname, aname)
    txt += '}\n\n'
    return txt, used


def g(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def node_blocks(kind, root_name, root_scale, first_region, animations, root_local_hitbox):
    """The node section. `kind` is 'rest' or 'merchant'.

    WHERE THE CHARACTER SCALE LIVES DEPENDS ON THE FACTORY, and getting it wrong is a silent 2x:

      rest site -- NRestSiteCharacterFactory declares NodeInfo<Control>("ControlRoot",
        MakeNameUnique: false), so FlexibleStructure == false (NodeFactory.cs:287-291) and
        TransferAndCreateNodes takes the non-flexible branch (:511-530): the source root is FREED and
        its children are re-parented onto the generated NRestSiteCharacter, onto which ConvertScene has
        copied the root's Scale (:342-352). A scale on the root therefore survives EXACTLY ONCE, which
        is what the rest-site figure needs (the room's Character_N container adds the 0.5 that brings
        the net scale back to 1). Unchanged.

      merchant -- NMerchantCharacterFactory passes an EMPTY node list, so FlexibleStructure == true
        (Enumerable.All over no entries) and :506 keeps the source root as child #0 *in addition to*
        the Scale that ConvertScene has already copied onto the generated NMerchantCharacter. A scale
        on the merchant root is therefore applied TWICE: measured live in a shop, sprite gscale
        5.0639 = 1.2534 x 2.01^2 instead of the authored 1.2534 x 2.01, i.e. 1,117 x 1,148 design px
        instead of 556 x 571 -- taller than the 1080-px screen, her head above the top edge.
        THE FIX: the merchant root carries scale 1 and `Visuals` carries the character scale, exactly
        the shape vanilla's own merchant scenes have (scenes/merchant/characters/ironclad_merchant:
        root `IroncladMerchant` Node2D with NO scale, SpineSprite 0.47). The scale still multiplies the
        Sprite2D's position and rect about the root origin (the feet), so the figure stays planted on
        the CharacterContainer slot -- verified on screen at design (564,766), net scale 2.01.
    """
    merchant = kind == "merchant"
    common = []
    common.append('[node name="%s" type="Node2D"]' % root_name)
    if merchant:
        common.append('; scale deliberately 1: the factory keeps this root as child #0 of the generated')
        common.append('; NMerchantCharacter AFTER copying this root\'s Scale onto it, so a scale here is')
        common.append('; applied twice (measured 2.01 x 2.01). The character scale is on Visuals below,')
        common.append('; which is also what vanilla\'s merchant scenes do (root Node2D scale 1, visual')
        common.append('; child 0.47). The rest-site scene keeps its scale HERE, because that factory')
        common.append('; discards the source root instead of keeping it.')
    elif abs(root_scale - 1.0) > 1e-9:
        common.append('scale = Vector2(%s, %s)' % (g(root_scale), g(root_scale)))
    common.append('')
    common.append('; Children live under Visuals so the factory can re-parent the whole subtree; the')
    common.append('; AnimationPlayer is a sibling of the Sprite2D it drives, so its track path is')
    common.append('; relative to Visuals (exactly as in creature_visuals/yetannia.tscn).')
    common.append('[node name="Visuals" type="Node2D" parent="."]')
    if merchant and abs(root_scale - 1.0) > 1e-9:
        common.append('scale = Vector2(%s, %s)' % (g(root_scale), g(root_scale)))
    common.append('')
    common.append('[node name="AnimationPlayer" type="AnimationPlayer" parent="Visuals"]')
    common.append('libraries = {')
    common.append('"": SubResource("AnimationLibrary_yetannia_alt")')
    common.append('}')
    common.append('autoplay = "%s"' % animations[0])
    common.append('playback_default_blend_time = 0.0')
    common.append('')
    common.append('[node name="Sprite2D" type="Sprite2D" parent="Visuals"]')
    common.append('texture = SubResource("%s")' % first_region)
    common.append('position = Vector2(%s, %s)' % (g(SPRITE_POS[0]), g(SPRITE_POS[1])))
    common.append('scale = Vector2(%s, %s)' % (g(SPRITE_SCALE), g(SPRITE_SCALE)))
    common.append('centered = false')
    common.append('')
    if kind == "rest":
        common.append('; MANDATORY (NRestSiteCharacterFactory): a direct child Control named')
        common.append('; "ControlRoot" and a Control named "Hitbox" anywhere below it. The factory sets')
        common.append('; unique_name_in_owner itself, and generates %SelectionReticle / %ThoughtBubble*')
        common.append('; from the Hitbox rect, so those are deliberately not authored here.')
        common.append('[node name="ControlRoot" type="Control" parent="."]')
        common.append('layout_mode = 3')
        common.append('anchors_preset = 0')
        common.append('mouse_filter = 2')
        common.append('')
        common.append('[node name="Hitbox" type="Control" parent="ControlRoot"]')
        common.append('unique_name_in_owner = true')
        common.append('layout_mode = 0')
        common.append('offset_left = %s' % g(root_local_hitbox[0]))
        common.append('offset_top = %s' % g(root_local_hitbox[1]))
        common.append('offset_right = %s' % g(root_local_hitbox[2]))
        common.append('offset_bottom = %s' % g(root_local_hitbox[3]))
        common.append('mouse_filter = 2')
        common.append('')
    return "\n".join(common)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rest-scale", type=float, default=2.0,
                    help="root scale for the rest site. The room puts the character in a container "
                         "scaled 0.5 (measured on the vanilla rest-site room), and the in-combat "
                         "silhouette is 277 design px, so 2.0 * 0.5 * 277 = 277 px -- inside the "
                         "vanilla rest-site range of 245-297 px.")
    ap.add_argument("--merchant-scale", type=float, default=2.01,
                    help="root scale for the merchant. No extra container scale there, and vanilla's "
                         "merchant figures are 461-598 design px tall, so 2.01 * 277 = 557 px.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    regions, anims, (atlas, _tid) = parse_creature(CREATURE)
    print("[src] %s\n      %d atlas regions, animations: %s"
          % (os.path.relpath(CREATURE), len(regions), sorted(anims)))
    for need in ("idle", "die"):
        if need not in anims:
            raise SystemExit("creature scene has no %r animation" % need)

    rest_txt, rest_used = emit(
        atlas, regions, anims, ["idle"],
        "Rest-site (campfire) model for Yetannia -- animated flipbook.",
        "BASE-LIB CONTRACT: the root is a Node2D (so its Scale survives conversion) whose children are\n"
        "; re-parented onto a generated NRestSiteCharacter; 'ControlRoot' and 'Hitbox' below are\n"
        "; mandatory. POSITION/ROOT-OFFSET ARE AN APPROXIMATION: the source data has no sitting clip, so\n"
        "; this plays the standing idle. Nothing in the game drives an NRestSiteCharacter's animation\n"
        "; (CustomAnimationPatch is wired to NCreature only), which is why the AnimationPlayer uses\n"
        "; autoplay rather than a trigger.")
    merch_txt, merch_used = emit(
        atlas, regions, anims, ["idle", "die"],
        "Merchant model for Yetannia -- animated flipbook.",
        "BASE-LIB CONTRACT: NMerchantCharacterFactory has no named-node requirements and keeps this\n"
        "; scene root as child #0 of the generated NMerchantCharacter, ON TOP OF copying that root's\n"
        "; Scale onto the generated node -- so the root's scale is 1 here and Visuals carries the\n"
        "; character scale (vanilla's merchant scenes have the same shape: root Node2D, no scale;\n"
        "; the visual child carries 0.47). With the scale on the root the figure is drawn at 2.01x\n"
        "; too large, head above the screen. NMerchantCharacter._Ready wraps\n"
        "; GetChild(0) in `new MegaSprite(...)`, which THROWS for anything but a SpineSprite, and stock\n"
        "; Godot has no SpineSprite -- so YetanniaPatches skips that call and plays this AnimationPlayer\n"
        "; instead (idle on ready, 'die' at the game-over screen), which also removes the ERROR the mod\n"
        "; used to log on every shop visit. POSITION/POSE ARE AN APPROXIMATION: no shopkeeper clip\n"
        "; exists in the source data; this is the standing idle.")

    # hitbox: the silhouette box, padded 10 %, in ROOT-local units (the rest-site root scale multiplies it)
    pad_x, pad_y = SIL_W * 0.10, SIL_H * 0.10
    hb = (BOUNDS[0] - pad_x, BOUNDS[1] - pad_y, BOUNDS[2] + pad_x, BOUNDS[3] + pad_y)
    rest_txt += node_blocks("rest", "YetanniaRestSite", args.rest_scale, "AtlasTexture_0", ["idle"], hb)
    merch_txt += node_blocks("merchant", "YetanniaMerchant", args.merchant_scale, "AtlasTexture_0",
                             ["idle", "die"], hb)

    print("[rest]     %d atlas regions reused, %d animations" % (len(rest_used), 1))
    print("[merchant] %d atlas regions reused, %d animations" % (len(merch_used), 2))
    print("[size]     rest     : scale %.4f on the ROOT (that factory discards the root) -> %.0f x %.0f "
          "design px (vanilla rest site 153-247 x 245-297)"
          % (args.rest_scale, SIL_W * args.rest_scale * 0.5, SIL_H * args.rest_scale * 0.5))
    print("[size]     merchant : scale %.4f on VISUALS (the root scale would be applied twice) -> "
          "%.0f x %.0f design px from this scene's own Bounds box (vanilla merchant 343-478 x 461-598);"
          % (args.merchant_scale, SIL_W * args.merchant_scale, SIL_H * args.merchant_scale))
    print("[size]                the IDLE alpha union measured off the atlas is 262.0 x 277.0 root-local "
          "= %.0f x %.0f design px at this scale"
          % (262.0 * args.merchant_scale, 277.0 * args.merchant_scale))
    print("[vram]     +0 MiB: both scenes reference %s, already loaded by the in-combat flipbook."
          % os.path.basename(atlas))

    if args.dry_run:
        print("\n--- rest ---\n" + rest_txt[:1200] + "\n...")
        return
    for path, txt in ((OUT_REST, rest_txt), (OUT_MERCH, merch_txt)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        io.open(path, "w", encoding="utf-8", newline="\n").write(txt + "\n")
        print("[write] %s (%d bytes)" % (os.path.relpath(path), len(txt) + 1))


if __name__ == "__main__":
    main()
