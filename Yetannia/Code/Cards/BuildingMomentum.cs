using BaseLib.Abstracts;
using BaseLib.Extensions;
using BaseLib.Utils;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 先知打击 — 蓝卡（Uncommon），1 费攻击：
/// 造成 6（升级 9）点伤害；你每拥有 1 张[先知]卡牌，此牌额外造成 2（升级 3）点伤害。[先知]。
///
/// The per-card bonus is a <see cref="CalculatedDamageVar"/> so the card face keeps up with the
/// count (see README's 宿命累积 / CalculatedDamageVar notes).
/// The multiplier must be a static lambda because <c>WithMultiplier</c> rejects delegates that
/// capture an <c>AbstractModel</c>.
/// </summary>
public sealed class BuildingMomentum : YetanniaCard
{
    private const int BaseDamage = 6;
    private const int BaseDamageUpgrade = 3; // 6 -> 9
    private const int BaseBonusPerCard = 2;
    private const int BonusUpgrade = 1; // 2 -> 3

    public BuildingMomentum()
        : base(1, CardType.Attack, CardRarity.Uncommon, TargetType.AnyEnemy)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new CalculationBaseVar(BaseDamage),
        new ExtraDamageVar(BaseBonusPerCard),
        new CalculatedDamageVar(ValueProp.Move).WithMultiplier(
            static (CardModel card, Creature _) => (decimal)YetanniaCard.ProphetCardCount(card))
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.CalculatedDamage)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    /// <summary>先知（无额外描述）：效果与打出相同，随机打一个目标。</summary>
    protected override async Task OnProphet(PlayerChoiceContext choiceContext)
    {
        await DamageCmd.Attack(DynamicVars.CalculatedDamage)
            .FromCard(this, null)
            .TargetingRandomOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.CalculationBase.UpgradeValueBy(BaseDamageUpgrade);
        DynamicVars.ExtraDamage.UpgradeValueBy(BonusUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "先知打击",
        "造成{CalculatedDamage:diff()}点伤害。你每拥有1张[gold]先知[/gold]牌，此牌额外造成{ExtraDamage:diff()}点伤害。\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Prophetic Strike",
        "Deal {CalculatedDamage:diff()} damage, plus {ExtraDamage:diff()} additional damage for each [gold]Prophet[/gold] card you have.\n[gold]Prophet[/gold].");
}
