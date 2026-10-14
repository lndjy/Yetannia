using BaseLib.Abstracts;
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
/// 试探 / Probe — Yetannia's starter card.
///
/// 1 energy: 对所有敌人造成 6 点伤害，并给予所有敌人 1 层[gold]易伤[/gold]和 1 层[gold]虚弱[/gold]。
/// 敲后：费用 1 → 0（层数与伤害不变）。
/// [gold]先知[/gold] — with no further text, which by this mod's convention means the Prophet
/// effect is the same as playing the card, so damage and debuffs are applied again.
///
/// Debuffs are applied through the collection overload of <see cref="PowerCmd.Apply{T}"/>, which is
/// also how the base game's own "all enemies" cards (e.g. Shockwave) do it.
/// </summary>
public sealed class OminousDecree : YetanniaCard, ITranscendenceCard
{
    private const int BaseDebuff = 1;
    private const int BaseDamage = 6;
    private const int CostReductionOnUpgrade = -1; // 1 -> 0

    public OminousDecree()
        : base(1, CardType.Attack, CardRarity.Basic, TargetType.AllEnemies)
    {
    }

    /// <summary>
    /// 欧罗巴斯（Orobas）的「替换初始卡」：<c>ArchaicTooth</c> 会通过 BaseLib 的补丁把这张牌
    /// 换成它的超越版本。
    /// </summary>
    public CardModel GetTranscendenceTransformedCard() => ModelDb.Card<OminousDecreeTranscendent>();

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(BaseDamage, ValueProp.Move),
        new PowerVar<VulnerablePower>(BaseDebuff),
        new PowerVar<WeakPower>(BaseDebuff)
    ];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromPower<VulnerablePower>(),
        HoverTipFactory.FromPower<WeakPower>()
    ];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay) =>
        StrikeAndDebuff(choiceContext, cardPlay);

    /// <summary>先知：效果与打出相同。</summary>
    protected override Task OnProphet(PlayerChoiceContext choiceContext) =>
        StrikeAndDebuff(choiceContext, null);

    private async Task StrikeAndDebuff(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var enemies = CombatState?.HittableEnemies;
        if (enemies == null || enemies.Count == 0) return;

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .TargetingAllOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        await PowerCmd.Apply<WeakPower>(choiceContext, enemies, DynamicVars.Weak.BaseValue, Owner.Creature, this);
        await PowerCmd.Apply<VulnerablePower>(choiceContext, enemies, DynamicVars.Vulnerable.BaseValue, Owner.Creature, this);
    }

    protected override void OnUpgrade()
    {
        // 敲后不增加伤害/易伤/虚弱，而是把费用降到 0。
        EnergyCost.UpgradeBy(CostReductionOnUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "试探",
        "对所有敌人造成{Damage:diff()}点伤害，并给予所有敌人{VulnerablePower:diff()}层[gold]易伤[/gold]和{WeakPower:diff()}层[gold]虚弱[/gold]。\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Probe",
        "Deal {Damage:diff()} damage and apply {VulnerablePower:diff()} [gold]Vulnerable[/gold] and {WeakPower:diff()} [gold]Weak[/gold] to ALL enemies.\n[gold]Prophet[/gold].");
}
