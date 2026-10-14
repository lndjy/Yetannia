#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-check: code card classes <-> README.md generated card table <-> packed art."""
import os, re, glob, collections, io

ROOT = r"D:\桌面\sts2mod"
CARDS = os.path.join(ROOT, "Yetannia", "Code", "Cards")
README = os.path.join(ROOT, "README.md")
ART = os.path.join(ROOT, ".tools", "pckproject", "Yetannia", "images", "card_portraits")

out = io.StringIO()
def w(s=""): out.write(s + "\n")

# ---- code ----
code = {}
for f in sorted(glob.glob(os.path.join(CARDS, "*.cs"))):
    src = open(f, encoding="utf-8").read()
    m = re.search(r"public\s+(?:sealed\s+)?(?:abstract\s+)?class\s+(\w+)\s*:\s*YetanniaCard", src)
    if not m: continue
    cls = m.group(1)
    b = re.search(r":\s*base\(\s*([^)]*?)\)", src, re.S)
    if not b: continue
    args = [a.strip() for a in b.group(1).split(",")]
    if len(args) < 4 or args[0] == "int cost":
        continue  # the abstract base itself
    typ, rar = args[1].replace("CardType.", ""), args[2].replace("CardRarity.", "")
    mp = None
    mm = re.search(r"MultiplayerConstraint\s*=>\s*([^;]+);", src, re.S)
    if mm: mp = "MultiplayerOnly" in mm.group(1)
    cn = None
    cm = re.search(r"Chinese\s*=\s*new CardLoc\(\s*\n?\s*\"([^\"]*)\"", src)
    if cm: cn = cm.group(1)
    code[cls] = dict(typ=typ, rar=rar, mp=bool(mp), cn=cn, file=os.path.basename(f))

w("=== code cards: %d ===" % len(code))
w("rarity: %s" % dict(collections.Counter(v["rar"] for v in code.values())))
w("type  : %s" % dict(collections.Counter(v["typ"] for v in code.values())))
w("mp    : %d -> %s" % (sum(1 for v in code.values() if v["mp"]),
                        sorted(v["cn"] for v in code.values() if v["mp"])))

def snake(n):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", n).lower()

# ---- art coverage ----
art = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ART, "*.png"))}
art.discard("test"); art.discard("test2"); art.discard("blank")
stems = {snake(c) for c in code}
w()
w("=== art coverage ===")
w("card portrait pngs (excl test/test2/blank): %d" % len(art))
w("distinct card name stems                 : %d" % len(stems))
w("cards WITHOUT their own art file         : %s" % sorted(stems - art))
w("art files with no card                   : %s" % sorted(art - stems))

# ---- README table ----
txt = open(README, encoding="utf-8").read()
i = txt.index("<!-- BEGIN CARD TABLE")
j = txt.index("<!-- END CARD TABLE -->")
tbl = txt[i:j]
w()
w("=== README.md card table ===")
head = re.search(r"\*\*共 (\d+) 张。\*\*", tbl)
w("headline: 共 %s 张" % (head.group(1) if head else "?"))
sections = re.findall(r"\*\*([^\n*]+?)（([^）]+)），(\d+) 张\*\*", tbl)
tot = 0
for label, rar, n in sections:
    w("  section %-4s %-14s claims %s" % (label, rar, n))
    tot += int(n)
w("  sum of section headers = %d" % tot)

rows = [l for l in tbl.splitlines() if l.startswith("| ") and not l.startswith("|---")]
rows = [l for l in rows if "卡 | 费" not in l]
w("  data rows in table = %d" % len(rows))
# per-row parse
rowrar = collections.Counter()
rowtyp = collections.Counter()
# walk sections in order
cur = None
sect_counts = collections.Counter()
for l in tbl.splitlines():
    s = re.match(r"\*\*[^（]+（(\w+)），(\d+) 张\*\*", l)
    if s:
        cur = s.group(1); continue
    if l.startswith("| ") and "卡 | 费" not in l and not l.startswith("|---"):
        cells = [c.strip() for c in l.strip("|").split("|")]
        if len(cells) >= 4:
            rowrar[cur] += 1
            rowtyp[cells[2]] += 1
w("  rows per section: %s" % dict(rowrar))
w("  rows per type   : %s" % dict(rowtyp))

# ---- per-row comparison against code ----
w()
w("=== per-card comparison (README row name+class vs code) ===")
mismatch = []
seen = set()
for l in tbl.splitlines():
    m = re.match(r"\|\s*([^`]+?)\s*`(\w+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", l)
    if not m: continue
    cn, cls, cost, typ = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()
    if cls not in code:
        mismatch.append("README row %s/%s not a code card class" % (cn, cls)); continue
    seen.add(cls)
    c = code[cls]
    typc = {"攻击": "Attack", "技能": "Skill", "能力": "Power", "状态": "Status"}.get(typ, typ)
    if c["cn"] != cn:
        mismatch.append("%s: README name %r vs code %r" % (cls, cn, c["cn"]))
    if typc != c["typ"]:
        mismatch.append("%s: README type %r vs code %r" % (cls, typ, c["typ"]))
w("rows matched to a code class: %d" % len(seen))
w("code classes missing from README rows: %s" % sorted(set(code) - seen))
w("mismatches: %d" % len(mismatch))
for m in mismatch: w("   " + m)

open(os.path.join(ROOT, ".tools", "readme-fix-crosscheck.txt"), "w", encoding="utf-8").write(out.getvalue())
print("ok", len(out.getvalue()))
