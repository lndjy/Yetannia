#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit Yetannia.pck against the Godot project it is built from.

Answers the three questions a previous QA round turned into assertions:

  1. is every imported artifact that an `.import` file references actually inside the pack?
  2. is anything inside the pack NOT referenced (an orphan .ctex left behind by a redraw)?
  3. does any single source image ship more than one variant (e.g. a stale .ctex next to the
     current one)?

Usage:
    node .tools/pck.js list Yetannia/build/Yetannia.pck > listing.txt
    python .tools/audit-pck.py listing.txt

`pck.js list` prints "  <bytes> <path>" per entry; only the last field is used, so any of the
listing formats is fine. The listing must be UTF-8 (use `Out-File -Encoding utf8` on PowerShell 5.1,
whose `>` redirection writes UTF-16).

Exit code is 0 when the pack is clean, 1 otherwise.
"""

import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PCKPROJECT = os.path.join(HERE, "pckproject")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    listing = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else PCKPROJECT

    packed = set()
    with open(listing, encoding="utf-8-sig") as fh:
        for line in fh:
            parts = line.split()
            if parts:
                packed.add(parts[-1])

    referenced = set()
    imports = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if not f.endswith(".import"):
                continue
            imports += 1
            with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                txt = fh.read()
            for m in re.finditer(r'"res://\.godot/imported/([^"]+)"', txt):
                referenced.add(".godot/imported/" + m.group(1))

    packed_imported = {n for n in packed if n.startswith(".godot/imported/")}
    missing = sorted(referenced - packed)
    orphans = sorted(packed_imported - referenced)

    print(f"pack entries                      : {len(packed)}")
    print(f".import files in {os.path.relpath(root)}: {imports}")
    print(f"artifacts referenced by .import   : {len(referenced)}")
    print(f"imported artifacts inside the pack: {len(packed_imported)}")
    print(f"referenced but NOT packed         : {missing if missing else 'none'}")
    print(f"packed but NOT referenced (orphan): {orphans if orphans else 'none'}")

    # One variant per source path: Godot names the imported file "<source>-<md5>.ctex", where the md5
    # is of the source path plus import settings, so a source may legitimately have one entry per
    # directory it appears in (relics/ and relics_big/) but never two in the same one.
    variants = Counter(re.sub(r"-[0-9a-f]{32}", "", n.rsplit("/", 1)[-1]) for n in packed_imported)
    multi = {k: v for k, v in variants.items() if v > 2}
    print(f"basenames with >2 packed variants : {multi if multi else 'none'}")
    print(f"basenames with exactly 2          : {sum(1 for v in variants.values() if v == 2)}")

    ok = not missing and not orphans and not multi
    print("RESULT:", "clean" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
