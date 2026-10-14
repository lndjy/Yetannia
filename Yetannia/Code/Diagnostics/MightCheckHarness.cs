using System;
using System.Threading.Tasks;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using Yetannia.YetanniaCode.Cards;

namespace Yetannia.YetanniaCode.Diagnostics;

/// <summary>
/// Drives 未命名·奋起 and 未命名·从容 through their "permanent" branches without a human, so the
/// <c>[rising]</c> / <c>[agility]</c> lines answer the "permanent stat doesn't work" report.
///
/// Enable with an empty <c>mods/Yetannia/might.flag</c>.
///
/// The scenario plays three Attacks first, which is what 奋起 needs ("more than 2 attacks this turn")
/// and is also a valid state for 从容 (taking no damage is the easy branch), then plays both cards and
/// lets the log record which branch ran and what the resulting power amounts were.
/// </summary>
[HarmonyPatch(typeof(NCombatRoom), nameof(NCombatRoom._Ready))]
internal static class MightCheckHarness
{
    private const string FlagFileName = "might.flag";
    private static bool _ran;

    [HarmonyPostfix]
    private static void Postfix()
    {
        if (_ran) return;

        try
        {
            var modDir = Godot.ProjectSettings.GlobalizePath("res://");
            var path = System.IO.Path.Combine(modDir, "mods", "Yetannia", FlagFileName);
            if (!System.IO.File.Exists(path))
            {
                MainFile.Logger.Info(
                    $"[mightcheck] disabled (create mods/Yetannia/{FlagFileName} to enable)");
                return;
            }
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[mightcheck] could not probe the flag: {e.Message}");
            return;
        }

        _ran = true;
        TaskHelper.RunSafely(RunAsync());
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
                MainFile.Logger.Error("[mightcheck] no local player after 20s; aborting");
                return;
            }

            // Let the combat-start relic scry settle so this does not run on top of a pending choice.
            for (var attempt = 0; attempt < 120 && ScryTrace.InFlight > 0; attempt++)
            {
                await Cmd.Wait(0.5f);
            }

            MainFile.Logger.Info("[mightcheck] === scenario start ===");

            var context = new BlockingPlayerChoiceContext();

            // Three Attacks first: that is 奋起's "more than 2 Attack cards this turn" condition, and
            // it leaves 从容 on its "took no damage" branch.
            for (var i = 0; i < 3; i++)
            {
                var attack = player.Creature.CombatState.CreateCard<Strike>(player);
                await CardPileCmd.AddGeneratedCardToCombat(attack, PileType.Hand, player);
                await CardCmd.AutoPlay(context, attack, null);
            }

            var might = player.Creature.CombatState.CreateCard<RisingMight>(player);
            await CardPileCmd.AddGeneratedCardToCombat(might, PileType.Hand, player);
            await CardCmd.AutoPlay(context, might, null);
            await Cmd.Wait(1f);

            var agility = player.Creature.CombatState.CreateCard<SteadyAgility>(player);
            await CardPileCmd.AddGeneratedCardToCombat(agility, PileType.Hand, player);
            await CardCmd.AutoPlay(context, agility, null);
            await Cmd.Wait(1f);

            MainFile.Logger.Info("[mightcheck] === scenario finished ===");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[mightcheck] scenario threw: {e}");
        }
    }
}
