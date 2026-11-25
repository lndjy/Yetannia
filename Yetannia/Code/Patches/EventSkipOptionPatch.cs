using System;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Events;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Events;
using Yetannia.YetanniaCode.Relics;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// 先知的手链 — appends a "skip this event, gain 50 gold" option to every ? event.
///
/// <c>EventModel.GenerateInitialOptions</c> is abstract and overridden by every event, so patching
/// it would mean patching each one. <c>GenerateInitialOptionsWrapper</c> is the single
/// non-overridden wrapper the framework calls around it (the docs describe it as exactly that), so
/// postfixing the wrapper covers all events at once.
///
/// The option is only added when the acting player actually holds
/// <see cref="ProphetsBracelet"/>.
/// </summary>
[HarmonyPatch(typeof(EventModel), "GenerateInitialOptionsWrapper")]
internal static class EventSkipOptionPatch
{
    private const string OptionKey = "YETANNIA-SKIP_EVENT";

    [HarmonyPostfix]
    private static void Postfix(EventModel __instance, ref IReadOnlyList<EventOption> __result)
    {
        try
        {
            // The Architect is the run-ending event: skipping it would strand the run with no way
            // to finish. It is deliberately exempt.
            if (__instance is TheArchitect) return;

            // v0.114 shared events: in multiplayer every player votes on an option *index*, and the
            // winning option runs for everyone. Appending an option that exists only for the bracelet
            // holder would make the option lists (and therefore the vote indexes) differ between
            // peers -- exactly the "different option, different result, desync" case. The bracelet is
            // deliberately inert in these co-op voting events: no option is added on any peer.
            if (__instance.IsShared) return;

            var player = __instance.Owner;
            if (player == null) return;
            if (!ProphetsBracelet.IsHeldBy(player)) return;

            // Don't stack the option if this event is being (re)generated for a holder.
            if (__result != null && __result.Any(o => o.TextKey == OptionKey)) return;

            var option = new EventOption(
                eventModel: __instance,
                onChosen: () => SkipEvent(__instance, player),
                title: new LocString("events", OptionKey + ".title"),
                description: new LocString("events", OptionKey + ".description"),
                textKey: OptionKey,
                hoverTips: Array.Empty<IHoverTip>())
                .ThatWontSaveToChoiceHistory();

            var list = (__result ?? Array.Empty<EventOption>()).ToList();
            list.Add(option);
            __result = list;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"Event skip option patch failed: {e}");
        }
    }

    private static async Task SkipEvent(EventModel eventModel, Player player)
    {
        await PlayerCmd.GainGold(ProphetsBracelet.SkipReward, player);

        // End the event with no options left, which is how an event finishes and hands the room back.
        var setEventState = AccessTools.Method(typeof(EventModel), "SetEventState");
        var emptyLoc = new LocString("ancients", "PROCEED.description");
        setEventState?.Invoke(eventModel, [emptyLoc, Array.Empty<EventOption>()]);
    }
}
