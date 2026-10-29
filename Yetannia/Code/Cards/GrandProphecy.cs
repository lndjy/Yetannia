using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using Yetannia.YetanniaCode.Config;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 背水一战 — 金卡（Rare），2 费技能，[消耗]：
/// 预见；[消耗]因此被弃置的牌（原版与东尼测试版的升级档还会触发它们的[先知]效果）；然后抽走剩下的牌。
///
/// 两档不同：
/// - 原版（<see cref="CardBalanceMode.Original"/>）：预见 6（升级 8），两档都触发被弃置牌的先知效果。
/// - 东尼测试版（<see cref="CardBalanceMode.TonyTest"/>）：两档统一预见 7，**未升级不触发**被弃置牌的
///   先知效果，升级后才触发。
/// (Original: Scry 6, upgraded 8, and the discarded cards' Prophet effects trigger at both upgrade
/// levels. Tony draft: Scry 7 at both upgrade levels, and only the upgraded copy triggers them.)
///
/// 「剩下的牌」= 本次预见看到的牌里没有被弃置的那些。预见前先记下会看到几张
/// （受抽牌堆实际张数限制），预见到之后用 看到张数 - 弃置张数 得出要抽几张。
///
/// The Prophet trigger on each exhausted card is NOT fired by this card: the discard performed inside
/// the scry already triggered it (see the note in <c>OnPlay</c>). Replay and the Prophet tally therefore
/// see exactly one trigger per discarded card. In the 东尼测试版 unupgraded case that automatic
/// trigger is deliberately silenced instead — see <see cref="ProphetQueue.SuppressFor"/>.
///
/// The Power-card Limbo move is skipped: exhausting already takes the card out of play, so the two would
/// fight over the same pile.
/// </summary>
public sealed class GrandProphecy : YetanniaCard
{
    private const int OriginalScryBase = 6;
    private const int ScryUpgrade = 2; // 6 -> 8（仅原版）
    private const int TonyScryBase = 7; // 东尼测试版两档都是 7

    public GrandProphecy()
        : base(2, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new ScryVar(CardBalance.IsTony ? TonyScryBase : OriginalScryBase)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var scryAmount = (int)DynamicVars["Scry"].BaseValue;
        var expectedSeen = Math.Min(scryAmount, PileType.Draw.GetPile(Owner).Cards.Count);

        // 东尼测试版：未升级不触发被弃置牌的先知效果，升级后才触发；原版两档都触发。
        var triggerProphets = !CardBalance.IsTony || IsUpgraded;

        // Snapshot the automatic-trigger counter before the scry: everything the discard hook fires for
        // moves the counter past this value.
        var tokenBefore = YetanniaCard.CurrentProphetToken;

        // The scry's own discards would fire every discarded 先知 card through the pile-change hook, so
        // the "don't trigger" draft has to silence that hook for this player while the scry runs — the
        // card cannot just skip its own fallback below, because the automatic trigger is the common path.
        var previousSuppression = triggerProphets ? null : ProphetQueue.SuppressFor(Owner);

        ScryResult result;
        try
        {
            result = await Scry(choiceContext, scryAmount);
        }
        finally
        {
            if (!triggerProphets)
            {
                ProphetQueue.RestoreSuppression(previousSuppression);
            }
        }

        foreach (var card in result.Discarded)
        {
            // The discard inside the scry normally triggers the Prophet effect on its own (the card is a
            // hook listener and sees its own Draw -> Discard). Blindly calling ResolveProphet here as well
            // made every discarded Prophet card resolve TWICE, so it is only called for cards the
            // automatic hook actually missed — the card text promises the trigger, and the hook drops
            // roughly one discard in ten.
            if (triggerProphets
                && card is YetanniaCard prophetCard
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

    protected override void OnUpgrade()
    {
        // 东尼测试版两档都是预见 7，升级只开启「触发先知效果」，不加预见。
        if (!CardBalance.IsTony)
        {
            DynamicVars["Scry"].UpgradeValueBy(ScryUpgrade);
        }
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static List<(string, string)> Chinese => CardBalance.IsTony
        ? new CardLoc(
            "背水一战",
            "预见{Scry:diff()}。\n[gold]消耗[/gold]因此被弃置的牌{IfUpgraded:show:，并触发它们的[gold]先知[/gold]效果|}。\n抽取剩下的牌。")
        : new CardLoc(
            "背水一战",
            "预见{Scry:diff()}。\n[gold]消耗[/gold]因此被弃置的牌，并触发它们的[gold]先知[/gold]效果。\n抽取剩下的牌。");

    private static List<(string, string)> English => CardBalance.IsTony
        ? new CardLoc(
            "Last Stand",
            "Scry {Scry:diff()}.\n[gold]Exhaust[/gold] the cards discarded this way{IfUpgraded:show:, triggering their [gold]Prophet[/gold] effects|}.\nDraw the remaining cards.")
        : new CardLoc(
            "Last Stand",
            "Scry {Scry:diff()}.\n[gold]Exhaust[/gold] the cards discarded this way, triggering their [gold]Prophet[/gold] effects.\nDraw the remaining cards.");
}
