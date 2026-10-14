using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;
using MegaCrit.Sts2.Core.Nodes.Screens.CharacterSelect;
using MegaCrit.Sts2.Core.Nodes.Screens.MainMenu;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using Yetannia.YetanniaCode.Character;

namespace Yetannia.YetanniaCode.Voice;

/// <summary>
/// The seven voice moments the game has no character-SFX slot for, plus the two that DO have a slot but
/// whose slot the game never reaches.
///
/// WHY THESE EXIST AT ALL. A sentinel (see <see cref="VoicePack"/>) can only hijack a sound the game was
/// already going to ask for. Only four character slots are ever consulted: attack and cast come from
/// <c>CreatureCmd.TriggerAnim</c>, death from <c>NCreature.StartDeathAnim</c>, select from
/// <c>NCharacterSelectScreen.SelectCharacter</c> — and two of those four turn out never to reach
/// <c>SfxCmd.Play</c> at all (see the per-class notes below). Run start, combat start, card reward, rest,
/// shop, event and relic have no slot whatsoever, so the only correct seam is the moment itself.
///
/// THE GUARD. Every hook watches a *global* game event, so each one has to answer "is the local player
/// Yetannia?" before making a sound — otherwise a Silent run would start speaking in Yetannia's voice.
/// <see cref="IsLocalYetannia()"/> is that answer, and it is the one place that reads the run state.
///
/// One [HarmonyPatch] class per target, each carrying the attribute on the CLASS: a helper class with the
/// attribute only on its methods is skipped silently by PatchAll, which this project has already paid for
/// twice. <see cref="VoicePatchSelfCheck"/> reports whether every one of them actually landed.
/// </summary>
internal static class VoiceMoments
{
    /// <summary>
    /// True when the local player of the current run is Yetannia. Read from the live run state rather than
    /// from a captured reference, because a run can start and end without the mod being reloaded.
    /// </summary>
    internal static bool IsLocalYetannia()
    {
        try
        {
            return IsLocalYetannia(RunManager.Instance?.DebugOnlyGetState());
        }
        catch (Exception e)
        {
            // GetMe throws when the local player is not in the collection (e.g. between runs). Sound is
            // never worth an exception escaping into an engine callback.
            MainFile.Logger.Debug($"[voice] local player lookup failed: {e.Message}");
            return false;
        }
    }

    /// <summary>Same guard, for hooks that already hold the run state (avoids a second global lookup).</summary>
    internal static bool IsLocalYetannia(IPlayerCollection players)
    {
        if (players == null)
        {
            return false;
        }
        try
        {
            return LocalContext.GetMe(players)?.Character is YetanniaCharacter;
        }
        catch (Exception e)
        {
            MainFile.Logger.Debug($"[voice] local player lookup failed: {e.Message}");
            return false;
        }
    }

    /// <summary>Plays a line if the local player is Yetannia. Never throws.</summary>
    internal static void Fire(string stem, bool isOurs)
    {
        if (!isOurs)
        {
            return;
        }
        try
        {
            VoicePack.PlayLine(stem);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] moment '{stem}' failed: {e}");
        }
    }
}

// ---------------------------------------------------------------------------- select
//
// MEASURED: this moment is wired to the sentinel and still reached FMOD. `SelectCharacter` DOES call
// `SfxCmd.Play(characterModel.CharacterSelectSfx)` (NCharacterSelectScreen.cs:817, and the sentinel is
// what `YetanniaCharacter.CharacterSelectSfx` returns), yet the live game log shows the string
// "event:/sfx/characters/yetannia/yetannia_select" arriving at NAudioManager.PlayOneShot with NO
// "[voice]" line from our prefix — i.e. the call did not travel through the patched method. Something in
// the installed mod stack (RitsuLib transpiles `SelectCharacter` for the background factory; see
// CharacterSelectBgPathPatch.cs in RitsuLib) means the patched call site cannot be relied on, so the
// moment itself is hooked here as well. The sentinel route now swallows this stem without playing (see
// VoicePack.VisitOwnedStems), so this hook is the line's ONLY source and a click can never double it.
//
// ONCE PER VISIT, NOT ONCE PER CLICK. The character-select screen is a *cached* submenu — created once and
// re-shown for every visit (NMainMenuSubmenuStack.cs:285-291 caches `_characterSelectSubmenu`) — so
// "once per instance" would mean "once per game session", which is wrong in the other direction: leaving
// the screen and coming back is a new visit and should be able to speak again. The game's own per-visit
// signal is used instead:
//   * enter = `NSubmenuStack.Push` calls `screen.OnSubmenuOpened()` (NSubmenuStack.cs:128) — every entry
//     path goes through it, including `NSingleplayerSubmenu.OpenCharacterSelect` (NSingleplayerSubmenu.cs:156);
//   * leave = `NSubmenuStack.Pop` calls `screen.OnSubmenuClosed()` (NSubmenuStack.cs:141), and the back
//     button is literally `_stack.Pop()` (NSubmenu.cs:135-138).
// Browsing tiles calls neither, so it stays inside one visit. See VoiceSelectVisit.
//
// WHAT "ONCE PER VISIT" ACTUALLY MEANS, precisely: opening the screen does NOT select Yetannia. The last
// thing `OnSubmenuOpened` does is call `Select()` on the FIRST character button
// (NCharacterSelectScreen.cs:587-590), which runs `SelectCharacter` for that character — in this profile
// the Ironclad, so what plays on entry is the Ironclad's own vanilla select sound, not this line. Yetannia
// speaks the first time SHE is selected inside that visit, and never again until the screen is re-entered.
// (Even if the first tile happened to be her, there is still exactly one play: `TryConsume` marks the visit
// as spoken *before* the sound is started.)
[HarmonyPatch(typeof(NCharacterSelectScreen), nameof(NCharacterSelectScreen.SelectCharacter))]
internal static class VoiceSelectMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix(NCharacterSelectScreen __instance, NCharacterSelectButton charSelectButton, CharacterModel characterModel)
    {
        try
        {
            // Mirror the vanilla condition: the random button deliberately plays no character line.
            if (charSelectButton != null && charSelectButton.IsRandom)
            {
                return;
            }
            if (characterModel is not YetanniaCharacter)
            {
                return;
            }
            // Same visit, already spoken: stay silent (this is the "browsing must not replay" rule).
            if (!VoiceSelectVisit.TryConsume(__instance))
            {
                MainFile.Logger.Debug("[voice] select: already played in this visit; not replaying");
                return;
            }
            VoiceMoments.Fire(VoicePack.SelectStem, true);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] select hook failed: {e}");
        }
    }
}

/// <summary>
/// Per-visit state for the character-select line.
///
/// Keyed on the screen instance with a <c>ConditionalWeakTable</c> (reference identity, and the entry dies
/// with the node), so two live screens can never share a visit. Note that instance identity is NOT what
/// makes re-entry work — the same cached instance is reused for every visit — which is exactly why the
/// reset lives in <see cref="Opened"/> rather than in the constructor or in `_Ready`.
///
/// The happy path is: <see cref="Opened"/> clears the flag when the screen is pushed, the first Yetannia
/// selection of that visit consumes it, and <see cref="Closed"/> drops the entry when the screen is
/// popped. <see cref="TryConsume"/> deliberately treats "no entry" as "not played yet", so a screen that
/// is somehow shown without going through `Push` still speaks once rather than never.
/// </summary>
internal static class VoiceSelectVisit
{
    private sealed class VisitState
    {
        internal bool Played;
    }

    private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<NCharacterSelectScreen, VisitState> Visits = new();

    /// <summary>Entering the screen: this visit has not spoken yet.</summary>
    internal static void Opened(NCharacterSelectScreen screen)
    {
        if (screen == null)
        {
            return;
        }
        Visits.GetOrCreateValue(screen).Played = false;
    }

    /// <summary>Leaving the screen: forget it, so nothing lingers on a cached submenu.</summary>
    internal static void Closed(NCharacterSelectScreen screen)
    {
        if (screen != null)
        {
            Visits.Remove(screen);
        }
    }

    /// <summary>True exactly once per visit; every later call in the same visit returns false.</summary>
    internal static bool TryConsume(NCharacterSelectScreen screen)
    {
        if (screen == null)
        {
            return true;
        }
        var state = Visits.GetOrCreateValue(screen);
        if (state.Played)
        {
            return false;
        }
        state.Played = true;
        return true;
    }
}

/// <summary>
/// Marks the start of a visit. A PREFIX, not a postfix: `NCharacterSelectScreen.OnSubmenuOpened` ends by
/// calling `Select()` on the first character button (NCharacterSelectScreen.cs:589), which runs
/// `SelectCharacter` — so the visit must be cleared before the body runs, or an entry-time selection would
/// be judged against the previous visit's state.
/// </summary>
[HarmonyPatch(typeof(NCharacterSelectScreen), nameof(NCharacterSelectScreen.OnSubmenuOpened))]
internal static class VoiceSelectVisitOpenPatch
{
    [HarmonyPrefix]
    private static void Prefix(NCharacterSelectScreen __instance)
    {
        try
        {
            VoiceSelectVisit.Opened(__instance);
            MainFile.Logger.Debug("[voice] select visit opened");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] select visit-open hook failed: {e}");
        }
    }
}

/// <summary>Marks the end of a visit (back button -&gt; `_stack.Pop()` -&gt; `OnSubmenuClosed`).</summary>
[HarmonyPatch(typeof(NCharacterSelectScreen), nameof(NCharacterSelectScreen.OnSubmenuClosed))]
internal static class VoiceSelectVisitClosePatch
{
    [HarmonyPrefix]
    private static void Prefix(NCharacterSelectScreen __instance)
    {
        try
        {
            VoiceSelectVisit.Closed(__instance);
            MainFile.Logger.Debug("[voice] select visit closed");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] select visit-close hook failed: {e}");
        }
    }
}

// ---------------------------------------------------------------------------- select: the random tile
//
// The random tile is a SECOND way to end up on Yetannia, and it shares none of the manual path's audio:
//   * clicking random routes to `SelectCharacter(randomButton, RandomCharacter)`, and vanilla skips its
//     own sfx for `IsRandom` (NCharacterSelectScreen.cs:815-818) — so the hook above deliberately ignores
//     it and never speaks for a roll;
//   * when the lobby later resolves the roll, `PlayerChanged(player, isRandomCharacterResolution: true)`
//     calls `OnLocalCharacterChangedForRandom(resolvedCharacter)` (NCharacterSelectScreen.cs:964-972),
//     which plays `resolvedCharacter.CharacterSelectSfx` (NCharacterSelectScreen.cs:694).
//
// That route is exactly why this class exists. It used to reach the sentinel, but the sentinel now
// swallows the select stem without playing it (see VoicePack.VisitOwnedStems) so that a click can never
// double the line — which would have made a roll onto Yetannia silent. That is a regression this work
// would have introduced, so it is fixed here instead of being left as a trap: the seam is the resolved
// character itself, so a roll onto her speaks exactly like a click on her tile, and it shares the same
// per-visit gate (a roll followed by a manual click in the same visit is still one line, in either order).
[HarmonyPatch(typeof(NCharacterSelectScreen), "OnLocalCharacterChangedForRandom", new[] { typeof(CharacterModel) })]
internal static class VoiceSelectRandomMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix(NCharacterSelectScreen __instance, CharacterModel characterModel)
    {
        try
        {
            if (characterModel is not YetanniaCharacter)
            {
                return;
            }
            if (!VoiceSelectVisit.TryConsume(__instance))
            {
                MainFile.Logger.Debug("[voice] select: the random tile resolved to Yetannia in a visit that already spoke; not replaying");
                return;
            }
            VoiceMoments.Fire(VoicePack.SelectStem, true);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] select (random tile) hook failed: {e}");
        }
    }
}

// ---------------------------------------------------------------------------- run start
//
// `NRun.Create(RunState)` is called once per run, with the run state in hand — so unlike the other hooks
// this one needs no global lookup and cannot race the state being installed.
[HarmonyPatch(typeof(NRun), nameof(NRun.Create))]
internal static class VoiceRunStartMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix(RunState state)
    {
        VoiceMoments.Fire(VoicePack.RunStartStem, VoiceMoments.IsLocalYetannia(state));
    }
}

// ---------------------------------------------------------------------------- combat start
//
// NCombatRoom is also created in VisualOnly (combat-style events, enemies visible but not fightable) and
// FinishedCombat (a save loaded after the fight) modes, so the line is gated on ActiveCombat.
[HarmonyPatch(typeof(NCombatRoom), nameof(NCombatRoom._Ready))]
internal static class VoiceCombatStartMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix(NCombatRoom __instance)
    {
        try
        {
            if (__instance.Mode != CombatRoomMode.ActiveCombat)
            {
                return;
            }
            VoiceMoments.Fire(VoicePack.CombatStartStem, VoiceMoments.IsLocalYetannia());
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] combat-start hook failed: {e}");
        }
    }
}

// ---------------------------------------------------------------------------- card reward
[HarmonyPatch(typeof(NCardRewardSelectionScreen), nameof(NCardRewardSelectionScreen._Ready))]
internal static class VoiceCardRewardMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix()
    {
        VoiceMoments.Fire(VoicePack.CardRewardStem, VoiceMoments.IsLocalYetannia());
    }
}

// ---------------------------------------------------------------------------- rest site (campfire)
//
// The room, not the figure: NRestSiteCharacter is created once per player, so hooking it would speak once
// per player in multiplayer rather than once per visit.
[HarmonyPatch(typeof(NRestSiteRoom), nameof(NRestSiteRoom._Ready))]
internal static class VoiceRestMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix()
    {
        VoiceMoments.Fire(VoicePack.RestStem, VoiceMoments.IsLocalYetannia());
    }
}

// ---------------------------------------------------------------------------- shop
[HarmonyPatch(typeof(NMerchantRoom), nameof(NMerchantRoom._Ready))]
internal static class VoiceShopMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix()
    {
        VoiceMoments.Fire(VoicePack.ShopStem, VoiceMoments.IsLocalYetannia());
    }
}

// ---------------------------------------------------------------------------- event
[HarmonyPatch(typeof(NEventRoom), nameof(NEventRoom._Ready))]
internal static class VoiceEventMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix()
    {
        VoiceMoments.Fire(VoicePack.EventStem, VoiceMoments.IsLocalYetannia());
    }
}

// ---------------------------------------------------------------------------- relic obtained
//
// RelicCmd.Obtain is the single acquisition path (reward screen, shop purchase, chest, every event, the
// rest-site dig options), and it is NOT the path the starting relic takes — Player.PopulateStartingRelics
// calls Player.AddRelicInternal directly — so hooking here gives "you got a relic" and not "your run
// began". LocalContext.IsMe is the same check the game itself makes before animating the HUD row.
[HarmonyPatch(typeof(RelicCmd), nameof(RelicCmd.Obtain), new[] { typeof(RelicModel), typeof(Player), typeof(int) })]
internal static class VoiceRelicMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix(Player player)
    {
        try
        {
            var ours = LocalContext.IsMe(player) && player?.Character is YetanniaCharacter;
            VoiceMoments.Fire(VoicePack.RelicStem, ours);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] relic hook failed: {e}");
        }
    }
}

// ---------------------------------------------------------------------------- death
//
// MEASURED, and the reason the death line never played: every route to the player's death SFX is inside
// `if (_spineAnimator != null)` in NCreature.StartDeathAnim (NCreature.cs:944), and a Node2D + flipbook
// character never builds a SpineAnimator — so `SfxCmd.PlayDeath(Entity.Player)` at NCreature.cs:953 is not
// merely un-intercepted, it is never reached. (Even if it were, SfxCmd.PlayDeath calls
// NAudioManager.PlayOneShot(player.Character.DeathSfx) directly, bypassing SfxCmd.Play — SfxCmd.cs:94-100.)
// StartDeathAnim itself runs for every creature regardless of rig (CreatureCmd.Kill -> NCreature.cs:546),
// which makes it the correct seam: it is the moment, not the Spine rig's idea of the moment.
[HarmonyPatch(typeof(NCreature), nameof(NCreature.StartDeathAnim))]
internal static class VoiceDeathMomentPatch
{
    [HarmonyPostfix]
    private static void Postfix(NCreature __instance)
    {
        try
        {
            var entity = __instance?.Entity;
            var player = entity?.Player;
            VoiceMoments.Fire(VoicePack.DeathStem, player != null && player.Character is YetanniaCharacter);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] death hook failed: {e}");
        }
    }
}

/// <summary>
/// Reports, once, whether every voice patch in this file actually attached.
///
/// This is not belt-and-braces: <c>PatchAll</c> silently skips a class whose [HarmonyPatch] attribute sits
/// on its methods instead of on the class, and a missed attachment here is exactly the failure mode the
/// user reported (a wired-up moment that never fires). One line per target, from the live Harmony patch
/// table, turns "the campfire is still silent" into a one-line answer.
///
/// Runs on NMainMenu._Ready like the other self-checks: by then every mod's PatchAll has run.
/// </summary>
[HarmonyPatch(typeof(NMainMenu), nameof(NMainMenu._Ready))]
internal static class VoicePatchSelfCheck
{
    private static bool _reported;

    [HarmonyPostfix]
    private static void Report()
    {
        if (_reported)
        {
            return;
        }
        _reported = true;

        try
        {
            Report1("sfx.play", AccessTools.Method(typeof(SfxCmd), "Play", new[] { typeof(string), typeof(float) }));
            Report1("audio.oneshot", AccessTools.Method(typeof(MegaCrit.Sts2.Core.Nodes.Audio.NAudioManager), "PlayOneShot", new[] { typeof(string), typeof(float) }));
            Report1("audio.oneshot.params", AccessTools.Method(typeof(MegaCrit.Sts2.Core.Nodes.Audio.NAudioManager), "PlayOneShot", new[] { typeof(string), typeof(Dictionary<string, float>), typeof(float) }));
            Report1("moment.select", AccessTools.Method(typeof(NCharacterSelectScreen), "SelectCharacter", new[] { typeof(NCharacterSelectButton), typeof(CharacterModel) }));
            Report1("select.visitopen", AccessTools.Method(typeof(NCharacterSelectScreen), "OnSubmenuOpened"));
            Report1("select.visitclose", AccessTools.Method(typeof(NCharacterSelectScreen), "OnSubmenuClosed"));
            Report1("select.random", AccessTools.Method(typeof(NCharacterSelectScreen), "OnLocalCharacterChangedForRandom", new[] { typeof(CharacterModel) }));
            Report1("moment.runstart", AccessTools.Method(typeof(NRun), "Create", new[] { typeof(RunState) }));
            Report1("moment.combatstart", AccessTools.Method(typeof(NCombatRoom), "_Ready"));
            Report1("moment.cardreward", AccessTools.Method(typeof(NCardRewardSelectionScreen), "_Ready"));
            Report1("moment.rest", AccessTools.Method(typeof(NRestSiteRoom), "_Ready"));
            Report1("moment.shop", AccessTools.Method(typeof(NMerchantRoom), "_Ready"));
            Report1("moment.event", AccessTools.Method(typeof(NEventRoom), "_Ready"));
            Report1("moment.relic", AccessTools.Method(typeof(RelicCmd), "Obtain", new[] { typeof(RelicModel), typeof(Player), typeof(int) }));
            Report1("moment.death", AccessTools.Method(typeof(NCreature), "StartDeathAnim", new[] { typeof(bool) }));
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] patch self-check failed: {e}");
        }
    }

    private static void Report1(string label, MethodBase target)
    {
        if (target == null)
        {
            MainFile.Logger.Error($"[voice] patch self-check: {label} target method NOT FOUND");
            return;
        }
        var info = Harmony.GetPatchInfo(target);
        var mine = 0;
        if (info != null)
        {
            mine += info.Prefixes.Count(p => p.owner == MainFile.ModId);
            mine += info.Postfixes.Count(p => p.owner == MainFile.ModId);
        }
        var all = (info?.Prefixes?.Count ?? 0) + (info?.Postfixes?.Count ?? 0) + (info?.Transpilers?.Count ?? 0);
        MainFile.Logger.Info($"[voice] patch self-check: {label,-24} ours={mine} total={all}");
    }
}
