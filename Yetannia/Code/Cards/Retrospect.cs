using System.Collections.Generic;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 回溯 — 金卡（Rare），X 费技能：
/// 随机打出你弃牌堆的 X（升级 X+1）张牌。
///
/// Written the way the base game's 倾泻 (<c>Cascade</c>) is: the X value comes from
/// <c>ResolveEnergyXValue()</c> with the upgrade adding one, and the playing is delegated to the engine's
/// auto-play path rather than to a hand-rolled loop over <c>CardCmd.AutoPlay</c>.
///
/// <c>CardPileCmd.AutoPlayFromDrawPile</c> is the engine helper Cascade uses, but it hard-codes
/// <c>PileType.Draw</c>, so this card repeats its shape against the discard pile instead. The shape is the
/// part that matters and it is preserved exactly:
/// <list type="bullet">
/// <item>short-circuit when the combat is already over or ending;</item>
/// <item><b>gather first, play second</b> — every chosen card is moved into the play pile before any of
/// them is played. Playing as it picked would let an earlier play move a card the later picks were still
/// choosing from;</item>
/// <item>random picks come from <c>Rng.CombatCardSelection</c>, the same RNG the engine uses for its own
/// random pile picks, and are read from the live pile each pass so nothing is chosen twice;</item>
/// <item>stop if the player died partway through.</item>
/// </list>
///
/// Deliberately no <c>skipXCapture</c>: Cascade does not pass it either, so an X-cost card played this way
/// captures the player's current energy exactly as it would under the base game's card. Matching the
/// original was the explicit request, and diverging here would make 回溯 behave differently from 倾泻 for
/// no reason the player could see.
/// </summary>
public sealed class Retrospect : YetanniaCard
{
    public Retrospect()
        : base(-1, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override bool HasEnergyCostX => true;

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        if (CombatManager.Instance.IsOverOrEnding) return;

        var count = ResolveEnergyXValue();
        if (IsUpgraded) count += 1;
        if (count <= 0) return;

        var discardPile = PileType.Discard.GetPile(Owner);
        var chosen = new List<CardModel>(count);

        for (var i = 0; i < count; i++)
        {
            var card = Owner.RunState.Rng.CombatCardSelection.NextItem(discardPile.Cards);
            if (card == null) break;

            chosen.Add(card);
            await CardPileCmd.Add(card, PileType.Play);
        }

        foreach (var card in chosen)
        {
            if (card.Owner.Creature.IsDead) break;

            await CardCmd.AutoPlay(choiceContext, card, null);
        }
    }

    /// <summary>
    /// No numbers to upgrade — the upgrade is the extra card played, which lives in <c>OnPlay</c> and is
    /// shown on the face through <c>{IfUpgraded:show:X+1|X}</c>.
    /// </summary>
    protected override void OnUpgrade()
    {
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "回溯",
        "随机打出你弃牌堆的{IfUpgraded:show:X+1|X}张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Retrospect",
        "Play {IfUpgraded:show:X+1|X} random cards from your discard pile.");
}
