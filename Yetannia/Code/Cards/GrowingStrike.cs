using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Saves.Runs;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 命定的抗争 — 蓝卡（Uncommon），2 费攻击，[虚无]：
/// 造成 18（升级 26）点伤害。**当这张牌被消耗时，本局游戏中它的伤害永久 +2。**
///
/// Name is a placeholder (the request did not give one).
///
/// The growth is **run-scoped**, not combat-scoped. That is the base game's GeneticAlgorithm
/// pattern: the accumulated bonus lives in a <c>[SavedProperty]</c> field (so it survives saving and
/// loading), and the same bonus is also written to <c>DeckVersion</c> — the persistent card in the
/// player's deck — so the next combat starts from the higher number.
///
/// Being Ethereal is what makes the loop work: an unplayed copy exhausts at end of turn and grows.
/// </summary>
public sealed class GrowingStrike : YetanniaCard
{
    private const int BaseDamage = 18;
    private const int UpgradedDamage = 26;
    private const int BonusPerExhaust = 2;

    private int _bonusDamage;

    public GrowingStrike()
        : base(2, CardType.Attack, CardRarity.Uncommon, TargetType.AnyEnemy)
    {
    }

    /// <summary>
    /// [虚无] only, deliberately NOT [消耗].
    ///
    /// The card is meant to be a choice: play it now for its damage and give up the growth, or leave it
    /// in hand and let Ethereal burn it at end of turn to grow it for the rest of the run. Carrying
    /// [消耗] defeated that, because <c>CardModel</c>'s post-play resolution exhausts on
    /// <c>ExhaustOnNextPlay || Keywords.Contains(CardKeyword.Exhaust)</c> — so playing it destroyed it
    /// and grew it at the same time, and there was never a reason not to play it. Ethereal alone does
    /// NOT exhaust a card that was played, so dropping the keyword is what creates the choice.
    /// </summary>
    public override IEnumerable<CardKeyword> CanonicalKeywords =>
        [CardKeyword.Ethereal];

    /// <summary>本局游戏累计的额外伤害。存档字段，跨战斗保留。</summary>
    [SavedProperty]
    public int BonusDamage
    {
        get => _bonusDamage;
        set
        {
            AssertMutable();
            _bonusDamage = value;
            DynamicVars.Damage.BaseValue = PrintedDamage + _bonusDamage;
        }
    }

    private int PrintedDamage => IsUpgraded ? UpgradedDamage : BaseDamage;

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

    /// <summary>当此牌被消耗时，本局游戏中它的伤害永久 +2（同时写回牌组里的那张）。</summary>
    public override Task AfterCardExhausted(PlayerChoiceContext choiceContext, CardModel card, bool causedByEthereal)
    {
        if (!ReferenceEquals(card, this)) return Task.CompletedTask;

        BonusDamage += BonusPerExhaust;

        // DeckVersion is the persistent deck card; buffing it is what makes this survive the combat.
        if (DeckVersion is GrowingStrike deckCopy && !ReferenceEquals(deckCopy, this))
        {
            deckCopy.BonusDamage += BonusPerExhaust;
        }

        return Task.CompletedTask;
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Damage.UpgradeValueBy(UpgradedDamage - BaseDamage);
        DynamicVars.Damage.BaseValue = PrintedDamage + _bonusDamage;
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "命定的抗争",
        "造成{Damage:diff()}点伤害。\n当这张牌被消耗时，本局游戏中它的伤害永久+2。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Defiance of Fate",
        "Deal {Damage:diff()} damage.\nWhen this card is exhausted, it permanently deals 2 more damage for the rest of the run.");
}
