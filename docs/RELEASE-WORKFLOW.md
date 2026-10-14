# Release workflow

The exact sequence for shipping a version of this mod. It exists because every step below has, at least
once, failed *silently* and shipped something wrong — a build that reported success while the project had
not actually loaded, a `.gitignore` whose rules were all inert, a debug symbol record leaking the
builder's home directory into the published binary. Each step therefore ends in an **observation**, not
in a command that "ran fine".

Nothing here is optional except where it says so.

---

## 0. Where things live

| | |
|---|---|
| Mod source | `Yetannia/` |
| Packed art | `.tools/pckproject/` → `Yetannia/build/Yetannia.pck` |
| Tester readme (ships in the zip) | `.tools/mod-readme.txt` |
| Visitor-facing readme (GitHub) | `README.md` |
| Tools | `.tools/*.ps1`, `.tools/*.py`, `.tools/*.js` |
| QA evidence | `.tools/qa/` |
| Workshop workspace | `.tools/uploader/win/YetanniaWorkshop/` (`content/` holds the files that get uploaded) |

Paths in this document are relative to the repository root, and are written with placeholders where a
machine-specific path would be a privacy leak. **This file is published on GitHub: do not put a local
user name, an absolute path containing one, a Steam account id, or any credential in it.**

---

## 1. Freeze the change set

Know what changed, because steps 4 and 5 depend on it:

* **code changed?** → rebuild, and the `.dll` is a new artifact.
* **anything under `.tools/pckproject/` changed?** → the `.pck` **must** be re-exported (§4).
  `.tools/package-mod.ps1` does **not** re-export it; it packages whatever `.pck` is already on disk.
  Forgetting this ships old art with new code, and the zip looks perfectly fine.
* **either changed?** → a version bump (§5) and a full QA round (§7).

---

## 2. Build

```powershell
.tools\dotnet\dotnet.exe build Yetannia\Yetannia.csproj -c Release --no-restore
```

**Do not trust the build output.** `dotnet build` has already reported `0 个错误` in this project while
the project had in fact failed to load (an XML comment containing `--` is illegal, and the failure is
not surfaced as a compile error). The observation that proves the build happened is the artifact:

```powershell
Get-Item Yetannia\bin\Release\Yetannia.dll | Select-Object Length, LastWriteTime
```

The timestamp must be now **and** the size must differ from the previous build if the source changed.
Note also that the output path is `Yetannia\bin\Release\`, **not** `bin\Release\net9.0\`
(`AppendTargetFrameworkToOutputPath` is false).

A `.dll` hash that changed is **not** evidence of a code change: these builds are not reproducible, and
an identical source tree still produces a `.dll` differing by ~70 bytes of PE timestamp/MVID. Byte
identity of the IL has to be measured with a metadata reader (see `.tools/qa/QA-RETEST47.md`), not
inferred from the file hash.

---

## 3. Install for testing

Deploy the four shipped files into the game's `mods\Yetannia\`:

```
Yetannia.json   Yetannia.dll   Yetannia.pck   README.txt
```

The folder must contain **exactly** those four files — in particular **no `Yetannia.pdb`**. Release
builds set `DebugType=none`, and `.tools/package-mod.ps1` defaults `-IncludePdb` to `$false`; a stale
`.pdb` left behind by an older run is both a privacy leak and a lie about what was tested.

The QA runners (`.tools/qa/rt*-run.py`) do this deployment themselves, hash-gated: they refuse to launch
unless all four workspace files match the hashes they expect.

---

## 4. Re-export the packed art (if anything under `.tools/pckproject/` changed)

```powershell
.tools\export-pck.ps1
```

It imports through a script-free Godot project and writes `Yetannia/build/Yetannia.pck`. The observation:
the `.pck` timestamp and size changed, and the entry count is what you expect. A silently-empty or
unchanged `.pck` is the failure mode this step guards against.

---

## 5. Version bump

```powershell
.tools\bump-version.ps1 v1.0.1
```

Updates the version in `Yetannia/Yetannia.json` (the manifest the game reads) and on the first line of
`.tools/mod-readme.txt`, then regenerates the card table. The script is deliberately ASCII-only and
writes BOM-less UTF-8: a UTF-8 BOM in `Yetannia.json` makes the manifest unparseable for both the game
and the card-table generator.

Also update the Workshop change note in `.tools/make-workshop.py` (`changeNote`) so the Workshop entry
says what changed. The author field lives in `Yetannia/Yetannia.json` (`"author"`).

---

## 6. Package

```powershell
.tools\package-mod.ps1 -SkipBuild -Out Yetannia-v1.0.1.zip
```

`-SkipBuild` because §2 already built it. The zip's top level must be exactly `Yetannia/`, with no
directory entries, so that extracting it into `mods\` produces `mods\Yetannia\`.

---

## 7. Test — **one single-player run, one multiplayer run**

> **Protocol change.** Earlier rounds tested single-player twice. A second single-player run re-covers
> what the first already covered and leaves the multiplayer-only paths (map drawing and pings, the
> rock-paper-scissors relic minigame, remote targeting lines, the multiplayer-only cards, and netcode
> timing) completely untested. The protocol is now **1 × single-player + 1 × multiplayer**.

Single-player run:

```powershell
python .tools\qa\rt<NN>-run.py --tag rt<NN>-a
```

Multiplayer run: **this is possible on one machine without a second Steam account**, using the game's
own Steam-free networking path. The full mechanism, the line-by-line code evidence, the preconditions
and the side effects are in `docs/MULTIPLAYER-TESTING.md`; the runnable form is:

```powershell
python .tools\qa\rt48-mp.py stage                 # stage BaseLib locally (Steam off means no Workshop scan)
python .tools\qa\rt48-mp.py run --seconds 180     # host + client, 127.0.0.1:33771
python .tools\qa\rt48-mp.py unstage               # put the mods folder back
```

Three things must not be got wrong, and they are why this is a script rather than a remembered command:
`--force-steam=off` on **both** instances (with Steam on, the two peers see different gameplay mod sets
and the handshake refuses), a locally staged `BaseLib` (with Steam off the Workshop folder is not
scanned), and `--clientId=1000` on the client (without it the client's platform id defaults to 1 and it
writes into the *host's* save scope). With Steam off the game writes only under
`%APPDATA%\SlayTheSpire2\default\<id>\`, so the author's real Steam profile and `mod_configs` are not
touched.

If a multiplayer mechanism is genuinely unavailable, record that explicitly in the QA report — do
**not** silently substitute a second single-player run, and do not report the round as "multiplayer
tested".

Both runs must be launched with `--autoslay --qacheck`, which drives a full automated run and dumps the
in-game self-check into the log. Then read the log, not the exit code:

```powershell
Select-String -Path "$env:APPDATA\SlayTheSpire2\logs\godot.log" -Pattern 'Yetannia'
```

What has to be true in the captured log:

| check | what to look for |
|---|---|
| the mod booted | `self-check character : registered=True` |
| every Harmony patch landed | `patch self-check:` — `ours=1` on **every** line; a `target method NOT FOUND` is a hard fail |
| voice | `[voice] first play:` for every moment the run should have reached |
| scry diagnostics | `[scry] … BEGIN` / `END` pairs; an unbalanced `STILL PENDING` is a finding |
| card/pool integrity | `self-check card pool`, `portrait ok`, `UNRESOLVED placeholders` |
| multiplayer-only values | `self-check mp colours` |

**Every ERROR/WARN line must be attributed** to this mod, to another mod, or to the engine — see
`.tools/qa/QA-RETEST47.md` §⑥ for the method. An unattributed error is an open finding, not a pass.

Then write the round up as `.tools/qa/QA-RETEST<NN>.md`: verdict per priority, the artifacts table with
hashes, the runs table, and an explicit list of what was **not** verified.

---

## 8. Security and privacy gate — **blocking**

Run this **after packaging and before uploading**, and treat a single hit as a blocker. Everything in
this section exists because it has already gone wrong here once.

The whole of §8.1–§8.4 is automated by one script, which scans in ASCII **and** both UTF-16 byte orders,
and whose marker set it derives from this machine at run time (never hard-coded — the script is itself
published):

```powershell
python .tools\privacy-scan.py Yetannia-v1.0.1.zip
```

It exits non-zero on any hit. A `FAIL` line names the artifact, the encoding, and the surrounding
readable text, so the finding can be judged rather than just counted. **Two calibration facts matter
when you trust it:** it reports `PASS` on the published v1.0.0 zip (independently audited clean in
`.tools/qa/QA-RETEST47.md` §①), and it reports `FAIL` on `Yetannia\bin\Debug\Yetannia.dll`, which really
does carry a CodeView debug record and a build `obj` path — so it is known to both pass clean input and
catch the exact leak this project shipped once.

Its limits, stated so they are not mistaken for coverage: it is a **marker** scanner, not a proof. A leak
that resembles neither a debug record, a filesystem path, a SteamID, a machine/user name, nor a
forbidden filename would pass. §8.5 and §8.6 are not automated and must still be done by hand.

### 8.1 The published binary must carry no builder identity

Scan the `.dll` **inside the zip** (not the workspace copy), in **both** ASCII and UTF-16:

* 0 occurrences of a CodeView debug record or of a `.pdb` reference — such a record embeds the absolute
  path of the `.pdb`, which contains the local user name. This is exactly the leak a Release build with
  `DebugType=portable` shipped once.
* 0 occurrences of a drive letter followed by a path, of a Windows profile directory segment, of
  `AppData`, of a build `obj` directory, or of the local user name.
* 0 occurrences in UTF-16LE and UTF-16BE (a UTF-16 string is invisible to a naive ASCII scan).

### 8.2 The packed art must carry no source paths

Scan every entry of the `.pck` for the same markers. The ext-resource container embeds the import path
of each source asset.

### 8.3 The shipped readme

`.tools/mod-readme.txt` → `README.txt` must contain no local path (other than documented `%APPDATA%`
environment-variable references), no user name, no Steam id, no build-machine information.

### 8.4 The zip's shape

* top level exactly `Yetannia/`, no directory entries;
* exactly the intended file set — no `*.pdb`, no `.dll`/`.json`/`README.txt` *inside* the `.pck`, no
  editor or backup files (`*.bak`, `*~`, `*.orig`, `.DS_Store`, `Thumbs.db`);
* the zip's four entries are byte-identical to `.tools/package/Yetannia/`.

### 8.5 The repository staging list — check what you are about to commit

This is the one that nearly published a Steam account id and a `settings.save` backup. Before any
`git add`, list what the ignore rules actually match, and **verify the rules are live**:

```powershell
git status --porcelain=v1 --untracked-files=all
git check-ignore -v .tools\qa\anything.md      # must print a matching rule, not nothing
git check-ignore -v .tools\out\anything        # must print a matching rule, not nothing
```

`.gitignore` does **not** support trailing comments — text after a pattern on the same line becomes part
of the pattern and silently disables the rule. Every comment must be on its own line. If
`git check-ignore -v` prints nothing for a path that should be ignored, the rule is broken; fix it
before staging anything.

Then confirm nothing in the staged set is a local-only artifact:

```powershell
git diff --cached --name-only
```

Must contain **no** `.tools/qa/**`, `.tools/out/**`, `.tools/dotnet/**`, `.tools/godot/**`,
`settings.save*`, `mod_configs/**`, `logs/**`, `*.log`, `*.pdb`, `*.dll`, `*.pck`, `*.zip`, `*.xlsx`, or
anything matching the private-directory list.

**Never run `git add -A` on this workspace.** The tree is multi-gigabyte, the add times out and leaves a
stale `.git/index.lock` behind; stage explicit paths.

### 8.5b Scan the repository itself, not just the release zip

The zip is not the only thing that gets published — the repository does too, and it is public. The same
scanner can be pointed at everything git tracks:

```powershell
$git = "$env:ProgramFiles\Git\cmd\git.exe"      # git is not necessarily on PATH
[IO.File]::WriteAllLines("$PWD\.tools\qa\_tracked.txt", (& $git ls-files), [Text.UTF8Encoding]::new($false))
python .tools\privacy-scan.py --files-from .tools\qa\_tracked.txt --quiet-notes
```

`[IO.File]::WriteAllLines` rather than `>` or `Set-Content -Encoding UTF8`, because those write a BOM or
UTF-16 and the first "path" then fails to open.

**This check has found a real leak, so it stays.** The tracked tree used to contain the builder's Windows
user name and a SteamID64 — in `docs/DEVELOPMENT.md` and in two checked-in QA scripts — because those
documents quoted a `settings.save` path verbatim. They now derive the SteamID64 from the active account
at run time instead. Two consequences worth remembering:

* **A history rewrite is the only thing that removes a leak from a public repository.** Fixing the
  working tree fixes `HEAD` and nothing else; the old commit keeps serving the string. If a leak like
  this is found, decide deliberately whether to rewrite history and force-push, and treat it as a
  separate, user-approved operation.
* The scan currently reports a few **accepted, non-identity** findings: the name of the CodeView debug
  record inside a `.csproj` comment that documents it, a JavaScript regex escape that happens to look
  like a package-cache directory, and machine-layout paths such as `C:\temp\art` and a Steam library
  path inside build scripts that need a real path to run. None of them carries a user name, an account
  id, or a credential. Judge each finding; do not silence the check to make the count zero.
* The scanner **skips its own source file**, which necessarily contains its entire marker table — without
  that exception the scanner would report itself on every run and the check would be worthless.

### 8.6 Credentials

No token, cookie, Steam Guard code, or account name may appear in any committed file, in the Workshop
description, in the uploaded readme, or in a chat message. Upload using the already-signed-in Steam
client and the already-authenticated `gh` login; do not paste a credential anywhere.

---

## 9. Upload

### 9.1 Workshop

Prerequisites, all mandatory:

1. the Steam **client** is running (the uploader is MegaCrit's official `ModUploader.exe`, which talks to
   the running client through `steam_api64.dll` — there is no `steamcmd` path and no Steam Guard step);
2. the **correct account** is the active one. Verify, do not assume — this machine has more than one
   Steam account that owns the game:
   ```powershell
   reg query HKCU\Software\Valve\Steam\ActiveProcess /v ActiveUser
   ```
3. the **game is closed**. An upload makes Steam open the Workshop page in a browser; doing that while
   the author is mid-run is disruptive.

The intended Workshop visibility and the branch restriction live in `.tools/make-workshop.py`
(`visibility`, `minBranch`/`maxBranch`) and the description in `.tools/workshop-description.txt`, whose
first line must keep the beta-only notice.

Known failures and what they mean:

* `k_ESteamAPIInitResult_NoSteamClient` — Steam is not running, or is running as a different user.
* `k_EResultTimeout` at the commit stage — a Steam-backend timeout. It is **not** fixed by retrying in a
  tight loop; record the attempt and move on. Note that the runs print either
  `No modifications were made to dependencies.` or `Found N dependencies.`; a change on that line
  coincides with the commit step and is worth capturing.

### 9.2 GitHub

```powershell
$env:HTTPS_PROXY='http://127.0.0.1:7890'   # gh is a Go binary and ignores the Windows system proxy
gh auth status
```

Commit with explicit paths (§8.5), push, and confirm the remote commit hash afterwards.

---

## 10. After the upload

1. Confirm the live Workshop item shows the new version and the beta-only note.
2. Confirm the GitHub remote is at the commit you think it is.
3. Report honestly: what shipped, the hashes, what was tested, and — explicitly — anything that was
   **not** verified. A failed upload or an untested path must be stated as such, never implied to have
   succeeded.

---

## Appendix — shell traps that have cost real time here

* The shell is **Windows PowerShell 5.1**: no `??`; `Select-String` is case-**in**sensitive; native
  commands receive arguments containing spaces split apart; `>` writes **UTF-16**.
* **Never round-trip UTF-8 text through `Get-Content`/`Set-Content`.** PowerShell 5.1 reads UTF-8 as
  ANSI and destroys Chinese text. Use a file-editing tool or Python, and never print Chinese to the
  console — the console codepage mangles it and you will believe the file is corrupt when it is not.
* To write UTF-8 without a BOM from PowerShell, use
  `[IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))`.
* `gh` writes its success message to stderr, so PowerShell may report exit 1 for a command that worked.
  Check the effect, not the exit code.
