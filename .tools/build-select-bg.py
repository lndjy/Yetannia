# build-select-bg.py -- make the character-select backdrop and the locked icon.
#
# ROUND 42: the backdrop is now a REAL CROP OF THE LANDSCAPE MASTER, not a portrait with synthetic
# filler. History, because it is the whole point of this rewrite:
#   * round 39 built the backdrop from the 528x780 PORTRAIT (char_select_yetannia.png) by scaling it to
#     full height and inventing the remaining ~1747 px of width from a stretched+blurred copy. The
#     user's report was "enormously zoomed in, with two smeared bands" -- the filler is those bands.
#   * the actual artwork is a landscape painting that exists as a Wallpaper Engine video:
#       D:\SteamLibrary\steamapps\workshop\content\431960\3113725063\l2d 2_tvai.mp4
#       3043x1714, 60 fps, 320 frames, 5.333 s (ffprobe-measured), workshop item 3113725063.
#   * the user's instruction is to use that landscape directly, so this script takes ONE FRAME of it,
#     crops it 1:1 to the vanilla canvas' aspect and resamples once. NO filler of any kind: every pixel
#     of the output is a pixel of the master frame.
#
# THE CANVAS (measured, not assumed -- see .tools/out/selectbg/ for the audit):
#   * vanilla's bg scenes hold the art in a TextureRect of 2634x1236 local px
#     (offsets -437,-107 .. 2197,1129), expand_mode = 2, no stretch_mode (i.e. STRETCH_SCALE = fill),
#     inside a root Control of 2560x1200 (offsets -960,-521 .. 1600,679, pivot (1280,600)). This scene
#     already matches that exactly, which is why this script does not touch the .tscn.
#   * vanilla's own art is 2561x1201 -- a ~2.13:1 painting, NOT a portrait.
#   * the game does NOT show the whole canvas: the select screen lays out in a fixed 1920x1080 design
#     space (the display setting is aspect_ratio = sixteen_by_nine, so a non-16:9 window is pillarboxed
#     with black), and AnimatedBg scales 1.1, so the visible window is 1696x952 canvas px at 16:9 --
#     66.3 % of the width and 79.4 % of the height. The model is in out/selectbg/gamemodel.py and is
#     fitted against a live screenshot by out/selectbg/fit.py (predicted cols 569.6..2265.2 rows
#     150.8..1103.1; the fit says 569.7 / 1104.0 once the black bars are excluded from its mask).
#     This script therefore reports the framing BOTH as the canvas crop and as the visible window.
#
# DECISION -- DO NOT "OPTIMISE" THE FRAMING (user-chosen, 2026-10-12):
#   The backdrop deliberately keeps vanilla's own TextureRect (2634x1236 local) instead of shrinking it
#   to show the whole painting. Consequence: on a 16:9 display only 66.2 % of this 1.78:1 painting's
#   width is visible and Yetannia occupies ~81 % of the screen height. Shrinking the rect to ~1810x995
#   would show the entire painting with her at ~55 %, BUT it introduces black bars at aspects below
#   ~1.83 and at 4:3. The user was shown both options and explicitly chose "same framing as vanilla".
#   So the visible-window crop above is the INTENDED result, not a bug to fix.
#
# SOURCE CROP ARITHMETIC (all of it in the printed build.json):
#   master 3043x1714 (1.7754)  ->  canvas 2560x1200 (2.1333)
#   fit the WIDTH: scale = 2560/3043 = 0.8412751  ->  2560 x 1442.5, so 242 canvas rows (16.8 %) are
#   trimmed vertically. In source pixels that is 1426 of 1714 rows kept, i.e. 288 rows (16.8 %) dropped
#   from wherever --crop-y says. Fit the HEIGHT instead would need 430 px of width that does not exist,
#   which is exactly the filler this rewrite removes; that is why width wins.
#
# usage:
#   python .tools/build-select-bg.py                      # write the shipped assets + audit images
#   python .tools/build-select-bg.py --crop-y 150         # try another vertical window (audit only)
#   python .tools/build-select-bg.py --no-write           # audit images only, do not touch the pack
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "out", "selectbg"))
import gamemodel  # noqa: E402  (the measured model of the select screen's layout chain)

VIDEO = r"D:\SteamLibrary\steamapps\workshop\content\431960\3113725063\l2d 2_tvai.mp4"
FFMPEG = os.path.join(HERE, "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe")

OUT = os.path.join(HERE, "out", "selectbg")
# the asset the pack actually ships
DEST = os.path.join(HERE, "pckproject", "Yetannia", "images", "charui")
SRC_ICON = os.path.join(DEST, "character_icon_yetannia.png")

# ---- measured geometry -------------------------------------------------------------------------
MASTER = (3043, 1714)
CANVAS = (2560, 1200)
SCALE = CANVAS[0] / float(MASTER[0])            # 0.8412751, fit width
SX = 2634.0 / CANVAS[0]                         # canvas px -> local px inside the TextureRect
CROP_H = int(round(CANVAS[1] / SCALE))          # 1426 source rows for 1200 canvas rows
CROP_Y_MAX = MASTER[1] - CROP_H                 # 288
# the window the game actually shows, in canvas px, computed by the model rather than written down:
#   16:9 (any window at least 16:9, which includes the user's 1920x1080 and the harness' 1902x1033)
#   4:3  (the narrowest case the NCharacterSelectScreenBg scale rule allows: the window shrinks)
BG_SCENE = os.path.join(HERE, "pckproject", "Yetannia", "scenes", "char_select",
                        "char_select_bg_yetannia.tscn")


def visible_window(win_w, win_h):
    g = gamemodel.tex_window(BG_SCENE, win_w, win_h, CANVAS[0], CANVAS[1])
    return (round(g["x0"], 1), round(g["x1"], 1), round(g["y0"], 1), round(g["y1"], 1))


VIS_C16 = visible_window(1920, 1080)
VIS_43 = visible_window(1440, 1080)

# ---- the chosen frame --------------------------------------------------------------------------
# frame 120 of 320. Chosen by measurement + eye, not by taste alone: it is rank 1 of 320 on
# eyes-open (teal iris 48.4 % of the eye box, the widest of the loop -- frames 43-57 and 205/231 are
# mid-blink, see sheets/zoom_A.png) AND rank 1 on face sharpness (Laplacian variance 998 of 796..1021,
# so no motion softness). See .tools/out/selectbg/pick.py output in the round report.
FRAME = 120
# source row that becomes canvas row 0. Chosen from the audit overlay (sheets/crop_overlay_*): the
# visible 16:9 window ends up at source rows 309..1442, which keeps her hair ornament ~90 px clear of
# the top edge, her toes ~55 px clear of the bottom, and the cart platform and wheel arc below her.
# crop-y 186 cut her head; crop-y 0/90 cut the cart and put her too close to the bottom edge; 288 cut
# the top of her head. See the report's framing table.
CROP_Y = 130

LOCK_W, LOCK_H = 132, 195
LOCK_BG = (128, 128, 128)


def extract_master(frame=FRAME, dest=None):
    """Pull one frame straight out of the wallpaper video, losslessly, as PNG."""
    dest = dest or os.path.join(OUT, "master_f%03d.png" % frame)
    if os.path.exists(dest):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", VIDEO,
           "-vf", "select=eq(n\\,%d)" % frame, "-fps_mode", "passthrough", "-frames:v", "1",
           "-compression_level", "3", dest]
    subprocess.check_call(cmd)
    return dest


def build_backdrop(master, crop_y=CROP_Y):
    """The canvas: one crop of the master, one resample, zero synthesis."""
    mw, mh = master.size
    if crop_y < 0 or crop_y + CROP_H > mh:
        raise SystemExit("crop_y %d out of range 0..%d" % (crop_y, CROP_Y_MAX))
    box = (0, crop_y, mw, crop_y + CROP_H)
    return master.crop(box).resize(CANVAS, Image.LANCZOS), box


def locked_icon(icon_path, w=LOCK_W, h=LOCK_H, margin=4):
    """Black silhouette of the rendered cut-out icon, centred on the vanilla grey field."""
    ic = Image.open(icon_path).convert("RGBA")
    a = np.asarray(ic)[..., 3]
    ys, xs = np.nonzero(a > 8)
    bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    bw, bh = bb[2] - bb[0] + 1, bb[3] - bb[1] + 1
    s = min((w - 2 * margin) / float(bw), (h - 2 * margin) / float(bh))
    nw, nh = max(1, int(round(bw * s))), max(1, int(round(bh * s)))
    sub = ic.crop((bb[0], bb[1], bb[2] + 1, bb[3] + 1)).resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGB", (w, h), LOCK_BG)
    black = Image.new("RGB", (nw, nh), (0, 0, 0))
    out.paste(black, ((w - nw) // 2, (h - nh) // 2), sub.getchannel("A"))
    return out, dict(src_bbox=bb, scale=s, size=[w, h])


def audit_overlay(master, box, vis, vis_narrow, path, label):
    """The master frame with the crop rectangle and the visible windows drawn on it.

    This is the audit for item "show the crop rectangle overlaid on the frame": the outer rectangle is
    what this script keeps, the inner ones are what the game actually shows on screen -- green at 16:9
    (the user's case, and the widest the window ever gets) and blue at 4:3 (the narrowest, where
    NCharacterSelectScreenBg raises its own scale to 1.2683 and the window shrinks).
    """
    im = master.convert("RGB").copy()
    dr = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    dr.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 96, 40), width=6)
    for (cx0, cx1, cy0, cy1), col in (((vis[0], vis[1], vis[2], vis[3]), (120, 255, 130)),
                                      ((vis_narrow[0], vis_narrow[1], vis_narrow[2],
                                        vis_narrow[3]), (90, 200, 255))):
        # canvas -> source
        sx0, sx1 = cx0 / SCALE, cx1 / SCALE
        sy0, sy1 = cy0 / SCALE + y0, cy1 / SCALE + y0
        dr.rectangle([sx0, sy0, sx1, sy1], outline=col, width=4)
    for gy in range(0, master.height, 100):
        dr.line([(0, gy), (26, gy)], fill=(255, 235, 120), width=3)
        dr.text((30, gy + 2), str(gy), fill=(255, 235, 120))
    for gx in range(0, master.width, 250):
        dr.line([(gx, 0), (gx, 26)], fill=(255, 235, 120), width=3)
        dr.text((gx + 4, 28), str(gx), fill=(255, 235, 120))
    dr.text((30, 52), label, fill=(255, 255, 255))
    sk = 1.0 if master.width <= 1600 else 1600.0 / master.width
    im.resize((int(master.width * sk), int(master.height * sk)), Image.LANCZOS).save(path)
    return path


def preview_ingame(bg, path, vis):
    """What the player sees at 16:9: the visible window of the canvas, at screen resolution."""
    cx0, cx1, cy0, cy1 = vis
    win = bg.crop((int(round(cx0)), int(round(cy0)), int(round(cx1)), int(round(cy1))))
    win = win.resize((1920, 1080), Image.LANCZOS)
    win.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=int, default=FRAME)
    ap.add_argument("--crop-y", type=int, default=CROP_Y)
    ap.add_argument("--no-write", action="store_true", help="audit images only")
    ap.add_argument("--dest", default=DEST)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "sheets"), exist_ok=True)
    master = Image.open(extract_master(args.frame)).convert("RGB")
    print("[master] %s  %dx%d  (video frame %d)" % (VIDEO, master.width, master.height, args.frame))

    bg, box = build_backdrop(master, args.crop_y)
    print("[canvas] %dx%d  from master box %s   scale %.6f (fit width)" % (bg.width, bg.height,
                                                                          box, SCALE))
    print("[canvas] source rows kept %d..%d of %d ; dropped %d top + %d bottom (%d = %.1f%%)"
          % (box[1], box[3] - 1, master.height, box[1], master.height - box[3],
             master.height - CROP_H, (master.height - CROP_H) * 100.0 / master.height))
    src_win16 = tuple(round(v / SCALE + (box[1] if i >= 2 else 0), 1)
                      for i, v in enumerate(VIS_C16))
    print("[window] 16:9 shows canvas %s -> master %s" % (VIS_C16, src_win16))
    print("[window] visible = %.1f%% of the canvas width and %.1f%% of its height"
          % ((VIS_C16[1] - VIS_C16[0]) / CANVAS[0] * 100,
             (VIS_C16[3] - VIS_C16[2]) / CANVAS[1] * 100))

    ov = audit_overlay(master, box, VIS_C16, VIS_43,
                       os.path.join(OUT, "sheets", "crop_overlay_f%03d_y%03d.png"
                                    % (args.frame, args.crop_y)),
                       "frame %d | orange = canvas crop %s | green = 16:9 window | blue = 4:3 window"
                       % (args.frame, box))
    print("[audit] %s" % ov)
    pv = preview_ingame(bg, os.path.join(OUT, "sheets", "ingame_16x9_preview.png"), VIS_C16)
    print("[audit] %s  (what the player sees at 16:9)" % pv)
    bg.resize((1280, 600), Image.LANCZOS).save(os.path.join(OUT, "sheets", "canvas_flat.png"))

    if args.no_write:
        print("[write] skipped (--no-write)")
    else:
        os.makedirs(args.dest, exist_ok=True)
        bp = os.path.join(args.dest, "char_select_yetannia_bg.png")
        bg.save(bp)
        print("[bg] %s  %dx%d" % (bp, bg.width, bg.height))

        lock, linfo = locked_icon(SRC_ICON)
        lp = os.path.join(args.dest, "char_select_yetannia_locked.png")
        lock.save(lp)
        print("[locked] %s  %dx%d  %s" % (lp, lock.width, lock.height, json.dumps(linfo)))
    if args.no_write:
        linfo = dict(note="not regenerated (--no-write)")

    meta = dict(
        source=dict(video=VIDEO, workshop_id=3113725063, frame=args.frame,
                    master=list(master.size)),
        canvas=list(CANVAS), scale_fit_width=SCALE, source_crop=list(box),
        source_rows_dropped=dict(top=box[1], bottom=master.height - box[3],
                                 total=master.height - CROP_H),
        visible_window_16x9=list(VIS_C16), visible_window_16x9_source=list(src_win16),
        visible_window_4x3=list(VIS_43),
        visible_fraction=dict(w=(VIS_C16[1] - VIS_C16[0]) / CANVAS[0],
                              h=(VIS_C16[3] - VIS_C16[2]) / CANVAS[1]),
        filler="none -- every output pixel is a pixel of the master frame",
        locked=linfo)
    with open(os.path.join(OUT, "build.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print("[build.json] %s" % os.path.join(OUT, "build.json"))


if __name__ == "__main__":
    main()
