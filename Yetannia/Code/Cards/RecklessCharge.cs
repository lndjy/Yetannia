using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 奋不顾身 — 白卡（Common），0 费攻击：
/// 造成 11（升级 15）点伤害，然后将一张[眩晕]加入你的弃牌堆。
///
/// The Dazed is created the same way 殚精竭虑 does it: <c>CreateCard</c> on the combat state plus
/// <c>AddGeneratedCardToCombat</c>, so generated-card hooks stay consistent.
/// </summary>
public sealed class RecklessCharge : YetanniaCard
{
    private const int BaseDamage = 11;
    private const int DamageUpgrade = 4; // 11 -> 15

    public RecklessCharge()
        : base(0, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(BaseDamage, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        var combatState = CombatState;
        if (combatState == null) return;

        var dazed = combatState.CreateCard<Dazed>(Owner);
        await CardPileCmd.AddGeneratedCardToCombat(dazed, PileType.Discard, Owner);
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "奋不顾身",
        "造成{Damage:diff()}点伤害。将一张[gold]眩晕[/gold]加入你的弃牌堆。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Reckless Charge",
        "Deal {Damage:diff()} damage. Add a [gold]Dazed[/gold] into your discard pile.");
}
