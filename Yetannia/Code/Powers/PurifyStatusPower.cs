using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 趁势而动 的能力：每回合你抽到状态牌的前 1（升级 2）次，将其消耗。
///
/// The per-turn counter resets in <see cref="AbstractModel.BeforeHandDraw"/>, not in
/// <c>AfterPlayerTurnStart</c>. CombatManager draws the opening hand *before* dispatching
/// AfterPlayerTurnStart (BeforeHandDraw → Draw(fromHandDraw: true) → AfterPlayerTurnStart), so a reset
/// in the latter ran after those cards had already been drawn: they were compared against the previous
/// turn's leftover count and silently skipped. From turn 2 on, every opening hand with a Status card
/// leaked one. Resetting before the draw is what makes “the first N you draw each turn” true for the
/// opening hand too — the same ordering trick 先知发饰 uses.
/// </summary>
public sealed class PurifyStatusPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    /// <summary>
    /// Counter, not Single: the icon label is only filled in for Counter powers
    /// (<c>NPower.RefreshAmount</c> writes <c>DisplayAmount</c> alone otherwise), so a Single power
    /// showed the literal “X” from its text forever.
    /// </summary>
    public override PowerStackType StackType => PowerStackType.Counter;

    private int _limit = 1;
    private int _drawnThisTurn;

    /// <summary>The real limit, so the icon shows 1 or 2 rather than a meaningless stack count.</summary>
    public override int DisplayAmount => _limit;

    public void MarkUpgraded() => _limit = 2;

    public override async Task AfterCardDrawn(PlayerChoiceContext choiceContext, CardModel card, bool fromHandDraw)
    {
        if (card.Owner != Owner.Player) return;
        if (card.Rarity != CardRarity.Status) return;
        if (_drawnThisTurn >= _limit) return;

        _drawnThisTurn++;
        await CardCmd.Exhaust(choiceContext, card);
    }

    /// <summary>Runs once per turn, immediately before that turn's opening hand is drawn.</summary>
    public override Task BeforeHandDraw(Player player, PlayerChoiceContext choiceContext, ICombatState combatState)
    {
        if (player == Owner.Player)
        {
            _drawnThisTurn = 0;
            InvokeDisplayAmountChanged();
        }

        return Task.CompletedTask;
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/purify.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/purify.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "趁势而动",
        "每回合你抽到状态牌的前 X 次，将它消耗。",
        "每回合你抽到状态牌的前 X 次，将它消耗。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Seize the Moment",
        "The first X Status card(s) you draw each turn are exhausted.",
        "The first X Status card(s) you draw each turn are exhausted.");
}
