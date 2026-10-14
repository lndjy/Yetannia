using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 制敌机先 — 蓝卡（Uncommon），1 费攻击：
/// 造成 9（升级 12）点伤害；如果目标敌人的意图是攻击，再给予 2 层[虚弱]。
///
/// "Intends to attack" is <c>MonsterModel.IntendsToAttack</c>, which the base game defines as the
/// next move containing an Attack or DeathBlow intent — the same check the game uses for its own
/// intent-driven effects.
/// </summary>
public sealed class SeizeTheInitiative : YetanniaCard
{
    private const int BaseDamage = 9;
    private const int DamageUpgrade = 3; // 9 -> 12
    private const int WeakAmount = 2;

    public SeizeTheInitiative()
        : base(1, CardType.Attack, CardRarity.Uncommon, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(BaseDamage, ValueProp.Move),
        new PowerVar<WeakPower>(WeakAmount)
    ];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
        [HoverTipFactory.FromPower<WeakPower>()];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        if (cardPlay.Target.Monster?.IntendsToAttack == true)
        {
            await PowerCmd.Apply<WeakPower>(
                choiceContext, cardPlay.Target, DynamicVars.Weak.BaseValue, Owner.Creature, this);
        }
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "制敌机先",
        "造成{Damage:diff()}点伤害。如果目标敌人的意图是攻击，给予其{WeakPower:diff()}层[gold]虚弱[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Seize the Initiative",
        "Deal {Damage:diff()} damage. If the enemy intends to attack, apply {WeakPower:diff()} [gold]Weak[/gold].");
}
