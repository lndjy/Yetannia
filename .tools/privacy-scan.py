#!/usr/bin/env python3
"""privacy-scan.py -- the section-8 security and privacy gate of docs/RELEASE-WORKFLOW.md, as a command.

Scans the artifacts that are about to be published (the release zip, or any file/directory) for
builder-identity markers in ASCII **and** both UTF-16 byte orders, and for filenames that must never
ship. Exits non-zero on any hit, so it can gate a release.

WHY THIS EXISTS AS A SCRIPT. Every marker below has already been shipped by accident in this project
once: a CodeView debug record put the absolute path of the builder's .pdb (and therefore the local user
name) into the released .dll, and a .gitignore whose trailing comments were inert put a settings backup
containing a Steam account id into the staging area. Both were invisible to the checks being done at the
time, because both were done by pattern-matching readable ASCII in the wrong file.

WHY THE PRINTABLE-RUN RULE MATTERS. A naive "does this 40 MB blob contain `X:/`" scan is worthless: a
three-byte pattern occurs thousands of times by chance in compressed binary (measured: 1136 hits in this
mod's own .pck, all noise). A path is only evidence of a leak when it sits inside a run of **readable
text**, so text patterns are only applied to convertible printable runs of at least --min-run characters,
and the run itself is printed so a human can see what actually matched.

The local user name / machine name are read from the ENVIRONMENT at run time and never hard-coded --
this file is itself published.

usage:
    python .tools/privacy-scan.py Yetannia-v1.0.1.zip
    python .tools/privacy-scan.py Yetannia/bin/Release/Yetannia.dll Yetannia/build/Yetannia.pck
    python .tools/privacy-scan.py --no-zip-shape Yetannia-v1.0.1.zip
"""
import argparse
import os
import re
import sys
import zipfile

# ------------------------------------------------------------------ markers

# Literal byte strings that indicate a debug record or a build-machine path. Each of these is long and
# shaped enough that a chance occurrence in binary is not a practical concern.
LITERAL_MARKERS = [
    b"RSDS",            # CodeView debug directory entry -> embeds the .pdb's absolute path
    b"NB10",            # the other CodeView flavour
    b"\\Users\\",
    b"/Users/",
    b"\\obj\\Release",
    b"/obj/Release",
    b"\\obj\\Debug",
    b"\\.nuget\\",
    b"\\Desktop\\",
]

# Regexes, applied only to printable runs. `.pdb` and `AppData` are deliberately NOT markers: both occur
# legitimately in the shipped README (which documents installing into `%APPDATA%\SlayTheSpire2\mods`), and
# mentioning a string is not a leak. FORBIDDEN_NAMES refuses a real .pdb file instead.
TEXT_PATTERNS = [
    # The negative lookbehind is load-bearing: without it the `s:/` of every Godot `res://` path in the
    # .pck matches, which produced hundreds of false positives on a clean artifact. The `looks_like_path`
    # post-filter below then removes the remaining binary noise (a bare `X:\` occurs by chance inside
    # long printable runs of compressed data -- measured: one hit, `i:\2$cF*!p`, on a clean .pck).
    (re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s\x00]{2,}"), "an absolute drive-letter path",
     "path"),
    (re.compile(r"7656119\d{10}"), "a SteamID64", None),
    (re.compile(r"\b\d{17}\b"), "a 17-digit account/Steam id", None),
    (re.compile(r"\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_$]"), "a UNC path", None),
]


# Matches that are public knowledge rather than identity. 76561197960265728 is Valve's SteamID64 base
# offset -- a universal constant that appears in every "account id -> SteamID64" formula, including the
# one this repository uses to avoid hard-coding an account, so flagging it would train the reader to
# ignore the SteamID check.
ALLOWED_MATCHES = {"76561197960265728"}


def looks_like_path(text):
    """True when a `X:\\...` match has enough structure to be a real path rather than binary noise.

    A real build path is deep (`D:\\<dir>\\<proj>\\obj\\Release\\Yetannia.pdb`) or has a file extension
    (`D:\\file.txt`); random binary produces neither.
    """
    tail = text[3:]
    seps = tail.count("\\") + tail.count("/")
    return (seps >= 1 and "." in tail) or seps >= 2

# Filenames that must not appear in anything that ships (inside zips, and on disk).
FORBIDDEN_NAMES = re.compile(
    r"(\.pdb$|\.bak$|\.orig$|~$|^Thumbs\.db$|^\.DS_Store$|settings\.save|\.log$"
    r"|\.token$|\.cookie$|credentials|steam_appid)",
    re.IGNORECASE,
)

PRINTABLE = set(range(0x20, 0x7F))  # documentation of what "printable" means below

# Fast run extractors. Doing this with a Python byte loop over a 40 MB .pck took minutes; the equivalent
# regexes run in C. A UTF-16 run is a sequence of printable ASCII code units, i.e. `XX 00` little-endian
# or `00 XX` big-endian -- NOT a raw run of printable bytes, which is why each order needs its own
# pattern (and why a naive ASCII-only scan misses every UTF-16 leak).
RUN_PATTERNS = {
    "ascii": (re.compile(rb"[\x20-\x7e]{8,}"), "ascii"),
    "utf-16le": (re.compile(rb"(?:[\x20-\x7e]\x00){8,}"), "utf-16-le"),
    "utf-16be": (re.compile(rb"(?:\x00[\x20-\x7e]){8,}"), "utf-16-be"),
}


def env_markers():
    """Markers derived from this machine at run time (never hard-coded -- this file is published)."""
    out = []
    for var in ("USERNAME", "USER", "COMPUTERNAME", "HOSTNAME"):
        val = os.environ.get(var)
        if val and len(val) > 2:
            out.append((val.encode("utf-8"), "%s (the local %s)" % (val, var.lower())))
    profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    if profile:
        base = os.path.basename(profile.rstrip("\\/"))
        if base and len(base) > 2:
            out.append((base.encode("utf-8"), "the home directory name"))
    return out


def runs_of(data, enc):
    """Yield the readable text of every maximal printable run of >= 8 characters.

    `enc` is one of the RUN_PATTERNS keys. For the UTF-16 orders the code units are assembled by the
    regex itself, so the result does not depend on a BOM or on a decoder's byte-order guess.
    """
    pat, codec = RUN_PATTERNS[enc]
    for m in pat.finditer(data):
        yield m.start(), m.group().decode(codec, "replace")


def scan_bytes(name, blob, findings):
    # 1) literal markers, in every encoding a compiler can emit them in
    for enc in ("ascii", "utf-16le", "utf-16be"):
        for marker in LITERAL_MARKERS + [m for m, _ in env_markers()]:
            try:
                needle = marker if enc == "ascii" else marker.decode("utf-8").encode(enc)
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            count = blob.count(needle)
            if count:
                findings.append((name, "%r x%d" % (marker.decode("utf-8", "replace"), count), enc))

    # 2) text patterns, only inside readable runs
    for enc in ("ascii", "utf-16le", "utf-16be"):
        for _off, text in runs_of(blob, enc):
            for pat, label, kind in TEXT_PATTERNS:
                for m in pat.finditer(text):
                    hit = m.group()
                    if hit in ALLOWED_MATCHES:
                        continue
                    if kind == "path" and not looks_like_path(hit):
                        continue
                    lo = max(0, m.start() - 24)
                    hi = min(len(text), m.end() + 24)
                    findings.append((name, "%s -- ...%s..." % (label, text[lo:hi]), enc))
            for var, label in env_markers():
                needle = var.decode("utf-8", "replace")
                if needle in text:
                    findings.append((name, "%s -- ...%s..." % (label, text[:80]), enc))


def check_zip_shape(name, zf, findings, notes):
    names = zf.namelist()
    tops = sorted({n.split("/", 1)[0] for n in names})
    notes.append("%s: %d entries, top level %s" % (name, len(names), tops))
    if tops != ["Yetannia"]:
        findings.append((name, "top level is %s, expected ['Yetannia']" % tops, "-"))
    for n in names:
        if n.endswith("/"):
            findings.append((name, "directory entry %s" % n, "-"))
        if FORBIDDEN_NAMES.search(os.path.basename(n)):
            findings.append((name, "forbidden filename %s" % n, "-"))


def main():
    # The Windows console is a legacy codepage (GBK here), so printing a path that contains non-ASCII
    # characters raises UnicodeEncodeError and kills the report -- which would look like a clean run to
    # anything reading only the exit status. Never let the report itself be the failure.
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--files-from",
                    help="a text file of newline-separated paths to scan as well (e.g. the output of "
                         "`git ls-files`), for checking a whole repository without a huge command line")
    ap.add_argument("--no-zip-shape", action="store_true",
                    help="skip the entry-name/top-level checks for .zip inputs")
    ap.add_argument("--quiet-notes", action="store_true")
    args = ap.parse_args()

    targets = list(args.paths)
    if args.files_from:
        with open(args.files_from, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    targets.append(line)
    if not targets:
        ap.error("no paths given")

    findings = []
    notes = []
    total = 0
    self_path = os.path.abspath(__file__)

    for path in targets:
        # This scanner's own source necessarily contains its whole marker table, so scanning it would
        # report the scanner on every run and train the reader to ignore the gate. Documented in
        # docs/RELEASE-WORKFLOW.md 8.5b.
        if os.path.isfile(path) and os.path.abspath(path) == self_path:
            notes.append("%s: skipped (the scanner's own marker table)" % path)
            continue
        if not os.path.exists(path):
            findings.append((path, "does not exist", "-"))
            continue
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as zf:
                if not args.no_zip_shape:
                    check_zip_shape(os.path.basename(path), zf, findings, notes)
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    total += 1
                    label = "%s :: %s" % (os.path.basename(path), info.filename)
                    scan_bytes(label, zf.read(info), findings)
        elif os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for f in sorted(files):
                    full = os.path.join(root, f)
                    total += 1
                    rel = os.path.relpath(full, path)
                    if FORBIDDEN_NAMES.search(f):
                        findings.append((rel, "forbidden filename", "-"))
                    with open(full, "rb") as fh:
                        scan_bytes(rel, fh.read(), findings)
        else:
            total += 1
            with open(path, "rb") as fh:
                blob = fh.read()
            # Report the path AS GIVEN, not the basename: two files in different directories can share a
            # name, and a bare basename hides which one to go and fix.
            scan_bytes(path, blob, findings)
            notes.append("%s: %d bytes scanned" % (path, len(blob)))

    if not args.quiet_notes:
        for n in notes:
            print("  note: %s" % n)
    print("scanned %d file(s) across %d input(s)" % (total, len(targets)))
    if findings:
        print("")
        print("FAIL -- %d privacy/security finding(s):" % len(findings))
        for where, what, enc in findings:
            print("  %s" % where)
            print("      %-4s %s" % (enc, what[:160]))
        return 1
    print("PASS -- no builder identity, no forbidden filename, no path-shaped string")
    return 0


if __name__ == "__main__":
    sys.exit(main())
