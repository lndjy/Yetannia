using MegaCrit.Sts2.Core.HoverTips;
using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>剑之所指 — 金卡（Rare），1 费能力（敲后[固有]）：你可以免费打出你的纯爱幻想和幻想纯爱。</summary>
public sealed class FreeStatus : YetanniaCard
{
    public FreeStatus()
        : base(1, CardType.Power, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<FreeStatusPower>(choiceContext, Owner.Creature, 1, Owner.Creature, this);
    }

    protected override void OnUpgrade() => AddKeyword(CardKeyword.Innate);

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

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "剑之所指", "你可以免费打出你的纯爱幻想和幻想纯爱。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Where the Sword Points", "You may play your Pure Love Fantasies and Fantasies of Pure Love for free.");
}
