using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 重排命运 — 白卡（Common），0 费技能：将任意数量的手牌放到抽牌堆顶。
///
/// 选择器用 <see cref="CardSelectorPrefs"/> 的 (prompt, min, max) 重载，min 为 0 且 max 为手牌数，
/// 就是「任意数量」。放回时按逆序添加，因为 <see cref="CardPilePosition.Top"/> 是插入到索引 0，
/// 逆序才能保持玩家选择的顺序。
///
/// 需求：基础带[消耗]，敲后去掉[消耗]。
/// </summary>
public sealed class RearrangedFate : YetanniaCard
{
    public RearrangedFate()
        : base(0, CardType.Skill, CardRarity.Common, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust, CardKeyword.Retain];

    protected override IEnumerable<DynamicVar> CanonicalVars => [];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var hand = PileType.Hand.GetPile(Owner);
        var handSize = hand.Cards.Count;
        if (handSize == 0) return;

        var prefs = new CardSelectorPrefs(SelectionScreenPrompt, 0, handSize);
        var chosen = (await CardSelectCmd.FromHand(
            prefs: prefs,
            context: choiceContext,
            player: Owner,
            filter: null,
            source: this)).ToList();
        if (chosen.Count == 0) return;

        await CardPileCmd.Add(chosen.AsEnumerable().Reverse(), PileType.Draw, CardPilePosition.Top);
    }

    /// <summary>敲后：去掉[消耗]。</summary>
    protected override void OnUpgrade() => RemoveKeyword(CardKeyword.Exhaust);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "预备",
        "将任意数量的手牌放到抽牌堆顶。",
        ("selectionScreenPrompt", "选择要放到抽牌堆顶的牌。"));

    private static readonly List<(string, string)> English = new CardLoc(
        "Prepare",
        "Put any number of cards from your hand on top of your draw pile.",
        ("selectionScreenPrompt", "Choose cards to put on top of your draw pile."));
}
