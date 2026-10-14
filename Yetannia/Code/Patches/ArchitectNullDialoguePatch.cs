using System;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Ancients;
using MegaCrit.Sts2.Core.Models.Events;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Makes 建筑师 (The Architect) resolvable for characters that have no Architect dialogue.
///
/// <c>TheArchitect.DefineDialogues()</c> hard-codes a dialogue list per vanilla character and leaves
/// <c>AgnosticDialogues</c> empty, while <c>LoadDialogue()</c> calls
/// <c>GetValidDialogues(..., allowAnyCharacterDialogues: false)</c>. For a custom character that
/// returns an empty list, <c>Rng.NextItem</c> returns <c>default</c>, and <c>Dialogue</c> is left
/// null.
///
/// A null Dialogue is fine everywhere except <c>WinRun</c>, which dereferences
/// <c>Dialogue.EndAttackers</c> twice with no guard — so the run-ending event throws a
/// NullReferenceException the moment the player clicks 继续 and the run can never be completed.
/// (<c>PlayCurrentLine</c> does guard; it is the only other unguarded-looking reader.)
///
/// The fix supplies an empty dialogue right before <c>WinRun</c> runs, and only when there was none,
/// so vanilla characters are untouched. "Empty" means the dialogue's single line has a null
/// <c>LineText</c>: <c>PlayCurrentLine</c> bails out on that, so nothing is ever said, and
/// <c>EndAttackers</c> defaults to <see cref="ArchitectAttackers.None"/> so no attack animation
/// plays either — the event just proceeds and the run resolves.
/// </summary>
[HarmonyPatch(typeof(TheArchitect), "WinRun")]
internal static class ArchitectNullDialoguePatch
{
    [HarmonyPrefix]
    private static void Prefix(TheArchitect __instance)
    {
        try
        {
            var property = AccessTools.Property(typeof(TheArchitect), "Dialogue");
            if (property == null)
            {
                MainFile.Logger.Error("Architect patch: could not find the Dialogue property");
                return;
            }

            if (property.GetValue(__instance) != null) return;

            var fallback = new AncientDialogue("") { EndAttackers = ArchitectAttackers.None };

            try
            {
                property.SetValue(__instance, fallback);
            }
            catch (Exception e)
            {
                // The setter runs AssertMutable(); if the event happens to be sealed at this point,
                // fall back to the backing field so the run can still be finished.
                var field = AccessTools.Field(typeof(TheArchitect), "_dialogue");
                if (field == null) throw;

                MainFile.Logger.Warn($"Architect patch: setter refused ({e.GetType().Name}), writing the field instead");
                field.SetValue(__instance, fallback);
            }

            MainFile.Logger.Info("Architect patch: character has no Architect dialogue, supplied an empty one");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"Architect patch failed: {e}");
        }
    }
}
