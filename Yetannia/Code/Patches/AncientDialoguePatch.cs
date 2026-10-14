using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Ancients;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Ancients;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Gives 耶坦尼娅 her own dialogue at every Ancient, including 建筑师 (The Architect).
///
/// WHY A POSTFIX ON <c>PopulateLocKeys</c> AND NOT ON <c>DefineDialogues</c>:
/// the eight Ancient models and The Architect all reach <c>AncientDialogueSet.PopulateLocKeys</c>
/// through their own <c>DialogueSet</c> getter, which calls it once, immediately after building the
/// set and before the set is ever read (<c>AncientEventModel.DialogueSet</c>;
/// <c>TheArchitect.DialogueSet</c> has its own copy of the same three lines because it is not an
/// <c>AncientEventModel</c>). Hooking there means one patch covers all nine — including the Architect,
/// whose <c>DefineDialogues</c> is a private static method on a different base class — and means
/// vanilla's own key derivation has already finished, so it never touches this mod's entries.
///
/// PatchAll only picks up patch classes that carry a class-level <c>[HarmonyPatch]</c> attribute, which
/// is exactly the failure this mod was bitten by before; both classes below therefore annotate the
/// class, and <see cref="AncientDialogueSelfCheck"/> asserts the attachment at runtime.
/// </summary>
[HarmonyPatch(typeof(AncientDialogueSet), nameof(AncientDialogueSet.PopulateLocKeys))]
internal static class AncientDialoguePatch
{
    [HarmonyPostfix]
    private static void Attach(string ancientEntry, AncientDialogueSet __instance)
    {
        try
        {
            YetanniaAncientDialoguePlan.Attach(__instance, ancientEntry);
        }
        catch (Exception e)
        {
            // Swallowing here would leave the character with no dialogue; the Ancient event still
            // works (it falls back to the vanilla agnostic line, and the Architect has
            // ArchitectNullDialoguePatch), but the log has to say so.
            MainFile.Logger.Error($"ancient dialogue: attach failed for '{ancientEntry}': {e}");
        }
    }
}

/// <summary>
/// Injects this mod's Ancient-dialogue text into the <c>ancients</c> table.
///
/// Same shape as <see cref="Keywords.KeywordLocPatch"/>, <see cref="SettingsLocPatch"/> and
/// <see cref="ModelLocReloadPatch"/>, and for the same reason: the vanilla language dropdown calls
/// <c>LocManager.SetLanguage</c>, which rebuilds every <see cref="LocTable"/> from disk
/// (<c>LoadTablesFromPath</c>). Anything injected once at model-init time is wiped by that, and the
/// player would see raw <c>YETANNIA-TALK.…</c> keys. Filling the freshly loaded table the first time
/// the game hands it to us — keyed on the instance, so each language switch fills its own table
/// exactly once — is what makes the dialogue survive a mid-session language switch.
///
/// The keys live in this mod's own namespace, so vanilla entries are never read or written.
/// </summary>
[HarmonyPatch(typeof(LocManager), nameof(LocManager.GetTable))]
internal static class AncientDialogueLocPatch
{
    // Reference-keyed so that each freshly loaded LocTable (i.e. each language switch) is patched once.
    private static readonly ConditionalWeakTable<LocTable, object> Injected = new();

    [HarmonyPostfix]
    private static void Inject(string name, LocTable __result)
    {
        if (__result == null) return;
        if (name != YetanniaAncientDialoguePlan.Table) return;
        if (Injected.TryGetValue(__result, out _)) return;

        Injected.Add(__result, null);

        // Deliberately not language-dependent: the user's dialogue is Chinese only and is registered
        // for every language so that a raw key can never be rendered. `Loc.IsEnglish` is passed so the
        // call site already carries the language for the day English copy exists.
        __result.MergeWith(YetanniaAncientDialoguePlan.LocEntries(Loc.IsEnglish));
    }
}

/// <summary>
/// Stops vanilla's character-agnostic (<c>ANY</c>) Ancient lines from competing with Yetannia's own.
///
/// THE PROBLEM, read out of the game rather than guessed. <c>AncientDialogueSet.GetValidDialogues</c>
/// (<c>Core/Entities/Ancients/AncientDialogueSet.cs:104-138</c>) documents its priority at <c>:90-95</c>:
/// (1) <c>FirstVisitEverDialogue</c> when <c>totalVisits == 0</c>; (2) the visit-exact group for this
/// character (<c>:111-119</c>); (3) the visit-exact agnostic group (<c>:120-127</c>); (4) the repeating
/// pool (<c>:128-137</c>). Branch 4 appends the character's repeating entries *and* every repeating
/// <c>AgnosticDialogues</c> entry into one list, and the caller then picks one of them at random
/// (<c>Core/Nodes/Rooms/NEventRoom.cs:243-244</c>: <c>Rng.Chaotic.NextItem(validDialogues)</c>).
/// Yetannia's authored groups are exact-matched only on the 1st..3rd visit (see
/// <see cref="YetanniaAncientDialoguePlan"/>), so from the 4th visit on her seven repeating entries share
/// that pool with vanilla's generic <c>&lt;ANCIENT&gt;.talk.ANY.&lt;n&gt;</c> lines — measured before this
/// patch, DARV: <c>charVisits=3 candidates=9 ours=7</c>, i.e. a 2-in-9 chance of a line that was never
/// written for her.
///
/// WHAT THIS DOES. A postfix that drops exactly those entries which are elements of
/// <c>AgnosticDialogues</c> — vanilla's <c>ANY</c> pool — and only when the visiting character is
/// Yetannia and at least one of her own entries would survive. Vanilla characters never get past the
/// character test, and no vanilla object is modified: only the returned sequence changes.
///
/// WHY IT CANNOT EMPTY THE POOL. Emptying it is not a cosmetic failure. <c>Rng.NextItem</c> returns
/// <c>default</c> for an empty sequence (<c>Core/Random/Rng.cs:289-299</c>) and
/// <c>NEventRoom.SetupLayout</c> dereferences the result without a guard (<c>:244-249</c>), so an empty
/// candidate set is a NullReferenceException, not a missing line. Two cases are therefore deliberately
/// left exactly as they were:
///   * The Architect's 2nd+ win. <c>TheArchitect.LoadDialogue</c> calls this method with
///     <c>allowAnyCharacterDialogues: false</c> and <c>AgnosticDialogues</c> is empty
///     (<c>Core/Models/Events/TheArchitect.cs:306, :314</c>), so there is nothing to drop and the
///     filter returns before touching the result; his 0 candidates still reach
///     <see cref="ArchitectNullDialoguePatch"/>.
///   * Any Ancient/visit where filtering would leave nothing (our pool absent or empty — e.g. the plan
///     could not resolve the character id). The unfiltered list is returned instead, which is exactly
///     the pre-patch behaviour: vanilla's line, no crash, no raw key.
/// <c>totalVisits == 0</c> returns vanilla's <c>FirstVisitEverDialogue</c> (<c>:106-109</c>), which is
/// not part of the agnostic pool and is therefore never dropped.
/// </summary>
[HarmonyPatch(typeof(AncientDialogueSet), nameof(AncientDialogueSet.GetValidDialogues))]
internal static class AncientDialogueVanillaAgnosticFilterPatch
{
    [HarmonyPostfix]
    private static void Filter(ModelId characterId, int charVisits, int totalVisits,
        AncientDialogueSet __instance, ref IEnumerable<AncientDialogue> __result)
    {
        try
        {
            if (__result == null || __instance == null || characterId == null) return;

            // Yetannia only. This is the whole guard for vanilla characters: they never reach the
            // enumeration below, let alone a replacement of the result.
            var ourEntry = YetanniaAncientDialoguePlan.CharacterEntry;
            if (string.IsNullOrEmpty(ourEntry) ||
                !string.Equals(characterId.Entry, ourEntry, StringComparison.Ordinal)) return;

            var agnostic = __instance.AgnosticDialogues;
            if (agnostic == null || agnostic.Count == 0) return; // The Architect: nothing vanilla to drop

            var before = __result as IList<AncientDialogue> ?? __result.ToList();
            var kept = new List<AncientDialogue>(before.Count);
            var dropped = new List<string>();
            foreach (var dialogue in before)
            {
                if (IsAgnostic(dialogue, agnostic))
                {
                    dropped.Add(Describe(dialogue));
                    continue;
                }
                kept.Add(dialogue);
            }

            // Branches (1)..(3) contain no agnostic entry, so there is nothing to do and nothing to say.
            if (dropped.Count == 0) return;

            if (kept.Count == 0)
            {
                // Filtering would leave the caller with an empty sequence, which is an NRE at
                // NEventRoom.cs:245 (see the class comment). Previous behaviour stands.
                MainFile.Logger.Warn(
                    $"ancient dialogue: only vanilla ANY candidates for {ourEntry} at charVisits={charVisits} " +
                    $"(totalVisits={totalVisits}); leaving them in place: [{string.Join(", ", dropped)}]");
                return;
            }

            MainFile.Logger.Info(
                $"ancient dialogue: dropped {dropped.Count} vanilla ANY candidate(s) for {ourEntry} at " +
                $"charVisits={charVisits} (totalVisits={totalVisits}): {before.Count} -> {kept.Count} " +
                $"dropped=[{string.Join(", ", dropped)}]");
            __result = kept;
        }
        catch (Exception e)
        {
            // Never let a diagnostic turn into a missing dialogue: on failure the unfiltered result the
            // game produced is what the caller keeps.
            MainFile.Logger.Error($"ancient dialogue: vanilla ANY filter failed: {e}");
        }
    }

    /// <summary>Element identity against the set's own vanilla agnostic pool.</summary>
    private static bool IsAgnostic(AncientDialogue dialogue, IReadOnlyList<AncientDialogue> agnostic)
    {
        for (var i = 0; i < agnostic.Count; i++)
        {
            if (ReferenceEquals(agnostic[i], dialogue)) return true;
        }
        return false;
    }

    /// <summary>The dropped entry's own loc key (&lt;ANCIENT&gt;.talk.ANY.…), for the log.</summary>
    private static string Describe(AncientDialogue dialogue)
    {
        if (dialogue?.Lines == null || dialogue.Lines.Count == 0) return "<no lines>";
        var text = dialogue.Lines[0].LineText;
        return text == null ? "<no LineText>" : text.LocEntryKey;
    }
}
