#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the repackaged release zip and the docs-only change."""
import hashlib, io, os, zipfile, shutil

ROOT = r"D:\桌面\sts2mod"
MODS = r"D:\SteamLibrary\steamapps\common\Slay the Spire 2\mods\Yetannia"
ZIP = os.path.join(ROOT, "Yetannia-v1.0.0.zip")
out = io.StringIO()
def w(s=""): out.write(s + "\n")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()

EXPECT = {
    "dll": "211F1E507DC6197266C9A4E50380A006269C14417D8DE78C49A67D6D55D9ADD5",
    "pck": "366C4CF60D66CFBDDA8E8E1878C804CD4D4834D3368E9A91D6E5EE8C165B358F",
}

files = {
    "dll": os.path.join(ROOT, "Yetannia", "bin", "Release", "Yetannia.dll"),
    "pck": os.path.join(ROOT, "Yetannia", "build", "Yetannia.pck"),
    "json": os.path.join(ROOT, "Yetannia", "Yetannia.json"),
    "readme_src": os.path.join(ROOT, ".tools", "mod-readme.txt"),
    "readme_md": os.path.join(ROOT, "README.md"),
}

w("=== workspace artifacts ===")
for k, p in files.items():
    w("%-11s %-60s %10d  %s" % (k, os.path.relpath(p, ROOT), os.path.getsize(p), sha(p)))

w()
w("=== byte-identity of the binaries (must equal the stated QA-47 hashes) ===")
ok = True
for k in ("dll", "pck"):
    got = sha(files[k])
    same = got == EXPECT[k]
    ok &= same
    w("%-4s %s   expected %s   %s" % (k, got, EXPECT[k], "IDENTICAL" if same else "*** CHANGED ***"))
w("BINARIES UNCHANGED: %s" % ("YES" if ok else "NO"))

w()
w("=== the release zip ===")
w("path   %s" % ZIP)
w("size   %d bytes" % os.path.getsize(ZIP))
w("sha256 %s" % sha(ZIP))

with zipfile.ZipFile(ZIP) as z:
    names = z.namelist()
    w()
    w("entries: %d" % len(names))
    for n in names:
        w("   %-28s %10d" % (n, z.getinfo(n).file_size))
    tops = sorted({n.split("/")[0] for n in names})
    w("top-level names: %s" % tops)
    w("directory entries: %d" % sum(1 for n in names if n.endswith("/")))
    w("any .pdb entry: %s" % any(n.lower().endswith(".pdb") for n in names))
    w("any .deps.json entry: %s" % any(n.lower().endswith(".deps.json") for n in names))
    w("exactly 4 entries under Yetannia/: %s" % (len([n for n in names if n.startswith("Yetannia/")]) == 4))

    w()
    w("=== each entry vs the staged/workspace source ===")
    pairs = [
        ("Yetannia/Yetannia.json", files["json"]),
        ("Yetannia/Yetannia.dll", files["dll"]),
        ("Yetannia/Yetannia.pck", files["pck"]),
        ("Yetannia/README.txt", files["readme_src"]),
    ]
    for n, src in pairs:
        zb = z.read(n)
        sb = open(src, "rb").read()
        w("%-24s zip=%s  src=%s  %s" % (
            n, hashlib.sha256(zb).hexdigest().upper()[:16],
            hashlib.sha256(sb).hexdigest().upper()[:16],
            "IDENTICAL" if zb == sb else "*** DIFFERENT ***"))
    w()
    w("zip README.txt == .tools/mod-readme.txt : %s" % (z.read("Yetannia/README.txt") == open(files["readme_src"], "rb").read()))

w()
w("=== installed mods folder ===")
w("path %s" % MODS)
inst = sorted(os.listdir(MODS))
w("files: %s" % inst)
for f in inst:
    p = os.path.join(MODS, f)
    w("   %-18s %10d  %s" % (f, os.path.getsize(p), sha(p)))
w()
w("installed set == zip contents : %s" % (
    (lambda z2: sorted(inst) == sorted(n.split("/", 1)[1] for n in z2.namelist()) and
     all(z2.read("Yetannia/" + f) == open(os.path.join(MODS, f), "rb").read() for f in inst))(
        zipfile.ZipFile(ZIP))))
w("installed has no .pdb : %s" % (not any(f.lower().endswith(".pdb") for f in inst)))

w()
w("=== README.md card-table region ===")
t = open(files["readme_md"], encoding="utf-8").read()
i = t.index("<!-- BEGIN CARD TABLE"); j = t.index("<!-- END CARD TABLE -->")
tbl = t[i:j]
w("markers present: True")
w("rows: %d" % sum(1 for l in tbl.splitlines()
                   if l.startswith("| ") and "卡 | 费" not in l and not l.startswith("|---")))
w("headline present: %s" % ("**共 82 张。**" in t[i:j]))
w("generator reported it 'already up to date' (unchanged) - see the packaging output")

open(os.path.join(ROOT, ".tools", "readme-fix-verify.txt"), "w", encoding="utf-8").write(out.getvalue())
print("ok")
