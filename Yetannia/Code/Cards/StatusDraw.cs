using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>凯旋之路 — 蓝卡（Uncommon），2 费（敲后 1 费）能力：当你消耗一张状态牌时，抽一张牌。
/// v1.0.5：稀有度 金卡 → 蓝卡；两档（原版 / 东尼测试版）都生效。</summary>
public sealed class StatusDraw : YetanniaCard
{
    public StatusDraw()
        : base(2, CardType.Power, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<StatusDrawPower>(choiceContext, Owner.Creature, 1, Owner.Creature, this);
    }

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(-1); // 2 -> 1

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "凯旋之路", "当你消耗一张状态牌时，抽一张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Road of Triumph", "Whenever you exhaust a Status card, draw 1 card.");
}
