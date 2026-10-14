using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 全力进攻 — 金卡（Rare），1 费技能：
/// 你手牌中所有牌的耗能降低 1，直到它被打出。敲后：这张牌自己的费用 1 → 0。
///
/// "Until it is played" is exactly what <c>CardEnergyCost.AddThisTurnOrUntilPlayed</c> expresses
/// (its expiry is EndOfTurn | WhenPlayed), so the discount drops off as soon as the card is used
/// rather than lingering for the whole turn.
/// </summary>
public sealed class AllOutAttack : YetanniaCard
{
    private const int CostReduction = 1;
    private const int SelfCostUpgrade = -1; // this card's own cost 1 -> 0

    public AllOutAttack()
        : base(1, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        // Snapshot first: the card being played is in the play pile, not the hand, so it is not
        // discounted — only what is left in hand.
        foreach (var card in PileType.Hand.GetPile(Owner).Cards.ToList())
        {
            card.EnergyCost.AddThisTurnOrUntilPlayed(-CostReduction);
        }

        return Task.CompletedTask;
    }

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(SelfCostUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "全力进攻",
        "你手牌中所有牌的耗能降低1点，直到它被打出。");

    private static readonly List<(string, string)> English = new CardLoc(
        "All-Out Attack",
        "All cards in your hand cost 1 less until played.");
}
