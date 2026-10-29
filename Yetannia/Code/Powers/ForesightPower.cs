using BaseLib.Abstracts;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Diagnostics;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 有条不紊 / Methodical (ported from Slay the Spire 1's Watcher card Foresight):
/// at the start of your turn, Scry X.
/// </summary>
public sealed class ForesightPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Counter;

    /// <summary>
    /// Runs before the turn's 5-card draw. <c>AfterPlayerTurnStart</c> (and even its "Early" pass)
    /// is dispatched after <c>CardPileCmd.Draw</c> in SetupPlayerTurn, which would make the player
    /// scry cards they are about to draw anyway.
    /// </summary>
    public override async Task BeforeHandDraw(Player player, PlayerChoiceContext choiceContext, ICombatState combatState)
    {
        if (player != Owner.Player) return;
        if (Amount <= 0) return;

        await ScryTrace.Run(nameof(ForesightPower), choiceContext, player, (int)Amount);
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/foresight.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/foresight.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "有条不紊",
        "在你的回合开始时，预见 X。",
        "在你的回合开始时，预见 X。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Methodical",
        "At the start of your turn, Scry X.",
        "At the start of your turn, Scry X.");
}
