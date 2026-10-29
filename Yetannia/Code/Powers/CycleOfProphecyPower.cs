using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 殚精竭虑 — at the start of your **next** turn, add one 晕眩 (Dazed) to your discard pile, then
/// remove this power.
///
/// It used to fire every turn for the rest of the combat; the request narrowed the drawback to a
/// single, next-turn tax, so the power now takes itself off after paying out.
/// </summary>
public sealed class CycleOfProphecyPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Counter;

    public override async Task AfterPlayerTurnStart(PlayerChoiceContext choiceContext, Player player)
    {
        if (player != Owner.Player) return;

        var combatState = Owner.CombatState;
        if (combatState == null) return;

        // One-shot: remove first so a nested dispatch cannot double-fire it.
        await PowerCmd.Remove(this);

        var dazed = combatState.CreateCard<Dazed>(player);
        await CardPileCmd.AddGeneratedCardToCombat(dazed, PileType.Discard, player);
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/cycle_of_prophecy.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/cycle_of_prophecy.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "殚精竭虑",
        "下个回合开始时，将一张[gold]晕眩[/gold]加入你的弃牌堆。",
        "下个回合开始时，将一张[gold]晕眩[/gold]加入你的弃牌堆。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Exhaustive Planning",
        "At the start of your next turn, add a [gold]Dazed[/gold] into your discard pile.",
        "At the start of your next turn, add a [gold]Dazed[/gold] into your discard pile.");
}
