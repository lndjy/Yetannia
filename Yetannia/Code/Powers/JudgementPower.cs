using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 星光破晓之刻 — 拥有[易伤]的敌人受到的伤害 +25%；拥有[虚弱]的敌人造成的伤害 -15%。
///
/// This is a *second* layer on top of the base game's own Vulnerable (+50% taken) and Weak
/// (-25% dealt); it does not replace them.
///
/// <c>ModifyDamageMultiplicative</c> is asked for every damage instance with the target and the
/// dealer in hand, so both halves are expressed as multipliers:
///   * +25% applies to damage whose **dealer is this power's owner** (our damage) and whose target
///     has Vulnerable — "拥有易伤的敌人受到伤害增加" reads as the player's damage being amplified.
///   * -15% applies to damage whose **dealer has Weak** and is not on our side — i.e. enemy attacks.
/// </summary>
public sealed class JudgementPower : CustomPowerModel
{
    private const decimal VulnerableTargetMultiplier = 1.25m;
    private const decimal WeakDealerMultiplier = 0.85m;

    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    public override decimal ModifyDamageMultiplicative(
        Creature target,
        decimal amount,
        ValueProp props,
        Creature dealer,
        CardModel cardSource,
        CardPlay cardPlay)
    {
        if (dealer == null) return 1m;

        // Our damage against a Vulnerable enemy.
        if (dealer == Owner && target != null && target.HasPower<VulnerablePower>())
        {
            return VulnerableTargetMultiplier;
        }

        // A Weak enemy's damage against us.
        if (dealer != Owner && dealer.Side != Owner.Side && dealer.HasPower<WeakPower>())
        {
            return WeakDealerMultiplier;
        }

        return 1m;
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/judgement.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/judgement.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "星光破晓之刻",
        "拥有[gold]易伤[/gold]的敌人受到的伤害增加25%。拥有[gold]虚弱[/gold]的敌人造成的伤害减少15%。",
        "拥有[gold]易伤[/gold]的敌人受到的伤害增加25%。拥有[gold]虚弱[/gold]的敌人造成的伤害减少15%。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Starlight at Dawn",
        "Enemies with [gold]Vulnerable[/gold] take 25% more damage. Enemies with [gold]Weak[/gold] deal 15% less damage.",
        "Enemies with [gold]Vulnerable[/gold] take 25% more damage. Enemies with [gold]Weak[/gold] deal 15% less damage.");
}
