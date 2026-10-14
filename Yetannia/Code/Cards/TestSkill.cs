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
/// 运筹帷幄 — 蓝卡（Uncommon），0 费技能，消耗：
/// 将你的所有手牌置于抽牌堆顶，预见 8（升级 10），然后抽取等量的牌。
///
/// "That many" is the number of cards that were put back, so your hand size is preserved while
/// Scry lets you filter the top of the pile.
/// </summary>
public sealed class TestSkill : YetanniaCard
{
    private const int ScryAmount = 8;
    private const int ScryUpgrade = 2; // 8 -> 10

    public TestSkill()
        : base(0, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

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
