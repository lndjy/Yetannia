using Yetannia.YetanniaCode.Cards;
using MegaCrit.Sts2.Core.HoverTips;
using System.Collections.Generic;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Powers;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 幻想纯爱 的能力（标记）：纯爱幻想/幻想纯爱 在结算「被消耗时」效果前会检查这个能力，
/// 有则伤害/格挡翻倍。逻辑在卡牌侧（见 <c>StrikeStrike</c> / <c>DefendDefend</c>），
/// 这里只负责「存在」。
/// </summary>
public sealed class DoubleStatusPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;
    public override string? CustomPackedIconPath => ModAssets.Image("powers/double_status.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/double_status.png");

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
        "幻想纯爱",
        "你的纯爱幻想和幻想纯爱造成的伤害、获得的格挡翻倍。",
        "你的纯爱幻想和幻想纯爱造成的伤害、获得的格挡翻倍。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Fantasy of Pure Love",
        "Your Pure Love Fantasies and Fantasies of Pure Love deal double damage and gain double Block.",
        "Your Pure Love Fantasies and Fantasies of Pure Love deal double damage and gain double Block.");
}
