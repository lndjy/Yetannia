using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 水色之舞 — 白卡（Common），0 费攻击：
/// 造成 11（升级 15）点伤害。**只有当目标敌人的意图是攻击时才能打出。**
///
/// Name is a placeholder (the request did not give one).
///
/// The rule is enforced in two places because no single hook can express it:
///
/// * <see cref="ShouldPlay"/> is a *necessary* pre-filter — with no attacker-intent enemy on the
///   field there is no legal target at all, so the card greys out in hand. This hook is not given
///   the chosen target, so it cannot be the whole rule.
/// * <c>CounterStrikeTargetPatch</c> adds the *sufficient* half on the target-aware
///   <c>CardModel.CanPlayTargeting(target)</c>, which is the gate the manual-play path actually
///   uses. That is what makes it strict about the enemy you drop the card on.
///
/// <c>MonsterModel.IntendsToAttack</c> covers Attack and DeathBlow, matching the game's own
/// definition of "intends to attack".
/// </summary>
public sealed class CounterStrike : YetanniaCard
{
    private const int BaseDamage = 11;
    private const int DamageUpgrade = 4; // 11 -> 15

    public CounterStrike()
        : base(0, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(BaseDamage, ValueProp.Move)];

    /// <summary>
    /// 必要条件：场上至少有一个敌人的意图是攻击。
    /// 精确到「你打的那个敌人」的判定在 <c>CounterStrikeTargetPatch</c> 里（这个钩子拿不到目标）。
    /// </summary>
    public override bool ShouldPlay(CardModel card, AutoPlayType autoPlayType)
    {
        if (!ReferenceEquals(card, this)) return true;

        var enemies = CombatState?.HittableEnemies;
        if (enemies == null) return false;

        return enemies.Any(enemy => enemy.Monster?.IntendsToAttack == true);
    }

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "水色之舞",
        "造成{Damage:diff()}点伤害。\n只有当目标敌人的意图是攻击时才能打出。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Dance of Azure",
        "Deal {Damage:diff()} damage.\nCan only be played against an enemy that intends to attack.");
}
