using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>纯爱幻想 — 状态牌，1 费：当此牌被消耗时，对随机敌人造成 6 点伤害，然后抽 1 张牌。[消耗]</summary>
public sealed class StrikeStrike : YetanniaCard
{
    public override int MaxUpgradeLevel => 0;

    public StrikeStrike()
        : base(1, CardType.Status, CardRarity.Status, TargetType.None)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DamageVar(6, ValueProp.Move)];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay) => Task.CompletedTask;

    public override async Task AfterCardExhausted(PlayerChoiceContext choiceContext, CardModel card, bool causedByEthereal)
    {
        if (!ReferenceEquals(card, this)) return;
        var damage = DynamicVars.Damage.BaseValue;
        if (Owner.Creature.GetPower<DoubleStatusPower>() != null) damage *= 2;
        await DamageCmd.Attack(damage)
            .FromCard(this, null)
            .TargetingRandomOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        // 被消耗时补一张牌（v1.0.5）。Drawn after the damage so the fizzle of a dead combat cannot eat the
        // draw, and through CardPileCmd.Draw so every draw hook (涅槃 / 不灭 / 先知研习) still sees it.
        await CardPileCmd.Draw(choiceContext, 1, Owner);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "纯爱幻想", "当此牌被消耗时，对随机敌人造成6点伤害，然后抽1张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Pure Love Fantasy", "When this card is exhausted, deal 6 damage to a random enemy, then draw 1 card.");
}
