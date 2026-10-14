using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 重整旗鼓 — 金卡（Rare），1 费技能：
/// 消耗你抽牌堆、弃牌堆和手牌里的所有状态牌。敲后：费用 1 → 0。
///
/// Only <see cref="CardType.Status"/> cards are ever touched — the card widens *which piles* are
/// searched, not *what* is taken from them.
///
/// An earlier version searched only the draw pile and added the other two piles on upgrade; the
/// request moved the full scope onto the base card and made the upgrade a cost reduction instead.
///
/// Statuses are collected into a list before any exhaust so the piles are not mutated mid-enumeration.
/// </summary>
public sealed class Regroup : YetanniaCard
{
    private static readonly PileType[] SearchedPiles = [PileType.Draw, PileType.Discard, PileType.Hand];

    private const int CostReductionOnUpgrade = -1; // 1 -> 0

    public Regroup()
        : base(1, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var statuses = SearchedPiles
            .SelectMany(pileType => pileType.GetPile(Owner).Cards)
            .Where(card => card.Type == CardType.Status)
            .ToList();

        foreach (var status in statuses)
        {
            await CardCmd.Exhaust(choiceContext, status);
        }
    }

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(CostReductionOnUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "重整旗鼓",
        "消耗你抽牌堆、弃牌堆和手牌中的所有状态牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Regroup",
        "Exhaust all Status cards in your draw pile, discard pile, and hand.");
}
