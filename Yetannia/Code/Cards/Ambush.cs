using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 奇袭 — 蓝卡（Uncommon），1 费技能：
/// 给予目标 2（升级 3）层[易伤]；如果它的意图不是攻击，再获得 1 点[力量]。
///
/// A Skill: it deals no damage, only debuffs. (It was originally declared as an Attack; the
/// request moved it to Skill.)
/// </summary>
public sealed class Ambush : YetanniaCard
{
    private const int BaseVulnerable = 2;
    private const int VulnerableUpgrade = 1; // 2 -> 3
    private const int BaseStrength = 1;
    private const int StrengthUpgrade = 1; // 1 -> 2

    public Ambush()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new PowerVar<VulnerablePower>(BaseVulnerable),
        new PowerVar<StrengthPower>(BaseStrength)
    ];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromPower<VulnerablePower>(),
        HoverTipFactory.FromPower<StrengthPower>()
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await PowerCmd.Apply<VulnerablePower>(
            choiceContext, cardPlay.Target, DynamicVars.Vulnerable.BaseValue, Owner.Creature, this);

        // Always gain Strength; double it when the target doesn't intend to attack (null Monster =
        // not a monster, so a player-side target counts as "not attacking").
        var strength = DynamicVars.Strength.BaseValue;
        if (cardPlay.Target.Monster?.IntendsToAttack != true)
        {
            strength *= 2;
        }

        await PowerCmd.Apply<StrengthPower>(
            choiceContext, Owner.Creature, strength, Owner.Creature, this);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Vulnerable.UpgradeValueBy(VulnerableUpgrade);
        DynamicVars.Strength.UpgradeValueBy(StrengthUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "奇袭",
        "给予{VulnerablePower:diff()}层[gold]易伤[/gold]，获得{StrengthPower:diff()}点[gold]力量[/gold]。如果目标敌人的意图不是攻击，则获得的力量翻倍。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Ambush",
        "Apply {VulnerablePower:diff()} [gold]Vulnerable[/gold] and gain {StrengthPower:diff()} [gold]Strength[/gold]. If the target enemy does not intend to attack, the Strength gained is doubled.");
}
