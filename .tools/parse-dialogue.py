#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse Yetannia's Ancient-dialogue .docx drafts into structured UTF-8 JSON.

Input : .tools/dialogue/*.docx    (a .docx is a zip; text lives in word/document.xml
                                   as <w:t> runs inside <w:p> paragraphs)
Output: .tools/dialogue/parsed.json          all NPCs, normalised
        .tools/dialogue/parsed/<npc>.json    one file per NPC
        .tools/dialogue/report.json          everything a human needs to audit the parse

Run:  python .tools/parse-dialogue.py
      python .tools/parse-dialogue.py --dump    # ASCII-safe summary (never trust a console for the text)

MEASURED FORMAT (from the real files, not assumed):

    涅奥                              <- first non-empty paragraph = NPC name
    前言：...                         <- author's note (speaker-looking, but a note)
    通用1：                           <- section heading (trailing colon optional)
    涅奥：“杀死...建筑师...”           <- "speaker：line"
    ...
    1.初次见面                        <- heading, may carry a leading "N." ordinal
    涅奥：“...”
    耶坦尼娅：“...”
                        <- a paragraph with NO colon at all is a bare line: it belongs to the
                           character (stage direction) -- the docx mixes both styles
    （达弗给耶坦尼娅看了那块玉石）

The docx is a writing draft: heading spellings vary (`重复拜访` vs `重复拜访1`), speaker
spellings have typos (`欧罗巴斯` for 欧洛巴斯, `努诺佩普` for 诺奴佩普), and one line uses a
stray double colon (`涅奥：：“...”`). All of that is normalised here, and every normalisation
is reported in report.json rather than applied silently.

The script never changes the words: it only strips the `说话人：` markup prefix, an optional
single pair of wrapping 「“…”」 quotes (--keep-quotes turns that off), and the stray extra
colon. Nothing is translated or reworded.
"""

import argparse
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

HERE = os.path.dirname(os.path.abspath(__file__))
DIALOGUE_DIR = os.path.join(HERE, "dialogue")
OUT_ALL = os.path.join(DIALOGUE_DIR, "parsed.json")
OUT_REPORT = os.path.join(DIALOGUE_DIR, "report.json")
OUT_DIR = os.path.join(DIALOGUE_DIR, "parsed")

# Canonical NPC order and the docx file each one lives in. The canonical (in-game) name is on
# the right; two of the files spell the name differently in their first paragraph (see
# SPEAKER_ALIASES below), so the file name is what identifies the NPC.
FILES = [
    ("涅奥", "涅奥.docx"),
    ("欧洛巴斯", "欧洛巴斯.docx"),
    ("佩尔", "佩尔.docx"),
    ("瓦库", "瓦库.docx"),
    ("坦克斯", "坦克斯.docx"),
    ("特兹卡塔拉", "特兹卡塔拉.docx"),
    ("诺奴佩普", "诺奴佩普.docx"),
    ("达弗", "达弗.docx"),
    ("建筑师", "建筑师.docx"),
]

CHARACTER_NAME = "耶坦尼娅"

# Heading (after normalisation) -> slot id. The slot ids are what the code generator turns into
# `AncientDialogueSet.CharacterDialogues` / `AgnosticDialogues` entries.
HEADING_SLOTS = {
    "通用1": "generic1",
    "通用2": "generic2",
    "初始见面": "first",
    "初次见面": "first",
    "首次见面": "first",
    "分支1": "first@branch1",
    "重复拜访": "repeat1",
    "重复拜访1": "repeat1",
    "重复拜访2": "repeat2",
    "第三次及其以后": "late",
    "第三次及其以后分支1": "late@branch1",
    "第三次及其以后分支2": "late@branch2",
}

# The two generic, engine-shipped button labels. Vanilla's own dialogue `.next` entries use
# short generic verbs (继续 / 回应 / 提问 / 回答); these two are the ones the `ancients` table
# ships unconditionally (THE_ARCHITECT.CONTINUE / THE_ARCHITECT.RESPOND), so reusing them means
# no new UI wording is authored here.
NEXT_CONTINUE = "THE_ARCHITECT.CONTINUE"
NEXT_RESPOND = "THE_ARCHITECT.RESPOND"

# Speaker tokens that mean "the Ancient is talking" even though they are not the canonical name
# (typos in the draft) -- recorded so the normalisation is auditable.
SPEAKER_ALIASES = {
    "欧罗巴斯": "欧洛巴斯",
    "努诺佩普": "诺奴佩普",
    "诺奴佩普": "诺奴佩普",
}

ROMAN_OR_NUM_PREFIX = re.compile(r"^\s*\d+\s*[.、]\s*")
WRAPPING_QUOTES = re.compile(r'^\s*[“"](.*)[”"]\s*$', re.S)


def paragraphs(path):
    """Plain text of every <w:p> in document.xml; <w:tab/> -> tab, <w:br/> -> newline."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    for p in root.iter(W + "p"):
        parts = []
        for node in p.iter():
            if node.tag == W + "t":
                parts.append(node.text or "")
            elif node.tag == W + "tab":
                parts.append("\t")
            elif node.tag == W + "br":
                parts.append("\n")
        yield "".join(parts)


def dump_raw(keep_quotes):
    """Write .tools/dialogue/raw-paragraphs.json: the untouched paragraph list per file.

    Kept because the *structure* is the thing that had to be reverse-engineered (mixed heading
    styles, bare stage-direction paragraphs, unbalanced quotes), and re-reading it is how a future
    round can tell a parser bug from a draft quirk without unzipping the .docx by hand.
    """
    out = {}
    for npc, filename in FILES:
        path = os.path.join(DIALOGUE_DIR, filename)
        out[npc] = [p.strip() for p in paragraphs(path) if p.strip() != ""]
    target = os.path.join(DIALOGUE_DIR, "raw-paragraphs.json")
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return target


def split_speaker(text):
    """Split one paragraph into (speaker, utterance).

    Returns (None, text) when the paragraph has no speaker prefix at all -- the docx uses a bare
    paragraph for stage directions such as （达弗给耶坦尼娅看了那块玉石）.
    A trailing-colon heading like `通用1：` comes back as ("通用1", "").
    """
    m = re.match(r"^\s*([^：:\n]{1,24})\s*[：:]+[：:]*\s*(.*)$", text, re.S)
    if not m:
        return None, text.strip()
    return m.group(1).strip(), m.group(2).strip()


def strip_quotes(text, keep, fixes=None):
    """Drop one wrapping pair of “…” quotes, or a single unmatched one.

    The draft has one line whose closing quote is missing (瓦库's 通用1). Leaving the stray
    opening quote in would show up in game, so an unbalanced wrapper is stripped too -- and
    recorded in the fixes list so the change is visible rather than silent.
    """
    if keep:
        return text
    m = WRAPPING_QUOTES.match(text)
    if m:
        return m.group(1).strip()
    if text.startswith("“") and "”" not in text:
        if fixes is not None:
            fixes.append(f"unbalanced leading “: {text!r}")
        return text[1:].strip()
    if text.endswith("”") and "“" not in text:
        if fixes is not None:
            fixes.append(f"unbalanced trailing ”: {text!r}")
        return text[:-1].strip()
    return text


def normalise_heading(raw):
    """`1.初次见面` -> 初次见面; `通用1：` -> 通用1 (the colon was eaten by split_speaker)."""
    h = ROMAN_OR_NUM_PREFIX.sub("", raw).strip().rstrip("：:").strip()
    return h


def classify_speaker(token, npc):
    """'ancient' or 'character'. Anything that is not Yetannia is the NPC speaking."""
    if token is None:
        return None
    if CHARACTER_NAME in token:
        return "character"
    return "ancient"


def parse_file(npc, filename, keep_quotes, is_architect):
    path = os.path.join(DIALOGUE_DIR, filename)
    raw_paras = [p.strip() for p in paragraphs(path)]
    paras = [p for p in raw_paras if p != ""]

    warnings = []
    notes = []
    speaker_spellings = {}
    normalisations = []
    quote_fixes = []

    if not paras:
        return {"npc": npc, "file": filename, "sections": [], "notes": [],
                "warnings": ["empty document"]}

    # paragraph 1 is the NPC's own name (possibly spelled differently from the canonical one)
    declared = paras[0]
    if declared != npc:
        normalisations.append(f"first paragraph {declared!r} != canonical {npc!r}")

    sections = []
    current = None

    if is_architect:
        # The Architect's file has no headings at all: one flat conversation. Seed the section so
        # its lines are not mistaken for author notes (which is what "line before any heading"
        # means everywhere else).
        current = {"heading": "(flat)", "slot": "architect-main", "lines": []}
        sections.append(current)

    for text in paras[1:]:
        speaker, utterance = split_speaker(text)

        if speaker is not None and utterance == "":
            # `通用1：` -- a heading written with a trailing colon
            heading = normalise_heading(speaker)
            current = {"heading": heading, "slot": HEADING_SLOTS.get(heading, "UNKNOWN"),
                       "lines": []}
            sections.append(current)
            if heading not in HEADING_SLOTS:
                normalisations.append(f"unmapped heading {heading!r}")
            continue

        if speaker is None:
            if is_architect:
                # The Architect's file is one flat conversation: every paragraph is dialogue.
                pass
            elif len(utterance) <= 40 and utterance.endswith("："):
                pass
            else:
                # A bare paragraph. When it is short and colon-free it is either a heading
                # (`初次见面`) or an author note (`前言：...` / `我的思路是...`).
                heading = normalise_heading(utterance)
                if heading in HEADING_SLOTS:
                    current = {"heading": heading, "slot": HEADING_SLOTS[heading], "lines": []}
                    sections.append(current)
                    continue
                if utterance.startswith(("前言", "我的思路")) or len(utterance) > 60:
                    notes.append(utterance)
                    continue
                # otherwise: a stage direction -> character line (see module docstring)
                if current is None:
                    current = {"heading": "(none)", "slot": "UNKNOWN", "lines": []}
                    sections.append(current)
                    warnings.append(f"line before any heading: {utterance!r}")
                current["lines"].append({"speaker": "character", "speaker_token": None,
                                         "text": strip_quotes(utterance, keep_quotes, quote_fixes)})
                continue

        # speaker + utterance
        kind = classify_speaker(speaker, npc)
        if current is None:
            # A speaker-prefixed paragraph before any heading: an author note such as `前言：...`
            notes.append(text)
            continue
        if kind == "ancient" and speaker != npc:
            speaker_spellings[speaker] = SPEAKER_ALIASES.get(speaker, speaker)
        current["lines"].append({
            "speaker": kind,
            "speaker_token": speaker,
            "text": strip_quotes(utterance, keep_quotes, quote_fixes),
        })

    # `通用1`/`通用2` are the character-agnostic flavour lines. Vanilla stores those as
    # `{ANCIENT}.talk.ANY.{n}-0r.ancient` -- always the Ancient speaking, even when the draft
    # wrote the line as bare narration. Force that here so the two cannot disagree.
    for s in sections:
        if s["slot"] in ("generic1", "generic2"):
            for ln in s["lines"]:
                if ln["speaker"] != "ancient":
                    normalisations.append(
                        f"{s['heading']}: forced speaker ancient (draft said {ln['speaker']})")
                ln["speaker"] = "ancient"

    # drop empty sections (a heading with a dash-only or empty body)
    sections = [s for s in sections if s["lines"] or s["slot"] != "UNKNOWN"]

    if is_architect:
        # No headings at all: the seeded section already holds the whole conversation.
        sections = [s for s in sections if s["lines"]]

    if speaker_spellings:
        normalisations.append("speaker spellings treated as the Ancient: " +
                              ", ".join(f"{k}->{v}" for k, v in sorted(speaker_spellings.items())))

    return {
        "npc": npc,
        "file": filename,
        "sections": sections,
        "notes": notes,
        "normalisations": normalisations + quote_fixes,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", action="store_true", help="print an ASCII-safe summary")
    ap.add_argument("--keep-quotes", action="store_true",
                    help="keep the wrapping “…” of each line (default: strip it)")
    ap.add_argument("--raw", action="store_true",
                    help="also write dialogue/raw-paragraphs.json (untouched paragraph lists)")
    args = ap.parse_args()

    if not os.path.isdir(DIALOGUE_DIR):
        sys.exit(f"no such directory: {DIALOGUE_DIR}")

    if args.raw:
        print(f"wrote {dump_raw(args.keep_quotes)}")

    os.makedirs(OUT_DIR, exist_ok=True)
    parsed = {}
    report = {"files": [], "unknown_headings": [], "no_speaker_lines": [],
              "empty_sections": [], "multi_line_generic": []}

    for npc, filename in FILES:
        data = parse_file(npc, filename, args.keep_quotes, is_architect=(npc == "建筑师"))
        parsed[npc] = data
        for s in data["sections"]:
            if s["slot"] == "UNKNOWN":
                report["unknown_headings"].append({"npc": npc, "heading": s["heading"]})
            if s["slot"] in ("generic1", "generic2") and len(s["lines"]) != 1:
                report["multi_line_generic"].append(
                    {"npc": npc, "heading": s["heading"], "lines": len(s["lines"])})
            for ln in s["lines"]:
                if ln["speaker_token"] is None:
                    report["no_speaker_lines"].append(
                        {"npc": npc, "heading": s["heading"], "text": ln["text"][:40]})
        report["files"].append({
            "npc": npc,
            "file": filename,
            "sections": [{"heading": s["heading"], "slot": s["slot"],
                          "lines": len(s["lines"]),
                          "speakers": [l["speaker"] for l in s["lines"]]}
                         for s in data["sections"]],
            "notes": data["notes"],
            "normalisations": data["normalisations"],
            "warnings": data["warnings"],
        })

        with open(os.path.join(OUT_DIR, npc + ".json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    with open(OUT_ALL, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(parsed, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    total = sum(len(s["lines"]) for d in parsed.values() for s in d["sections"])
    print(f"parsed {len(parsed)} file(s), "
          f"{sum(len(d['sections']) for d in parsed.values())} section(s), {total} dialogue line(s)")
    print(f"  keep_quotes={args.keep_quotes}")
    print(f"  wrote {OUT_ALL}")
    print(f"  wrote {OUT_REPORT}")

    if args.dump:
        for npc, d in parsed.items():
            print(f"\n=== {npc} ({d['file']}) ===")
            for s in d["sections"]:
                print(f"  [{s['heading']}] slot={s['slot']} {len(s['lines'])} line(s)")
                for ln in s["lines"]:
                    print(f"      {ln['speaker'][:4]:9s} {len(ln['text']):3d} chars")
            for n in d["notes"]:
                print(f"  note: {len(n)} chars")
            for w in d["warnings"]:
                print(f"  !! {w}")

    for npc, d in parsed.items():
        for w in d["warnings"]:
            print(f"WARNING {npc}: {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
