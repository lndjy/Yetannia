using BaseLib.Abstracts;
using BaseLib.Extensions;
using BaseLib.Hooks;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 编织 / Weave — ported from Slay the Spire 1 (Watcher, Uncommon, 0 energy Attack):
/// "Deal 4 damage. Whenever you Scry, return this from the discard pile to your hand."
/// Upgraded: 6 damage.
///
/// The "whenever you Scry" clause uses BaseLib's <see cref="IAfterScryed"/> hook. A card sitting in
/// a combat pile is a hook listener, so Weave hears about scries while it is in the discard pile.
/// </summary>
public sealed class Weave : YetanniaCard, IAfterScryed
{
    private const int DamageBase = 4;
    private const int DamageUpgrade = 2; // 4 -> 6

    public Weave()
        : base(0, CardType.Attack, CardRarity.Uncommon, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(DamageBase, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    public async Task AfterScryed(PlayerChoiceContext ctx, Player player, int scryAmount, int discardAmount,
        List<CardModel> seen, List<CardModel> discarded)
    {
        if (player != Owner) return;
        if (Pile?.Type != PileType.Discard) return;
        if (PileType.Hand.GetPile(player).Cards.Count >= CardPile.MaxCardsInHand) return;

        await CardPileCmd.Add(this, PileType.Hand, CardPilePosition.Bottom);
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "回马枪",
        "造成{Damage:diff()}点伤害。\n每当你[gold]预见[/gold]时，将此牌从弃牌堆移回你的手牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Backswing",
        "Deal {Damage:diff()} damage.\nWhenever you [gold]Scry[/gold], return this from the discard pile to your hand.");
}
