using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 纯爱形态 — 金卡（Rare），2 费能力（敲后 1 费）：
/// 本场战斗中，当你从抽牌堆弃置非[先知]牌时，将其加入手牌，本回合免费打出。
///
/// The clause in the request's parentheses is an instruction to the implementer, not card text, so
/// it is deliberately absent from the description. The mechanic itself lives in
/// <see cref="Powers.PureLoveFormPower"/>.
/// </summary>
public sealed class PureLoveForm : YetanniaCard
{
    private const int CostReductionOnUpgrade = -1; // 2 -> 1

    public PureLoveForm()
        : base(2, CardType.Power, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<PureLoveFormPower>(
            choiceContext, Owner.Creature, 1m, Owner.Creature, this);
    }

    /// <summary>敲后：费用 2 → 1。</summary>
    protected override void OnUpgrade() => EnergyCost.UpgradeBy(CostReductionOnUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "纯爱形态",
        "本场战斗中，当你从抽牌堆弃置非[gold]先知[/gold]牌时，使其耗能变为0，直到你下次打出它。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Pure Love Form",
        "This combat, when you discard a non-[gold]Prophet[/gold] card from your draw pile, it costs 0 until the next time you play it.");
}
