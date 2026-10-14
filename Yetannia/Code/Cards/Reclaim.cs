using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 现场休整 — 蓝卡（Uncommon），1 费技能：
/// 将弃牌堆中至多 2 张牌放到抽牌堆顶。敲后获得[保留]。
///
/// Name is a placeholder (the request did not give one).
///
/// Selection is (min 0, max 2) so the player can pick nothing and confirm; the chosen cards are
/// re-added in reverse so their original top-to-bottom order is preserved (Top == index 0).
/// </summary>
public sealed class Reclaim : YetanniaCard
{
    private const int MaxCards = 2;

    public Reclaim()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var discard = PileType.Discard.GetPile(Owner);
        if (discard.Cards.Count == 0) return;

        var chosen = (await CardSelectCmd.FromCombatPile(
            context: choiceContext,
            pile: discard,
            player: Owner,
            prefs: new CardSelectorPrefs(SelectionScreenPrompt, 0, MaxCards),
            filter: null)).ToList();

        if (chosen.Count > 0)
        {
            await CardPileCmd.Add(chosen.AsEnumerable().Reverse(), PileType.Draw, CardPilePosition.Top);
        }
    }

    protected override void OnUpgrade() => AddKeyword(CardKeyword.Retain);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "现场休整",
        "将弃牌堆中至多 2 张牌放到抽牌堆顶。",
        ("selectionScreenPrompt", "选择要放到抽牌堆顶的牌。"));

    private static readonly List<(string, string)> English = new CardLoc(
        "Field Rest",
        "Put up to 2 cards from your discard pile on top of your draw pile.",
        ("selectionScreenPrompt", "Choose cards to put on top of your draw pile."));
}
