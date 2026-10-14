#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cardart-import.py -- install the user's card art into the mod's Godot project.

The user draws card art as PNGs named after the card's *Chinese* display name and drops them in
`.tools/cardart/` (e.g. `打击.png`). This script turns whatever is present there into the files the
game actually loads, and nothing else:

  * resizes each drawing to the size the game draws a card portrait at. That size is **per rarity**:
    500x380 for the ordinary `%Portrait` window, 608x856 for the portrait-shaped `%AncientPortrait`
    the game routes `CardRarity.Ancient` to (see RULES and the comment above it),
  * writes it as `.tools/pckproject/Yetannia/images/card_portraits/<stem>.png` where `<stem>` is the
    model id without the mod prefix (`YETANNIA-EMBER_BOON` -> `ember_boon`), which is what
    `YetanniaCard.CustomPortraitPath` looks up at runtime,
  * writes the matching `.import` sidecar with an explicit compression policy (Godot adopts the
    params of an existing `.import`; it fills in the `.ctex` path itself),
  * removes anything a *previous* run installed that this one no longer produces (png + `.import` +
    `.ctex` + `.md5`) **and** any `.godot/imported` artifact whose own `.import` no longer references
    its hash, so the pack can never accumulate orphan `.ctex` files -- including the landscape artifact
    left behind when an Ancient card is re-imported at the (portrait) size of its own slot.

It deliberately does NOT touch `test.png` / `test2.png` / `blank.png` (the shared placeholder faces
every card without art still resolves to) and it never invents art for a card the user has not
delivered.

AFTER RUNNING THIS YOU MUST RUN `.tools/export-pck.ps1` -- Godot only generates the `.ctex` on
import, and the game loads the `.ctex`, not the PNG.

usage:
    python .tools/cardart-import.py              # install / refresh
    python .tools/cardart-import.py --dry-run    # say what it would do, write nothing
    python .tools/cardart-import.py --check      # fail if the installed files are stale/wrong

The Chinese names never go through the console in a way that matters: every result is also written
to `.tools/cardart-import-report.md` as UTF-8, because Windows PowerShell 5.1 reads and writes
UTF-8 as ANSI and mangles Chinese.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import unicodedata

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(HERE, "cardart")
CARDS = os.path.join(ROOT, "Yetannia", "Code", "Cards")
PORTRAITS = os.path.join(HERE, "pckproject", "Yetannia", "images", "card_portraits")
MANIFEST = os.path.join(HERE, "cardart-import-manifest.json")
REPORT = os.path.join(HERE, "cardart-import-report.md")
LOGDIR = os.path.join(HERE, "qa", "logs")
CROPS = os.path.join(HERE, "qa", "crops")
IMPORTED = os.path.join(HERE, "pckproject", ".godot", "imported")
PROJECT = os.path.join(HERE, "pckproject")

# --------------------------------------------------------------------------- target size, PER RARITY
# MEASURED, not guessed:
#   * res://scenes/cards/card.tscn (retail pack) has the `Portrait` TextureRect at
#     offset -125..125 x -168..22 = 250x190, stretch_mode=5.
#   * the retail pack's card art agrees: 577 of the 626 `AtlasTexture` regions under
#     images/atlases/card_atlas.sprites/ are exactly 250x190 (the source PNG imports to exactly
#     250*190*4 + header bytes).
#   * NCard.UpdatePortrait (Core/Nodes/Cards/NCard.cs:1244-1266, `_ancientPortrait.Texture =
#     portrait` at :1262) sends CardRarity.Ancient at a DIFFERENT node, `%AncientPortrait`. In
#     card.tscn (:189-203) that node is anchors 0,0..1,1 with offsets -153..445 x -215..627 under a
#     0x0 parent Control, i.e. 598x842 local units, drawn at its own `scale = Vector2(0.5, 0.5)`
#     -> 299x421 on screen. Crucially it has NO `stretch_mode`, so it is Godot's default
#     STRETCH_SCALE: stretch-to-fill, aspect ignored. The other 22 vanilla card regions are 250x351
#     -- the Ancient art -- and 250x351 stretched into 598x842 is 0.29% off, which is how the rect is
#     known to be *for* portrait art.
#   * NInspectCardScreen scales the whole card node to 2x while it is open, so the largest a portrait
#     is ever drawn at is 2x its rect.
# So the target size is a function of the card's rarity, not a constant:
#   * every rarity except Ancient keeps 500x380 = the 250x190 window x2, which is also exactly the
#     250:190 ratio so the engine's own cover-crop is a no-op;
#   * Ancient gets 608x856. BPTC/BC7 refuses a dimension that is not a multiple of 4, so 598x842
#     cannot be uploaded as-is; 608x856 is the multiple-of-4 pair nearest 2x the drawn size with an
#     aspect error of 0.0094% -- and because %AncientPortrait stretches to fill, that aspect error IS
#     the geometric distortion the player sees. (The obvious "2x vanilla" 500x702 is both lower
#     resolution and not a multiple of 4; the nearest multiple-of-4 partner of 500, 500x704, would be
#     upscaled 1.2x on the card and 2.4x on inspect.)
# Both of these live in RULES below, keyed by CardRarity, so framing is data and not a special case
# buried in the cropping code.
DEFAULT_RULE = {"size": (500, 380), "window": "center"}
RULES = {
    "Ancient": {"size": (608, 856), "window": "subject"},
}


def rule_for(rarity):
    """The framing rule for a rarity: {'size': (w, h), 'window': 'center'|'subject'}."""
    return RULES.get(rarity, DEFAULT_RULE)

# --------------------------------------------------------------------------- import policy
# BC7 (compress/mode=2 + high_quality=true), NOT lossless. Every number below was measured on this
# mod's own card art at 500x380 with .tools/out/visual/vram-import.ps1 (which dumps the
# engine-decompressed pixels) and scored by .tools/qa/r-cardart-compress.py:
#
#   variant            .ctex bytes   mean|dRGB| 1:1   %px off >8 1:1   mean at 250x190
#   lossless (mode 0)      252,986            0.00            0.00%            0.00
#   BC7      (mode 2 hq)   190,052            1.27            1.18%            0.74
#   DXT1     (mode 2)       95,052            5.39           15.97%            3.59   <- rejected
#   BC7 + mipmaps          254,852            -               -                +34% bytes only
#
#   * BC7 saves 24.9% of the .ctex (~4.8 MB over 76 cards) and 4x the VRAM (1 B/px vs 4 B/px:
#     14.4 MB vs 57.8 MB for the whole set) for an error the eye cannot see at the size the card is
#     drawn -- and at the 250x190 card size only 0.04% of pixels move by more than 8/255.
#   * high_quality=true is what selects BPTC_RGBA (BC7) instead of DXT1; without it the same
#     setting silently produced a 5.4/255 mean error, which is why the DXT1 row is here.
#   * process/fix_alpha_border made no measurable difference on this art (it is fully opaque), but it
#     is kept on: it is Godot's default and it is what stops BC7 bleeding black into soft alpha edges
#     if a future drawing does have transparency.
#   * mipmaps are off: the portrait is never sampled below 1:1 (the card rect is 250x190 and the
#     inspect screen is 2x), so a mip chain is +34% bytes and bytes-for-nothing.
#   * This matches what the player already sees in VANILLA: the retail pack's card atlas is
#     images/atlases/card_atlas_0.png.import -> path.bptc / imported_formats ["s3tc_bptc","etc2_astc"]
#     / vram_texture=true, i.e. BC7-class VRAM compression of the very 250x190 regions the card draws.
#     Ours is BC7 at 2x that resolution, so a 1:1 read on the 2x inspect screen is sharper than
#     vanilla's own upscaled 250x190.
#   * It is also this mod's existing policy for large 2D art (charui/char_select_yetannia_bg.png,
#     creature/yetannia_atlas_0.png, ui/hands/*). Only the small icons are lossless.
#
# detect_3d/compress_to=0: the importer's "this texture touched a 3D material, switch me to Lossy"
# heuristic would otherwise silently re-compress the art on some future re-import. Same guard the
# creature atlas and the char-select textures carry.
IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://Yetannia/images/card_portraits/%(stem)s.png"

[params]

compress/mode=%(mode)d
compress/high_quality=%(hq)s
compress/lossy_quality=0.7
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=false
mipmaps/limit=-1
roughness/mode=0
process/fix_alpha_border=true
process/premult_alpha=false
process/size_limit=0
detect_3d/compress_to=0
"""

MODE = 2
HIGH_QUALITY = "true"

# The params this script owns. Godot adds uid= / path.bptc= / a dozen more defaults of its own when it
# imports, so the sidecar is compared and patched on these keys only -- rewriting the whole file from
# the template would throw Godot's uid away and churn the .md5 on every run.
POLICY = {
    "compress/mode": str(MODE),
    "compress/high_quality": HIGH_QUALITY,
    "detect_3d/compress_to": "0",
    "mipmaps/generate": "false",
    "process/fix_alpha_border": "true",
}


def patch_sidecar(text, stem):
    """Bring an .import in line with POLICY. Returns (new_text, note) -- note is None when it was fine."""
    want_src = 'source_file="res://Yetannia/images/card_portraits/%s.png"' % stem
    template = IMPORT_TEMPLATE % {"stem": stem, "mode": MODE, "hq": HIGH_QUALITY}
    if want_src not in text:
        return template, "rewritten (source_file did not point at this png)"
    changed = []
    for key, value in POLICY.items():
        pat = re.compile(r"^%s=.*$" % re.escape(key), re.M)
        m = pat.search(text)
        if m is None:
            return template, "rewritten (no %s line to patch)" % key
        if m.group(0).strip() != "%s=%s" % (key, value):
            text = pat.sub("%s=%s" % (key, value), text)
            changed.append(key)
    return text, ("patched " + ", ".join(changed)) if changed else None

# The three faces the runtime falls back to. Never written, never removed: the script is allowed to
# add card art, not to change what a card without art looks like.
RESERVED = {"test.png", "test2.png", "blank.png"}

CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def say(msg=""):
    """Print without ever dying on the console's codepage (Chinese prints as mojibake, or raises)."""
    enc = sys.stdout.encoding or "ascii"
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode(enc, "replace").decode(enc, "replace"))


# --------------------------------------------------------------------------- card list
CLASS_RE = re.compile(r"^\s*public\s+((?:\w+\s+)*)class\s+(\w+)\s*:\s*(\w+)", re.M)
RARITY_RE = re.compile(r"base\(\s*\d+\s*,\s*CardType\.\w+\s*,\s*CardRarity\.(\w+)\s*,")
# `<Name> = new CardLoc(` then the title string on the same or the next line. The optional `(` covers
# the tuple-style constructors used by the other content types.
LOC_RE = r'%s\s*=\s*new\s+\w*Loc\(\s*\n?\s*\(?\s*(?:\$?)"((?:[^"\\]|\\.)*)"'
CHINESE_RE = re.compile(LOC_RE % "Chinese")
ENGLISH_RE = re.compile(LOC_RE % "English")


def slugify(name):
    """The game's StringHelper.Slugify: 'AllOutAttack' -> 'ALL_OUT_ATTACK'."""
    t = re.sub(r"([A-Za-z0-9])([A-Z])", r"\1_\2", name.strip())
    t = re.sub(r"\s+", "_", t.upper())
    return re.sub(r"[^A-Z0-9_]", "", t)


def read_cards():
    """Every concrete YetanniaCard subclass, its Chinese title, rarity and pck file stem."""
    cards = []
    for fn in sorted(os.listdir(CARDS)):
        if not fn.endswith(".cs"):
            continue
        text = io.open(os.path.join(CARDS, fn), encoding="utf-8").read()
        # The card's own class is the `class X : Y` whose base is YetanniaCard; helper types in the
        # same folder (YetanniaCard itself, ProphetQueue) are skipped here.
        decls = [(m.group(1), m.group(2), m.group(3)) for m in CLASS_RE.finditer(text)]
        mine = [(mods, cls) for mods, cls, base in decls if base == "YetanniaCard"]
        if not mine:
            continue
        mods, cls = mine[0]
        if "abstract" in mods.split():
            continue

        zh = CHINESE_RE.search(text)
        en = ENGLISH_RE.search(text)
        rarity = RARITY_RE.search(text)
        if zh is None:
            say("WARNING %s: no Chinese CardLoc title found -- cannot match art by name" % fn)
        cards.append({
            "file": fn,
            "class": cls,
            "stem": slugify(cls).lower(),
            "zh": zh.group(1) if zh else "",
            "en": en.group(1) if en else "",
            "rarity": rarity.group(1) if rarity else "?",
        })
    return cards


def cross_check_ids(cards):
    """Check our stem derivation against model ids the game itself logged.

    `YetanniaCard.CustomPortraitPath` derives the file name from `Id.Entry`, and the self-check prints
    every card's real id. Reading one of those logs proves the two agree *before* 76 files are named
    after a guessed slug -- a mismatch here would otherwise only show up as "art missing in game".
    Returns (checked_count, mismatches).
    """
    if not os.path.isdir(LOGDIR):
        return 0, []
    newest, newest_mtime = None, 0
    for fn in os.listdir(LOGDIR):
        p = os.path.join(LOGDIR, fn)
        m = os.path.getmtime(p)
        if m > newest_mtime:
            newest, newest_mtime = p, m
    if newest is None:
        return 0, []

    ids = set()
    with io.open(newest, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.search(r"self-check card\s*:\s*(YETANNIA-[A-Z0-9_]+)", line)
            if m:
                ids.add(m.group(1))
    if not ids:
        return 0, []

    by_class = {c["class"]: c for c in cards}
    mism = []
    for cid in sorted(ids):
        slug = cid.split("-", 1)[1].lower()
        # find the card whose class slugifies to this
        if not any(c["stem"] == slug for c in cards):
            mism.append(cid)
    return len(ids), mism


# --------------------------------------------------------------------------- matching
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\s·・、,，。.．\-_]+", "", s)


# --------------------------------------------------------------------------- file-name aliases
# Drawings are matched to cards by the card's Chinese display title. One delivered file does not match
# any card title, and this is the whole of the exception list:
#
#   `白刃连斩.png`  vs  FlurryStrike 白刃乱舞
#
# The evidence that it belongs to FlurryStrike: the user delivered exactly the 6 cards that had no art,
# and 5 of the 6 file names match a card title exactly (合击, 冰刃连斩, 未雨绸缪, 全力进攻, 长驱直入).
# `白刃连斩` is the only file left over and FlurryStrike is the only card left over, and 白刃连斩 / 白刃乱舞
# differ in two characters. NOTE: this is an inference, not a confirmation. It mirrors the 归途终竟 /
# 归途终尽 typo resolved by the user in the previous round, where the user's file name was ruled correct
# and the CARD was renamed -- so the open question here is whether FlurryStrike should be renamed to
# 白刃连斩. That rename is deliberately NOT done this round (the brief allows no card-name changes); the
# art is installed under the existing id and the mismatch is reported instead of hidden.
ALIASES = {
    "白刃连斩": "flurry_strike",
}


def prepare(src_path, rarity):
    """Crop the drawing to the slot's aspect and resize to the slot's size.

    Returns (png_bytes, source_size, crop_report) where crop_report is a dict describing what was
    kept, so the run can be audited after the fact instead of trusted.
    """
    rule = rule_for(rarity)
    tw, th = rule["size"]
    ratio = tw / float(th)

    with Image.open(src_path) as im0:
        im = im0.convert("RGBA")
        w, h = im.size
        want_w = max(1, int(round(h * ratio)))
        report = {"src": (w, h), "target": (tw, th), "crop_x": 0, "crop_w": w, "why": "no crop"}

        if want_w < w:
            x0, why, stats = choose_window(im, want_w, rule["window"])
            im = im.crop((x0, 0, x0 + want_w, h))
            report.update({"crop_x": x0, "crop_w": want_w, "why": why, "stats": stats,
                           "kept": 100.0 * want_w / w})
        elif want_w > w:
            want_h = max(1, int(round(w / ratio)))
            y0 = (h - want_h) // 2
            im = im.crop((0, y0, w, y0 + want_h))
            report.update({"crop_w": w, "why": "height cropped, centred",
                           "kept": 100.0 * w / w})

        im = im.resize((tw, th), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=False, compress_level=9)
        return buf.getvalue(), (w, h), report


# --------------------------------------------------------------------------- where to cut
# A landscape drawing dropped into the portrait %AncientPortrait slot has to lose ~47% of its width.
# Cutting the middle is the obvious thing and is exactly what the brief says not to do blindly, so the
# window is scored: `edge * (0.35 + saturation)` summed over every full-height window, where `edge` is
# the luminance gradient magnitude (detail) and the saturation factor keeps the score from chasing the
# high-frequency *background* -- the sunburst rays behind 合击 and the ice shards behind 冰刃连斩 are
# full of edges but are much less saturated than the figures. The 0.35 floor stops the factor from
# zeroing out a genuinely monochrome subject.
#
# The metric is then NOT trusted on its own. Measured on the two Ancient drawings that exist:
#
#   card                          source     window   centre   best vs centre   score curve
#   引领之光 (darvs_prophecy)      992x752    296      229      +1.7%            -40%..+7% of median
#   合击 (ominous_decree_...)     1024x768   242      239      +0.0%            -17%..+11% of median
#
# i.e. the metric's own optimum is within 1.7% of the centre, on a curve whose own spread is ten times
# that, so it has no real preference between them -- on 合击 it picks the centre to within 3 px. A
# 1.7% score win is not worth moving the frame off the composition the artist centred, so the centre is
# kept unless the metric wins by more than MARGIN. Both numbers are printed per card, so the choice is
# auditable rather than asserted.
MARGIN = 0.05


def choose_window(im, want_w, mode):
    """Pick the horizontal window offset. Returns (x0, why, stats)."""
    w, h = im.size
    centre = (w - want_w) // 2
    if mode != "subject":
        return centre, "centre", None

    import numpy as np

    small = im.convert("RGB").resize((512, 384), Image.LANCZOS)
    a = np.asarray(small, dtype=np.float32) / 255.0
    lum = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    gy, gx = np.gradient(lum)
    weight = np.hypot(gx, gy) * (0.35 + sat)

    # column totals -> every window's score in O(1)
    col = weight.sum(axis=0)
    c = np.concatenate([[0.0], np.cumsum(col)])
    small_w = max(1, int(round(want_w * len(col) / float(w))))
    stop = len(col) - small_w + 1
    if stop < 1:
        return centre, "centre (source too small to slide)", None
    sc = c[small_w:small_w + stop] - c[0:stop]

    i = int(np.argmax(sc))
    best_x = max(0, min(w - want_w, int(round(i * w / float(len(col))))))
    centre_i = min(len(sc) - 1, int(round(centre * len(col) / float(w))))
    gain = sc[i] / sc[centre_i] - 1.0
    med = float(np.median(sc))
    stats = {
        "best_x": best_x, "centre_x": centre, "gain": gain,
        "curve": (float(sc.min()) / med - 1.0, float(sc.max()) / med - 1.0),
    }
    if gain > MARGIN:
        return best_x, ("detail-mass window (x0=%d, centre=%d, +%.1f%% score)"
                        % (best_x, centre, gain * 100)), stats
    return centre, ("centre (detail-mass best x0=%d is only %+.1f%% better than the centre, "
                    "curve spans %+.0f%%..%+.0f%% of the median)"
                    % (best_x, gain * 100, stats["curve"][0] * 100, stats["curve"][1] * 100)), stats


def cache_is_stale(import_text, src_png):
    """Whether Godot's import cache no longer matches `src_png`.

    Godot records the md5 of the source it imported in the artifact's sibling `.md5` file as
    `source_md5="..."`, together with the `dest_md5` of the artifact it produced. That is the engine's
    own staleness record and therefore the authoritative test -- it stays correct across an
    interrupted run, a hand-edited PNG or a re-copy, none of which any bookkeeping of ours would see.
    Verified against this project: for an unchanged card `source_md5` equals the PNG's md5 exactly.
    """
    if not import_text:
        return False
    arts = re.findall(r"res://\.godot/imported/([^\"]+)", import_text)
    if not arts:
        return True
    try:
        with open(src_png, "rb") as fh:
            have = hashlib.md5(fh.read()).hexdigest()
    except OSError:
        return True
    for art in arts:
        if not os.path.exists(os.path.join(IMPORTED, art)):
            return True
        m = re.match(r"^(.*\.png-[0-9a-f]+)\.", art)
        mdf = os.path.join(IMPORTED, (m.group(1) if m else art) + ".md5")
        if not os.path.exists(mdf):
            return True
        mm = re.search(r'source_md5="([0-9a-f]+)"',
                       io.open(mdf, encoding="utf-8", errors="replace").read())
        if mm and mm.group(1) != have:
            return True
    return False


def invalidate_cache(import_text):
    """Delete the .godot/imported artifacts an (about to be stale) .import sidecar points at.

    Returns the names removed. Deleting the `.ctex` alongside its `.md5` is what makes Godot treat the
    source as not-yet-imported, so the next `--import` regenerates it instead of assuming the cache is
    current -- which matters because a param-only change is reimported only about half the time
    (measured, see the note in main()).
    """
    gone = []
    for art in re.findall(r"res://\.godot/imported/([^\"]+)", import_text):
        for name in (art, art + ".md5"):
            p = os.path.join(IMPORTED, name)
            if os.path.exists(p):
                os.remove(p)
                gone.append(name)
        # a variant artifact also has a bare `<stem>-<hash>.md5` companion
        m = re.match(r"^(.*\.png-[0-9a-f]+)\.", art)
        if m:
            p = os.path.join(IMPORTED, m.group(1) + ".md5")
            if os.path.exists(p):
                os.remove(p)
                gone.append(os.path.basename(p))
    return gone


def write_overlay(src_path, dst_path, report):
    """Draw the chosen window (and, for comparison, the centre window) on the source."""
    try:
        with Image.open(src_path) as im0:
            im = im0.convert("RGB")
        d = ImageDraw.Draw(im)
        w, h = im.size
        cw = report["crop_w"]
        centre = (w - cw) // 2
        if centre != report["crop_x"]:
            d.rectangle([centre, 0, centre + cw - 1, h - 1], outline=(255, 40, 40), width=4)
        d.rectangle([report["crop_x"], 0, report["crop_x"] + cw - 1, h - 1],
                    outline=(40, 255, 40), width=4)
        d.text((12, 12), "%s  RED=centre  GREEN=chosen  x0=%d  keeps %.1f%% of %dx%d"
               % (report["why"], report["crop_x"], report.get("kept", 100.0), w, h),
               fill=(255, 255, 0))
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        im.save(dst_path)
        return dst_path
    except Exception as e:                                        # noqa: BLE001
        return "<overlay failed: %s: %s>" % (type(e).__name__, e)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="do not write anything")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if an installed file would change (nothing is written)")
    args = ap.parse_args()

    for size in [r["size"] for r in list(RULES.values()) + [DEFAULT_RULE]]:
        if size[0] % 4 or size[1] % 4:
            sys.exit("target size %dx%d is not a multiple of 4 (BPTC/S3TC would refuse it)" % size)

    cards = read_cards()
    by_norm_zh = {}
    for c in cards:
        if c["zh"]:
            by_norm_zh.setdefault(norm(c["zh"]), c)
    by_stem = {c["stem"]: c for c in cards}

    if not os.path.isdir(ART):
        sys.exit("no art directory: %s" % ART)

    art_files = sorted(f for f in os.listdir(ART)
                       if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))

    matched, unmatched, aliased = [], [], []
    for f in art_files:
        stem = os.path.splitext(f)[0]
        c = by_norm_zh.get(norm(stem)) or by_stem.get(norm(stem).lower())
        if c is None and stem in ALIASES:
            c = by_stem.get(ALIASES[stem])
            if c is not None:
                aliased.append((f, c["stem"], c["zh"]))
        if c is None:
            unmatched.append(f)
        else:
            matched.append((f, c))

    # one art file per card; a duplicate is a real mistake, so say it out loud
    seen, dupes = {}, []
    for f, c in matched:
        if c["stem"] in seen:
            dupes.append((c["stem"], seen[c["stem"]], f))
        else:
            seen[c["stem"]] = f
    matched = [(f, c) for f, c in matched if seen[c["stem"]] == f]

    have_art = {c["stem"] for _, c in matched}
    missing = [c for c in cards if c["stem"] not in have_art]

    id_count, id_mismatch = cross_check_ids(cards)

    # ------------------------------------------------------------------ install
    changed, kept, failed, sidecars, overlays = [], [], [], [], []
    removed, orphans = [], []
    rules_hit = []
    for f, c in matched:
        src = os.path.join(ART, f)
        dst = os.path.join(PORTRAITS, c["stem"] + ".png")
        try:
            data, srcsize, crop = prepare(src, c["rarity"])
        except Exception as e:                                    # noqa: BLE001 - report, never crash
            failed.append((f, c["stem"], "%s: %s" % (type(e).__name__, e)))
            continue
        old = None
        if os.path.exists(dst):
            with open(dst, "rb") as fh:
                old = fh.read()
        if old == data:
            kept.append((f, c, len(data), crop))
        else:
            changed.append((f, c, len(data), srcsize, crop))
            if not args.dry_run and not args.check:
                os.makedirs(PORTRAITS, exist_ok=True)
                with open(dst, "wb") as fh:
                    fh.write(data)

        if rule_for(c["rarity"]) is not DEFAULT_RULE:
            rules_hit.append((c, crop))
        # Any rarity on a non-default rule gets an overlay showing the window that was chosen on top
        # of the source, so a crop nobody looked at cannot ship. Written even on --dry-run (it is a
        # report, not an installed asset).
        if rule_for(c["rarity"]) is not DEFAULT_RULE and not args.check:
            overlays.append((c["stem"], write_overlay(
                src, os.path.join(CROPS, "%s-window.png" % c["stem"]), crop)))

        imp = dst + ".import"
        cur = io.open(imp, encoding="utf-8").read() if os.path.exists(imp) else None
        if cur is None:
            want, note = IMPORT_TEMPLATE % {"stem": c["stem"], "mode": MODE, "hq": HIGH_QUALITY}, "created"
        else:
            want, note = patch_sidecar(cur, c["stem"])

        # Invalidate the cache whenever the params were patched, or the cache no longer matches the
        # pixels we just wrote. MEASURED with .tools/qa/r2-hashprobe.py (the engine, not a guess):
        #
        #   * the artifact's hash is derived from the source PATH only -- it is identical for the
        #     lossless and the BC7 artifact of the same PNG, and it survived this round's
        #     darvs_prophecy change from 500x380 to 608x856. So a *content* change reimports into the
        #     same name and cannot orphan anything.
        #   * the *variant suffix* comes from the params. A param change makes Godot write
        #     `<stem>.png-<hash>.bptc.ctex` and LEAVE the previous `<stem>.png-<hash>.ctex` behind --
        #     that is the orphan, and it is the only way this importer can create one, because it is
        #     the thing that patches params.
        #   * `godot --headless --import` reimported a param-only change in 2 of 4 identical probe runs
        #     and silently did nothing in the other 2. So the patch cannot be left to the importer to
        #     notice: deleting the artifact AND its `.md5` is what forces the reimport (probe step 2b),
        #     and a source change reimports reliably (9/9).
        #
        # Net effect: the pack can never hold two compression variants of one source, and a param
        # patch can never be silently inert.
        if cur is not None and (note is not None or cache_is_stale(cur, dst)) \
                and not args.dry_run and not args.check:
            removed += invalidate_cache(cur)

        if note is not None:
            sidecars.append((c["stem"], note))
            if not args.dry_run and not args.check:
                os.makedirs(PORTRAITS, exist_ok=True)
                io.open(imp, "w", encoding="utf-8", newline="\n").write(want)

    # ------------------------------------------------------------------ remove stale installs
    manifest = {}
    if os.path.exists(MANIFEST):
        manifest = json.load(io.open(MANIFEST, encoding="utf-8"))
    stale = sorted(set(manifest.get("stems", [])) - have_art)
    if not args.dry_run and not args.check:
        for stem in stale:
            for p in (os.path.join(PORTRAITS, stem + ".png"),
                      os.path.join(PORTRAITS, stem + ".png.import")):
                if os.path.exists(p):
                    os.remove(p)
                    removed.append(os.path.basename(p))
            for fn in os.listdir(IMPORTED) if os.path.isdir(IMPORTED) else []:
                if fn.startswith(stem + ".png-"):
                    os.remove(os.path.join(IMPORTED, fn))
                    removed.append(fn)

    # Orphan .ctex. Godot names an import artifact
    # `.godot/imported/<source-basename>-<import-hash>.<variant>.ctex` with a sibling `.md5`, and the
    # hash is NOT the file's md5 -- it changes when the *import parameters or the source size* change.
    # Re-importing an Ancient card at the new portrait size therefore leaves the old landscape
    # artifact sitting in the cache under a stale hash, and `--export-pack` ships the whole
    # `.godot/imported` directory, so it would ride along into Yetannia.pck as dead weight.
    #
    # The artifact is named after the source's BASENAME, so `card_portraits/ember_boon.png` and
    # `powers/ember_boon.png` and `powers_big/ember_boon.png` produce three artifacts that all start
    # `ember_boon.png-`. Reading only the card_portraits sidecar therefore marks the live power icons
    # as orphans -- measured, and it would have deleted 64 live artifacts. Liveness is therefore
    # decided against every `.import` in the project, and the *scope* of what may be deleted is still
    # limited to stems that exist as a portrait in card_portraits/.
    live = set()
    for dirpath, _dirs, files in os.walk(PROJECT):
        for fn in files:
            if not fn.endswith(".import"):
                continue
            text = io.open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            live.update(re.findall(r"res://\.godot/imported/([^\"]+)", text))

    def is_live(name):
        if name in live:
            return True
        # the `.md5` companion of a live artifact carries the same stem+hash, minus the variant suffix
        if name.endswith(".md5"):
            base = name[:-len(".md5")]
            return any(a.startswith(base + ".") for a in live)
        return False

    for fn in sorted(os.listdir(IMPORTED) if os.path.isdir(IMPORTED) else []):
        m = re.match(r"^(.*\.png)-[0-9a-f]+\.", fn)
        if not m or not os.path.exists(os.path.join(PORTRAITS, m.group(1))):
            continue
        if is_live(fn):
            continue
        orphans.append(fn)
    if not args.dry_run and not args.check:
        for fn in orphans:
            os.remove(os.path.join(IMPORTED, fn))
            removed.append(fn)
    if not args.dry_run and not args.check:
        json.dump({"stems": sorted(have_art)},
                  io.open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ------------------------------------------------------------------ report
    lines = []
    lines.append("# 卡图导入 / card art import\n")
    lines.append("- 脚本: `.tools/cardart-import.py`（可重跑）")
    lines.append("- 图源: `.tools/cardart/`  共 **%d** 个文件" % len(art_files))
    lines.append("- 卡表: `Yetannia/Code/Cards/*.cs`  共 **%d** 张卡" % len(cards))
    lines.append("- 目标尺寸: **按稀有度**（见下表；`%Portrait` 250x190 的 2 倍 / `%AncientPortrait` 598x842 的 2 倍）")
    lines.append("- 安装位置: `.tools/pckproject/Yetannia/images/card_portraits/<stem>.png`")
    lines.append("- 压缩: `compress/mode=%d` + `high_quality=%s` = **BC7 (BPTC)**，1 B/px；"
                 "实测均值误差 1.27/255（500x380 1:1）、卡面 250x190 下 0.74/255。\n"
                 % (MODE, HIGH_QUALITY))
    lines.append("| 稀有度 | 目标尺寸 | 长宽比 | 取景 |\n|---|---|---|---|")
    lines.append("| 其它（默认） | %dx%d | %.5f | 居中裁切（居中即 `%%Portrait` 的 KEEP_ASPECT 行为） |"
                 % (DEFAULT_RULE["size"][0], DEFAULT_RULE["size"][1],
                    DEFAULT_RULE["size"][0] / float(DEFAULT_RULE["size"][1])))
    for r in sorted(RULES):
        lines.append("| %s | %dx%d | %.5f | %s |"
                     % (r, RULES[r]["size"][0], RULES[r]["size"][1],
                        RULES[r]["size"][0] / float(RULES[r]["size"][1]),
                        "主体取景（详见下方实测）" if RULES[r]["window"] == "subject" else "居中裁切"))
    lines.append("")
    lines.append("| 结果 | 数量 |\n|---|---|")
    lines.append("| 新装/更新 | %d |" % len(changed))
    lines.append("| 已是最新（跳过） | %d |" % len(kept))
    lines.append("| `.import` 重新写过 | %d |" % len(sidecars))
    lines.append("| 转换失败 | %d |" % len(failed))
    lines.append("| 有图没配到卡 | %d |" % len(unmatched))
    lines.append("| 有卡没有图 | %d |" % len(missing))
    lines.append("| 清掉的孤立 `.ctex`/`.md5` | %d |\n" % len(orphans))

    if changed:
        lines.append("## 新装/更新\n")
        lines.append("| 中文名 | 类 | stem | 源尺寸 | 输出尺寸 | 输出字节 | 取景 |\n|---|---|---|---|---|---|---|")
        for f, c, size, srcsize, crop in changed:
            lines.append("| %s | %s | `%s` | %dx%d | %dx%d | %d | %s |"
                         % (c["zh"], c["class"], c["stem"], srcsize[0], srcsize[1],
                            crop["target"][0], crop["target"][1], size, crop["why"]))
        lines.append("")

    if rules_hit:
        lines.append("## 非默认取景规则实际命中的卡（每次运行都会列，和有没有新装无关）\n")
        lines.append("| 中文名 | 类 | 稀有度 | 源尺寸 | 输出尺寸 | 裁掉的窗口 | 理由 |")
        lines.append("|---|---|---|---|---|---|---|")
        for c, crop in rules_hit:
            lines.append("| %s | %s | %s | %dx%d | %dx%d | x=%d w=%d（保留 %.1f%%） | %s |"
                         % (c["zh"], c["class"], c["rarity"],
                            crop["src"][0], crop["src"][1],
                            crop["target"][0], crop["target"][1],
                            crop["crop_x"], crop["crop_w"], crop.get("kept", 100.0), crop["why"]))
        lines.append("")

    if aliased:
        lines.append("## 文件名与卡名对不上、按别名表安装（**需要确认**）\n")
        lines.append("别名表在脚本顶部 `ALIASES`，这里列出的是**推断**而不是确认：")
        for f, stem, zh in aliased:
            lines.append("- `%s` -> `%s`（卡名 `%s`）" % (f, stem, zh))
        lines.append("")

    if overlays:
        lines.append("## 取景叠加图（源图上画出选中的窗口）\n")
        for stem, path in overlays:
            lines.append("- `%s` -> `%s`" % (stem, path))
        lines.append("")

    if failed:
        lines.append("## 转换失败（这些卡没有装进去）\n")
        for f, stem, err in failed:
            lines.append("- %s -> `%s` : %s" % (f, stem, err))
        lines.append("")

    if unmatched:
        lines.append("## 有图但表中没有对应的卡\n")
        for f in unmatched:
            lines.append("- %s" % f)
        lines.append("")

    if dupes:
        lines.append("## 多个文件匹配到同一张卡（只用了第一个）\n")
        for stem, a, b in dupes:
            lines.append("- `%s`: %s / %s" % (stem, a, b))
        lines.append("")

    lines.append("## 缺图（没有编造占位图，游戏仍回落到共用卡面）\n")
    lines.append("| 中文名 | 类 | 稀有度 | 现在显示 |\n|---|---|---|---|")
    for c in missing:
        face = "test2.png（金卡）" if c["rarity"] == "Rare" else "test.png（白/蓝/基础/先古共用）"
        lines.append("| %s | %s | %s | %s |" % (c["zh"] or "(无中文名)", c["class"], c["rarity"], face))
    lines.append("")

    if stale:
        lines.append("## 清理掉的旧安装（图源里已经没有它们了）\n")
        for stem in stale:
            lines.append("- `%s`" % stem)
        lines.append("")

    if orphans:
        lines.append("## 清理掉的孤立导入缓存（`.import` 的 `dest_files` 不再引用它们）\n")
        for fn in orphans:
            lines.append("- `%s`" % fn)
        lines.append("")

    lines.append("## 自检\n")
    if id_count:
        lines.append("- 拿日志里的真实模型 id 交叉核对过 stem 推导：%d 个 id，%d 个对不上"
                     % (id_count, len(id_mismatch)))
        for m in id_mismatch:
            lines.append("  - 对不上: %s" % m)
    else:
        lines.append("- 没有可用日志可交叉核对 stem（`self-check card : YETANNIA-...` 一行都没找到）")
    lines.append("- 必须再跑一次 `.tools/export-pck.ps1`：Godot 只在 import 时生成 `.ctex`，"
                 "游戏读的是 `.ctex` 不是 PNG。\n")

    io.open(REPORT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    # ------------------------------------------------------------------ console
    say("art files            : %d" % len(art_files))
    say("cards                : %d" % len(cards))
    say("installed/updated    : %d" % len(changed))
    say("already current      : %d" % len(kept))
    say(".import rewritten    : %d" % len(sidecars))
    say("failed               : %d" % len(failed))
    say("art with no card     : %d" % len(unmatched))
    say("cards with no art    : %d" % len(missing))
    say("orphan cache removed : %d" % len(orphans))
    if aliased:
        say("aliased file names   : %d (inferred, reported above)" % len(aliased))
    if id_count:
        say("stem cross-check     : %d ids from the log, %d mismatched" % (id_count, len(id_mismatch)))
    if stale:
        say("stale installs gone  : %d" % len(stale))
    say("")
    say("cards still without art (placeholders, nothing invented):")
    for c in missing:
        say("   %-22s %-28s %s" % (c["zh"], c["class"], c["rarity"]))
    if unmatched:
        say("")
        say("art files with no matching card:")
        for f in unmatched:
            say("   %s" % f)
    say("")
    say("report -> %s" % REPORT)
    say("NEXT: .tools\\export-pck.ps1   (mandatory — it is what produces the .ctex)")

    if failed:
        return 1
    if args.check and (changed or sidecars or stale or unmatched):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
