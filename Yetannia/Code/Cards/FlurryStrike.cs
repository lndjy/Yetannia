using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 白刃乱舞 — 蓝卡（Uncommon），1 费攻击：
/// 造成 3（升级 4）点伤害 X 次，X 为本回合此前打出的牌数。
///
/// Name is a placeholder (the request did not give one).
///
/// Modelled on the base game's <c>Finisher</c>, which is the same idea (it counts Attacks instead of
/// every card). Two things are copied from it deliberately:
/// * the hit count is a <c>CalculatedVar</c> so the value is computed at play time, not baked in;
/// * the count filters on <c>e.CardPlay.Player == card.Owner</c> — combat history is shared between
///   players in co-op, so without that filter a teammate's plays would inflate this card.
///
/// This card's own play is not counted: its history entry is appended when the play *finishes*,
/// which is after <c>OnPlay</c> has run.
/// </summary>
public sealed class FlurryStrike : YetanniaCard
{
    private const int BaseDamage = 3;
    private const int DamageUpgrade = 1; // 3 -> 4

    public FlurryStrike()
        : base(1, CardType.Attack, CardRarity.Uncommon, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(BaseDamage, ValueProp.Move),
        // CalculatedVar is value = CalculationBase + CalculationExtra * multiplier, and it *looks
        // those two up by name* — omitting them throws KeyNotFoundException the first time the card
        // face or the play tries to calculate. <c>Finisher</c> declares both for the same reason.
        new CalculationBaseVar(0m),
        new CalculationExtraVar(1m),
        new CalculatedVar("CalculatedHits").WithMultiplier(
            static (CardModel card, Creature _) => CardsPlayedThisTurn(card)),
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        var hits = (int)((CalculatedVar)DynamicVars["CalculatedHits"]).Calculate(cardPlay.Target);

        // Nothing played yet this turn means nothing to mirror. Skipping avoids running the attack
        // animation for a zero-hit swing.
        if (hits <= 0) return;

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .WithHitCount(hits)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    private static decimal CardsPlayedThisTurn(CardModel card) =>
        CombatManager.Instance.History.CardPlaysFinished.Count(
            (CardPlayFinishedEntry e) =>
                e.HappenedThisTurn(card.CombatState) && e.CardPlay.Player == card.Owner);

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "白刃乱舞",
        "造成{Damage:diff()}点伤害 X 次。X 为本回合此前打出的牌数。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Blade Frenzy",
        "Deal {Damage:diff()} damage X times, where X is the number of cards you played earlier this turn.");
}
