# Verifies the Workshop description before (and optionally after) an upload.
#
# WHY THIS EXISTS -- the v1.0.6 incident: the Chinese half of the description carried its 更新记录 block at
# the very END of the Chinese section, far below the fold, so readers (and reviewers) concluded the
# Chinese description had no update notes at all while the English half clearly had a Changelog. The
# rule that prevents it: BOTH languages must lead with their changelog, each inside its own section, and
# the whole description must stay under Steam's ~8 KB limit (k_EResultInvalidParam above ~8,000 bytes).
#
# Usage:
#   python .tools/verify-workshop-desc.py            # checks the local description file
#   python .tools/verify-workshop-desc.py --live     # also checks what Steam actually stored
import io
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "workshop-description.txt")
EN_HEAD = "[h1]English[/h1]"
ZH_MARK = "[h2]更新记录[/h2]"
EN_MARK = "[h2]Changelog[/h2]"
MAX_BYTES = 8000
MAX_LEAD = 600          # the changelog must start within this many chars of its section's start
ITEM_ID = "3819506337"


def check(text: str, label: str) -> list:
    problems = []
    data = text.encode("utf-8")
    if len(data) > MAX_BYTES:
        problems.append("%s: %d bytes > %d (Steam rejects it)" % (label, len(data), MAX_BYTES))
    if EN_HEAD not in text:
        problems.append("%s: missing %s" % (label, EN_HEAD))
        return problems
    zh, en = text.split(EN_HEAD, 1)
    if ZH_MARK not in zh:
        problems.append("%s: Chinese half has no %s" % (label, ZH_MARK))
    else:
        pos = zh.index(ZH_MARK)
        if pos > MAX_LEAD:
            problems.append("%s: Chinese changelog starts at char %d of the Chinese section (must be < %d)"
                            % (label, pos, MAX_LEAD))
    if EN_MARK not in en:
        problems.append("%s: English half has no %s" % (label, EN_MARK))
    else:
        pos = en.index(EN_MARK)
        if pos > MAX_LEAD:
            problems.append("%s: English changelog starts at char %d of the English section (must be < %d)"
                            % (label, pos, MAX_LEAD))
    return problems


def live_description() -> str:
    body = urllib.parse.urlencode({
        "itemcount": 1,
        "publishedfileids[0]": ITEM_ID,
    }).encode()
    req = urllib.request.Request(
        "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
        data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    return payload["response"]["publishedfiledetails"][0]["description"]


def main() -> int:
    want_live = "--live" in sys.argv
    if not os.path.exists(LOCAL):
        print("FAIL: %s not found" % LOCAL)
        return 2
    text = io.open(LOCAL, encoding="utf-8").read()
    problems = check(text, "local")

    print("local description: %d chars / %d bytes" % (len(text), len(text.encode("utf-8"))))
    print("  zh changelog at char %d | en changelog at char %d"
          % (text.find(ZH_MARK), text.find(EN_MARK)))

    if want_live:
        try:
            live = live_description()
        except Exception as e:
            problems.append("live: could not read the uploaded description (%s)" % e)
            live = None
        if live is not None:
            problems += check(live, "live")
            print("live description : %d chars / %d bytes" % (len(live), len(live.encode("utf-8"))))
            print("  zh changelog at char %d | en changelog at char %d"
                  % (live.find(ZH_MARK), live.find(EN_MARK)))

    if problems:
        print("\nFAIL:")
        for p in problems:
            print("  -", p)
        return 1
    print("\nPASS: both languages carry their changelog near the top of their own section,"
          " and the description fits Steam's limit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
