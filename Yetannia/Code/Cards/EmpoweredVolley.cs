using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Config;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 夹击之势 — 金卡（Rare），X 费攻击：重复 X 次，每次先获得[力量]，再对随机敌人造成伤害。
/// - 原版（<see cref="CardBalanceMode.Original"/>）：获得 1 点（永久）[力量]，造成 10（升级 14）点伤害。
/// - 东尼测试版（<see cref="CardBalanceMode.TonyTest"/>）：获得 2（升级 3）点**临时**[力量]，
///   造成 7（升级 9）点伤害。
/// (Original: gain 1 permanent Strength, then deal 10 / 14 damage. Tony draft: gain 2 / 3 temporary
/// Strength, then deal 7 / 9 damage.)
///
/// Name is a placeholder (the request did not give one).
///
/// The Strength is granted *before* each hit, so the volley escalates: the first hit is unmodified,
/// the second is +1 (original) or +2 (Tony draft), the third +2 / +4, and so on. Each hit picks its
/// own random target, matching the "随机" wording.
/// </summary>
public sealed class EmpoweredVolley : YetanniaCard
{
    private const int OriginalBaseDamage = 10;
    private const int OriginalDamageUpgrade = 4; // 10 -> 14
    private const int OriginalStrengthPerHit = 1;

    private const int TonyBaseDamage = 7;
    private const int TonyDamageUpgrade = 2; // 7 -> 9
    private const int TonyStrengthPerHit = 2;
    private const int TonyStrengthUpgrade = 1; // 2 -> 3，仅东尼测试版敲后

    public EmpoweredVolley()
        : base(0, CardType.Attack, CardRarity.Rare, TargetType.AllEnemies)
    {
    }

    protected override bool HasEnergyCostX => true;

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(CardBalance.IsTony ? TonyBaseDamage : OriginalBaseDamage, ValueProp.Move),
        CardBalance.IsTony
            ? new PowerVar<TempMightPower>(TonyStrengthPerHit)
            : new PowerVar<StrengthPower>(OriginalStrengthPerHit)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var x = ResolveEnergyXValue();
        if (x <= 0) return;

        for (var i = 0; i < x; i++)
        {
            if (CardBalance.IsTony)
            {
                // 东尼测试版：临时力量（回合结束收回），不是永久力量。
                await PowerCmd.Apply<TempMightPower>(
                    choiceContext, Owner.Creature, DynamicVars.Power<TempMightPower>().BaseValue,
                    Owner.Creature, this);
            }
            else
            {
                await PowerCmd.Apply<StrengthPower>(
                    choiceContext, Owner.Creature, DynamicVars.Strength.BaseValue, Owner.Creature, this);
            }

            await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
                .FromCard(this, cardPlay)
                .TargetingRandomOpponents(CombatState)
                .WithHitFx("vfx/vfx_attack_slash")
                .Execute(choiceContext);
        }
    }

    protected override void OnUpgrade()
    {
        if (CardBalance.IsTony)
        {
            DynamicVars.Damage.UpgradeValueBy(TonyDamageUpgrade);
            DynamicVars.Power<TempMightPower>().UpgradeValueBy(TonyStrengthUpgrade);
            return;
        }

        DynamicVars.Damage.UpgradeValueBy(OriginalDamageUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    // PowerVar<T> names its variable after the power type, so the placeholder differs per draft.
    private static List<(string, string)> Chinese => CardBalance.IsTony
        ? new CardLoc(
            "夹击之势",
            "重复X次：获得{TempMightPower:diff()}点临时[gold]力量[/gold]，对随机敌人造成{Damage:diff()}点伤害。")
        : new CardLoc(
            "夹击之势",
            "重复X次：获得{StrengthPower:diff()}点[gold]力量[/gold]，对随机敌人造成{Damage:diff()}点伤害。");

    private static List<(string, string)> English => CardBalance.IsTony
        ? new CardLoc(
            "Pincer Movement",
            "Repeat X times: gain {TempMightPower:diff()} temporary [gold]Strength[/gold], then deal {Damage:diff()} damage to a random enemy.")
        : new CardLoc(
            "Pincer Movement",
            "Repeat X times: gain {StrengthPower:diff()} [gold]Strength[/gold], then deal {Damage:diff()} damage to a random enemy.");
}
