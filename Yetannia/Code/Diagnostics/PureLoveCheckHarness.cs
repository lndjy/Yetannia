using System;
using System.Linq;
using System.Threading.Tasks;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using Yetannia.YetanniaCode.Cards;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Diagnostics;

/// <summary>
/// Reproduces one specific suspicion: with 纯爱形态 (PureLoveFormPower) up, a card that itself scries
/// gets discarded from the draw pile, so the power autoplays it and that autoplay opens a *nested*
/// player choice (预见's card-selection grid).
///
/// Enable with an empty <c>mods/Yetannia/purelove.flag</c>. The next combat runs the scenario once.
///
/// Why this is worth a harness rather than reasoning: the tester's log contained exactly one
/// <c>GameAction ... source POWER.YETANNIA-PURE_LOVE_FORM_POWER ... last involved
/// CARD.YETANNIA-CUT_THROUGH_FATE ... completed with exception: (An attempt was made to transition a
/// task to a final state when it had already completed.)</c> — 先制/CutThroughFate being a scry card.
/// That run was on v0.5.7, i.e. with the <c>ScryThresholdPower</c> bug alive, and that bug threw from
/// inside exactly this autoplay. So the question is whether this error was fallout from that faulted
/// task or a defect of its own. This harness answers it.
///
/// The scenario drives the Draw -&gt; Discard transition directly instead of playing a scry card,
/// because that transition is all PureLoveFormPower watches: it fires the identical hook with none of
/// the "which cards did the scry show" nondeterminism.
/// </summary>
[HarmonyPatch(typeof(NCombatRoom), nameof(NCombatRoom._Ready))]
internal static class PureLoveCheckHarness
{
    private const string FlagFileName = "purelove.flag";
    private const int TransitionTimeoutSeconds = 15;

    /// <summary>After the trigger, how long to keep the selector installed for the async hook.</summary>
    private const int SettleSeconds = 6;

    private static bool _ran;

    [HarmonyPostfix]
    private static void Postfix()
    {
        if (_ran) return;

        if (!FlagExists(FlagFileName))
        {
            MainFile.Logger.Info(
                $"[purelovecheck] disabled (create mods/Yetannia/{FlagFileName} to enable)");
            return;
        }

        _ran = true;
        TaskHelper.RunSafely(RunAsync());
    }

    private static bool FlagExists(string fileName)
    {
        try
        {
            var modDir = Godot.ProjectSettings.GlobalizePath("res://");
            return System.IO.File.Exists(System.IO.Path.Combine(modDir, "mods", "Yetannia", fileName));
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[purelovecheck] could not probe {fileName}: {e.Message}");
            return false;
        }
    }

    private static async Task RunAsync()
    {
        try
        {
            Player player = null;
            for (var attempt = 0; attempt < 40 && player == null; attempt++)
            {
                await Cmd.Wait(0.5f);
                var state = CombatManager.Instance?.DebugOnlyGetState();
                player = state == null ? null : LocalContext.GetMe(state);
            }

            if (player == null)
            {
                MainFile.Logger.Error("[purelovecheck] no local player after 20s; aborting");
                return;
            }

            // The starting relic scries at combat start. If that is still open we would be starting a
            // second choice on top of it, and any weirdness afterwards would be our own doing.
            for (var attempt = 0; attempt < 120 && ScryTrace.InFlight > 0; attempt++)
            {
                await Cmd.Wait(0.5f);
            }
            if (ScryTrace.InFlight > 0)
            {
                MainFile.Logger.Error(
                    $"[purelovecheck] {ScryTrace.InFlight} scry still in flight after 60s; " +
                    "starting anyway — expect the result to be noisy");
            }

            MainFile.Logger.Info("[purelovecheck] === scenario start ===");

            // Kept installed across the whole scenario, not just the trigger call: the hook runs as its
            // own GameAction, so the nested scry happens *after* the trigger returns.
            using (CardSelectCmd.UseSelector(new AutoCardSelector(), localOnly: true))
            {
                var power = await PowerCmd.Apply<PureLoveFormPower>(
                    new BlockingPlayerChoiceContext(), player.Creature, 1, player.Creature, null);
                MainFile.Logger.Info($"[purelovecheck] 纯爱形态 applied: {power != null}");

                var card = player.Creature.CombatState.CreateCard<CutThroughFate>(player);
                await CardPileCmd.AddGeneratedCardToCombat(card, PileType.Draw, player);
                MainFile.Logger.Info(
                    $"[purelovecheck] {card.Id.Entry} into draw pile (pile={card.Pile?.Type})");

                var trigger = CardPileCmd.Add(card, PileType.Discard);
                var winner = await Task.WhenAny(
                    trigger, Task.Delay(TimeSpan.FromSeconds(TransitionTimeoutSeconds)));

                if (winner != trigger)
                {
                    MainFile.Logger.Error(
                        $"[purelovecheck] TIMED OUT after {TransitionTimeoutSeconds}s on the " +
                        "Draw -> Discard transition");
                }
                else
                {
                    try
                    {
                        await trigger;
                        MainFile.Logger.Info("[purelovecheck] Draw -> Discard transition completed");
                    }
                    catch (Exception e)
                    {
                        MainFile.Logger.Error($"[purelovecheck] transition threw: {e}");
                    }
                }

                // The autoplay hook is dispatched as a separate GameAction, so its failure (if any)
                // lands after the trigger returns. Stay inside the selector scope while it runs.
                await Cmd.Wait(SettleSeconds);
            }

            MainFile.Logger.Info(
                "[purelovecheck] === scenario finished (check the lines above for the autoplay) ===");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[purelovecheck] scenario threw: {e}");
        }
    }
}
