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
    "changeNote": "v1.0.2：\n· 修好了联机状态分歧（desync）。「玛瑙的药水腰带」和「未命名·预见」的计数之前是普通私有字段，不参与同步。一局三人联机的分歧报告（RitsuLib checksum #797）显示：计数不同步时，先数到 3 瓶的那一端会单独抽共享的 CombatPotionGeneration 随机数、凭空多出一瓶迅捷药水，另一端完全看不到，于是校验和不一致。现在两个计数器都改成 [SavedProperty] 存档同步属性——原版 46 个遗物都是这么写的。\n· 八个能力 buff 的名称不再显示「未命名·xx」占位符，改成对应卡牌的名字：冰刃连斩 / 剑之所指 / 她眼中的世界 / 趁势而动 / 回应愿景之心 / 凯旋之路 / 临危不乱 / 幻想纯爱。\n· 自查新增两条断言：必须同步的计数器是否真的标了 [SavedProperty]，以及能力名不得还是占位符——以后再犯会直接在日志里报错。\n· 工坊说明已改为中英双语，并使用 Steam 支持的富文本格式。",
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
