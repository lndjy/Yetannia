using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 背水一战 — 金卡（Rare），2 费技能，[消耗]：
/// 预见 6（升级 8）；[消耗]因此被弃置的牌，**并触发它们的[先知]效果**；然后抽走剩下的牌。
///
/// 「剩下的牌」= 本次预见看到的牌里没有被弃置的那些。预见前先记下会看到几张
/// （受抽牌堆实际张数限制），预见到之后用 看到张数 - 弃置张数 得出要抽几张。
///
/// The Prophet trigger on each exhausted card is NOT fired by this card: the discard performed inside
/// the scry already triggered it (see the note in <c>OnPlay</c>). Replay and the Prophet tally therefore
/// see exactly one trigger per discarded card.
///
/// The Power-card Limbo move is skipped: exhausting already takes the card out of play, so the two would
/// fight over the same pile.
/// </summary>
public sealed class GrandProphecy : YetanniaCard
{
    private const int ScryBase = 6;
    private const int ScryUpgrade = 2; // 6 -> 8

    public GrandProphecy()
        : base(2, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new ScryVar(ScryBase)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var scryAmount = (int)DynamicVars["Scry"].BaseValue;
        var expectedSeen = Math.Min(scryAmount, PileType.Draw.GetPile(Owner).Cards.Count);

        // Snapshot the automatic-trigger counter before the scry: everything the discard hook fires for
        // moves the counter past this value.
        var tokenBefore = YetanniaCard.CurrentProphetToken;

        var result = await Scry(choiceContext, scryAmount);

        foreach (var card in result.Discarded)
        {
            // The discard inside the scry normally triggers the Prophet effect on its own (the card is a
            // hook listener and sees its own Draw -> Discard). Blindly calling ResolveProphet here as well
            // made every discarded Prophet card resolve TWICE, so it is only called for cards the
            // automatic hook actually missed — the card text promises the trigger, and the hook drops
            // roughly one discard in ten.
            if (card is YetanniaCard prophetCard
                && card.Keywords.Contains(YetanniaKeywords.Prophet)
                && prophetCard.LastProphetToken <= tokenBefore)
            {
                MainFile.Logger.Info(
                    $"[prophet] {card.Id.Entry} was discarded by GrandProphecy without its automatic trigger; firing it here");
                await prophetCard.ResolveProphet(choiceContext);
            }

            await CardCmd.Exhaust(choiceContext, card);
        }

        var toDraw = Math.Max(0, expectedSeen - result.Discarded.Count);
        if (toDraw > 0)
        {
            await CardPileCmd.Draw(choiceContext, toDraw, Owner);
        }
    }

    protected override void OnUpgrade() => DynamicVars["Scry"].UpgradeValueBy(ScryUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "背水一战",
        "预见{Scry:diff()}。\n[gold]消耗[/gold]因此被弃置的牌，并触发它们的[gold]先知[/gold]效果。\n抽取剩下的牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Last Stand",
        "Scry {Scry:diff()}.\n[gold]Exhaust[/gold] the cards discarded this way, triggering their [gold]Prophet[/gold] effects.\nDraw the remaining cards.");
}
