using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 长驱直入 — 金卡（Rare），1 费攻击：
/// 对所有敌人造成 11（升级 15）点伤害；敌人身上每有一种负面状态，伤害 +4（升级 5）。
///
/// Name is a placeholder (the request did not give one).
///
/// Modelled on the base game's <c>Rend</c> (single-target, 10 + 5 per debuff), which is
/// <c>CalculationBaseVar</c> + <c>ExtraDamageVar</c> + <c>CalculatedDamageVar</c> with a per-target
/// multiplier counting debuffs. This card hits every enemy, and <c>AttackCommand</c> applies a single
/// amount to all AOE targets, so the per-enemy scaling is done by looping and attacking each enemy
/// with its own <c>Calculate(enemy)</c> value.
/// </summary>
public sealed class Settlement : YetanniaCard
{
    private const int BaseDamage = 11;
    private const int BaseUpgrade = 4;  // 11 -> 15
    private const int BonusDamage = 4;
    private const int BonusUpgrade = 1; // 4 -> 5

    public Settlement()
        : base(1, CardType.Attack, CardRarity.Rare, TargetType.AllEnemies)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new CalculationBaseVar(BaseDamage),
        new ExtraDamageVar(BonusDamage),
        new CalculatedDamageVar(ValueProp.Move).WithMultiplier(
            static (CardModel card, Creature target) =>
                target?.Powers.Count(p =>
                    p.TypeForCurrentAmount == PowerType.Debuff && p is not ITemporaryPower) ?? 0),
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var enemies = CombatState?.HittableEnemies?.ToList();
        if (enemies == null || enemies.Count == 0) return;

        var calculated = (CalculatedDamageVar)DynamicVars["CalculatedDamage"];

        foreach (var enemy in enemies)
        {
            if (!enemy.IsAlive) continue;
            await DamageCmd.Attack(calculated.Calculate(enemy))
                .FromCard(this, cardPlay)
                .Targeting(enemy)
                .WithHitFx("vfx/vfx_attack_slash")
                .Execute(choiceContext);
        }
    }

    protected override void OnUpgrade()
    {
        DynamicVars.CalculationBase.UpgradeValueBy(BaseUpgrade);
        DynamicVars.ExtraDamage.UpgradeValueBy(BonusUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "长驱直入",
        "对所有敌人造成{CalculationBase:diff()}点伤害。敌人身上每有一种负面状态，伤害+{ExtraDamage:diff()}。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Drive Straight In",
        "Deal {CalculationBase:diff()} damage to ALL enemies. Increase this damage by {ExtraDamage:diff()} for each kind of negative status on the enemy.");
}
