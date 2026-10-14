#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final safety scan + diff summary for the docs-only change."""
import io, os, re, difflib

ROOT = r"D:\桌面\sts2mod"
out = io.StringIO()
def w(s=""): out.write(s + "\n")

new_help = open(os.path.join(ROOT, ".tools", "mod-readme.txt"), "rb").read()
old_help = open(os.path.join(ROOT, ".tools", "readme-fix-backup-mod-readme.txt"), "rb").read()
new_md = open(os.path.join(ROOT, "README.md"), "rb").read()
old_md = open(os.path.join(ROOT, ".tools", "readme-fix-backup-README.md"), "rb").read()

w("=== encoding sanity ===")
for name, b in (("mod-readme.txt", new_help), ("README.md", new_md)):
    w("%-16s bytes=%-7d BOM=%s  strict-utf8=%s  U+FFFD=%d  lone-surrogates=%d" % (
        name, len(b), b[:3] == b"\xef\xbb\xbf",
        (lambda: (b.decode("utf-8"), True)[1])(), b.decode("utf-8").count("\ufffd"),
        b.decode("utf-8", "surrogatepass").count("\ud800")))
    # mojibake smoke test: common GBK-misread artifacts
    t = b.decode("utf-8")
    w("%-16s contains 'æ'/'ç'/'ä' mojibake letters: %s" % (name, any(c in t for c in "æçäåéè")))

w()
w("=== forbidden/stale strings in the SHIPPED .tools/mod-readme.txt ===")
t = new_help.decode("utf-8")
for pat in ["pdb", "PDB", "60 张", "55 张", "5 张", "15 张", "未命名·薪火", "未命名·同调",
            "未命名·共鸣", "未命名·时之礼", "两张自制图", "燃烧之血", "共用"]:
    hits = [i + 1 for i, l in enumerate(t.splitlines()) if pat in l]
    w("  %-16s %s" % (pat, ("lines %s" % hits) if hits else "absent"))

w()
w("=== forbidden/stale strings left in README.md (outside the generated markers) ===")
md = new_md.decode("utf-8")
i = md.index("<!-- BEGIN CARD TABLE"); j = md.index("<!-- END CARD TABLE -->")
outside = md[:i] + md[j:]
for pat in ["burning_blood", "card pool : 39", "新增 5 张联机专属", "5 张联机专属牌",
            "未命名·薪火", "未命名·同调", "未命名·共鸣", "未命名·时之礼"]:
    hits = [k + 1 for k, l in enumerate(outside.splitlines()) if pat in l]
    w("  %-22s %s" % (pat, ("lines %s" % hits) if hits else "absent"))
w("  'Yetannia.pdb' anywhere in README.md: %s" % ("Yetannia.pdb" in md))
w("  'Yetannia.pdb' inside a 4-file table row: %s" % bool(re.search(r"^\|\s*`Yetannia\.pdb`", md, re.M)))

w()
w("######## DIFF: .tools/mod-readme.txt (%d -> %d bytes) ########" % (len(old_help), len(new_help)))
w("".join(difflib.unified_diff(
    old_help.decode("utf-8").splitlines(True), new_help.decode("utf-8").splitlines(True),
    "mod-readme.txt.old", "mod-readme.txt.new", n=1)))

w()
w("######## DIFF: README.md (%d -> %d bytes) ########" % (len(old_md), len(new_md)))
w("".join(difflib.unified_diff(
    old_md.decode("utf-8").splitlines(True), new_md.decode("utf-8").splitlines(True),
    "README.md.old", "README.md.new", n=1)))

open(os.path.join(ROOT, ".tools", "readme-fix-final.txt"), "w", encoding="utf-8").write(out.getvalue())
print("ok")
