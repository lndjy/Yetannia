# make-workshop.py — fill in the Steam Workshop workspace for the official uploader.
#
# The uploader (`ModUploader.exe` from megacrit/sts2-mod-uploader) expects, in its workspace:
#   content/     the mod files that get uploaded (this root becomes the mod's folder on Steam)
#   workshop.json  title / description / visibility / branch range / ...
#   image.png    the workshop preview, MUST be under 1 MB
#
# The branch fields matter here: the user requires the mod to be marked beta-only. The uploader's own
# README documents `minBranch` / `maxBranch` (e.g. "public-beta"), but also warns those two "seem to
# have weird behavior ... prefer updating them on the web instead" — so the restriction is ALSO stated
# in the description text, which is always visible.
#
# usage: python .tools/make-workshop.py
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.join(HERE, "uploader", "win", "YetanniaWorkshop")
DESC = os.path.join(HERE, "workshop-description.txt")
BG = os.path.join(HERE, "pckproject", "Yetannia", "images", "charui", "char_select_yetannia_bg.png")

with open(DESC, encoding="utf-8") as fh:
    description = fh.read()

cfg = {
    "title": "耶坦尼娅 Yetannia",
    "description": description,
    # Public: the user asked for the workshop item to be published openly. (The earlier "don't make
    # it public" referred to the *voice assets* on GitHub, not to this item's visibility.)
    "visibility": "public",
    "changeNote": "首个版本。",
    "tags": [],
    # Left empty on purpose: this field wants Steam workshop IDs (found in the item URL). The mod
    # requires BaseLib at runtime, and that requirement is already declared in Yetannia.json; adding
    # a wrong numeric id here would attach a bogus dependency, so it is left for the web UI.
    "dependencies": [],
    "contentDescriptors": [],
    "minBranch": "public-beta",
    "maxBranch": "public-beta",
}

out = os.path.join(WS, "workshop.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(cfg, fh, ensure_ascii=False, indent=2)
print("wrote", out, os.path.getsize(out), "bytes")
print("  title      :", cfg["title"])
print("  visibility :", cfg["visibility"])
print("  branch     :", cfg["minBranch"], "->", cfg["maxBranch"])
print("  description:", len(description), "chars, first line:", description.splitlines()[0])

from PIL import Image  # noqa: E402

# Steam rejects a preview >= 1 MB, so shrink until it fits instead of guessing one size. The
# backdrop is a wide painting, so a 16:9-ish crop reads better than squashing it.
LIMIT = 1024 * 1024
src = Image.open(BG).convert("RGB")
img = os.path.join(WS, "image.png")
chosen = None
for w in (1280, 1024, 960, 800, 640, 512):
    h = round(w * 600 / 1280)          # keep the 1280x600 framing
    cand = src.resize((w, h), Image.LANCZOS)
    cand.save(img, "PNG", optimize=True)
    size = os.path.getsize(img)
    print(f"  try {w}x{h}: {size:,} bytes" + ("  <- fits" if size < LIMIT else "  (over)"))
    if size < LIMIT:
        chosen = (w, h, size)
        break
if chosen is None:
    raise SystemExit("*** could not get the preview under 1 MB ***")
print("wrote", img, chosen[2], "bytes  OK (limit 1,048,576)")

print("\nworkspace tree:")
for dp, dn, fn in os.walk(WS):
    for f in sorted(fn):
        p = os.path.join(dp, f)
        print("   {:>10,}  {}".format(os.path.getsize(p), os.path.relpath(p, WS)))
