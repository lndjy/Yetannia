using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 严阵以待 — 蓝卡（Uncommon），X 费技能：
/// 获得 7X（升级 9X）点[格挡]；下个回合开始时预见 X。
///
/// Name is a placeholder (the request did not give one).
///
/// X comes from <c>ResolveEnergyXValue()</c> (the base game's helper for cost-X cards), which is
/// also what the block amount and the banked scry are computed from.
/// </summary>
public sealed class ForecastBulwark : YetanniaCard
{
    private const int BaseBlockPerX = 7;
    private const int BlockPerXUpgrade = 2; // 7 -> 9

    private const string PerXVar = "BlockPerX";

    public ForecastBulwark()
        : base(0, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override bool HasEnergyCostX => true;

    public override bool GainsBlock => true;

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DynamicVar(PerXVar, BaseBlockPerX)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var x = ResolveEnergyXValue();
        if (x <= 0) return;

        var block = DynamicVars[PerXVar].BaseValue * x;
        await CreatureCmd.GainBlock(Owner.Creature, block, ValueProp.Move, cardPlay);

        await PowerCmd.Apply<DelayedScryPower>(
            choiceContext, Owner.Creature, x, Owner.Creature, this);
    }

    protected override void OnUpgrade() => DynamicVars[PerXVar].UpgradeValueBy(BlockPerXUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "严阵以待",
        "获得{BlockPerX:diff()}×X点[gold]格挡[/gold]。下个回合开始时预见X。");

    private static readonly List<(string, string)> English = new CardLoc(
        "In Formation",
        "Gain {BlockPerX:diff()}×X [gold]Block[/gold]. Scry X at the start of next turn.");
}
