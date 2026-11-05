using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 运筹帷幄 — 金卡（Rare），0 费技能，[保留][消耗]：
/// 将你的所有手牌置于抽牌堆顶，预见 8（升级 10），然后抽取等量的牌。
///
/// v1.0.5：稀有度 蓝卡 → 金卡，并加上[保留]。两档（原版 / 东尼测试版）都生效。
///
/// "That many" is the number of cards that were put back, so your hand size is preserved while
/// Scry lets you filter the top of the pile.
/// </summary>
public sealed class TestSkill : YetanniaCard
{
    private const int ScryAmount = 8;
    private const int ScryUpgrade = 2; // 8 -> 10

    public TestSkill()
        : base(0, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    // [消耗] 是原本就有的；v1.0.5 又加了[保留]——没打出去时回合结束会留在手里，
    // 打出去时仍然按 Exhaust 进消耗堆，两者并不冲突。
    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust, CardKeyword.Retain];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new ScryVar(ScryAmount)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var hand = PileType.Hand.GetPile(Owner).Cards.ToList();
        var handSize = hand.Count;

        if (handSize > 0)
        {
            // Card positions are indices into the pile and Top == index 0, so adding the hand in
            // reverse inserts the first card last and keeps the hand's original top-to-bottom order.
            await CardPileCmd.Add(hand.AsEnumerable().Reverse(), PileType.Draw, CardPilePosition.Top);
        }

        // Read the dynamic var, not the constant: the upgrade raises Scry 8 -> 10 and only the var
        // knows about it. Using the constant here made the upgrade a no-op.
        await Scry(choiceContext, DynamicVars["Scry"].BaseValue);

        if (handSize > 0)
        {
            await CardPileCmd.Draw(choiceContext, handSize, Owner);
        }
    }

    protected override void OnUpgrade() => DynamicVars["Scry"].UpgradeValueBy(ScryUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "运筹帷幄",
        "将你的所有手牌置于抽牌堆顶，预见{Scry:diff()}，然后抽取等量的牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Strategize",
        "Put your entire hand on top of your draw pile. Scry {Scry:diff()}, then draw that many cards.");
}
