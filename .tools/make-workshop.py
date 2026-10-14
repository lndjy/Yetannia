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
    "changeNote": "介绍更新：工坊说明改为中英双语，并改用 Steam 支持的富文本格式（加粗 / 标题 / 列表），不再显示成一堆星号和井号。\n\nMod 内容没有改动，仍是 v1.0.1：\n· 修复了施法语音一直无法触发的问题（现在打出技能/能力牌会说话）。\n· 联机里画笔和标记的颜色改成蓝色（原来的黑色看不出来）。\n· 重绘了联机石头剪刀布的手部立绘。\n· 联机时「预见」的卡死看门狗从 30 秒延长到 300 秒，不再把队友思考误报成卡死。\n· 作者名改为 lndjy。",
    "tags": [],
    # 3737335127 is BaseLib's Workshop item id -- not a guess: the uploader itself resolves the mod's
    # declared BaseLib dependency to exactly this id and prints "Removed dependency on 3737335127" when
    # this list is empty, which is how it was identified. Keeping it here means the Workshop page shows
    # the requirement to subscribers instead of the uploader silently dropping it on every update.
    # (Yetannia.json still declares the same dependency, which is what the game actually enforces.)
    "dependencies": [3737335127],
    "contentDescriptors": [],
    # minBranch / maxBranch are DELIBERATELY ABSENT. They were "public-beta" / "public-beta" and every
    # upload attempt that sent them failed at the commit step -- three times with k_EResultTimeout and
    # once, after a retry, with k_EResultFail. Removing just these two keys made the very next upload
    # commit successfully. The uploader's own README already warns that these two "seem to have weird
    # behavior ... prefer updating them on the web instead", so that is what has to happen: the
    # beta-only restriction must be kept in the item's branch settings on the Workshop web page. It is
    # also stated unconditionally in the description text (see workshop-description.txt, first line),
    # which is visible regardless of what the branch fields say.
}

out = os.path.join(WS, "workshop.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(cfg, fh, ensure_ascii=False, indent=2)
print("wrote", out, os.path.getsize(out), "bytes")
print("  title      :", cfg["title"])
print("  visibility :", cfg["visibility"])
print("  branch     : not sent (see the note on minBranch/maxBranch above)")
print("  deps       :", cfg["dependencies"])
print("  description:", len(description), "chars, first line:", description.splitlines()[0])

from PIL import Image  # noqa: E402

# Steam rejects a preview >= 1 MB, so shrink until it fits instead of guessing one size. The
# backdrop is a wide painting, so a 16:9-ish crop reads better than squashing it.
#
# 1008 comes before 1024 on purpose. MEASURED: Steam keys an item's "last updated" timestamp on its
# CONTENT, not on its metadata -- three uploads that changed only the description and the change note
# left `time_updated` pinned at the previous content upload, even though the stored description did
# change. A new preview image IS a content change, so it is what makes Steam re-publish the item (and
# therefore what makes an edited description visible instead of a cached copy). 1008x472 is the same
# crop and framing as 1024x480, so this is invisible; it exists so that a description-only update can
# be forced through when Steam's caches are serving the old render.
LIMIT = 1024 * 1024
src = Image.open(BG).convert("RGB")
img = os.path.join(WS, "image.png")
chosen = None
for w in (1280, 1008, 1024, 960, 800, 640, 512):
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
