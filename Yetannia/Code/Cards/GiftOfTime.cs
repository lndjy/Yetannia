using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 先知的援助 — 蓝卡，3 费（敲后 2 费）技能，多人专属。
///
/// 指定一名队友：他本回合结束时获得一个额外回合；然后**立刻结束你自己的回合**。
///
/// 结束自己回合用的是原版 <c>VoidForm</c> 的写法 <c>PlayerCmd.EndTurn(Owner, canBackOut: false)</c>——
/// 注意它返回 void，不能 await。"下个回合结束时再动"这件事交给
/// <see cref="GrantedTurnPower"/> 的两个钩子，这里不做任何计时。
/// </summary>
public sealed class GiftOfTime : YetanniaCard
{
    public GiftOfTime()
        : base(3, CardType.Skill, CardRarity.Uncommon, TargetType.AnyAlly)
    {
    }

    public override CardMultiplayerConstraint MultiplayerConstraint =>
        CardMultiplayerConstraint.MultiplayerOnly;

    /// <summary>
    /// 消耗. Declared here, NOT written into the description: the card face appends keyword text
    /// itself, so repeating it in the loc string renders it twice.
    /// </summary>
    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var target = cardPlay.Target;
        if (target == null) return;

        await PowerCmd.Apply<GrantedTurnPower>(choiceContext, target, 1, Owner.Creature, this);

        PlayerCmd.EndTurn(Owner, canBackOut: false);
    }

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(-1);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "先知的援助",
        "选择一名其他角色。该角色本回合结束时，获得一个额外回合。\n结束你的回合。");

    private static readonly List<(string, string)> English = new CardLoc(
        "The Prophet\u2019s Aid",
        "Choose another character. At the end of their turn, they take an extra turn.\nEnd your turn.");
}
