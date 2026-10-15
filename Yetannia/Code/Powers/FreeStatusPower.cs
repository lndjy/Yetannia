using System.Collections.Generic;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Cards;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>剑之所指 的能力：你的纯爱幻想和幻想纯爱可以免费打出。</summary>
public sealed class FreeStatusPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    public override bool TryModifyEnergyCostInCombat(CardModel card, decimal originalCost, out decimal modifiedCost)
    {
        if (card is StrikeStrike or DefendDefend)
        {
            modifiedCost = 0m;
            return true;
        }
        modifiedCost = originalCost;
        return false;
    }
    public override string? CustomPackedIconPath => ModAssets.Image("powers/free_status.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/free_status.png");

    /// <summary>
    /// 纯爱幻想 / 幻想纯爱 are generated cards, so hovering this shows their faces — the same thing the
    /// base game does for cards that name 灵魂 (CaptureSpirit uses HoverTipFactory.FromCard&lt;Soul&gt;()).
    /// Without this the text named a card the player had no way to look up.
    /// </summary>
    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromCard<StrikeStrike>(),
        HoverTipFactory.FromCard<DefendDefend>()
    ];
    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "剑之所指",
        "你可以免费打出你的纯爱幻想和幻想纯爱。",
        "你可以免费打出你的纯爱幻想和幻想纯爱。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Where the Sword Points",
        "You may play your Pure Love Fantasies and Fantasies of Pure Love for free.",
        "You may play your Pure Love Fantasies and Fantasies of Pure Love for free.");
}
