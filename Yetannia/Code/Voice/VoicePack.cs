using System;
using System.Collections.Generic;
using BaseLib.Audio;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Voice;

/// <summary>Which dub to play. 关闭 means the character simply has no voice — see <see cref="VoicePack.TryPlay"/>.</summary>
internal enum VoiceLanguage
{
    Chinese,
    Japanese,
    Off,
}

/// <summary>
/// Yetannia's voice lines, played over the top of the base game's sound system.
///
/// Why this exists at all: the game's character SFX are **FMOD events** (`event:/sfx/characters/&lt;id&gt;/...`),
/// not files, and nothing in the assembly loads an extra FMOD bank from a mod folder — so a mod cannot add
/// new events. The only way to give a custom character her own voice is to play an ordinary audio file
/// ourselves, which BaseLib exposes through <see cref="ModAudio"/>.
///
/// There are **eleven moments**, in two groups, and both go through <see cref="PlayLine"/> so the language
/// setting and 关闭 can only ever be implemented once:
///
///   * Four are driven by <b>sentinels</b>: <c>YetanniaCharacter</c> points the game's own character-SFX
///     slots at event paths that deliberately DO NOT EXIST (<c>.../yetannia/yetannia_attack</c>), and
///     <see cref="Patches.VoiceSfxPatch"/> / <see cref="Patches.VoiceAudioManagerPatch"/> watch for exactly
///     those strings and play our ogg instead. This covers attack, cast, die and select, which is as much
///     as a sentinel can cover: the sentinel only exists in the slots the game itself consults.
///   * Seven have no slot to hijack — run start, combat start, card reward, rest site, shop, event and
///     relic — so <see cref="VoiceMoments"/> hooks the moment itself and calls <see cref="PlayLine"/>.
///
/// 关闭 is deliberately implemented as "swallow our own sentinel and play nothing". It never returns
/// <c>false</c> for a sentinel, so it cannot accidentally fall through to some other sound — and because the
/// only string it ever touches is our own non-existent event, music, UI and enemy audio are untouched.
///
/// Volume/pitch are deliberately left at the default (1.0/1.0) for every line: the clips were cut from the
/// same dub at a consistent level, so any per-line tweak would be a mastering change rather than a fix.
/// </summary>
internal static class VoicePack
{
    // ------------------------------------------------------------------ sentinels
    //
    // These must match YetanniaCharacter's slots exactly. The character overrides them to these strings;
    // nothing else in the game (or in any other mod) can produce them.

    internal const string AttackEvent = "event:/sfx/characters/yetannia/yetannia_attack";
    internal const string CastEvent = "event:/sfx/characters/yetannia/yetannia_cast";
    internal const string DeathEvent = "event:/sfx/characters/yetannia/yetannia_die";
    internal const string SelectEvent = "event:/sfx/characters/yetannia/yetannia_select";

    // ------------------------------------------------------------------ moment stems
    //
    // File names under audio/voice/<lang>/, i.e. ModAssets.Voice(lang, stem). Named after the MOMENT, not
    // after the source clip from the dub — which is why "select" is the dub's `Summon` under a different
    // name. .tools/voice-encode.py holds the full moment -> source-clip table.

    internal const string AttackStem = "attack";             // dub: Strike_Out_02
    internal const string CastStem = "cast";                 // dub: Skill_1_p01
    internal const string DeathStem = "die";                 // dub: Send_Back
    internal const string SelectStem = "select";             // dub: Summon
    internal const string RunStartStem = "run_start";        // dub: Send_Out
    internal const string CombatStartStem = "combat_start";  // dub: Bat_Stage
    internal const string CardRewardStem = "card_reward";    // dub: Role_Skillup
    internal const string RestStem = "rest";                 // dub: Work_Start
    internal const string ShopStem = "shop";                 // dub: Manage_01
    internal const string EventStem = "event";               // dub: Event
    internal const string RelicStem = "relic";               // dub: Notification

    /// <summary>Sentinel event path -> file stem under <c>audio/voice/&lt;lang&gt;/</c>.</summary>
    private static readonly Dictionary<string, string> Lines = new(StringComparer.Ordinal)
    {
        [AttackEvent] = AttackStem,
        [CastEvent] = CastStem,
        [DeathEvent] = DeathStem,
        [SelectEvent] = SelectStem,
    };

    /// <summary>
    /// How long the same line is ignored after it starts — and it only applies to the two stems that have
    /// TWO routes to the same line: the sentinel (when the game's own SFX slot is what fires) and the
    /// moment hook in <see cref="VoiceMoments"/> (which fires from the same call stack, microseconds later
    /// for select, and from inside StartDeathAnim for die). Both routes are kept — the sentinel is the
    /// forward-compatible one and the hook is the one that works when the slot is never consulted — so the
    /// second one has to be dropped, and 200 ms is far longer than that gap.
    ///
    /// Everything else deliberately has NO guard: attack and cast have only the sentinel route, and the
    /// other five moments fire from a single room/screen callback. Suppressing a repeat there would drop a
    /// real line (an attack animation that runs twice in a frame or two), which is the exact failure this
    /// whole file exists to fix.
    ///
    /// This is the ROUTE guard only — "two different code paths asked for the same line at the same
    /// instant, keep one". It is not the select screen's per-visit gate, which lives in
    /// <see cref="VoiceMoments"/> and answers a completely different question ("has this screen already
    /// had its line?"). The two are deliberately disjoint: select is no longer reachable by two routes at
    /// all (see <see cref="VisitOwnedStems"/>), so only die is left here.
    /// </summary>
    private const ulong RepeatGuardMs = 200;

    private static readonly HashSet<string> RouteDedupedStems = new(StringComparer.Ordinal)
    {
        DeathStem,
    };

    /// <summary>
    /// Stems that the sentinel must swallow WITHOUT playing, because exactly one place owns their
    /// playback. Currently just the character-select line: the game's character-select screen is a cached
    /// submenu that outlives every visit, so its line cannot be "played once per screen instance" — it has
    /// to be gated on the visit, and the only code that knows about visits is
    /// <see cref="VoiceMoments"/>'s screen hooks. Swallowing here means a character being clicked can
    /// never produce a second copy on top of the gated one, and it also silences the sentinel on the
    /// screens we deliberately do not voice (the custom-run / multiplayer-load previews).
    /// </summary>
    private static readonly HashSet<string> VisitOwnedStems = new(StringComparer.Ordinal)
    {
        SelectStem,
    };

    private static readonly Dictionary<string, ulong> LastPlayedMs = new(StringComparer.Ordinal);

    /// <summary>Stems already reported in the log, so the first play of each is visible without spam.</summary>
    private static readonly HashSet<string> ReportedOnce = new(StringComparer.Ordinal);

    /// <summary>
    /// The live setting. Starts on Japanese; the mod-config UI overwrites it on load (see
    /// <see cref="VoiceConfig"/>). Read every call rather than cached, because the player can change it
    /// mid-run from the settings screen.
    /// </summary>
    internal static VoiceLanguage Language { get; set; } = VoiceLanguage.Japanese;

    /// <summary>
    /// True when <paramref name="sfx"/> named one of our lines and the caller should therefore NOT let FMOD
    /// play it. False means "not ours, carry on" — the patch returns straight through.
    /// </summary>
    internal static bool TryPlay(string? sfx)
    {
        if (sfx == null || !Lines.TryGetValue(sfx, out var stem))
        {
            return false;
        }

        if (VisitOwnedStems.Contains(stem))
        {
            // Ours, but not this route's to play: swallowed silently so no FMOD lookup happens either.
            MainFile.Logger.Debug($"[voice] {stem} is owned by its moment hook; sentinel swallowed");
            return true;
        }

        PlayLine(stem);
        return true;
    }

    /// <summary>
    /// Plays one line by stem. Used by the sentinel path above and directly by <see cref="VoiceMoments"/>
    /// for the seven moments the game has no SFX slot for. Returns true when a sound was actually started.
    ///
    /// Never throws: every caller is on a game code path (a room opening, a relic being granted) where a
    /// failure must not be able to break the game. Failures are logged instead.
    /// </summary>
    internal static bool PlayLine(string stem)
    {
        try
        {
            // 关闭: play nothing. Not an error and not a warning — it is the documented behaviour.
            if (Language == VoiceLanguage.Off)
            {
                return false;
            }

            var now = Godot.Time.GetTicksMsec();
            if (RouteDedupedStems.Contains(stem) && LastPlayedMs.TryGetValue(stem, out var last) && now >= last && now - last < RepeatGuardMs)
            {
                return false;
            }

            var lang = Language == VoiceLanguage.Chinese ? "cn" : "jp";
            // SimplestPath is built through ModAssets so a renamed asset cannot leave a stale res:// string.
            var path = ModAssets.Voice(lang, stem);

            // Check existence OURSELVES rather than relying on the caller. BaseLib's
            // ModSound.GetOrLoadStream() already swallows a failure — it logs its own WARN and returns null
            // instead of throwing — so PlaySound is a silent no-op for a missing file and a try/catch would
            // never fire. Verified: a deliberately bogus path produces an engine ERROR plus a BaseLib WARN,
            // and never reaches an exception. This check is what makes a missing voice line diagnosable.
            if (!Godot.ResourceLoader.Exists(path))
            {
                MainFile.Logger.Warn($"[voice] missing audio file, playing nothing: {path}");
                return false;
            }

            LastPlayedMs[stem] = now;
            var sound = new ModSound(path);
            ModAudio.PlaySound(sound);

            // One Info line per stem per session: enough to answer "did that moment fire at all?" from any
            // player's log without turning a 200-line combat into hundreds of voice lines.
            if (ReportedOnce.Add(stem))
            {
                MainFile.Logger.Info($"[voice] first play: {stem} -> {path}");
            }
            else
            {
                MainFile.Logger.Debug($"[voice] play: {stem} -> {path}");
            }

            return true;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] could not play '{stem}' ({Language}): {e}");
            return false;
        }
    }
}
