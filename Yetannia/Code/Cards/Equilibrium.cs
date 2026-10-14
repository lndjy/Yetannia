using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 能量调和 — 蓝卡（Uncommon），1 费（升级 0）技能：
/// 如果本回合你打出的先知牌数和非先知牌数相等，从抽牌堆检索先知牌和非先知牌各一张加入手牌。
/// 卡面实时显示「当前先知牌 a 张，非先知牌 b 张」。
///
/// Name is a placeholder (the request did not give one).
///
/// "This turn" counts cards played *earlier* this turn (this card's own history entry is appended
/// only after its play finishes), the same convention as 白刃乱舞.
///
/// The two counts are displayed through two <see cref="CalculatedVar"/>s (ProphetPlayed /
/// NonProphetPlayed); they share the same CalculationBaseVar(0) + CalculationExtraVar(1) and only
/// differ in their multiplier, so both compute their own number.
/// </summary>
public sealed class Equilibrium : YetanniaCard
{
    public Equilibrium()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Retain, CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new CalculationBaseVar(0m),
        new CalculationExtraVar(1m),
        new CalculatedVar("ProphetPlayed").WithMultiplier(
            static (CardModel card, Creature _) => CountPlayedThisTurn(card, prophet: true)),
        new CalculatedVar("NonProphetPlayed").WithMultiplier(
            static (CardModel card, Creature _) => CountPlayedThisTurn(card, prophet: false)),
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var prophetPlayed = CountPlayedThisTurn(this, prophet: true);
        var nonProphetPlayed = CountPlayedThisTurn(this, prophet: false);

        if (prophetPlayed != nonProphetPlayed) return;

        var drawPile = PileType.Draw.GetPile(Owner);

        var prophetPrompt = new LocString("cards", Id.Entry + ".prophetSelectionPrompt");
        var prophet = (await CardSelectCmd.FromCombatPile(
            context: choiceContext,
            pile: drawPile,
            player: Owner,
            prefs: new CardSelectorPrefs(prophetPrompt, 1),
            filter: c => c.Keywords.Contains(YetanniaKeywords.Prophet))).FirstOrDefault();

        var nonProphetPrompt = new LocString("cards", Id.Entry + ".nonProphetSelectionPrompt");
        var nonProphet = (await CardSelectCmd.FromCombatPile(
            context: choiceContext,
            pile: drawPile,
            player: Owner,
            prefs: new CardSelectorPrefs(nonProphetPrompt, 1),
            filter: c => !c.Keywords.Contains(YetanniaKeywords.Prophet))).FirstOrDefault();

        if (prophet != null) await CardPileCmd.Add(prophet, PileType.Hand);
        if (nonProphet != null) await CardPileCmd.Add(nonProphet, PileType.Hand);
    }

    private static decimal CountPlayedThisTurn(CardModel card, bool prophet) =>
        CombatManager.Instance.History.CardPlaysFinished.Count(
            e => e.HappenedThisTurn(card.CombatState)
                 && e.CardPlay.Player == card.Owner
                 && e.CardPlay.Card.Keywords.Contains(YetanniaKeywords.Prophet) == prophet);

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(-1); // 1 -> 0

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "能量调和",
        "如果本回合你打出的先知牌数和非先知牌数相等，从抽牌堆检索先知牌和非先知牌各一张加入手牌。\n（当前先知牌{ProphetPlayed}张，非先知牌{NonProphetPlayed}张）",
        ("prophetSelectionPrompt", "选择一张先知牌。"),
        ("nonProphetSelectionPrompt", "选择一张非先知牌。"));

    private static readonly List<(string, string)> English = new CardLoc(
        "Energy Harmony",
        "If you have played the same number of Prophet and non-Prophet cards this turn, retrieve a Prophet card and a non-Prophet card from your draw pile and add them to your hand.\n(Prophet cards played this turn: {ProphetPlayed}; non-Prophet cards played this turn: {NonProphetPlayed})",
        ("prophetSelectionPrompt", "Choose a Prophet card."),
        ("nonProphetSelectionPrompt", "Choose a non-Prophet card."));
}
