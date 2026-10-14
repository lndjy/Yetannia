using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 先知研习 — 金卡（Rare），2 费能力（升级后 1 费）：每当你预见时，抽 1 张牌。
/// </summary>
public sealed class PropheticStudy : YetanniaCard
{
    private const int CostReductionOnUpgrade = -1; // 2 -> 1

    public PropheticStudy()
        : base(2, CardType.Power, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<PropheticStudyPower>(choiceContext, Owner.Creature, 1m, Owner.Creature, this);
    }

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(CostReductionOnUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "未雨绸缪",
        "每当你[gold]预见[/gold]时，抽1张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Forewarned",
        "Whenever you [gold]Scry[/gold], draw 1 card.");
}
