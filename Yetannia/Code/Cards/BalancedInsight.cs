using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 均衡洞察 — 蓝卡（Uncommon），3 费能力：获得 1（升级 2）点[力量]和[敏捷]。先知：效果相同。
/// </summary>
public sealed class BalancedInsight : YetanniaCard
{
    private const int BaseAmount = 1;
    private const int AmountUpgrade = 1; // 1 -> 2

    public BalancedInsight()
        : base(3, CardType.Power, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new PowerVar<StrengthPower>(BaseAmount),
        new PowerVar<DexterityPower>(BaseAmount)
    ];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromPower<StrengthPower>(),
        HoverTipFactory.FromPower<DexterityPower>()
    ];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay) =>
        GainStats(choiceContext);

    /// <summary>先知（无额外描述）：效果与打出相同。</summary>
    protected override Task OnProphet(PlayerChoiceContext choiceContext) =>
        GainStats(choiceContext);

    private async Task GainStats(PlayerChoiceContext choiceContext)
    {
        var creature = Owner.Creature;
        await PowerCmd.Apply<StrengthPower>(choiceContext, creature, DynamicVars.Strength.BaseValue, creature, this);
        await PowerCmd.Apply<DexterityPower>(choiceContext, creature, DynamicVars.Dexterity.BaseValue, creature, this);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Strength.UpgradeValueBy(AmountUpgrade);
        DynamicVars.Dexterity.UpgradeValueBy(AmountUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "按部就班",
        "获得{StrengthPower:diff()}点[gold]力量[/gold]和{DexterityPower:diff()}点[gold]敏捷[/gold]。\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Step by Step",
        "Gain {StrengthPower:diff()} [gold]Strength[/gold] and {DexterityPower:diff()} [gold]Dexterity[/gold].\n[gold]Prophet[/gold].");
}
