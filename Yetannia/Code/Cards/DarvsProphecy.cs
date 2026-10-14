using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 达弗的预言 — 达弗（Darv）的先古卡，通过「陈旧的书卷 / Dusty Tome」获得
/// （见 <see cref="ITomeCard"/>：BaseLib 的补丁会把实现了该接口的卡加入达弗的书卷奖励池）。
///
/// 技能牌，3 费，[固有]，预见你的整个抽牌堆，[消耗]。
/// </summary>
public sealed class DarvsProphecy : YetanniaCard, ITomeCard
{
    private const int CostReductionOnUpgrade = -1; // 3 -> 2

    public DarvsProphecy()
        : base(3, CardType.Skill, CardRarity.Ancient, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords =>
        [CardKeyword.Innate, CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars => [];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
        [HoverTipFactory.Static(BaseLib.Utils.BaseLibTip.Scry)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        // 预见你的抽牌堆：把整副抽牌堆都摊开给玩家挑选弃置。
        var drawPile = PileType.Draw.GetPile(Owner);
        var count = drawPile.Cards.Count;
        if (count <= 0) return;

        await Scry(choiceContext, count);
    }

    /// <summary>敲后 2 费（原本敲了没有任何变化）。</summary>
    protected override void OnUpgrade() => EnergyCost.UpgradeBy(CostReductionOnUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "引领之光",
        "预见你的抽牌堆。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Guiding Light",
        "Scry your draw pile.");
}
