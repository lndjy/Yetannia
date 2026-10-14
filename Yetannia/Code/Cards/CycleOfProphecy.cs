using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 先知轮回 — 金卡（Rare），0 费能力：
/// 获得 2（升级 3）点能量，预见 2（升级 3），抽 2（升级 3）张牌，
/// 并在下个回合开始时将一张[眩晕]加入弃牌堆（一次性，不是每回合）。
/// </summary>
public sealed class CycleOfProphecy : YetanniaCard
{
    private const int BaseValue = 2;
    private const int ValueUpgrade = 1; // 2 -> 3

    public CycleOfProphecy()
        : base(0, CardType.Power, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new EnergyVar(BaseValue),
        new ScryVar(BaseValue),
        new CardsVar(BaseValue)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PlayerCmd.GainEnergy(DynamicVars.Energy.BaseValue, Owner);
        await Scry(choiceContext, DynamicVars["Scry"].BaseValue);
        await CardPileCmd.Draw(choiceContext, DynamicVars.Cards.BaseValue, Owner);
        await PowerCmd.Apply<CycleOfProphecyPower>(choiceContext, Owner.Creature, 1m, Owner.Creature, this);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Energy.UpgradeValueBy(ValueUpgrade);
        DynamicVars["Scry"].UpgradeValueBy(ValueUpgrade);
        DynamicVars.Cards.UpgradeValueBy(ValueUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "殚精竭虑",
        "获得{Energy:energyIcons()}。\n预见{Scry:diff()}。\n抽{Cards:diff()}张牌。\n下个回合开始时，将一张[gold]眩晕[/gold]加入你的弃牌堆。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Exhaustive Planning",
        "Gain {Energy:energyIcons()}.\nScry {Scry:diff()}.\nDraw {Cards:diff()} cards.\nAt the start of your next turn, add a [gold]Dazed[/gold] into your discard pile.");
}
