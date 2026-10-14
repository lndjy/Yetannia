using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 厄运宣告·超越 — 欧罗巴斯（Orobas）的「替换初始卡」版本，由 <c>ArchaicTooth</c> 通过
/// <see cref="ITranscendenceCard"/> 替换掉 <see cref="OminousDecree"/>。
///
/// 给予所有敌人 2 层[易伤]和[虚弱]，并造成 15 点伤害。
/// 敲后不增加易伤/虚弱层数，而是把费用降到 0（伤害仍然 15 -> 20）。
/// 稀有度是「先古」而不是基础卡。
/// </summary>
public sealed class OminousDecreeTranscendent : YetanniaCard
{
    private const int DebuffBase = 2;
    private const int DamageBase = 15;
    private const int DamageUpgrade = 5; // 15 -> 20
    private const int CostReductionOnUpgrade = -1; // 1 -> 0

    public OminousDecreeTranscendent()
        : base(1, CardType.Attack, CardRarity.Ancient, TargetType.AllEnemies)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new PowerVar<VulnerablePower>(DebuffBase),
        new PowerVar<WeakPower>(DebuffBase),
        new DamageVar(DamageBase, ValueProp.Move)
    ];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromPower<VulnerablePower>(),
        HoverTipFactory.FromPower<WeakPower>()
    ];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay) =>
        Apply(choiceContext);

    /// <summary>先知（无额外描述）：效果与打出相同。</summary>
    protected override Task OnProphet(PlayerChoiceContext choiceContext) =>
        Apply(choiceContext);

    private async Task Apply(PlayerChoiceContext choiceContext)
    {
        var enemies = CombatState?.HittableEnemies;
        if (enemies == null || enemies.Count == 0) return;

        await PowerCmd.Apply<WeakPower>(choiceContext, enemies, DynamicVars.Weak.BaseValue, Owner.Creature, this);
        await PowerCmd.Apply<VulnerablePower>(choiceContext, enemies, DynamicVars.Vulnerable.BaseValue, Owner.Creature, this);

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, null)
            .TargetingAllOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    protected override void OnUpgrade()
    {
        // 敲后不增加易伤/虚弱层数，而是把费用降到 0（伤害仍然 15 -> 20）。
        EnergyCost.UpgradeBy(CostReductionOnUpgrade);
        DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "合击",
        "给予所有敌人{VulnerablePower:diff()}层[gold]易伤[/gold]和{WeakPower:diff()}层[gold]虚弱[/gold]，并造成{Damage:diff()}点伤害。\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Pincer Strike",
        "Apply {VulnerablePower:diff()} [gold]Vulnerable[/gold] and {WeakPower:diff()} [gold]Weak[/gold] to ALL enemies, then deal {Damage:diff()} damage.\n[gold]Prophet[/gold].");
}
