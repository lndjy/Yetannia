using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 挺身而出 — 蓝卡（Uncommon），2 费技能：
/// 获得 16 点[格挡]，给予自己 1 层[虚弱]，下回合获得 1（升级 2）点[能量]。
///
/// The request left this row's name blank. The display name below is a deliberate placeholder so
/// the card is not nameless in game; rename it by editing <see cref="Chinese"/> / <see cref="English"/>.
///
/// Only the next-turn energy scales with the upgrade — 16 Block and 1 Weak were given as fixed.
/// </summary>
public sealed class UnnamedTechnique : YetanniaCard
{
    private const int BlockAmount = 16;
    private const int WeakAmount = 1;
    private const int BaseEnergy = 1;
    private const int EnergyUpgrade = 1; // 1 -> 2

    public UnnamedTechnique()
        : base(2, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override bool GainsBlock => true;

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new BlockVar(BlockAmount, ValueProp.Move),
        new PowerVar<WeakPower>(WeakAmount),
        new EnergyVar(BaseEnergy)
    ];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
        [HoverTipFactory.FromPower<WeakPower>()];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var creature = Owner.Creature;
        await CreatureCmd.GainBlock(creature, DynamicVars.Block, cardPlay);

        await PowerCmd.Apply<WeakPower>(
            choiceContext, creature, DynamicVars.Weak.BaseValue, creature, this);

        await PowerCmd.Apply<EnergyNextTurnPower>(
            choiceContext, creature, DynamicVars.Energy.BaseValue, creature, this);
    }

    protected override void OnUpgrade() => DynamicVars.Energy.UpgradeValueBy(EnergyUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "挺身而出",
        "获得{Block:diff()}点[gold]格挡[/gold]。给予自己{WeakPower:diff()}层[gold]虚弱[/gold]。下回合获得{Energy:energyIcons()}。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Step Forward",
        "Gain {Block:diff()} [gold]Block[/gold]. Apply {WeakPower:diff()} [gold]Weak[/gold] to yourself. Gain {Energy:energyIcons()} next turn.");
}
