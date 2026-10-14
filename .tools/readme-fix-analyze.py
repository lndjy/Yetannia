#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derive the real card facts from the mod's own sources. Writes UTF-8 output."""
import os, re, glob, json, collections, io

ROOT = r"D:\桌面\sts2mod"
CARDS = os.path.join(ROOT, "Yetannia", "Code", "Cards")
RELICS = os.path.join(ROOT, "Yetannia", "Code", "Relics")
CHAR = os.path.join(ROOT, "Yetannia", "Code", "Character")

out = io.StringIO()

def w(s=""):
    out.write(s + "\n")

# ---------- cards ----------
files = sorted(glob.glob(os.path.join(CARDS, "*.cs")))
w("=== card .cs files: %d ===" % len(files))

rows = []
for f in files:
    src = open(f, encoding="utf-8").read()
    base = os.path.basename(f)[:-3]
    # base(...) constructor call: base(cost, CardType.X, CardRarity.Y, TargetType.Z)
    m = re.search(r":\s*base\(\s*([^)]*?)\)", src, re.S)
    cost = typ = rar = None
    if m:
        args = [a.strip() for a in m.group(1).split(",")]
        if len(args) >= 3:
            cost = args[0]
            typ = args[1]
            rar = args[2]
    # multiplayer constraint
    mp = None
    mm = re.search(r"MultiplayerConstraint\s*=>\s*([^;]+);", src, re.S)
    if mm:
        mp = " ".join(mm.group(1).split())
    # Chinese display name: the first string literal in the Chinese CardLoc(...)
    cn = None
    cm = re.search(r"Chinese\s*=\s*new CardLoc\(\s*\n?\s*\"([^\"]*)\"", src)
    if cm:
        cn = cm.group(1)
    # class name
    cm2 = re.search(r"public\s+(?:sealed\s+)?class\s+(\w+)\s*:", src)
    cls = cm2.group(1) if cm2 else base
    rows.append(dict(file=base, cls=cls, cost=cost, type=typ, rarity=rar, mp=mp, cn=cn))

w()
w("=== per-card ===")
for r in rows:
    w("%-30s cls=%-30s cost=%-12s type=%-24s rarity=%-22s cn=%-10s mp=%s" % (
        r["file"], r["cls"], r["cost"], r["type"], r["rarity"], r["cn"], r["mp"]))

# exclude the abstract base itself (no `class X : YetanniaCard` w/ concrete base call)
concrete = [r for r in rows if r["rarity"] and r["type"]]
w()
w("=== concrete cards: %d ===" % len(concrete))
w("files without a parsed base(...) rarity: %s" % [r["file"] for r in rows if not r["rarity"]])

def norm(v):
    return v.replace("CardType.", "").replace("CardRarity.", "").strip() if v else v

w()
w("--- rarity counts (from code) ---")
c = collections.Counter(norm(r["rarity"]) for r in concrete)
for k in sorted(c): w("  %-12s %d" % (k, c[k]))
w("  TOTAL %d" % sum(c.values()))

w()
w("--- type counts (from code) ---")
t = collections.Counter(norm(r["type"]) for r in concrete)
for k in sorted(t): w("  %-12s %d" % (k, t[k]))
w("  TOTAL %d" % sum(t.values()))

w()
w("--- rarity x type ---")
rt = collections.Counter((norm(r["rarity"]), norm(r["type"])) for r in concrete)
for k in sorted(rt): w("  %-12s %-12s %d" % (k[0], k[1], rt[k]))

w()
w("--- multiplayer-constrained cards ---")
mps = [r for r in concrete if r["mp"]]
for r in mps:
    w("  %-10s %-30s rarity=%-14s type=%-10s mp=%s" % (r["cn"], r["cls"], norm(r["rarity"]), norm(r["type"]), r["mp"]))
w("  count = %d" % len(mps))

w()
w("--- distinct MultiplayerConstraint expressions ---")
for k, v in collections.Counter(r["mp"] for r in concrete if r["mp"]).items():
    w("  %s  x%d" % (k, v))

w()
w("--- any other use of CardMultiplayerConstraint in Cards/ ---")
for f in files:
    src = open(f, encoding="utf-8").read()
    if "CardMultiplayerConstraint" in src and "MultiplayerConstraint =>" not in src:
        w("  %s" % os.path.basename(f))

# ---------- placeholder names ----------
w()
w("=== placeholder (\u672a\u547d\u540d) strings anywhere under Yetannia/Code ===")
ph_hits = collections.defaultdict(list)
for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "Yetannia", "Code")):
    for fn in filenames:
        if not fn.endswith(".cs"):
            continue
        p = os.path.join(dirpath, fn)
        src = open(p, encoding="utf-8").read()
        for i, line in enumerate(src.splitlines(), 1):
            if "\u672a\u547d\u540d" in line:
                rel = os.path.relpath(p, ROOT)
                ph_hits[rel].append((i, line.strip()))

for rel in sorted(ph_hits):
    w("-- %s" % rel)
    for i, line in ph_hits[rel]:
        w("   %4d  %s" % (i, line))

# ---------- relics ----------
w()
w("=== Relics ===")
if os.path.isdir(RELICS):
    for f in sorted(glob.glob(os.path.join(RELICS, "*.cs"))):
        src = open(f, encoding="utf-8").read()
        cls = re.search(r"public\s+(?:sealed\s+)?class\s+(\w+)", src)
        names = re.findall(r"new RelicLoc\(\s*\n?\s*\"([^\"]*)\"", src)
        title = re.search(r"public\s+override\s+string\s+Title\s*=>\s*\"([^\"]*)\"", src)
        w("-- %s  cls=%s" % (os.path.basename(f), cls.group(1) if cls else "?"))
        if title: w("   Title => %s" % title.group(1))
        for n in names: w("   loc string: %s" % n)
else:
    w("  (no Relics dir)")

# ---------- character ----------
w()
w("=== Character dir listing ===")
if os.path.isdir(CHAR):
    for f in sorted(glob.glob(os.path.join(CHAR, "*"))):
        w("  %s" % os.path.basename(f))
else:
    w("  (no Character dir)")

# ---------- scenes ----------
w()
w("=== .tools/pckproject scenes ===")
sd = os.path.join(ROOT, ".tools", "pckproject", "Yetannia", "scenes")
if os.path.isdir(sd):
    for dirpath, dirnames, filenames in os.walk(sd):
        for fn in sorted(filenames):
            w("  %s" % os.path.relpath(os.path.join(dirpath, fn), sd))
else:
    w("  (missing %s)" % sd)

open(os.path.join(ROOT, ".tools", "readme-fix-analyze.txt"), "w", encoding="utf-8").write(out.getvalue())
print("written", len(out.getvalue()), "chars")
