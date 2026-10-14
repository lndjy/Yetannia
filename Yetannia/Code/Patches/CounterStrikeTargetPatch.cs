using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Cards;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Makes 未命名·反击 readable as "only playable against an enemy that intends to attack" against the
/// **specific target**, not just "some enemy somewhere is attacking".
///
/// <c>AbstractModel.ShouldPlay(card, autoPlayType)</c> is the obvious hook, but it is not given the
/// chosen target, so a card that overrides it can only express a target-less condition.
/// <c>CardModel.CanPlayTargeting(Creature? target)</c> *is* target-aware and is exactly the gate the
/// manual-play path uses:
///
///   NCardPlay (drag feedback)  -&gt; CanPlayTargeting(target)
///   NCardPlay (drop)           -&gt; CardModel.TryManualPlay(target) -&gt; CanPlayTargeting(target)
///                                 -&gt; EnqueueManualPlay -&gt; PlayCardAction
///
/// so a postfix here blocks both the UI drop and the enqueue. It only ever narrows the result, and
/// only for <see cref="CounterStrike"/>, so no vanilla card is affected.
///
/// <see cref="CounterStrike.ShouldPlay"/> is kept as a *necessary* pre-filter (no enemy intends to
/// attack at all ⇒ the card is greyed out in hand); this patch supplies the sufficient part.
/// </summary>
[HarmonyPatch(typeof(CardModel), nameof(CardModel.CanPlayTargeting))]
internal static class CounterStrikeTargetPatch
{
    [HarmonyPostfix]
    private static void Postfix(CardModel __instance, Creature target, ref bool __result)
    {
        if (!__result) return;
        if (__instance is not CounterStrike) return;

        // Null target already fails CanPlayTargeting for a single-target card, so it never gets here.
        if (target == null) return;

        if (target.Monster?.IntendsToAttack != true)
        {
            __result = false;
        }
    }
}
