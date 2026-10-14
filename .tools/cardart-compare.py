# cardart-compare.py — which of Yetannia's cards have art, and which are still missing.
#
# The user supplies card art as PNGs named after the card's Chinese name, dropped in
# `.tools/cardart/`. This compares that set against the authoritative card list.
#
# The card list is read from README.md's generated table (between the BEGIN/END CARD TABLE
# markers, produced by .tools/cards-xlsx.js) because that table is generated from the mod's own
# card classes. It prints the table's header and first rows so the column layout is visible rather
# than assumed -- if the generator's format changes, this fails loudly instead of silently
# comparing the wrong column.
#
# usage: python .tools/cardart-compare.py
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ART = os.path.join(HERE, "cardart")
README = os.path.join(ROOT, "README.md")

# ---------------------------------------------------------------- art
art = {}
for f in os.listdir(ART):
    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        art[os.path.splitext(f)[0]] = f
print(f"art files: {len(art)}")

# ---------------------------------------------------------------- card list
with open(README, encoding="utf-8") as fh:
    lines = fh.read().splitlines()

begin = next((i for i, l in enumerate(lines) if "BEGIN CARD TABLE" in l), None)
end = next((i for i, l in enumerate(lines) if "END CARD TABLE" in l), None)
if begin is None or end is None:
    sys.exit("README card-table markers not found — refusing to guess")

table = lines[begin + 1:end]
print("\n--- card table head (to confirm the columns) ---")
for l in table[:6]:
    print("   ", l)

# Rows look like markdown table rows; the card name is the first non-empty cell.
rows = [l for l in table if l.strip().startswith("|")]
if not rows:
    sys.exit("no markdown rows found in the card table")

header = [c.strip() for c in rows[0].strip("|").split("|")]
print("\nheader cells:", header)
name_col = 0
for i, h in enumerate(header):
    if any(k in h for k in ("名称", "卡名", "名字", "name", "Name")):
        name_col = i
        break
print("using column", name_col, "->", header[name_col])

cards = []
for r in rows[1:]:
    cells = [c.strip() for c in r.strip("|").split("|")]
    if len(cells) <= name_col:
        continue
    nm = re.sub(r"[*`\[\]]", "", cells[name_col]).strip()
    if nm and not set(nm) <= set("-: "):
        cards.append(nm)

# The name cell is "<中文名> <EnglishClassName>" (e.g. "打击 YetanniaStrike"), so split it into the
# Chinese part and the ASCII part and match art against EITHER -- card art is named after the Chinese
# name, but a differently-named file should still line up rather than be reported as missing.
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
cardinfo = []
skipped = []
for nm in cards:
    zh = "".join(ch for ch in nm if CJK.match(ch) or ch in "·・")
    en = "".join(ch for ch in nm if ch.isascii() and (ch.isalnum() or ch == "_"))
    # The table repeats its header row once per rarity section, so a repeated header lands here as a
    # 1-2 char "name" with no class name. A real card always has an English class name -- drop the
    # rest rather than reporting them as missing art.
    if not en:
        skipped.append(nm)
        continue
    cardinfo.append((nm, zh.strip(), en.strip()))

print(f"\nrows skipped as headers/section noise: {len(skipped)} -> {skipped}")

# de-duplicate by the pair, preserving order
seen, uniq = set(), []
for t in cardinfo:
    k = (t[1], t[2])
    if k in seen:
        continue
    seen.add(k)
    uniq.append(t)
cardinfo = uniq
print(f"\ncards parsed: {len(cardinfo)}")
print("--- first 4 parsed (zh | en) ---")
for _, zh, en in cardinfo[:4]:
    print(f"    zh={zh!r} en={en!r}")


def norm(s):
    """NFKC + strip spaces/punctuation so a stray full-width char or trailing space still matches."""
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\s·・、,，。.．\-_]+", "", s)


art_by_norm = {norm(k): k for k in art}
matched, missing = {}, []
for nm, zh, en in cardinfo:
    k = art_by_norm.get(norm(zh)) or art_by_norm.get(norm(en))
    if k:
        matched[nm] = k
    else:
        missing.append((zh, en, nm))

art_used = set(matched.values())
unused = [k for k in art if k not in art_used]

# Write the result as UTF-8 so it can be read without the console's codepage mangling it.
outp = os.path.join(HERE, "cardart-report.md")
with open(outp, "w", encoding="utf-8") as fh:
    fh.write("# 卡图比对 / card art vs card table\n\n")
    fh.write(f"- 图集文件: **{len(art)}**\n- 表中卡数: **{len(cardinfo)}**\n")
    fh.write(f"- 已配到图: **{len(matched)}**\n- **缺图: {len(missing)}**\n")
    fh.write(f"- 有图但表中无此卡: {len(unused)}\n\n")
    fh.write("## 缺图（按表中顺序）\n\n")
    fh.write("| 中文名 | 英文类名 |\n|---|---|\n")
    for zh, en, _ in missing:
        fh.write(f"| {zh or '(解析为空)'} | {en} |\n")
    if unused:
        fh.write("\n## 有图但没配到卡\n\n")
        for k in sorted(unused):
            fh.write(f"- {k}\n")
    fh.write("\n## 已配到图（中文名 -> 文件名）\n\n")
    for nm, k in matched.items():
        fh.write(f"- {nm}  ->  {k}.png\n")
print(f"\nwrote {outp}")
print(f"cards={len(cardinfo)} matched={len(matched)} MISSING={len(missing)} unused_art={len(unused)}")
