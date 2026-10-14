# Testing Yetannia in a multiplayer session on one machine

**Scope of this document.** Static, read-only investigation (no game was launched, no save/setting/mod
file was touched) plus the one new file you are reading. All code evidence is line numbers in
`.tools/decomp/sts2.decompiled.cs` (the 508,374-line decompilation of the retail assembly), unless a
different file is named. Runtime facts were read from directory listings and the existing logs only.

---

## 0. Verdict

**POSSIBLE WITH CAVEATS.**

The single most important reason: **the retail build ships a first-class Steam-free network path.**
`--fastmp=host_standard` opens a raw ENet socket on `0.0.0.0:33771`, and `--fastmp=join` connects a
second instance to `127.0.0.1:33771`. Both bypass Steam entirely, and `--force-steam=off` additionally
skips Steam initialisation, which moves each instance into its own `default\<playerId>\` save scope so
your real Steam saves are never touched.

The one blocking caveat: **`BaseLib` is currently installed only via Steam Workshop, and with Steam
switched off the game does not scan the Workshop folder.** `mods\` contains `Yetannia`, `YetanniaQA`,
`SlaytheSpire2.unlockAll` and `EstaliaMod-v0.2.0.zip` — no `BaseLib`. Because the join handshake
*hard-fails on a gameplay-mod mismatch*, both instances must see an identical mod set, so `BaseLib`
must be staged locally **once** before the test. After that one-time step, the protocol becomes
"one single-player run + one two-instance multiplayer run".

Estimated one-time setup: copy one folder. No patching, no code changes, no extra Steam account.

---

## 1. Environment facts (verified on this machine)

| Fact | Value | How verified |
|---|---|---|
| Game install | `D:\SteamLibrary\steamapps\common\Slay the Spire 2` | `Test-Path` |
| Executable | `SlayTheSpire2.exe`, 894,748,672 bytes, FileVersion 1.0.0.0 | `Get-Item .VersionInfo` |
| Game version | `v0.111.0`, Godot `4.5.1.m.14.mono.custom_build` | log banner |
| `steam_appid.txt` | present, contains `2868840` | read of a 7-byte file |
| Mods folder | `<game>\mods\` -> `SlaytheSpire2.unlockAll`, `Yetannia`, `YetanniaQA`, `EstaliaMod-v0.2.0.zip` | directory listing |
| **`BaseLib` locally?** | **NO** | directory listing of `mods\` |
| BaseLib (Workshop) | `<steamapps>\workshop\content\2868840\3737335127\` — BaseLib v3.4.7 | listing + log line `* BaseLib (v3.4.7) workshopId=3737335127` |
| `mods_STEAMTEST\` | does not exist | `Test-Path` |
| User data | `%APPDATA%\SlayTheSpire2` | `Test-Path` |
| Steam-scoped saves | `%APPDATA%\SlayTheSpire2\steam\<steamid64>\` (two accounts present; ids masked) | directory listing |
| **No-Steam scope** | `%APPDATA%\SlayTheSpire2\default\1\` **already exists**, containing `profile1\`, `settings.save`, `settings.save.backup`, `console_history.log` | directory listing |
| Logs | `%APPDATA%\SlayTheSpire2\logs\godot.log` (11.4 MB) plus 4 rotated `godot<timestamp>.log` | directory listing |
| Steam | currently running (1 process); `C:\Program Files (x86)\Steam\steam.exe` present | `Get-Process` |
| Real MP on this machine? | **Yes.** `godot.log` and `godot2026-10-14T16.43.48.log` contain full Steam lobby joins with **2, 3 and 4 players** and `Embarking on a multiplayer run` | grep of logs |
| Two instances at once? | **No evidence.** The 5 retained sessions are strictly sequential; every one of them ran as the *client* (`Successfully connected to host <steamid>`) with **empty** command-line args | log timestamps + `Command Line Args:` lines |
| Mod's multiplayer-only cards | exactly **6**: `EmberBoon`, `GiftOfTime`, `GuidanceOfTheProphet`, `SharedMight`, `SharedFocus`, `SharedRegen` | `grep CardMultiplayerConstraint.MultiplayerOnly` in `Yetannia\Code\Cards\` |

The existence of `%APPDATA%\SlayTheSpire2\default\1\` is useful corroboration that the Steam-free
branch described below has already been exercised on this machine at least once (see INFERENCE I2).

---

## 2. Candidate mechanisms

Legend for "Available here": ✔ = usable now · ⚠ = usable after a one-time step · ✖ = not usable.

| # | Mechanism | What it actually is | Gate / condition (evidence) | Available here | Confidence |
|---|---|---|---|---|---|
| **A** | **`--fastmp` + `--force-steam=off` — two instances over ENet loopback** | Host binds a raw ENet socket on `0.0.0.0:33771`; client connects to `127.0.0.1:33771`. Both use `PlatformType.None`; no Steam. | `CheckCommandLineArgs` 355246-355295; `StartHostAsync` 358294-358309 (`platformType = (SteamInitializer.Initialized && !HasArg("fastmp")) ? Steam : None`, then `netService.StartENetHost(33771, 4)`); `FastMpJoin` 353457-353466 (`new ENetClientConnectionInitializer(netId, "127.0.0.1", 33771)`); `ENetHost.StartHost` 57053-57064 (`CreateHostBound("0.0.0.0", port, maxClients)`); `--force-steam=off` skip at 212620-212626 | **⚠** needs local `BaseLib` | **High** — every step read in code; arg parsing already proven by archived runs |
| **B** | `--fastmp=join` reached through the normal "Join Friends" screen | When Steam is off (or `fastmp` is set) the join-friends screen immediately calls `FastMpJoin()` instead of listing friends | `NJoinFriendScreen.OnSubmenuOpened` 353438-353450: `if ((!SteamInitializer.Initialized \|\| CommandLineHelper.HasArg("fastmp")) && !DebugFriendsButtons) { TaskHelper.RunSafely(FastMpJoin()); }` | **⚠** same as A | **High** |
| **C** | Hidden **debug friends / debug lobby UI** | The property exists but is a hardcoded constant, so the fake-friend list is dead code | `public bool DebugFriendsButtons => false;` at **353409**; consumed at 353442 and 353516. There is no build flag, settings field or command-line arg — it is a literal `false`. | **✖** (harmless: it is only unreachable *because* the Steam-off path goes straight to `FastMpJoin`) | **High** |
| **D** | **Debug multiplayer scene** `scenes/debug/multiplayer_test.tscn` | A real in-game GUI with a **non-Steam Host button** and a Join button with ID/IP fields (default `1000` / `127.0.0.1`) | Opened by dev-console command `multiplayer test`: `MultiplayerConsoleCmd` 186022-186043. Debug commands allowed when modded: 451129 `OS.HasFeature("editor") \|\| TestMode.IsOn \|\| ModManager.IsRunningModded() \|\| SettingsSave.FullConsole`. Host button 454394-454397 -> `StartHost(steam: false)` 454494-454503 -> `StartENetHost(33771, 4)`. Join button 454399-454404. Scene ships in retail PCK: `.tools/qa/r40-sts2-entries.txt:11584`. | **✔** reachable (we are modded) — but still needs **two processes**, so it is a GUI alternative to A, not a single-instance answer | **High** for reachability; **Medium** that the scene's node paths resolve at runtime (not executed) |
| **E** | `--bootstrap` multiplayer-mode run (single process, one player) | The bootstrap path can run "in multiplayer mode" but with only the local player in the lobby | `--bootstrap` 211935-211938 -> `NSceneBootstrapper` 453810-453874; `IBootstrapSettings.BootstrapInMultiplayer` 454046-454066. **Already proven on this machine**: `.tools/qa/logs/rt40-mp.log` was launched `--bootstrap --qaroom=treasure --seed=qa40mp`, and `QA-RETEST40.md` records that the multiplayer-mode bootstrap started but contained **one** player. | **✔** works, but `RunState.CardMultiplayerConstraint` 38205-38215 returns `SingleplayerOnly` when `Players.Count <= 1`, so **the 6 multiplayer-only cards stay excluded** | **High** |
| **F** | **Combat replay** (`.mcr`) via `NetReplayGameService` | A single-process replay that re-drives a recorded run (including a recorded *multiplayer* run) through a no-op net service, with real checksum divergence checking | `NetReplayGameService` 55606-55670 (all message methods have **empty bodies**); `RunManager.SetUpReplay` 39835; `NMultiplayerTest.RunReplay` 454623-454696; recording file `replays/latest.mcr` 40974; recording enabled in retail at 39902 `CombatReplayWriter.IsEnabled = !TestMode.IsOn` | **✔** but it **bypasses the lobby and all synchroniser/message traffic** (`CombatStateSynchronizer.IsDisabled = true` 454633, `EnqueueWithoutSynchronizing` 454669/454680) and `RunLobby` is never created (39922). Cannot be used to test the 6 MP-only cards in a real 2-player run. | **High** |
| **G** | `TestMode` + `RunManager.SetUpTest(..., disableCombatStateSync: false)` fake 2-player run | Fabricate a 2-player `RunState` in one process and puppeteer the remote player | `TestMode.IsOn` is a plain `public static bool { get; set; }` (11639); `SetUpTest` 39860-39876 sets `CombatStateSynchronizer.IsDisabled = disableCombatStateSync` (default `true`; `false` is the documented "test multiplayer scenarios" value); `RunState.AddPlayerDebug` 41992; `Player.CreateForNewRun(..., netId)` 176242; `TestFlags.ShouldSendResumeForRemotePlayers` 11631 (used at 172270/172463/172475) | **✖ today** — nothing in the shipped assembly ever calls `TurnOnInternal`/`SetUpTest`/`StartTestHost` (`AbstractTestNetHost` 11476 has **no concrete subclass**). Would require writing harness code in `YetanniaQA`. | **Medium-High** that it is unreachable as shipped; **Low** on whether a hand-written harness would actually work |
| **H** | `--fastmp` **without** `--force-steam=off` | ENet transport, but Steam stays initialised, so **both** instances share one Steam identity and one save scope | `fastmp` still forces `PlatformType.None` for the socket (358296), but `PlatformUtil.PrimaryPlatform` stays `Steam` (52397-52407), so `GetAccountScopedBasePath` 31294-31305 resolves to `steam/<id>/...` — i.e. `...\steam\<same steamid64>\` for **both** processes | **⚠/✖** — works but the two processes read and write the *same* `settings.save` and `current_run_mp.save`. Not recommended. | **High** on the sharing; Medium on how badly it misbehaves |
| **I** | `--autoslay` as the driver for the MP run | The engine's own bot | Gated at 211927 `if (!IsReleaseGame() && CommandLineHelper.HasArg("autoslay"))` with `IsReleaseGame()` hardcoded `return true` (211994-211997). Additionally `AutoSlayer` always clicks `MainMenuTextButtons/SingleplayerButton` (204991-204993) and has no lobby handler. | **✖** dead in retail; singleplayer-only by construction. (`YetanniaQA` already patches `IsReleaseGame()` for single-player QA, but that does not make the bot multiplayer-capable.) | **High** |
| **J** | `--connect_lobby` (Steam invite join) | Join a Steam lobby by id | `CheckForCommandLineJoin` 52925-52933 parses `+connect_lobby` | **✖** for one-machine testing — needs a real remote Steam lobby | **High** |
| **K** | Third-party LAN/co-op mod | Not part of the game | Not investigated. Note only: a `national_spire_coop` and an `sts2_lan_connect` directory exist under `%APPDATA%\SlayTheSpire2`, i.e. some third-party LAN/co-op mod is or was installed. | **?** out of scope | — |

**Conclusion:** mechanism **A** (optionally driven through **B**/**D** for the GUI) is the viable answer.

---

## 3. Recommended procedure (mechanism A)

### 3.0 The two invariants you must respect

1. **Both instances must load the exact same gameplay mod set.** The handshake hard-fails otherwise:
   `HandshakeManager` compares `peerVersionInfo.version` (67789), then
   `GetMissingModsOnRemote/Local(nonGameplay: false)` -> `HandshakeStatus.ModMismatch` (67794-67799), then
   `idDatabaseHash` (67801-67805). `PeerVersionInfo.LocalDefault()` fills these from
   `ModManager.GetGameplayRelevantModNameList()` (55782-55792).
   => Do **not** mix "host with Steam on" and "client with Steam off": the Steam instance would load ~60
   Workshop mods the other one cannot see, and the join would be refused. **Take Steam off in both.**
2. **Keep `YetanniaQA` on the same side in both instances.** It must be either enabled in both or disabled
   in both. Prefer enabled-in-both so you can reuse `--qagym` (the card-injection harness your previous QA
   rounds used) to get the 6 multiplayer-only cards into hand.

### 3.1 One-time setup (≈2 minutes)

1. Copy BaseLib out of the Workshop folder into the game's local mods folder:

   ```powershell
   $game = 'D:\SteamLibrary\steamapps\common\Slay the Spire 2'
   Copy-Item -Recurse 'D:\SteamLibrary\steamapps\workshop\content\2868840\3737335127' "$game\mods\BaseLib"
   ```

   (Equivalent alternative: copy it to `"$game\mods_STEAMTEST\BaseLib"`. That directory is also scanned, and
   entries in it are classified as `ModSource.SteamWorkshop` even without Steam — see
   `ModManager.Initialize` 155553-155561. Either location satisfies invariant 1.)

   > **Watch out:** `.tools/testrun.ps1` lines 13-16 do `Remove-Item -Recurse -Force "$game\mods\BaseLib"`.
   > Do not run that script between staging BaseLib and running the multiplayer test, or you will silently
   > break the test (and the symptom will be "Yetannia failed to load", not "mods missing").

2. Confirm the staging:

   ```powershell
   Get-ChildItem "$game\mods" | Select-Object -ExpandProperty Name
   # expect: SlaytheSpire2.unlockAll, Yetannia, YetanniaQA, BaseLib, EstaliaMod-v0.2.0.zip
   ```

### 3.2 First launch of the host (creates/uses the `default\1\` scope)

Your real, Steam-scoped saves are under `%APPDATA%\SlayTheSpire2\steam\<steamid64>\`. With
`--force-steam=off`, `PlatformUtil.PrimaryPlatform` becomes `None` and
`UserDataPathProvider.GetPlatformDirectoryName` returns `"default"` (31331-31338), so the instance writes
to `%APPDATA%\SlayTheSpire2\default\1\` instead. `default\1\` already exists on this machine; only the
`default\` tree is written.

```powershell
$game = 'D:\SteamLibrary\steamapps\common\Slay the Spire 2'
Start-Process -FilePath "$game\SlayTheSpire2.exe" -WorkingDirectory $game `
  -ArgumentList @('--force-steam=off','--fastmp=host_standard')
```

**Expect a modal "load mods?" popup.** On a scope where `SettingsSave.ModSettings == null`, the main menu
adds `NConfirmModLoadingPopup` (354834-354837). If you decline (or never answer), every mod is marked
`Disabled` — `TryLoadMod` 156129-156133: `else if (!PlayerAgreedToModLoading) { ... mod.state = ModLoadState.Disabled; }`.
If you accept, the game **saves the setting and then quits itself** —
`OnYesButtonPressed` 337519-337531 ends with `NGame.Instance.Quit()` (337529). So:

* First launch: click **Load mods** -> the game closes.
* Relaunch with the same command line -> mods load, and `--fastmp=host_standard` takes you straight to the
  multiplayer character-select screen (`FastHost` 358852-358856 -> `StartHostAsync` 358294).

> `default\1\` already contains a `settings.save`, so the popup may not appear for the **host**; it will
> appear for the **client** (its `default\1000\` does not exist yet). To skip the extra launch pair
> entirely you may copy the host's settings file to the client scope before launching:
> `Copy-Item "$env:APPDATA\SlayTheSpire2\default\1\settings.save" -Destination (New-Item -ItemType Directory -Force "$env:APPDATA\SlayTheSpire2\default\1000").FullName`
> (INFERENCE I3 — plausible because `settings.save` lives at the account-scope root (29517) and the
> per-account mod-enable list is inside it (155595), but I did not inspect the file's contents.)

Once the host is at the character-select screen it is **already listening** on `0.0.0.0:33771`
(`StartHostAsync` binds before pushing the screen, 358308). Pick a character and press **Embark**; the
host then shows the "ready and waiting" state (`OnEmbarkPressed` 384227-384253).

### 3.3 Launch the client

```powershell
Start-Process -FilePath "$game\SlayTheSpire2.exe" -WorkingDirectory $game `
  -ArgumentList @('--force-steam=off','--fastmp=join','--clientId=1000')
```

**`--clientId=1000` is not optional.** Without it the client's platform player id falls back to `1`
(`NullPlatformUtilStrategy` 54058 `public ulong LocalPlayerId { get; set; } = 1uL;`, overridden only by
`clientId` at 54066-54069) while its ENet id would be `1000` (353459-353463). That mismatch matters
because the platform player id is what builds the **save path** — the client would write into
`default\1\`, i.e. the **same directory as the host**. Passing `--clientId=1000` gives:

| Instance | ENet id | platform id | save scope |
|---|---|---|---|
| host | `1` (`ENetHost.NetId => 1uL`, 57046) | `1` | `%APPDATA%\SlayTheSpire2\default\1\` |
| client | `1000` | `1000` | `%APPDATA%\SlayTheSpire2\default\1000\` |

The client window title becomes **"Slay The Spire 2 (Client)"** (`DisplayServer.WindowSetTitle`, 353464) —
a handy manual marker, since the title is not written to the log.

Sequence: client reaches main menu -> `CheckCommandLineArgs` (called from `NMainMenu._Ready()`, 354778/354833) ->
`OnJoinFriendsPressed` (358926-358929) -> `NJoinFriendScreen.OnSubmenuOpened` -> `FastMpJoin()` ->
connects to `127.0.0.1:33771`.

**Timing:** start the host first and wait until it is on the character-select screen. `FastMpJoin`
connects immediately and gives up after a 10 s handshake timeout (`_handshakeTimeoutMsec = 10000`,
57028; `HandshakeManager` 67698). If the client logs a connection failure, just relaunch the client.

### 3.4 Run the test

1. Both instances are now in the multiplayer lobby / character select.
2. On the client, pick a character. On the host, press **Embark** once both are ready.
3. The run starts with `RunState.Players.Count == 2`. This is the switch that makes the mod's 6
   `MultiplayerOnly` cards eligible — `RunState.CardMultiplayerConstraint` 38205-38215 returns
   `MultiplayerOnly` when `Players.Count > 1`, and `CardPoolModel.GetUnlockedCards` 74812-74821 then strips
   the `SingleplayerOnly` cards and keeps the multiplayer ones.
4. Use your existing `--qagym` card-injection harness (add it to the arg list of **both** instances:
   `'--qagym','--qarelic','--qaprobe','--qacheck'`) to force `EmberBoon`, `GiftOfTime`,
   `GuidanceOfTheProphet`, `SharedMight`, `SharedFocus`, `SharedRegen` into hand and play them across the
   network boundary.
5. Specific things worth watching in a 2-player run: the shared map, the rock-paper-scissors relic
   minigame, map drawing, and per-player "this is me" colours (the mod overrides
   `CustomArmPointing/Rock/Paper/ScissorsTexturePath` in `Yetannia\Code\Character\YetanniaCharacter.cs`).

### 3.5 Shut down

Close both windows normally. Then, if you want the next single-player run to go back to your real Steam
profile, simply launch the game the normal way (through Steam / without `--force-steam=off`).

### 3.6 Side effects — read this before you start

* **Your real saves are not touched.** The two test instances write only under
  `%APPDATA%\SlayTheSpire2\default\`; nothing under `steam\<steamid64>\`, and nothing in `mod_configs`.
  `SaveManager` builds its store from `GetAccountScopedBasePath(null)` (29517) and only wraps it in a
  Steam cloud store when Steam is initialised (29519-29525).
* **The host instance will read and may update `%APPDATA%\SlayTheSpire2\default\1\`** (its `settings.save`
  and `profile1\` progress) — that scope already exists and is not your live profile.
* **A new directory `%APPDATA%\SlayTheSpire2\default\1000\` will be created.**
* **Both instances share one log file** `%APPDATA%\SlayTheSpire2\logs\godot.log`. The log path is built
  from `OS.GetUserDataDir()` (205136) and is **not** account-scoped, and the `log-file` command-line
  argument is *not* a Godot log redirect — it is only passed to `AutoSlayer` (211931-211933), which never
  runs in retail. I therefore expect the two processes' output to interleave in that one file (Godot's
  logger appends; I did not verify its rotation behaviour). See §5 for how to attribute lines by player id.
  If you want fully separate logs, see INFERENCE I6.
* The mods folder itself is only read. The one exception is `YetanniaQA`, which writes `qa-*.flag` files
  into its own mod folder; if both instances run it they share those flags. Prefer to run the QA scaffold
  in both or in neither.
* No single-instance lock exists — no mutex, no lock file, and no `SteamAPI_RestartAppIfNecessary` anywhere
  in the assembly (`grep -i "mutex|single.instance|RestartAppIfNecessary"` returns only an unrelated VFX
  comment at 231758). Two processes are fine.
* Launch the second instance **directly via the exe**, as shown. Do not use `steam://rungameid/2868840`
  (as `.tools/testrun-with-steam.ps1` does) — Steam would focus the already-running instance instead of
  starting a second one.

---

## 4. Why the other obvious ideas do not solve it

* **Debug friends list (`DebugFriendsButtons`)** — hardcoded `=> false` at 353409. Not gated on a build
  flag, a setting or an argument; there is nothing to flip.
* **The hidden debug MP scene** — this *does* exist and is reachable in your modded install (dev console
  command `multiplayer test`, gated by 451129 which is satisfied by `ModManager.IsRunningModded()`), and
  its Host button is explicitly `StartHost(steam: false)`. But it is still a *client of a peer*: hosting
  and joining are mutually exclusive in one process (`StartHost`/`JoinToHost` both begin with
  `Disconnect(...)`, 454501 and 454526), and the lobby holds one `NetService`. So it needs a second
  process just like mechanism A — it is a GUI convenience, not a single-instance solution.
* **Replays / `TestMode` / test seams** — `NetReplayGameService` is a no-op sink (empty `SendMessage` /
  `RegisterMessageHandler` bodies, 55629-55670) and the replay driver deliberately disables
  synchronisation. The genuine in-process multiplayer harness (`SetUpTest` with
  `disableCombatStateSync: false`, `AbstractTestNetHost`, `TestFlags.ShouldSendResumeForRemotePlayers`)
  exists as **unwired seams**: `AbstractTestNetHost` (11476) has no concrete subclass and `StartTestHost`
  (55242) has no caller in the shipped assembly. Using them would mean writing new harness code.
* **`--autoslay`** — dead in retail (211927 vs `IsReleaseGame() => true` at 211994-211997) and
  singleplayer-only. Note also that `QA-RETEST40.md` already recorded the honest limitation of the
  `--bootstrap` multiplayer-mode route: one player, so the multiplayer-only content stays filtered out.

---

## 5. How to run the mod test in that session, and what proves the multiplayer paths ran

Because both instances share one `godot.log`, attribute lines by **player id** and by **net id**. The
host's ids are `1`; the client's are `1000` (from `--clientId=1000`). The null-platform strategy even
gives them names: `1 -> "Test Host"`, `1000 -> "Test Client 1"` (54090-54097).

### 5.1 Startup markers (per instance)

| Marker | Meaning | Evidence |
|---|---|---|
| `Steam initialization skipped (editor mode). Use --force-steam to enable.` | `--force-steam=off` took effect; Steam is off for this process | 212624 (message text; it says "editor mode" even in retail — that is the literal string) |
| `Player chose to load mods` | the mod-consent popup was accepted (and the game then quit) | 337521 |
| `--- RUNNING MODDED! --- Loaded N mods (M total)` | mods loaded in this instance | 155585 |
| absence of `Steamworks initialization succeeded!` | confirms the Steam bypass | 52855 normally |

### 5.2 Host side

| Marker | Meaning | Evidence |
|---|---|---|
| `[ENetHost]` logger lines, e.g. `Acknowledging handshake for peer with ID 1000` | the client's handshake was accepted | 57106 / 57113 |
| `Second client attempted to connect with peer ID ...` (only with >1 client) | id-collision guard | 57095 |
| `[ENetHost] Peer ID 1000 disconnected, reason: ...` | client left | 57120 |

### 5.3 Client side and the join handshake

| Marker | Meaning | Evidence |
|---|---|---|
| `Attempting to join game with connection initializer ENetClientConnectionInitializer` | the client took the Steam-free path | 353546 |
| `[JoinFlow] Beginning join with initializer ...` | join flow started | 62668 |
| `[JoinFlow] Initializer connection completed, awaiting initial game info message` | ENet connect succeeded | 62694 |
| `Got handshake from sender 1000. Version: ... Branch: ... Hash: ...` | version/mod handshake exchanged | 67788 |
| `Mismatch in gameplay-relevant mods with the remote!` | **failure mode**: your two mod sets differ (re-check §3.0) | 67798 |
| `[JoinFlow] Received ClientLobbyJoinResponseMessage: ClientLobbyJoinResponseMessage Players: 2 Ascension: N` | client is in the lobby; **this exact line shape appears in your own real MP logs** | real log evidence |
| `Player connected: 1000` | host announced the peer | real log evidence |

### 5.4 Proof that a genuine 2-player run started

The single most valuable line:

```
Embarking on a multiplayer run. Players: Player 1, YETANNIA-YETANNIA_CHARACTER, Player 1000, YETANNIA-YETANNIA_CHARACTER. Ascension: N Seed: XXXXXXXXXXXX
```

Emitted at 384308. With two distinct player ids in the list, `Players.Count == 2`, which means the
multiplayer branch of `CardMultiplayerConstraint` was taken and the 6 multiplayer-only cards were in the
pool. (For contrast, the archived single-player `--bootstrap` MP-mode run could only ever print one id.)

### 5.5 Proof that cross-instance synchronisation is actually happening

| Marker | Meaning | Evidence |
|---|---|---|
| `[StartRunLobby] Received LobbyPlayerSetReadyMessage for player ...` | lobby messages are crossing the socket | real log evidence |
| `[PlayerChoiceSynchronizer] Awaiting remote choice 0 for player ...` | the engine is genuinely waiting on the *other process* for a card choice — this is the path your scry/choice cards exercise | real log evidence |
| `[ActionQueueSynchronizer] Sending message to host requesting to enqueue action ...` | per-action network traffic | real log evidence |
| `[NetQualityTracker]` ping lines | link quality | real log evidence |

For the mod specifically, `Yetannia\Code\Diagnostics\ScryTrace.cs` already documents that a real hang is
plausible exactly where the engine waits for a *human* to answer a card-selection screen — those
`Awaiting remote choice` lines are the ones to pair against your `[scry] #N BEGIN` / `END` markers.

### 5.6 Recommended assertions for the new protocol

1. Both instances logged `Steam initialization skipped`.
2. Exactly one `Embarking on a multiplayer run` line, and it lists **two** player ids.
3. `Awaiting remote choice` appears at least once (proves a real peer round-trip, not a solo lobby).
4. `Replay state divergence!` (61804) does **not** appear.
5. Zero exceptions; every `[scry] #N BEGIN` paired with an `END`, as in your existing single-player
   acceptance table.
6. The 6 multiplayer-only cards each produce their `QA probe:` evidence line in a 2-player run.

---

## 6. VERIFIED vs INFERENCE

### VERIFIED by reading code (line-cited above)

* `--fastmp` accepts `host`, `host_standard`, `host_daily`, `host_custom`, `load`, `join`; unknown values
  only log an error (355246-355295).
* `--fastmp` forces `PlatformType.None` for hosting, and `StartENetHost(33771, 4)` binds
  `0.0.0.0:33771` (358296-358308, 57053-57064).
* `--fastmp=join` connects to `127.0.0.1:33771` with net id from `--clientId`, default `1000`
  (353457-353466).
* `--clientId` also sets `NullPlatformUtilStrategy.LocalPlayerId`, whose default is `1` (54058-54069).
* `--force-steam=off` is the only command-line form that skips Steam initialisation in a retail build;
  bare `--force-steam` and `--force-steam=on` both *enable* it (212620-212626).
* `DebugFriendsButtons` is a hardcoded `false` (353409).
* Steam-off does not break startup: every `SteamInitializer.Initialized` use is guarded (23 sites), cloud
  saves are conditional (29519-29525), and `ReadSteamMods()` is skipped when Steam is off (155562-155565).
* Mods in the local `mods\` folder load regardless of Steam; `mods_STEAMTEST\` is read as Workshop source
  without Steam (155552-155561). Default enabled state is `true` (155595).
* Without `PlayerAgreedToModLoading`, all mods are set `Disabled` (156129-156133); accepting the popup
  writes the flag and then **quits the game** (337519-337531); the popup is auto-added at the main menu
  when `SettingsSave.ModSettings == null` (354834-354837).
* The no-Steam save scope is `user://default/<playerId>/...` (`GetPlatformDirectoryName` 31331-31338,
  `GetAccountScopedBasePath` 31294-31305), and the save store is built from it (29517).
* The join handshake enforces game version, gameplay-mod parity (`ModMismatch`) and `idDatabaseHash`
  (67789-67812), fed by `PeerVersionInfo.LocalDefault()` (55782-55792).
* `RunState.CardMultiplayerConstraint` needs `Players.Count > 1` for multiplayer-only cards
  (38205-38215; enum at 181737-181741).
* `IsReleaseGame()` is hardcoded `true` (211994-211997), making `--autoslay` dead (211927) and `AutoSlayer`
  singleplayer-only (204991-204993).
* Debug console commands are permitted when `ModManager.IsRunningModded()` (451129), and
  `multiplayer test` opens the debug MP scene (186022-186043), whose Host button is
  `StartHost(steam: false)` (454394-454397, 454494-454503) and whose Join button defaults to
  `1000` / `127.0.0.1` (454399-454404).
* `scenes/debug/multiplayer_test.tscn` and `scenes/debug/scene_bootstrapper.tscn` ship in the retail PCK
  (`.tools/qa/r40-sts2-entries.txt:11584` and `:11586`).
* There is no single-instance mutex/lock and no `RestartAppIfNecessary` in the assembly.
* The log path is `OS.GetUserDataDir()/logs/godot.log` and is not account-scoped (205136); `log-file` only
  reaches `AutoSlayer` (211931-211933).

### VERIFIED empirically (no game launched by me)

* `CommandLineHelper` really does receive `--key=value` arguments passed **directly to the exe**: the
  archived logs record `Command Line Args: --autoslay --qagym --qawin --seed=qa5` (and similar), and those
  runs demonstrably consumed the seed through `CommandLineHelper.GetValue("seed")`. This is why the
  `--force-steam=off` / `--fastmp=...` / `--clientId=1000` forms are safe. Note: do **not** put them after
  a `--` separator — `CommandLineHelper` reads `OS.GetCmdlineArgs()`, not the user-args list, and in every
  log checked so far `User Command Line Args:` is empty.
* Real Steam multiplayer sessions have run on this machine (2/3/4-player lobbies in `godot.log` and
  `godot2026-10-14T16.43.48.log`), but always as the *client* of a remote host, and never two instances
  concurrently.
* `%APPDATA%\SlayTheSpire2\default\1\` exists with a `settings.save`, i.e. the Steam-free scope has been
  used before.
* `BaseLib` is absent from `<game>\mods\` and present in the Workshop folder `3737335127` (v3.4.7).

### INFERENCE (not proven — treat as a hypothesis)

* **I1.** That mechanisms A/B will produce a *playable* 2-player run end to end on this machine. Every
  individual step is read in code and the argument-passing is proven, but the combination (two processes,
  no Steam, local player ids 1 and 1000) has **never been executed here**. The first run should be treated
  as a shakedown.
* **I2.** That the pre-existing `default\1\` scope was created by a `--force-steam=off`-style launch. I did
  not read its `settings.save`, so another cause is not excluded.
* **I3.** That copying `default\1\settings.save` to `default\1000\settings.save` will pre-grant mod-loading
  consent for the client and save one launch pair. Plausible from the code (account-scope root, mod list
  inside) but the file's contents were deliberately not inspected.
* **I4.** That a hand-written `YetanniaQA` harness using `TestMode.IsOn = true` +
  `RunManager.SetUpTest(runState, service, disableCombatStateSync: false)` +
  `TestFlags.ShouldSendResumeForRemotePlayers` could drive a fake 2-player run in a single process. The
  seams are public and present, but nothing ships using them and the choice-synchroniser behaviour under
  this configuration is unverified — I would not budget on this without a spike.
* **I5.** That `--position X,Y` (Godot 4 window-position argument) can be used to place the two windows
  side by side. I found no `wpos`/`position` handling in the game assembly, so this would be an
  engine-level argument; I did not confirm the exact Godot 4.5 spelling from the engine binary.
* **I6.** That setting a **per-process `APPDATA`** environment variable would give the second instance its
  own `user://` root (and therefore its own `godot.log`), which would remove the shared-log inconvenience
  of §3.6. Godot's Windows data path is documented as `%APPDATA%`-derived, and `%APPDATA%\SlayTheSpire2`
  matching `user://` is consistent with that, but I could not confirm from the engine source in this
  session that the variable is read live rather than resolved through the shell API. **Cheap test:** launch
  once with `$env:APPDATA` pointed at a scratch folder and see whether a `SlayTheSpire2\logs\godot.log`
  appears there. If it does, it is a strictly better isolation story than §3.6 and worth adopting.

---

## 7. Explicitly out of scope / not possible

* **A true single-instance multiplayer run using the shipped game alone.** No in-process transport, no
  remote-player simulation, and no loopback host ships in this assembly
  (`grep -i "SimulateRemote|Loopback|TestNet|DummyNet|MockNet|LocalTransport|HeadlessNet"` -> zero hits;
  `AbstractTestNetHost` has no subclass). The only single-process paths that touch multiplayer code
  (`--bootstrap` in multiplayer mode, and `.mcr` replays) both end up with `Players.Count == 1` or with
  synchronisation switched off, so **the 6 multiplayer-only cards cannot be exercised by them**.
* **A headless/dedicated second player.** No dedicated-server mode exists; `--headless` is only tolerated
  for logging and Sentry purposes (159458, 190206, 211108, 212004).
* **`--autoslay` driving the multiplayer run.** Dead in retail and singleplayer-only.
* **Testing with a second Steam account.** Not needed for mechanism A, and not investigated.
