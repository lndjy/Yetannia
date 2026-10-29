using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 纯爱形态 — 本场战斗中，当你从抽牌堆弃置非[先知]牌时，让它变成 0 费，**直到你下次打出它**。
///
/// 牌不会离开弃牌堆：只是挂上一个「打出前都算 0 费」的费用修正
/// （<see cref="CardEnergyCost.SetUntilPlayed"/>），所以洗牌后被抽到仍然是 0 费，
/// 打出那一次花 0 费，打完恢复原价；之后再被预见弃掉又重新变 0 费。
///
/// 之前这里是「视为打出」（<c>CardCmd.AutoPlay</c>）：联机下那张牌如果自己还要开一个玩家选择
/// （韬光养晦 / 预备 开手牌选择、预见开网格），会和 hook 自己的选择抢同一条 ActionQueue，
/// 报 "Attempting to enqueue GameAction ... which already has an ID ..." 并把战斗卡死。
/// 现在完全不碰玩家选择。
/// </summary>
public sealed class PureLoveFormPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    public override Task AfterCardChangedPiles(CardModel card, PileType oldPileType, AbstractModel clonedBy)
    {
        if (card?.Owner?.Creature != Owner) return Task.CompletedTask;
        if (oldPileType != PileType.Draw) return Task.CompletedTask;
        if (card.Pile?.Type != PileType.Discard) return Task.CompletedTask;

        // "非先知牌": Prophet cards run their own Prophet effect instead.
        if (card.Keywords.Contains(YetanniaKeywords.Prophet)) return Task.CompletedTask;

        card.EnergyCost.SetUntilPlayed(0);
        card.SetStarCostUntilPlayed(0);
        return Task.CompletedTask;
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/pure_love_form.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/pure_love_form.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "纯爱形态",
        "本场战斗中，当你从抽牌堆弃置非[gold]先知[/gold]牌时，使其耗能变为0，直到你下次打出它。",
        "本场战斗中，当你从抽牌堆弃置非[gold]先知[/gold]牌时，使其耗能变为0，直到你下次打出它。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Pure Love Form",
        "This combat, when you discard a non-[gold]Prophet[/gold] card from your draw pile, it costs 0 until the next time you play it.",
        "This combat, when you discard a non-[gold]Prophet[/gold] card from your draw pile, it costs 0 until the next time you play it.");
}
