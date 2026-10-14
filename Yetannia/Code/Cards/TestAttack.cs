using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 攻击牌 test — rare, 1 energy, deals 12 damage (16 upgraded).
///
/// [gold]先知[/gold]：对随机目标打出此牌，然后此牌伤害翻倍。
/// (Prophet: play this card against a random target, then double its damage.)
///
/// The "draw pile -&gt; discard pile" trigger itself lives in <see cref="YetanniaCard"/>; this card
/// only supplies the effect through <see cref="OnProphet"/>.
/// </summary>
public sealed class TestAttack : YetanniaCard
{
    private const int BaseDamage = 12;
    private const int DamageUpgrade = 4; // 12 -> 16
    private const int DamageMultiplierPerTrigger = 2;

    public TestAttack()
        : base(1, CardType.Attack, CardRarity.Rare, TargetType.AnyEnemy)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

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
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    /// <summary>
    /// 先知：对随机目标打出此牌，然后此牌伤害翻倍。
    ///
    /// The order is the point: the attack resolves with the *current* damage and only then does the
    /// value double, so the first trigger hits for 12 and leaves the card at 24, the second hits for
    /// 24 and leaves it at 48, and so on.
    ///
    /// Safe from recursion: the trigger is fired by a pile change (draw pile -&gt; discard pile), and
    /// attacking does not move this card, so it cannot re-enter
    /// <see cref="YetanniaCard.AfterCardChangedPiles"/>.
    /// </summary>
    protected override async Task OnProphet(PlayerChoiceContext choiceContext)
    {
        // FromCard with a null CardPlay: a Prophet trigger is not a card play, but the command still
        // needs the attacker (the owner's creature) and the card as its model source.
        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, null)
            .TargetingRandomOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        DynamicVars.Damage.BaseValue *= DamageMultiplierPerTrigger;
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "请君入瓮",
        "造成{Damage:diff()}点伤害。\n[gold]先知[/gold]：对随机目标打出此牌，然后此牌伤害翻倍。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Into the Trap",
        "Deal {Damage:diff()} damage.\n[gold]Prophet[/gold]: play this card against a random target, then double its damage.");
}
