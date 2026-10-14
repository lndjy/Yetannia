using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 夹击之势 — 金卡（Rare），X 费攻击：
/// 重复 X 次：（获得 1 点[力量]，对随机敌人造成 10（升级 14）点伤害）。
///
/// Name is a placeholder (the request did not give one).
///
/// The Strength is granted *before* each hit, so the volley escalates: the first hit is unmodified,
/// the second is +1, the third +2, and so on. Each hit picks its own random target, matching the
/// "随机" wording.
/// </summary>
public sealed class EmpoweredVolley : YetanniaCard
{
    private const int BaseDamage = 10;
    private const int DamageUpgrade = 4; // 10 -> 14
    private const int StrengthPerHit = 1;

    public EmpoweredVolley()
        : base(0, CardType.Attack, CardRarity.Rare, TargetType.AllEnemies)
    {
    }

    protected override bool HasEnergyCostX => true;

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(BaseDamage, ValueProp.Move),
        new PowerVar<StrengthPower>(StrengthPerHit)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var x = ResolveEnergyXValue();
        if (x <= 0) return;

        for (var i = 0; i < x; i++)
        {
            await PowerCmd.Apply<StrengthPower>(
                choiceContext, Owner.Creature, DynamicVars.Strength.BaseValue, Owner.Creature, this);

            await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
                .FromCard(this, cardPlay)
                .TargetingRandomOpponents(CombatState)
                .WithHitFx("vfx/vfx_attack_slash")
                .Execute(choiceContext);
        }
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "夹击之势",
        "重复X次：获得{StrengthPower:diff()}点[gold]力量[/gold]，对随机敌人造成{Damage:diff()}点伤害。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Pincer Movement",
        "Repeat X times: gain {StrengthPower:diff()} [gold]Strength[/gold], then deal {Damage:diff()} damage to a random enemy.");
}
