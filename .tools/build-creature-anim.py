# build-creature-anim.py -- turn the decoded 3D rig motion into a packed 2D flipbook for
# Yetannia's in-combat creature visual (res://Yetannia/scenes/creature_visuals/yetannia.tscn).
#
# WHY A FLIPBOOK: the game reaches an in-combat character's animation through
# NCreature.SetAnimationTrigger -> BaseLib's CustomAnimationPatch (a prefix on that method) ->
# BaseLib.Utils.CustomAnimation.PlayCustomAnimation, which looks for an AnimationTree, an
# AnimationPlayer or an AnimatedSprite2D under the NCreature node and plays the animation named
# after the trigger. See .tools/out/spine/CONTRACT.md, sections 1-4. No Spine rig is required.
#
# WHAT IS REUSED: nothing is re-decoded here. model-anim-clip.py does the clip -> bone TRS decoding
# and model-render.py does mesh/skin/rasterising. This script adds only
#   * a SINGLE camera shared by every clip. The frames already in out/render/anim/* were each
#     framed to their own bbox (camera_for over that clip's own bounds), so they cannot be stacked
#     into one sprite -- a frame of the idle and a frame of the dash are at different scales.
#   * the flipbook-specific bits: frame trimming, atlas packing, and the Godot scene/resource text.
#
# usage:
#   python .tools/build-creature-anim.py probe [--height H --width W]
#   python .tools/build-creature-anim.py build [--ssaa 2 --node-scale 0.85]
#   python .tools/build-creature-anim.py build --target-height 277      # solve node-scale for a size
#   python .tools/build-creature-anim.py build --no-toon               # A/B against the old shading
import argparse
import importlib.util
import json
import math
import os
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "spine")
# Staged output root. The generator must not write straight into .tools/pckproject (the mod's pack
# project) or into another agent's .tools/out/spine tree; --outdir overrides it.
OUTSTAGE = os.path.join(HERE, "out", "visual", "build")


def _imp(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mrv = _imp("model_anim_render", os.path.join(HERE, "model-anim-render.py"))
mr = mrv.mr
ma = mrv.ma

BUNDLE = mr.DEFAULT_BUNDLE
FWD = np.array([0.0, 0.0, 1.0])   # same as model-anim-render.py's default (no --flip-z)

# --------------------------------------------------------------------------- animation plan
#
# The trigger set a player creature can receive is (CONTRACT.md section 4):
#   Idle, Attack, Cast, PowerUp, Hit, Dead, Revive, Relaxed
# BaseLib tries these names in order (CustomAnimationPatch.SendTriggerToOtherAnimators, L151-168):
#   Hit  -> Hit, Hurt, hit, hurt          Dead -> Dead, Die, dead, die
#   other-> <Trigger>, <trigger lowercased>
# and Revive separately (PlayCustomAnimation(node, "revive", "Revive"), L139).
# Naming our animations with the lowercase form satisfies every one of those lists.
#
# src = (clip, first, last_inclusive, step, follow). follow="xz" cancels the skeleton root's
# horizontal translation, which is REQUIRED for the in-combat sprite: zd_jn_01 dashes ~6 m and the
# character must stay on its combat slot.
PLAN = {
    "idle": dict(src=("zd_daiji", 0, 61, 2, "none"), fps=15, loop=True,
                 note="REAL decoded motion: zd_daiji (the idle), every 2nd of its 62 frames."),
    "attack": dict(src=("zd_jn_01_xl", 0, 52, 2, "xz"), fps=15, loop=False,
                   note="APPROXIMATION: no authored single-attack clip exists. zd_jn_01_xl is the "
                        "compact ground-level staff-skill variant (the full zd_jn_01 goes airborne "
                        "to y=3.4 m and dashes 6 m, which cannot stay in a combat slot). It reads "
                        "as a lunging staff strike."),
    "cast": dict(src=("zd_jn_02_xl", 0, 51, 2, "xz"), fps=15, loop=False,
                 note="APPROXIMATION: zd_jn_02_xl, the other compact ground-level staff skill; it "
                      "reads as an overhead circular cast."),
    "powerup": dict(alias="cast"),
    "hurt": dict(synth="recoil", fps=15, loop=False,
                 note="SYNTHESIZED, NOT DECODED: the source bundle contains no hurt clip. A 4-frame "
                      "backward-lean recoil is built from the idle stance."),
    "die": dict(synth="collapse", fps=15, loop=False,
                note="SYNTHESIZED, NOT DECODED: the source bundle contains no death clip. The idle "
                     "stance is rotated about the feet and slid to the ground over 16 frames; the "
                     "last frame is held."),
    "revive": dict(synth="revive", fps=15, loop=False,
                   note="SYNTHESIZED, NOT DECODED: the synthesized death, frame-reversed."),
    "relaxed": dict(alias="idle"),
}

# No source-frame sub-ranges are needed: both skill clips used are already compact. Kept so a
# different take can be dialled in from the command line without editing code.
RANGES = {}


# --------------------------------------------------------------------------- rig helpers
_cache = {}


def get_rig(toon=None):
    if "rig" not in _cache:
        clips, _h2t, tid_to_chain = ma.load_clips(BUNDLE)
        rig = mrv.Rig(BUNDLE, toon=toon)
        rig.tid_to_chain = tid_to_chain
        _cache["clips"] = clips
        _cache["rig"] = rig
    return _cache["clips"], _cache["rig"]


def clip_frames(clip, rng, step):
    lo, hi = (0, clip.frame_count - 1) if rng is None else rng
    lo, hi = max(0, lo), min(clip.frame_count - 1, hi)
    return list(range(lo, hi + 1, step))


def clip_bbox(rig, clip, frames, follow, char_only=False):
    """(lo, hi, offsets) in world space after the follow offset.

    By default this includes EVERY rasterised part, weapons too, because posed_tris() renders all of
    mr.PARTS. The previous version framed only the body-and-cloth parts, and the two staffs
    (mx_3015004_01_weapon / _weapon01) were therefore allowed to leave the canvas: measured on the
    shipped 188x244 frames, `cast` touches the right border on 25 px and the top on 36 px, and
    `attack` on 11 px both. A flipbook cell CLIPS -- it does not zoom out -- so that was a real,
    visible defect (the staff head is sliced off during every cast).
    """
    offs = rig.root_offsets(clip, frames, follow)
    lo = np.array([1e9] * 3)
    hi = np.array([-1e9] * 3)
    for f in frames:
        rig.scene.reset_pose(clip.pose(f))
        off = offs[f] if offs else 0.0
        for g in rig.geoms:
            if char_only and g["name"].endswith(("weapon", "weapon01")):
                continue
            p = mr.build_part(rig.scene, g["name"], verbose=False, geom=g)
            V = p["P"] - off
            lo = np.minimum(lo, V.min(0))
            hi = np.maximum(hi, V.max(0))
    return lo, hi, offs


def fixed_camera(lo, hi, px_w, px_h, fov, margin):
    """ONE perspective camera containing the world box [lo,hi]; every clip renders through it.

    Deliberately not per-clip: sharing the MVP is what makes the frames pixel-registered.
    """
    center = (lo + hi) * 0.5
    size = np.maximum(hi - lo, 1e-6)
    aspect = float(px_w) / float(px_h)
    half_h = size[1] * 0.5 * margin
    half_w = max(size[0] * 0.5 * margin, half_h * aspect)
    half_h = max(half_h, half_w / aspect)
    t = math.tan(math.radians(fov) * 0.5)
    dist = half_h / t + size[2] * 0.5
    eye = center + FWD * dist
    near = max(0.05, dist * 0.02)
    far = dist + size[2] * 3 + 10.0
    MVP = mr.perspective(fov, aspect, near, far) @ mr.look_at(eye, center, np.array([0.0, 1.0, 0.0]))
    return MVP, center, eye, near, far, half_h


def project(MVP, pts, px_w, px_h):
    """world (N,3) -> canvas pixels (N,2), origin top-left, matching the rasteriser's viewport."""
    p = np.concatenate([np.asarray(pts, float), np.ones((len(pts), 1))], 1) @ MVP.T
    ndc = p[:, :2] / p[:, 3:4]
    return np.stack([(ndc[:, 0] + 1.0) * 0.5 * px_w, (1.0 - ndc[:, 1]) * 0.5 * px_h], 1)


def render_frames(rig, clip, frames, offs, MVP, px_w, px_h, ssaa, near):
    extras = getattr(rig, "extras", None)
    shade = None
    if getattr(rig, "use_toon", False):
        shade = {"mode": "toon", "fwd": FWD.tolist()}
    out = []
    for f in frames:
        rig.scene.reset_pose(clip.pose(f))
        gp, gn, gu, gt = rig.posed_tris()
        if offs:
            gp = gp - offs[f]
        col, alp = mr.rasterize_fast(gp, gn, gu, gt, rig.tex_arrays, rig.tex_alphas,
                                     MVP, px_w * ssaa, px_h * ssaa, near, verbose=False,
                                     extras=extras, shade=shade)
        col, alp = mrv.downsample(col, alp, ssaa, px_w, px_h)
        out.append(mrv.to_rgba(col, alp))
    return out


def alpha_bbox(frames, thr=0.35):
    """The real drawn silhouette: union of alpha>thr over the given RGBA frames, in canvas px.

    Measured from the RENDERED pixels (not from the projected 3D corners) so it automatically
    includes whatever the outline pass added.
    """
    x0 = y0 = 1 << 30
    x1 = y1 = -1
    for a in frames:
        m = np.asarray(a)[..., 3] > int(round(thr * 255))
        if not m.any():
            continue
        ys, xs = np.nonzero(m)
        x0, x1 = min(x0, int(xs.min())), max(x1, int(xs.max()))
        y0, y1 = min(y0, int(ys.min())), max(y1, int(ys.max()))
    if x1 < 0:
        return None
    return (x0, y0, x1, y1)


# --------------------------------------------------------------------------- synthesis
def _rot_bbox(bbox, ang_deg, pivot):
    """Bounding box of a rectangle after rotating it `ang_deg` about `pivot` (PIL's CCW sense)."""
    x0, y0, x1, y1 = bbox
    corners = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64)
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    dx = corners[:, 0] - pivot[0]
    dy = corners[:, 1] - pivot[1]
    rx = pivot[0] + ca * dx - sa * dy
    ry = pivot[1] + sa * dx + ca * dy
    return float(rx.min()), float(ry.min()), float(rx.max()), float(ry.max())


def synth_recoil(idle0, n=4, lean_deg=5.0):
    """A short backward-lean recoil built from the idle stance.

    SYNTHESIZED, not decoded: the bundle has no hurt clip. `idle0` is one idle frame (H,W,4 uint8).

    The pivot sits at 97 % of the height so the FEET stay planted; the previous version also pushed
    the whole image down by 2 % of the height, which sank her ~5 px through the combat floor line
    (the floor is sprite-local y=0, i.e. the lowest row the IDLE reaches).
    """
    h, w = idle0.shape[:2]
    src = Image.fromarray(idle0, "RGBA")
    pivot = (w * 0.5, h * 0.97)
    out = []
    for i in range(n):
        k = (i + 1) / float(n)
        ang = math.sin(math.pi * k) * lean_deg
        out.append(np.asarray(src.rotate(ang, resample=Image.BICUBIC, center=pivot)))
    return out


def synth_collapse(idle0, n=16, max_deg=44.0, slide=0.16, sink=0.34, margin=6):
    """Fall over: a crumple to the ground that stays INSIDE the frame.

    SYNTHESIZED, not decoded: the bundle has no death clip.

    The previous version rotated up to 80 deg about a pivot near the feet and slid the body 20 % of
    the width sideways. A 205 px-tall figure lying that flat needs ~200 px of canvas WIDTH, and the
    canvas is only 188 px wide, so most of the death animation was clipped off the right edge -- and
    because the outline pass runs after the crop, it then painted a hard ring along the canvas
    border. This version rotates about the waist (55 % of the height) instead, backs the angle off
    until the rotated figure fits, and sinks the body toward the floor.
    """
    h, w = idle0.shape[:2]
    src = Image.fromarray(idle0, "RGBA")
    a0 = np.asarray(idle0)
    m = a0[..., 3] > 8
    ys, xs = np.nonzero(m)
    bx0, bx1, by0, by1 = float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())
    pivot = (w * 0.5, h * 0.55)
    lim = (float(margin), float(margin), float(w - 1 - margin), float(h - 1 - margin))
    out = []
    for i in range(n):
        k = i / float(n - 1)
        e = k * k * (3 - 2 * k)
        if e == 0.0:
            # exact, not a 0-degree BICUBIC round trip: `revive` is this reversed, so the frame it
            # ends on must be the very same image as idle frame 0 (otherwise the atlas keeps a
            # near-duplicate and the character's resting pose differs by a hair from the idle's).
            out.append(idle0.copy())
            continue
        ang = max_deg * e
        while ang > 0.5:
            b = _rot_bbox((bx0, by0, bx1, by1), ang, pivot)
            if b[2] - b[0] <= lim[2] - lim[0] and b[3] - b[1] <= lim[3] - lim[1]:
                break
            ang -= 0.75
        im = src.rotate(ang, resample=Image.BICUBIC, center=pivot)
        b = _rot_bbox((bx0, by0, bx1, by1), ang, pivot)
        # PIL rotates counter-clockwise, i.e. the head travels to screen-left, so the slide follows.
        dx = -slide * w * e
        dy = sink * h * e
        dx = min(dx, lim[2] - b[2]); dx = max(dx, lim[0] - b[0])
        dy = min(dy, lim[3] - b[3]); dy = max(dy, lim[1] - b[1])
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(im, (int(round(dx)), int(round(dy))), im)
        out.append(np.asarray(canvas))
    return out


# --------------------------------------------------------------------------- atlas packing
def pack_atlas(px_w, px_h, n, page_w, pad=1):
    """Uniform grid atlas: every frame is px_w x px_h, so the rects are trivially predictable.

    Returns (page_w, page_h, placements[(x, y, w, h)]) for one page. A grid wastes at most one
    partial row, and one non-square page wastes far less than forcing 2048x2048 pages.
    """
    cols = max(1, (page_w - pad) // (px_w + pad))
    rows = int(math.ceil(n / float(cols)))
    page_h = rows * (px_h + pad) + pad
    places = []
    for i in range(n):
        c, r = i % cols, i // cols
        places.append((pad + c * (px_w + pad), pad + r * (px_h + pad), px_w, px_h))
    return page_w, page_h, places


# --------------------------------------------------------------------------- godot text
def fmtv(v):
    s = ("%.4f" % float(v)).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def scene_text(places, order, args, geo, trig):
    """The drop-in replacement scene.

    Node layout is the vanilla one. NCreatureVisuals._Ready hard-requires %Visuals (Node2D),
    %Bounds (Control), %IntentPos and %CenterPos (Marker2D) and optionally takes %FormVfx,
    %PhobiaModeVisuals, %OrbPos, %TalkPos -- NCreatureVisuals.cs:253-260.

    WHY `Visuals` IS NOT A SpineSprite, AND WHY THAT IS FINE
      * IsSpineNode only matches GetClass() == "SpineSprite" (NCreatureVisuals.cs:206-216), so
        SpineBody stays null and NCreature.HasSpineAnimation is false.
      * NCreature._Ready only builds the CreatureAnimator inside `if (HasSpineAnimation)`
        (NCreature.cs:507-525), so _spineAnimator is null and NCreature.SetAnimationTrigger is a
        no-op (NCreature.cs:872-875, `_spineAnimator?.SetTrigger(trigger)`).
      * BaseLib's prefix on that very method catches exactly this case and forwards the trigger to
        BaseLib.Utils.CustomAnimation (BaseLib.Patches.UI/CustomAnimationPatch.cs:142-170).
    So the game tolerates a non-Spine Visuals by construction, not by luck.

    WHY AN AnimationPlayer AND NOT AN AnimatedSprite2D
      CustomAnimation.SearchRecursive prefers an AnimationPlayer over an AnimatedSprite2D
      (CustomAnimation.cs:22-55, 96-116). Driving a Sprite2D:texture track from the AnimationPlayer
      is deterministic; the AnimatedSprite2D route is not: measured in Godot 4.5.1, a non-looping
      AnimatedSprite2D animation ends with playing == false and assigning `animation` again does NOT
      restart playback (and `playing` is not even assignable), so the character would freeze after
      its first attack. See .tools/out/spine/godotcheck/check.log.

    The AnimationPlayer is the FIRST child of Visuals, and Visuals is child 0 of NCreature
    (NCreature.cs:491-492), so the recursive search reaches it before any AnimationPlayer that a
    health bar, intent or VFX scene may contribute deeper in the tree.

    Class spellings are ENGINE spellings; an unknown class is silently replaced by a placeholder
    Node, which is why .tools/out/spine/godotcheck loads this exact scene in real Godot.
    """
    L = ['[gd_scene load_steps=4 format=3]', '']
    L += [
        '; In-combat creature visual for Yetannia -- ANIMATED (per-frame flipbook).',
        '; Generated by .tools/build-creature-anim.py -- do not hand-edit; retune the script instead.',
        '; Contract: .tools/out/spine/CONTRACT.md   Animation map: .tools/out/spine/ANIM_MAP.md',
        '',
        '[ext_resource type="Texture2D" path="res://Yetannia/images/creature/yetannia_atlas_0.png"'
        ' id="tex0"]',
        '',
    ]
    for idx, (x, y, w, h) in enumerate(places):
        L.append('[sub_resource type="AtlasTexture" id="AtlasTexture_%d"]' % idx)
        L.append('atlas = ExtResource("tex0")')
        L.append('region = Rect2(%d, %d, %d, %d)' % (x, y, w, h))
        L.append('')
    anim_ids = []
    for name, spec in order:
        aid = "Anim_%s" % name
        anim_ids.append((name, aid))
        times = ",".join(fmtv(i / spec["speed"]) for i in range(len(spec["frames"])))
        vals = ",".join('SubResource("AtlasTexture_%d")' % i for i, _d in spec["frames"])
        trans = ",".join("1" for _ in spec["frames"])
        L.append('[sub_resource type="Animation" id="%s"]' % aid)
        L.append('resource_name = "%s"' % esc(name))
        L.append('length = %s' % fmtv(len(spec["frames"]) / spec["speed"]))
        if spec["loop"]:
            L.append('loop_mode = 1')
        L.append('tracks/0/type = "value"')
        L.append('tracks/0/imported = false')
        L.append('tracks/0/enabled = true')
        L.append('tracks/0/path = NodePath("Sprite2D:texture")')
        L.append('tracks/0/interp = 1')
        L.append('tracks/0/loop_wrap = true')
        L.append('tracks/0/keys = {')
        L.append('"times": PackedFloat32Array(%s),' % times)
        L.append('"transitions": PackedFloat32Array(%s),' % trans)
        L.append('"update": 1,')
        L.append('"values": [%s]' % vals)
        L.append('}')
        L.append('')
    L.append('[sub_resource type="AnimationLibrary" id="AnimationLibrary_yetannia"]')
    L.append('_data = {')
    for name, aid in anim_ids:
        L.append('&"%s": SubResource("%s"),' % (esc(name), aid))
    L.append('}')
    L.append('')
    L.append('[node name="YetanniaVisuals" type="Node2D"]')
    L.append('')
    L.append('[node name="FormVfx" type="Control" parent="."]')
    L.append('unique_name_in_owner = true')
    L.append('layout_mode = 3')
    L.append('anchors_preset = 0')
    L.append('mouse_filter = 2')
    L.append('')
    L.append('[node name="Visuals" type="Node2D" parent="."]')
    L.append('unique_name_in_owner = true')
    L.append('')
    L.append('; First child on purpose -- see the header comment.')
    L.append('[node name="AnimationPlayer" type="AnimationPlayer" parent="Visuals"]')
    L.append('libraries = {')
    L.append('"": SubResource("AnimationLibrary_yetannia")')
    L.append('}')
    L.append('autoplay = "idle"')
    L.append('playback_default_blend_time = 0.0')
    L.append('')
    L.append('[node name="Sprite2D" type="Sprite2D" parent="Visuals"]')
    L.append('texture = SubResource("AtlasTexture_%d")' % order[0][1]["frames"][0][0])
    L.append('position = Vector2(%s, %s)' % (fmtv(geo["sprite"][0]), fmtv(geo["sprite"][1])))
    L.append('scale = Vector2(%s, %s)' % (fmtv(args.node_scale), fmtv(args.node_scale)))
    L.append('centered = false')
    L.append('')
    L.append('[node name="Bounds" type="Control" parent="."]')
    L.append('unique_name_in_owner = true')
    L.append('layout_mode = 3')
    L.append('anchors_preset = 0')
    L.append('offset_left = %s' % fmtv(geo["bounds"][0]))
    L.append('offset_top = %s' % fmtv(geo["bounds"][1]))
    L.append('offset_right = %s' % fmtv(geo["bounds"][2]))
    L.append('offset_bottom = %s' % fmtv(geo["bounds"][3]))
    L.append('mouse_filter = 2')
    L.append('')
    L.append('[node name="CenterPos" type="Marker2D" parent="."]')
    L.append('unique_name_in_owner = true')
    L.append('position = Vector2(%s, %s)' % (fmtv(geo["center"][0]), fmtv(geo["center"][1])))
    L.append('')
    L.append('[node name="IntentPos" type="Marker2D" parent="."]')
    L.append('unique_name_in_owner = true')
    L.append('position = Vector2(%s, %s)' % (fmtv(geo["intent"][0]), fmtv(geo["intent"][1])))
    L.append('')
    return "\n".join(L)


# --------------------------------------------------------------------------- atlas .import
# Godot's importer ADOPTS whatever params an existing .import already carries, so shipping this file
# next to the PNG is the only way to keep the atlas off the lossless default. Every value here was
# measured by importing this project's own atlas through Godot 4.5.1 -- see
# .tools/out/visual/vram-import.ps1 (which prints the Image::Format Godot picked) and
# .tools/out/visual/compress_compare.py (which scores the artefacts at display size).
#
#   compress/mode=0                     -> Image::FORMAT_RGBA8      4 B/px
#   compress/mode=2 compress/high_quality=false -> FORMAT_DXT5 (BC3) 1 B/px
#   compress/mode=2 compress/high_quality=true  -> FORMAT_BPTC_RGBA (BC7) 1 B/px  <- same VRAM
#   mipmaps/generate=true               -> +33 % VRAM for a chain that 1:1 drawing never samples
#
# process/fix_alpha_border=true is the Godot default and is KEPT on purpose: it floods the RGB of
# fully transparent texels from their opaque neighbours, which stops BC7 from bleeding black into the
# soft alpha edges (measured: 5.8 % vs 13.5 % of texels off by more than 8/255).
# detect_3d/compress_to=0 disables the importer's "this texture touched a 3D material, switch me to
# Lossy" heuristic, which would otherwise silently destroy the atlas in a future re-import.
IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="%(src)s"

[params]

compress/mode=%(mode)d
compress/high_quality=%(hq)s
compress/lossy_quality=0.7
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=%(mip)s
mipmaps/limit=-1
roughness/mode=0
process/fix_alpha_border=true
process/premult_alpha=false
process/size_limit=0
detect_3d/compress_to=0
"""


# --------------------------------------------------------------------------- character icon
# WHY THE ICON IS RENDERED AND NOT CROPPED FROM THE EXISTING ART
#   CustomIconTexturePath points at images/charui/character_icon_yetannia.png, which used to be a
#   340x340 RGB image: a square crop of an illustration, background and all, with NO alpha channel.
#   The base game's own character icons are 88x88 CUT-OUTS (measured: .tools/icon-outline.py
#   selftest reproduces all seven vanilla outline layers from them at IoU 0.95-0.98, and their bptc
#   .ctex payload is exactly 88*88 + 52 bytes). The vanilla "outline" layer is the icon's own alpha
#   silhouette, filled and dilated -- so with an opaque square icon the outline layer is invisible,
#   which is exactly the symptom reported for this mod.
#   Matting the 340x340 illustration is not viable (61 226 distinct colours, no flat background,
#   semi-transparent hair), so the icon is rendered from the same decoded 3D model as the flipbook,
#   which outputs clean RGBA on a transparent background by construction.
def render_icon(rig, clips, args):
    """Render the head-and-shoulders icon portrait and emit <outdir>/icon/*.png at --icon-size."""
    cands = []
    for spec in args.icon_candidates.split(","):
        spec = spec.strip()
        if not spec:
            continue
        anim, fr = spec.split(":")
        src = PLAN[anim]["src"]
        cands.append((anim, int(fr), clips[src[0]]))
    if not cands:
        return

    # world box of the FACE over the chosen poses -- that is what a portrait is framed on
    flo = np.array([1e9] * 3)
    fhi = np.array([-1e9] * 3)
    for _a, fr, clip in cands:
        rig.scene.reset_pose(clip.pose(fr))
        for g in rig.geoms:
            if not g["name"].endswith("face"):
                continue
            p = mr.build_part(rig.scene, g["name"], verbose=False, geom=g)
            flo = np.minimum(flo, p["P"].min(0))
            fhi = np.maximum(fhi, p["P"].max(0))
    fs = fhi - flo
    half = float(max(fs[0], fs[1])) * args.icon_zoom * 0.5
    ctr = (flo + fhi) * 0.5 + np.array([0.0, -args.icon_drop * float(fs[1]), 0.0])
    ilo, ihi = ctr - half, ctr + half
    print("[icon] face world box x=[%.3f,%.3f] y=[%.3f,%.3f] -> portrait view "
          "x=[%.3f,%.3f] y=[%.3f,%.3f] (%.3f m square)"
          % (flo[0], fhi[0], flo[1], fhi[1], ilo[0], ihi[0], ilo[1], ihi[1], 2 * half))

    N = args.icon_size * 6            # render big, downscale with LANCZOS -> clean 88 px edges
    MVP, _c, _e, near, _f, _hh = fixed_camera(ilo, ihi, N, N, args.fov, 1.02)
    shots = {}
    for anim, fr, clip in cands:
        arr = render_frames(rig, clip, [fr], None, MVP, N, N, args.ssaa, near)[0]
        shots[(anim, fr)] = arr
        print("[icon] rendered candidate %s:%d  (%dx%d)" % (anim, fr, N, N))

    picks = {}
    for key, arr in shots.items():
        bb = alpha_bbox([arr])
        if bb is None:
            continue
        x0, y0, x1, y1 = bb
        pad = int(round(args.icon_margin * args.icon_size))
        target = args.icon_size - 2 * pad
        cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        # square crop centred on the silhouette, then uniform scale so the silhouette fits target
        half_src = max(x1 - x0, y1 - y0) * 0.5 / (1.0 - 2.0 * args.icon_margin)
        box = (int(round(cx - half_src)), int(round(cy - half_src)),
               int(round(cx + half_src)), int(round(cy + half_src)))
        im = Image.fromarray(arr, "RGBA").crop(box).resize((args.icon_size, args.icon_size),
                                                           Image.LANCZOS)
        picks[key] = np.asarray(im.convert("RGBA"), dtype=np.uint8)
        _ = target

    outdir = os.path.join(args.outdir, "icon")
    os.makedirs(outdir, exist_ok=True)
    # candidate sheet at 4x so a human can pick
    k = 4
    tiles = []
    for (anim, fr), arr in sorted(picks.items()):
        im = Image.fromarray(arr, "RGBA").resize((args.icon_size * k, args.icon_size * k),
                                                 Image.NEAREST)
        bg = Image.new("RGBA", im.size, (22, 23, 28, 255))
        tiles.append(("%s:%d" % (anim, fr), Image.alpha_composite(bg, im).convert("RGB")))
    W = sum(t.width + 8 for _l, t in tiles) + 8
    sheet = Image.new("RGB", (W, args.icon_size * k + 22), (14, 15, 19))
    dr = ImageDraw.Draw(sheet)
    xx = 8
    for lbl, t in tiles:
        dr.text((xx + 2, 4), "%s  %dx%d" % (lbl, args.icon_size, args.icon_size),
                fill=(235, 235, 240))
        sheet.paste(t, (xx, 20))
        xx += t.width + 8
    sp = os.path.join(args.outdir, "icon_candidates.png")
    sheet.save(sp)
    print("[icon] %d candidates -> %s (each shown at %dx)" % (len(tiles), sp, k))

    anim, fr = args.icon_pick.split(":")
    pick = picks.get((anim, int(fr)))
    if pick is None:
        print("[icon] !! pick %s not among the candidates %s" % (args.icon_pick, sorted(picks)))
        return
    p = os.path.join(outdir, "character_icon_yetannia.png")
    Image.fromarray(pick, "RGBA").save(p)
    a = pick[..., 3]
    ys, xs = np.nonzero(a > 8)
    print("[icon] wrote %s  %dx%d  alpha>8 on %.1f%%  bbox x=[%d,%d] y=[%d,%d]"
          % (p, args.icon_size, args.icon_size, 100.0 * (a > 8).mean(),
             xs.min(), xs.max(), ys.min(), ys.max()))
    print("[icon] vanilla for comparison: 88x88, alpha>8 on 33.8-53.4%%, "
          "bbox x=[3,80] y=[3,82] (all five playable characters)")


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("probe", "probe-all", "build", "icon"))
    ap.add_argument("--height", type=int, default=384, help="shared RENDER canvas height in px")
    ap.add_argument("--width", type=int, default=380, help="shared RENDER canvas width in px")
    ap.add_argument("--fit-fully", default="idle,cast",
                    help="comma list of clips whose WEAPONS must stay inside the cell. Every other "
                         "clip only has its body (and cloth) guaranteed; the staff is allowed to "
                         "leave the cell there. The staff is 2.4 m long on a 1.8 m character and "
                         "the attack clip sweeps it to y=3.02 m / x=-1.10..1.77 m, so framing ALL "
                         "of it everywhere costs ~2.5x the atlas area for a pose that lasts a few "
                         "frames. 'all' frames everything (no clipping anywhere).")
    ap.add_argument("--fov", type=float, default=30.0)
    ap.add_argument("--margin", type=float, default=1.06)
    ap.add_argument("--ssaa", type=int, default=2)
    ap.add_argument("--step", type=int, default=None, help="override every clip's frame step")
    ap.add_argument("--attack-range", default=None, help="a,b source frames")
    ap.add_argument("--cast-range", default=None)
    ap.add_argument("--node-scale", type=float, default=None,
                    help="override the sprite scale instead of solving it from --target-height")
    ap.add_argument("--target-height", type=float, default=277.0,
                    help="desired IDLE SILHOUETTE height in game px (vanilla Ironclad's Bounds "
                         "height is 278 and Silent's is 244, Defect's 260); node-scale is solved "
                         "for exactly this")
    ap.add_argument("--page-w", type=int, default=2064)
    ap.add_argument("--outdir", default=OUTSTAGE,
                    help="where frames/atlas/scene/manifest/.import are staged")
    ap.add_argument("--reuse", action="store_true",
                    help="reuse <outdir>/frames/<anim>/*.png instead of re-rendering")
    # ---- stylised (toon) shading, see model-render.py's CHANNEL_SLOTS comment for the evidence
    ap.add_argument("--no-toon", dest="toon", action="store_false",
                    help="render with the OLD flat-lambert albedo-only shading (A/B comparison)")
    ap.add_argument("--cel-threshold", type=float, default=None,
                    help="override every material's own _DiffuseThreshold")
    ap.add_argument("--cel-smooth", type=float, default=0.055)
    ap.add_argument("--cel-space", choices=("half", "ndl"), default="half",
                    help="whether the material's _DiffuseThreshold is compared against "
                         "0.5+0.5*NdotL (half-lambert, the default: lights everything facing within "
                         "~50 deg of the light, which matches the real game's screenshots) or "
                         "against raw NdotL (much larger shadow side)")
    ap.add_argument("--rim", type=float, default=0.18, help="edge/rim light strength")
    ap.add_argument("--rim-color", default="0.62,0.82,1.0")
    ap.add_argument("--rim-power", type=float, default=3.2)
    ap.add_argument("--spec", type=float, default=0.30,
                    help="global scale on the material's _SpecularIntensity, gated by _MetalLightingInfo")
    ap.add_argument("--outline", type=int, default=2, help="baked silhouette outline width in px")
    ap.add_argument("--outline-color", default="0.055,0.075,0.16")
    ap.add_argument("--no-vram-compress", dest="vram_compress", action="store_false",
                    help="emit compress/mode=0 (lossless) in the atlas .import instead of mode=2")
    ap.add_argument("--vram-mipmaps", action="store_true",
                    help="enable mipmaps in the atlas .import (+33%% VRAM; not sampled at 1:1)")
    # ---- character ICON (res://Yetannia/images/charui/character_icon_yetannia.png)
    ap.add_argument("--icon-size", type=int, default=88,                    help="icon canvas edge in px. Vanilla is 88 for all five playable characters "
                         "(measured: .tools/icon-outline.py selftest reports 88x88 and the bptc "
                         ".ctex payload is exactly 88*88 + 52 bytes) and 72 for the deprecated "
                         "placeholder; the mod shipped 340x340.")
    ap.add_argument("--icon-candidates", default="idle:0,idle:10,idle:20,cast:10,attack:12",
                    help="anim:frame poses to render as icon candidates into icon_candidates.png")
    ap.add_argument("--icon-pick", default="idle:0", help="which candidate becomes the icon")
    ap.add_argument("--icon-margin", type=float, default=0.07,
                    help="fraction of the canvas left empty around the silhouette. Vanilla bboxes "
                         "are ~86%% of the canvas, i.e. ~7%% margin.")
    ap.add_argument("--icon-zoom", type=float, default=2.6,
                    help="portrait box size as a multiple of the FACE bounding box")
    ap.add_argument("--icon-drop", type=float, default=0.55,
                    help="how many face-heights below the face centre the portrait is centred, so "
                         "the shoulders are in frame")
    args = ap.parse_args()

    toon_opts = dict(enabled=bool(args.toon), spec=args.spec,
                     rim=args.rim, rim_power=args.rim_power,
                     rim_color=tuple(float(v) for v in args.rim_color.split(",")),
                     smoothness=args.cel_smooth,
                     half_lambert=(args.cel_space == "half"),
                     fwd=FWD.tolist())
    if args.cel_threshold is not None:
        toon_opts["threshold"] = args.cel_threshold
        toon_opts["threshold_force"] = True
    clips, rig = get_rig(toon=toon_opts)
    print("[shade] mode=%s  materials with a cel shadow map: %d/%d  (extras: %s)"
          % ("toon" if args.toon else "flat-lambert",
             sum(1 for e in getattr(rig, "extras", []) if e.get("shadow") is not None),
             len(getattr(rig, "extras", [])),
             ", ".join("%s=%s" % (e.get("material"), e["params"]["threshold"])
                       for e in getattr(rig, "extras", []))))

    if args.mode == "icon":
        render_icon(rig, clips, args)
        return

    if args.mode == "probe-all":
        # Survey EVERY clip in the bundle through one shared camera so the clips are comparable:
        # "which clip is a usable stand-in for attack / cast, and how much vertical room does it
        # need". follow=xz for all of them, because the in-combat sprite must not leave its slot.
        d = os.path.join(OUT, "probe_all")
        os.makedirs(d, exist_ok=True)
        boxes, steps = {}, {}
        for cname, clip in clips.items():
            fr = list(range(0, clip.frame_count, max(1, clip.frame_count // 16)))
            blo, bhi, offs = clip_bbox(rig, clip, fr, "xz")
            boxes[cname] = (blo, bhi, fr, offs)
            steps[cname] = (fr, offs)
            print("[all] %-22s %4d frames  x=[%7.3f,%7.3f] y=[%7.3f,%7.3f]  (sampled %d)"
                  % (cname, clip.frame_count, blo[0], bhi[0], blo[1], bhi[1], len(fr)))
        lo = np.min([b[0] for b in boxes.values()], 0)
        hi = np.max([b[1] for b in boxes.values()], 0)
        MVP, _c, _e, near, _f, _hh = fixed_camera(lo, hi, args.width, args.height, args.fov, 1.02)
        for cname, (blo, bhi, fr, offs) in boxes.items():
            arrs = render_frames(rig, clips[cname], fr, offs, MVP, args.width, args.height, 1, near)
            k = len(arrs)
            cols, pad, lab = 4, 4, 14
            rows = int(math.ceil(k / float(cols)))
            sheet = Image.new("RGB", (cols * (args.width + pad) + pad,
                                      rows * (args.height + pad + lab) + pad), (14, 15, 19))
            dr = ImageDraw.Draw(sheet)
            for i, a in enumerate(arrs):
                c, r = i % cols, i // cols
                x = pad + c * (args.width + pad)
                y = pad + r * (args.height + pad + lab)
                dr.text((x + 2, y + 2), "f%d" % fr[i], fill=(230, 230, 236))
                im = Image.fromarray(a, "RGBA")
                bg = Image.new("RGBA", im.size, (14, 15, 19, 255))
                sheet.paste(Image.alpha_composite(bg, im).convert("RGB"), (x, y + lab))
            sheet.save(os.path.join(d, "%s.png" % cname))
            print("[all] sheet -> %s" % os.path.join(d, "%s.png" % cname))
        return

    def rng_of(key):
        ov = {"attack": args.attack_range, "cast": args.cast_range}.get(key)
        if ov:
            a, b = (int(v) for v in ov.split(","))
            return (a, b)
        return RANGES.get(key)

    work, lo, hi = {}, np.array([1e9] * 3), np.array([-1e9] * 3)
    body_lo, body_hi = np.array([1e9] * 3), np.array([-1e9] * 3)
    fit_fully = set()
    if args.fit_fully.strip().lower() in ("all", "*"):
        fit_fully = set(PLAN.keys())
    else:
        for x in args.fit_fully.split(","):
            if x.strip():
                fit_fully.add(x.strip())
    allbox = {}
    for key, spec in PLAN.items():
        if "alias" in spec or "synth" in spec:
            continue
        cname, _a, _b, step, follow = spec["src"]
        clip = clips[cname]
        frames = clip_frames(clip, rng_of(key), args.step or step)
        blo, bhi, offs = clip_bbox(rig, clip, frames, follow)
        clo, chi, _o = clip_bbox(rig, clip, frames, follow, char_only=True)
        allbox[key] = (blo, bhi, clo, chi)
        body_lo = np.minimum(body_lo, clo)
        body_hi = np.maximum(body_hi, chi)
        work[key] = dict(clip=clip, frames=frames, offs=offs, lo=blo, hi=bhi, follow=follow,
                         clo=clo, chi=chi)
        whose = ("ALL parts, staff stays inside the cell" if key in fit_fully
                 else "body only, the staff is allowed to leave the cell")
        print("[bbox] %-8s %-12s follow=%-5s %3d frames  ALL x=[%7.3f,%7.3f] y=[%7.3f,%7.3f]"
              % (key, cname, follow, len(frames), blo[0], bhi[0], blo[1], bhi[1]))
        print("         %-8s %-12s   framing: %s" % ("", "", whose))
        if key in fit_fully:
            lo, hi = np.minimum(lo, blo), np.maximum(hi, bhi)
    # the union must also contain at least every clip's BODY, whatever the weapon policy
    lo, hi = np.minimum(lo, body_lo), np.maximum(hi, body_hi)
    print("[bbox] FRAME view (world)  x=[%.3f, %.3f] y=[%.3f, %.3f]  = %.3f x %.3f m"
          % (lo[0], hi[0], lo[1], hi[1], hi[0] - lo[0], hi[1] - lo[1]))
    for key, (blo, bhi, clo, chi) in allbox.items():
        over = ""
        if key not in fit_fully:
            dx = max(0.0, blo[0] - lo[0], hi[0] - bhi[0])
            dy = max(0.0, blo[1] - lo[1], hi[1] - bhi[1])
            if dx > 0.005 or dy > 0.005:
                over = ("  staff exceeds the cell by %.3f m horizontally / %.3f m vertically"
                        % (dx, dy))
        print("[bbox]   %-8s body %s  staff x=[%.3f,%.3f] y=[%.3f,%.3f]%s"
              % (key, "inside" if not over else "inside", blo[0], bhi[0], blo[1], bhi[1], over))

    print("[bbox] UNION char  x=[%.3f, %.3f]  y=[%.3f, %.3f]  height=%.3f m"
          % (lo[0], hi[0], lo[1], hi[1], hi[1] - lo[1]))

    MVP, center, eye, near, far, half_h = fixed_camera(lo, hi, args.width, args.height,
                                                       args.fov, args.margin)
    ppu = args.height / (2.0 * half_h)
    print("[camera] canvas %dx%d  px/unit=%.1f  char height on canvas=%.1f px"
          % (args.width, args.height, ppu, (hi[1] - lo[1]) * ppu))
    # Body-only idle footprint -- used for CenterPos.x / IntentPos.x, which vanilla places on the
    # figure's own centre-line (the WEAPON-inclusive box would push it 50 px to the right, because
    # the bow/staff sticks out).
    ilo, ihi = work["idle"]["clo"], work["idle"]["chi"]
    idle_corners = np.array([[x, y, z] for x in (ilo[0], ihi[0])
                             for y in (ilo[1], ihi[1]) for z in (ilo[2], ihi[2])])
    idle_px = project(MVP, idle_corners, args.width, args.height)
    # The sprite's local (0,0) is pinned to the MODEL ORIGIN at ground level -- world
    # (0, ground, centre-depth). That is where the game put the creature's slot, and it is the only
    # choice that keeps the feet on the ground line whatever the camera margins do.
    ground = float(lo[1])
    origin_px = project(MVP, [[0.0, ground, float(center[2])]], args.width, args.height)[0]
    print("[camera] idle footprint in canvas px: x=[%.1f,%.1f] y=[%.1f,%.1f]"
          % (idle_px[:, 0].min(), idle_px[:, 0].max(), idle_px[:, 1].min(), idle_px[:, 1].max()))
    print("[camera] model origin (world x=0, y=%.3f) is at canvas px (%.1f, %.1f)"
          % (ground, origin_px[0], origin_px[1]))

    if args.mode == "probe":
        d = os.path.join(OUT, "probe")
        os.makedirs(d, exist_ok=True)
        for key, w in work.items():
            t0 = time.time()
            arrs = render_frames(rig, w["clip"], w["frames"], w["offs"], MVP,
                                 args.width, args.height, 1, near)
            k = min(16, len(arrs))
            sel = np.linspace(0, len(arrs) - 1, k).round().astype(int)
            cols, pad, lab = 4, 6, 16
            rows = int(math.ceil(k / float(cols)))
            sheet = Image.new("RGB", (cols * (args.width + pad) + pad,
                                      rows * (args.height + pad + lab) + pad), (14, 15, 19))
            dr = ImageDraw.Draw(sheet)
            for i, si in enumerate(sel):
                c, r = i % cols, i // cols
                x = pad + c * (args.width + pad)
                y = pad + r * (args.height + pad + lab)
                dr.text((x + 2, y + 2), "clip frame %d" % w["frames"][si], fill=(230, 230, 236))
                im = Image.fromarray(arrs[si], "RGBA")
                bg = Image.new("RGBA", im.size, (14, 15, 19, 255))
                sheet.paste(Image.alpha_composite(bg, im).convert("RGB"), (x, y + lab))
            p = os.path.join(d, "%s_sheet.png" % key)
            sheet.save(p)
            print("[probe] %-8s %3d frames in %.1fs -> %s" % (key, len(arrs), time.time() - t0, p))
        return

    # ---- pass 2: render masters, synthesize the missing clips, atlas, emit Godot text
    masters = {}
    for key, w in work.items():
        kd = os.path.join(args.outdir, "frames", key)
        if args.reuse and os.path.isdir(kd):
            fs = sorted(f for f in os.listdir(kd) if f.endswith(".png"))
            masters[key] = [np.asarray(Image.open(os.path.join(kd, f)).convert("RGBA")) for f in fs]
            print("[reuse] %-8s %3d frames from %s" % (key, len(masters[key]), kd))
            continue
        t0 = time.time()
        masters[key] = render_frames(rig, w["clip"], w["frames"], w["offs"], MVP,
                                     args.width, args.height, args.ssaa, near)
        dt = time.time() - t0
        print("[render] %-8s %3d frames %6.1fs (%.2fs/frame)"
              % (key, len(masters[key]), dt, dt / max(1, len(masters[key]))))
    masters["hurt"] = synth_recoil(masters["idle"][0])
    masters["die"] = synth_collapse(masters["idle"][0])
    masters["revive"] = list(reversed(masters["die"]))
    for key, spec in PLAN.items():
        if "alias" in spec:
            masters[key] = masters[spec["alias"]]

    # ---- bake the silhouette outline BEFORE anything measures the silhouette or packs the atlas,
    # so the geometry below is derived from exactly the pixels that ship.
    # NewOutlineOn = 1.0 with an _OutlineColor and an _OutlineAmount on every character material, so
    # the authored look has an outline; a flipbook cannot run a second geometry pass, so the ring
    # is painted instead. It stays INSIDE each frame's canvas (the idle silhouette has ~19 px of
    # margin in a 244 px canvas), so the atlas padding does not have to grow.
    if args.outline > 0 and not args.reuse:
        ocol = tuple(float(v) for v in args.outline_color.split(","))
        for key in PLAN:
            masters[key] = [mr.apply_outline(a, ocol, args.outline) for a in masters[key]]
        print("[outline] baked a %d px outline, colour rgb%s on every frame" % (args.outline, ocol))

    # ---- TIGHT CROP. The shared perspective camera is fitted to the whole world union at the
    # centre depth plane and with a 1.06 margin, so most frames leave a wide transparent border: on
    # the shipped 188x244 frames the content union is only 162x187 px. Because every frame has the
    # same size, ONE global crop keeps the uniform grid atlas (and `centered = false` + a single
    # shifted position) while cutting the atlas area by roughly half. The frame the game draws is
    # unchanged: the sprite position absorbs the crop offset below.
    all_ab = alpha_bbox([a for k in PLAN for a in masters[k]])
    # `--reuse` reloads frames that were ALREADY cropped by a previous build, so cropping again would
    # trim another band of (empty) border each time. The pixels are unaffected, but the frame grid
    # would drift, so the crop only runs on freshly rendered frames.
    if args.reuse:
        all_ab = alpha_bbox([a for k in PLAN for a in masters[k]])
        crop = (0, 0, all_ab[2], all_ab[3])
        cw, ch = crop[2] - crop[0] + 1, crop[3] - crop[1] + 1
        frame_w, frame_h = cw, ch
        print("[crop] --reuse: frames are already cropped, keeping %dx%d" % (cw, ch))
    else:
        all_ab = alpha_bbox([a for k in PLAN for a in masters[k]])
        crop = (max(0, all_ab[0] - 1), max(0, all_ab[1] - 1),
                min(args.width - 1, all_ab[2] + 1), min(args.height - 1, all_ab[3] + 1))
        cw, ch = crop[2] - crop[0] + 1, crop[3] - crop[1] + 1
        frame_w, frame_h = cw, ch      # the preview sheet below reuses `cw` for its thumbnails
        if (cw, ch) != (args.width, args.height):
            for key in list(masters):
                masters[key] = [a[crop[1]:crop[3] + 1, crop[0]:crop[2] + 1] for a in masters[key]]
            origin_px = (origin_px[0] - crop[0], origin_px[1] - crop[1])
            print("[crop] render canvas %dx%d -> shipped frame %dx%d (crop offset %d,%d) "
                  "= %.0f%% of the area" % (args.width, args.height, cw, ch, crop[0], crop[1],
                                            100.0 * cw * ch / float(args.width * args.height)))
        else:
            print("[crop] render canvas %dx%d already tight" % (args.width, args.height))

    # ---- measure the silhouette from the RENDERED pixels (includes the outline), then solve the
    # sprite scale so the idle silhouette is exactly --target-height game px.
    all_ab = alpha_bbox([a for k in PLAN for a in masters[k]])
    idle_ab = alpha_bbox(masters["idle"])
    idle_w = idle_ab[2] - idle_ab[0] + 1
    idle_h = idle_ab[3] - idle_ab[1] + 1
    print("[silhouette] frame %dx%d   idle bbox px x=[%d,%d] y=[%d,%d]  -> %dx%d canvas px"
          % (cw, ch, idle_ab[0], idle_ab[2], idle_ab[1], idle_ab[3], idle_w, idle_h))
    print("[silhouette] all-animation union bbox px x=[%d,%d] y=[%d,%d] -> %dx%d"
          % (all_ab[0], all_ab[2], all_ab[1], all_ab[3],
             all_ab[2] - all_ab[0] + 1, all_ab[3] - all_ab[1] + 1))
    s = args.node_scale if args.node_scale else args.target_height / float(idle_h)
    print("[size] target idle silhouette %.0f px -> node scale %.4f (art is %s)"
          % (args.target_height, s,
             "1:1" if abs(s - 1.0) < 0.02 else ("UPSCALED %.2fx" % s if s > 1 else
                                                "DOWNSCALED %.2fx" % s)))

    uniq, arrs = {}, []
    for key in PLAN:
        for a in masters[key]:
            k = a.tobytes()
            if k not in uniq:
                uniq[k] = len(arrs)
                arrs.append(a)
    page_w, page_h, places = pack_atlas(cw, ch, len(arrs), args.page_w)
    used = len(arrs) * cw * ch
    print("[atlas] %d distinct frames of %dx%d -> one %dx%d page; %d/%d px used (%.0f%%)"
          % (len(arrs), cw, ch, page_w, page_h, used, page_w * page_h,
             100.0 * used / (page_w * page_h)))
    page = np.zeros((page_h, page_w, 4), np.uint8)
    for j, (x, y, w, h) in enumerate(places):
        page[y:y + h, x:x + w] = arrs[j]
    fd = os.path.join(args.outdir, "frames")
    os.makedirs(fd, exist_ok=True)
    fp = os.path.join(fd, "yetannia_atlas_0.png")
    Image.fromarray(page, "RGBA").save(fp, optimize=True)
    print("[atlas] wrote %s (%.1f KB)  VRAM lossless RGBA8 = %.2f MiB | VRAM BC7 = %.2f MiB"
          % (fp, os.path.getsize(fp) / 1024.0, page_w * page_h * 4 / 1048576.0,
             page_w * page_h / 1048576.0))
    # also emit the individual frames (debugging / re-packing without a re-render)
    for key in PLAN:
        kd = os.path.join(args.outdir, "frames", key)
        os.makedirs(kd, exist_ok=True)
        for i, a in enumerate(masters[key]):
            Image.fromarray(a, "RGBA").save(os.path.join(kd, "%s_%03d.png" % (key, i)))

    # Each one-shot animation gets the idle stance appended so that the frame it holds after the
    # AnimationPlayer stops is the resting pose. Nothing sends an "Idle" trigger after a player
    # attack -- the game's own CreatureAnimator queues idle_loop internally, and we bypass it -- so
    # without this tail the character would freeze in its last attack pose until the next trigger.
    # The tail reuses the idle's first AtlasTexture, so it costs no texture space.
    idle0 = uniq[masters["idle"][0].tobytes()]
    order = []
    for key, spec in PLAN.items():
        target = PLAN[spec["alias"]] if "alias" in spec else spec
        idxs = [uniq[a.tobytes()] for a in masters[key]]
        if key not in ("idle", "relaxed", "die", "revive") and idxs[-1] != idle0:
            idxs.append(idle0)
        order.append((key, dict(frames=[(i, 1.0 / float(target["fps"])) for i in idxs],
                                loop=bool(target["loop"]), speed=float(target["fps"]))))
    # BaseLib's candidate lists always contain the lowercase form of the trigger (and "hurt"/"die"
    # for Hit/Dead), so one lowercase animation per game animation name is enough -- and it keeps the
    # AnimationPlayer's library to 8 entries instead of 16 aliases of the same 8.
    trig = {}
    for key, _spec in order:
        trig[key] = key

    # How much of the character actually survives the canvas? A flipbook cell CLIPS, it does not
    # zoom out, so an animation that leaves the canvas loses body parts and (worse) the baked
    # outline gets painted along the canvas border. Report it per animation instead of hoping.
    print("[clip] per-animation alpha bbox inside the %dx%d shipped frame:" % (cw, ch))
    clipped = []
    for key in PLAN:
        bb = alpha_bbox(masters[key])
        if bb is None:
            print("  %-8s EMPTY" % key)
            continue
        touch = (bb[0] <= 0 or bb[1] <= 0 or bb[2] >= cw - 1 or bb[3] >= ch - 1)
        if touch:
            clipped.append(key)
        print("  %-8s x=[%3d,%3d] y=[%3d,%3d]  %3dx%3d  %s"
              % (key, bb[0], bb[2], bb[1], bb[3], bb[2] - bb[0] + 1, bb[3] - bb[1] + 1,
                 "CLIPPED at the frame border" if touch else "fits"))
    if clipped:
        print("  !! %s touch the frame border -- the character is cut off there" % clipped)

    # preview sheets: one row per animation, evenly sampled -- visual evidence for the report
    rows = [(key, [i for i, _d in spec["frames"]], spec) for key, spec in order]
    cols = max(len(i) for _k, i, _s in rows)
    cw, chh, lab = 96, 125, 14
    sheet = Image.new("RGB", (cols * cw + 8, len(rows) * (chh + lab) + 8), (14, 15, 19))
    dr = ImageDraw.Draw(sheet)
    for r, (key, idxs, spec) in enumerate(rows):
        dr.text((4, 8 + r * (chh + lab)),
                "%-8s %2d frames @%.0ffps loop=%-5s  animation name(s) the AnimationPlayer holds: %s"
                % (key, len(idxs), spec["speed"], spec["loop"],
                   ",".join(n for n in sorted(trig) if trig[n] == key)),
                fill=(225, 225, 232))
        step = max(1, len(idxs) // cols)
        for c, i in enumerate(idxs[::step][:cols]):
            im = Image.fromarray(arrs[i], "RGBA").resize((cw, chh), Image.LANCZOS)
            bg = Image.new("RGBA", im.size, (14, 15, 19, 255))
            sheet.paste(Image.alpha_composite(bg, im).convert("RGB"),
                        (4 + c * cw, 8 + r * (chh + lab) + lab))
    sheet.save(os.path.join(args.outdir, "preview_all.png"))
    print("[preview] wrote %s (%dx%d)" % (os.path.join(args.outdir, "preview_all.png"),
                                          sheet.width, sheet.height))

    # ------------------------------------------------------------------ geometry
    #
    # The sprite's local (0,0) is pinned to the GROUND CONTACT of the idle pose, so the character
    # stands exactly on the combat slot floor: local y=0 is the lowest row the idle ever reaches and
    # local x=0 is the model root's world x=0. Everything below is measured from the rendered alpha
    # of the frames that actually ship, at the solved node scale.
    #
    # WHAT `Bounds` IS FOR (do not "improve" it into a big box): NCreature.UpdateBounds derives the
    # whole mouse/focus hitbox from it (Hitbox.Size = Bounds.Size * Visuals.Scale / _tempScale), and
    # NCombatRoom.AdjustCreatureScaleForAspectRatio compares
    # GlobalPosition.X + Bounds.Size.X * 0.5 * SceneContainer.Scale.X against the viewport width and
    # shrinks BOTH combat containers when it overflows -- for players too. So Bounds is deliberately
    # tight around the standing figure and its width is kept at or below vanilla's 242.
    #
    # CenterPos is VfxSpawnPosition (NCreatureVisuals.cs:258). Vanilla puts it at 60.4 % of the
    # figure's height above the feet (Ironclad 168/278, Silent 146/244, Defect 179/260), NOT at the
    # 40 % that BaseLib's synthesise-it fallback formula uses; this now follows vanilla.
    # IntentPos is where the intent bubble points. Vanilla sits it 32-68 px above the head
    # (Ironclad 278+32, Silent 244+58, Defect 260+68); +33 reproduces Ironclad exactly.
    sprite = (-origin_px[0] * s, -idle_ab[3] * s)
    # Bounds width: the idle silhouette plus a 3 % margin. Deliberately tight -- see the comment
    # above; the extra 8 % the previous version used only widened the hitbox and the
    # aspect-ratio shrinker for no benefit.
    pad_x = 0.03 * idle_w * s
    bl = (idle_ab[0] - origin_px[0]) * s - pad_x
    br = (idle_ab[2] - origin_px[0]) * s + pad_x
    bt = (idle_ab[1] - idle_ab[3]) * s - 0.03 * idle_h * s
    # Feet exactly on the combat floor line, exactly like vanilla (Ironclad/Silent/Defect all omit
    # offset_bottom, i.e. their Bounds bottom IS y = 0).
    bb = 0.0
    h = bb - bt
    # CenterPos.x / IntentPos.x: vanilla puts both on the figure's own centre-line, NOT on the
    # centre of the bounds box -- Ironclad's bounds are symmetric so the two coincide there, but
    # ours are not (the staff/bow sticks out to the right). Measured on the BODY-only idle
    # silhouette, which is the same measurement that produced the previous build's x = 4.
    body_cx = ((idle_px[:, 0].min() + idle_px[:, 0].max()) * 0.5 - origin_px[0]) * s
    geo = dict(sprite=sprite, bounds=(bl, bt, br, bb),
               center=(body_cx, bb - 0.604 * h),
               intent=(body_cx, bb - h - 33.0))
    print("[geo] Bounds     = (%.1f, %.1f)-(%.1f, %.1f)  %.0f x %.0f px   "
          "(Ironclad 242x278, Silent 244x244, Defect 250x260)"
          % (bl, bt, br, bb, br - bl, bb - bt))
    print("[geo] Sprite2D.position = (%.1f, %.1f)   centred=false; floor row %d of %d frame rows"
          % (sprite[0], sprite[1], idle_ab[3], ch))
    print("[geo] CenterPos  = (%.1f, %.1f)  = %.1f%% of the height above the feet "
          "(vanilla Ironclad 60.4%%)" % (geo["center"][0], geo["center"][1],
                                         100.0 * (bb - geo["center"][1]) / h))
    print("[geo] IntentPos  = (%.1f, %.1f)  = %.0f px above the feet (vanilla Ironclad 310)"
          % (geo["intent"][0], geo["intent"][1], bb - geo["intent"][1]))
    print("[geo] MEASURED idle silhouette on screen = %.0f x %.0f px  (target %.0f)"
          % (idle_w * s, idle_h * s, args.target_height))

    scene = os.path.join(args.outdir, "creature_visuals", "yetannia.tscn")
    os.makedirs(os.path.dirname(scene), exist_ok=True)
    args.node_scale = s          # scene_text() writes the Sprite2D scale from this
    with open(scene, "w", encoding="utf-8", newline="\n") as f:
        f.write(scene_text(places, order, args, geo, trig))
    print("[scene] wrote %s (%d bytes)" % (scene, os.path.getsize(scene)))

    # The VRAM-compression choice has to travel WITH the PNG: export-pck.ps1's `--import` keeps
    # whatever params the .import already carries, so a checked-in .import is the only way to keep
    # the atlas off the lossless default. All figures below are MEASURED by importing this exact
    # atlas through Godot 4.5.1 (see .tools/out/visual/vram-import.ps1 + compress_compare.py):
    #   compress/mode=0                  -> Image::FORMAT_RGBA8, 4 B/px
    #   compress/mode=2 high_quality=false -> FORMAT_DXT5 (BC3), 1 B/px
    #   compress/mode=2 high_quality=true  -> FORMAT_BPTC_RGBA (BC7), 1 B/px   <- same VRAM, better
    #   mipmaps/generate=true            -> +33 % VRAM for a chain that is never sampled at 1:1
    # detect_3d/compress_to=0 is deliberate: left at its default of 1 the importer may silently
    # switch this texture to LOSSY (mode 1) if it ever gets seen by a 3D material.
    imp_path = fp + ".import"
    with open(imp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(IMPORT_TEMPLATE % dict(
            src="res://Yetannia/images/creature/yetannia_atlas_0.png",
            mode=2 if args.vram_compress else 0, hq="true" if args.vram_compress else "false",
            mip="true" if args.vram_mipmaps else "false"))
    print("[import] wrote %s (compress/mode=%d high_quality=%s mipmaps=%s)"
          % (imp_path, 2 if args.vram_compress else 0,
             "true" if args.vram_compress else "false", "true" if args.vram_mipmaps else "false"))

    man = dict(canvas=[args.width, args.height], frame=[frame_w, frame_h], crop=list(crop),
               node_scale=round(s, 5),
               node_scale_solved=bool(args.node_scale is None),
               target_height=args.target_height,
               atlas=[page_w, page_h], distinct_frames=len(arrs),
               atlas_pixels=page_w * page_h,
               atlas_bytes_png=os.path.getsize(fp),
               atlas_vram_bytes_rgba8=page_w * page_h * 4,
               atlas_vram_bytes_bc7=page_w * page_h,
               atlas_vram_mb_rgba8=round(page_w * page_h * 4 / 1048576.0, 2),
               atlas_vram_mb_bc7=round(page_w * page_h / 1048576.0, 2),
               silhouette=dict(idle_canvas_bbox=list(idle_ab),
                               idle_canvas_px=[idle_w, idle_h],
                               idle_screen_px=[round(idle_w * s, 1), round(idle_h * s, 1)],
                               all_anim_union_canvas_bbox=list(all_ab),
                               all_anim_union_canvas_px=[all_ab[2] - all_ab[0] + 1,
                                                         all_ab[3] - all_ab[1] + 1],
                               measured_from="alpha>0.35 of the rendered frames, outline included"),
               shading=dict(mode="toon" if args.toon else "flat-lambert",
                            cel_threshold=(args.cel_threshold if args.cel_threshold is not None
                                           else "per-material _DiffuseThreshold (0.65)"),
                            cel_smoothness=args.cel_smooth, rim=args.rim,
                            rim_color=args.rim_color, rim_power=args.rim_power,
                            spec=args.spec, outline_px=args.outline,
                            outline_color=args.outline_color,
                            shadow_map="per-material _ShadowTex (_anbu), RGB only",
                            ignored=["_LightTex (constant green placeholder)",
                                     "_BumpMap + NORMALMAP=0 in every material",
                                     "_Eye_LightingInfo (~99% black)"]),
               camera=dict(fov=args.fov, eye=eye.tolist(), center=center.tolist(),
                           px_per_unit=ppu, margin=args.margin,
                           world_char_bbox=[lo.tolist(), hi.tolist()]),
               geometry=dict(sprite=list(geo["sprite"]), bounds=list(geo["bounds"]),
                             center=list(geo["center"]), intent=list(geo["intent"]),
                             model_origin_canvas_px=list(origin_px),
                             vanilla_reference=dict(
                                 ironclad=dict(bounds=[242, 278], center=[4, -168],
                                               intent=[30, -310]),
                                 silent=dict(bounds=[244, 244], center=[0, -146],
                                             intent=[0, -302]),
                                 defect=dict(bounds=[250, 260], center=[4, -179],
                                             intent=[0, -328]))),
               animations=[dict(name=k, source=PLAN[k].get("src", PLAN[k].get("synth",
                                                                             PLAN[k].get("alias"))),
                                resolved_from=PLAN[k].get("alias"),
                                source_frames=len(masters[k]), animated_frames=len(v["frames"]),
                                idle_tail_appended=len(v["frames"]) > len(masters[k]),
                                fps=v["speed"], loop=v["loop"],
                                holds_end_pose=(not v["loop"] and k != "die"),
                                note=PLAN[PLAN[k].get("alias", k)]["note"],
                                trigger_names=[n for n, kk in trig.items() if kk == k])
                           for k, v in order],
               synthesized=[k for k in PLAN if "synth" in PLAN[k]],
               aliases={k: PLAN[k]["alias"] for k in PLAN if "alias" in PLAN[k]})
    with open(os.path.join(args.outdir, "anim_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1, ensure_ascii=False)
    print("[manifest] wrote %s" % os.path.join(args.outdir, "anim_manifest.json"))


if __name__ == "__main__":
    main()
