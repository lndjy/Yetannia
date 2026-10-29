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
using Yetannia.YetanniaCode.Config;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 合击 / Pincer Strike — 欧罗巴斯（Orobas）的「替换初始卡」版本，由 <c>ArchaicTooth</c> 通过
/// <see cref="ITranscendenceCard"/> 替换掉 <see cref="OminousDecree"/>。
///
/// 两档都是 1 费、稀有度「先古」：给予所有敌人 2 层[易伤]和[虚弱]，并造成 15 点伤害。
/// 原版（<see cref="CardBalanceMode.Original"/>）敲后：费用 1 → 0，且伤害 15 → 20。
/// 东尼测试版（<see cref="CardBalanceMode.TonyTest"/>）敲后：**只减费**（1 → 0），伤害仍是 15。
///
/// (Both drafts: 1 energy, 2 Vulnerable + 2 Weak to ALL enemies, then 15 damage. Upgraded in the
/// original it costs 0 and deals 20; in the Tony draft the upgrade only makes it cost 0 and the
/// damage stays at 15.)
/// </summary>
public sealed class OminousDecreeTranscendent : YetanniaCard
{
    private const int DebuffBase = 2;
    private const int DamageBase = 15;
    private const int DamageUpgrade = 5; // 15 -> 20，仅原版
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
        // 两档都减费；只有原版才同时加伤害（15 -> 20），东尼测试版敲后伤害仍是 15。
        EnergyCost.UpgradeBy(CostReductionOnUpgrade);
        if (!CardBalance.IsTony)
        {
            DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);
        }
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "合击",
        "给予所有敌人{VulnerablePower:diff()}层[gold]易伤[/gold]和{WeakPower:diff()}层[gold]虚弱[/gold]，并造成{Damage:diff()}点伤害。\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Pincer Strike",
        "Apply {VulnerablePower:diff()} [gold]Vulnerable[/gold] and {WeakPower:diff()} [gold]Weak[/gold] to ALL enemies, then deal {Damage:diff()} damage.\n[gold]Prophet[/gold].");
}
