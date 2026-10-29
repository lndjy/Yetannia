using BaseLib.Abstracts;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Diagnostics;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 未命名·预壁 的延时预见 — at the start of the owner's next turn (before the hand is drawn),
/// Scry <c>Amount</c>, then remove this power.
///
/// <c>BeforeHandDraw</c> rather than <c>AfterPlayerTurnStart</c>: the turn-start hook runs *after*
/// the opening hand is drawn, which would make the player scry the very cards they just drew.
/// </summary>
public sealed class DelayedScryPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    /// <summary>Amount is the scry amount.</summary>
    public override PowerStackType StackType => PowerStackType.Counter;

    /// <summary>Bookkeeping only — the scry is a one-shot, nothing to act on.</summary>
    protected override bool IsVisibleInternal => false;

    public override async Task BeforeHandDraw(
        Player player, PlayerChoiceContext choiceContext, ICombatState combatState)
    {
        if (player != Owner.Player) return;

        var amount = Amount;
        await PowerCmd.Remove(this);

        if (amount > 0)
        {
            await ScryTrace.Run(nameof(DelayedScryPower), choiceContext, player, amount);
        }
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/delayed_scry.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/delayed_scry.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "预知",
        "下个回合开始时，预见 X。",
        "下个回合开始时，预见 X。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Foreknowledge",
        "Scry X at the start of your next turn.",
        "Scry X at the start of your next turn.");
}
