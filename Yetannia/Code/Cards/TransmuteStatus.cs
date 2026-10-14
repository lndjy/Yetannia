using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Factories;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.CommonUi;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>少女幻想之忆 — 蓝卡（Uncommon），1 费技能：[消耗]（敲后去掉消耗）。将你抽牌堆、手牌、弃牌堆的所有状态牌随机变为纯爱幻想或幻想纯爱。</summary>
public sealed class TransmuteStatus : YetanniaCard
{
    public TransmuteStatus()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var statuses = new List<CardModel>();
        foreach (var pile in new[] { PileType.Draw, PileType.Hand, PileType.Discard }.Select(p => p.GetPile(Owner)))
        {
            statuses.AddRange(pile.Cards.Where(c => c.Rarity == CardRarity.Status));
        }

        foreach (var card in statuses)
        {
            var canonical = Owner.RunState.Rng.CombatCardGeneration.NextItem(
                new CardModel[] { ModelDb.Card<StrikeStrike>(), ModelDb.Card<DefendDefend>() });
            var replacement = CardFactory.GetForCombat(
                Owner, [canonical], 1, Owner.RunState.Rng.CombatCardGeneration).First();
            await CardCmd.Transform(card, replacement, CardPreviewStyle.None);
        }
    }

    protected override void OnUpgrade() => RemoveKeyword(CardKeyword.Exhaust);

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
        "少女幻想之忆", "将你抽牌堆、手牌、弃牌堆的所有状态牌随机变为纯爱幻想或幻想纯爱。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Fantasy Memory of a Maiden", "Transform all Status cards in your draw pile, hand and discard pile into a random Pure Love Fantasy or Fantasy of Pure Love.");
}
