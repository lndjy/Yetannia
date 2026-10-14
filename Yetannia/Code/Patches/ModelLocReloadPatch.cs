using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using BaseLib.Abstracts;
using BaseLib.Patches.Localization;
using HarmonyLib;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Re-injects this mod's model text (<see cref="ILocalizationProvider.Localization"/>) after the player
/// changes the game's language, so the mod's cards / powers / characters / relics keep their names and
/// descriptions instead of degrading to raw keys.
///
/// WHY THIS EXISTS — BaseLib's <c>ModelLocPatch</c> is a postfix on <c>ModelDb.Init</c>, which runs once
/// per process: it walks the model database, and for every <see cref="ILocalizationProvider"/> writes
/// <c>Id.Entry + "." + key</c> into the relevant <see cref="LocTable"/>'s <c>_translations</c> dictionary.
/// The vanilla language dropdown does <em>not</em> restart the game — it calls
/// <c>LocManager.SetLanguage</c>, which only rebuilds <c>LocManager._tables</c> from disk. The freshly
/// loaded tables therefore contain no mod text at all, and switching back does not help (that is another
/// set of fresh tables). Measured before this patch: a table census of <c>YETANNIA-</c> keys went
/// <c>cards</c> 169→0, <c>powers</c> 66→0, <c>characters</c> 16→0, <c>relics</c> 15→0 after a switch, and it
/// never recovered.
///
/// This is worse than cosmetic: <c>CardModel.SelectionScreenPrompt</c> throws
/// <c>InvalidOperationException("No selection screen prompt for " + Id)</c> when the key is missing, so a
/// language switch mid-run could abort the run itself (observed: <c>CARD.YETANNIA-RECLAIM</c>).
///
/// HOW IT WORKS — the same shape as <see cref="Keywords.KeywordLocPatch"/> and
/// <see cref="SettingsLocPatch"/>: a postfix on <see cref="LocManager.GetTable"/>, keyed on the returned
/// <see cref="LocTable"/> instance with a <see cref="ConditionalWeakTable{TKey,TValue}"/> so each freshly
/// loaded table (i.e. each language switch) is filled exactly once. BaseLib's own startup injection is
/// left completely untouched — during <c>ModelDb.Init</c> this postfix fills the same table with the same
/// values that BaseLib then writes again, which is idempotent.
///
/// Injecting at <c>GetTable</c> rather than at <c>SetLanguage</c> is deliberate: <c>SetLanguage</c> fires
/// its locale-change callbacks before it returns, so a postfix on it would run after the first UI code
/// that asks for a mod string. Here the text is in place before the table can be read.
///
/// ONLY this mod's own models are touched: the model's type has to come from this assembly <em>and</em> its
/// id has to carry the mod's <c>YETANNIA-</c> prefix. Vanilla entries are never read or written.
/// </summary>
[HarmonyPatch(typeof(LocManager), nameof(LocManager.GetTable))]
internal static class ModelLocReloadPatch
{
    /// <summary>The mod's model-id prefix (BaseLib's <c>ModPrefix</c> for this mod).</summary>
    private const string ModPrefix = "YETANNIA-";

    /// <summary>
    /// Which <see cref="LocTable"/> each model category belongs in, copied from BaseLib's
    /// <c>ModelLocPatch.CategoryToLocTable</c>. The keys are what <c>ModelId.Category</c> holds for a model
    /// of that base type. BaseLib's two entries with no <c>AbstractModel</c> behind them
    /// (<c>EpochModel</c>, <c>DynamicVar</c> — BaseLib's own comment says they cannot function) are omitted.
    /// </summary>
    private static readonly IReadOnlyDictionary<string, string> CategoryToLocTable = new Dictionary<string, string>
    {
        [ModelId.SlugifyCategory(nameof(ActModel))] = "acts",
        [ModelId.SlugifyCategory(nameof(AfflictionModel))] = "afflictions",
        [ModelId.SlugifyCategory(nameof(CardModel))] = "cards",
        [ModelId.SlugifyCategory(nameof(CharacterModel))] = "characters",
        [ModelId.SlugifyCategory(nameof(EnchantmentModel))] = "enchantments",
        [ModelId.SlugifyCategory(nameof(EncounterModel))] = "encounters",
        [ModelId.SlugifyCategory(nameof(ModifierModel))] = "modifiers",
        [ModelId.SlugifyCategory(nameof(MonsterModel))] = "monsters",
        [ModelId.SlugifyCategory(nameof(OrbModel))] = "orbs",
        [ModelId.SlugifyCategory(nameof(PotionModel))] = "potions",
        [ModelId.SlugifyCategory(nameof(PowerModel))] = "powers",
        [ModelId.SlugifyCategory(nameof(RelicModel))] = "relics",
    };

    /// <summary>The tables this patch may have to fill; anything else returns on a set lookup.</summary>
    private static readonly HashSet<string> ModelTables = new(CategoryToLocTable.Values);

    private static readonly Assembly ModAssembly = typeof(MainFile).Assembly;

    // Reference-keyed so that each freshly loaded LocTable (i.e. each language switch) is patched once.
    private static readonly ConditionalWeakTable<LocTable, object> Injected = new();

    [HarmonyPostfix]
    private static void ReinjectModelText(string name, LocTable __result)
    {
        if (__result == null) return;
        if (!ModelTables.Contains(name)) return;
        if (Injected.TryGetValue(__result, out _)) return;

        // A language switch calls GetTable for other tables first, so nothing is injected until the table
        // the game actually asked for is the one being filled. Merging is idempotent, so the overlap with
        // BaseLib's own injection during ModelDb.Init is harmless.
        var entries = new Dictionary<string, string>();
        var sawOurs = false;

        foreach (var model in ModelDb.All)
        {
            if (model is not ILocalizationProvider provider) continue;
            if (model.GetType().Assembly != ModAssembly) continue;
            if (!model.Id.Entry.StartsWith(ModPrefix, StringComparison.Ordinal)) continue;

            sawOurs = true;

            // Same table resolution BaseLib uses: the model's own override, else its category.
            var table = provider.LocTable ?? CategoryToLocTable.GetValueOrDefault(model.Id.Category);
            if (table != name) continue;

            var localization = provider.Localization;
            if (localization == null) continue;

            foreach (var (key, value) in localization)
            {
                entries[$"{model.Id.Entry}.{key}"] = SimpleLoc.TrySimplify(value);
            }
        }

        // No mod model exists yet, so ModelDb.Init has not populated the database: this must NOT mark the
        // table as done, or the injection would be skipped for the rest of this table's life. Callers that
        // ask for a table before Init are rare, so the retry costs nothing.
        if (!sawOurs) return;

        Injected.Add(__result, null);

        if (entries.Count > 0)
        {
            __result.MergeWith(entries);
        }
    }
}
