using System;
using System.Linq;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;
using Yetannia.YetanniaCode.Diagnostics;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Conditional in-combat card highlighting.
///
/// 奋起 / 从容 glow gold in the hand via the base game's own model hook
/// <c>CardModel.ShouldGlowGoldInternal</c> (see those two cards) — no patch is needed there, because
/// <c>NHandCardHolder.UpdateCard</c> already consults it and re-evaluates after every combat state change.
///
/// The 先知 (Prophet) glow during 预见 (scry) cannot use that hook: the scried cards are draw-pile
/// cards shown in a grid (<c>NSimpleCardSelectScreen</c> → <c>NCardGrid</c>), never hand cards.
/// BaseLib's <c>ScryCmd</c> opens that grid with no per-card condition, so this patch runs right after
/// the grid populates and gold-glows every Prophet-keyword card while a scry is in flight.
///
/// TWO gates, and both are needed.
///
/// 1. <c>ScryTrace.InFlight &gt; 0</c>. Every scry in this mod funnels through that counter, so it is
///    &gt; 0 for the whole time a scry is up. On its own it is NOT sufficient, because the counter used
///    to be poisoned by a scry that never returned — see the release in <c>ScryTrace.Watchdog</c>.
///    While it was poisoned this patch gold-glowed Prophet cards in the deck view, the combat-pile view
///    and at the campfire, which is exactly the bug that was reported.
///
/// 2. <c>IsScryScreen</c>. Six screens derive from <c>NCardGridSelectionScreen</c> and every one of them
///    hosts an <c>NCardGrid</c>: the scry grid (<c>NSimpleCardSelectScreen</c>) plus deck view / removal
///    (<c>NDeckCardSelectScreen</c>), combat-pile view (<c>NCombatPileCardSelectScreen</c>), campfire
///    upgrade (<c>NDeckUpgradeSelectScreen</c>), transform and enchant. Asking which screen owns the grid
///    is therefore the structural answer to "is this grid a scry", and it stays correct regardless of
///    what the counter happens to read. <c>NCardGrid.InitGrid</c> fires for all six, so without this the
///    patch cannot tell them apart at all.
/// </summary>
[HarmonyPatch(typeof(NCardGrid), "InitGrid", new Type[0])]
internal static class ConditionalHighlightPatch
{
    [HarmonyPostfix]
    private static void Postfix(NCardGrid __instance)
    {
        try
        {
            if (ScryTrace.InFlight <= 0)
            {
                return;
            }

            if (!IsScryScreen(__instance))
            {
                return;
            }

            // A scry is waiting on a selection screen right now, so this grid *is* that screen.
            // Logging it separates the two ways a scry can hang: "the screen never appeared" leaves a
            // BEGIN with no GRID line, while "the screen appeared but the answer was never delivered"
            // leaves a GRID line and then nothing. An empty grid is called out separately because a
            // screen with no cards gives the player nothing to confirm.
            var displayed = __instance.CurrentlyDisplayedCardHolders?.Count() ?? -1;
            MainFile.Logger.Info(
                $"[scry] GRID shown while inFlight={ScryTrace.InFlight} cards={displayed}" +
                (displayed == 0 ? " (EMPTY GRID — nothing to confirm)" : string.Empty));

            foreach (var holder in __instance.CurrentlyDisplayedCardHolders)
            {
                var card = holder.CardModel;
                if (card == null || !card.Keywords.Contains(YetanniaKeywords.Prophet))
                {
                    continue;
                }

                var highlight = holder.CardNode?.CardHighlight;
                if (highlight == null)
                {
                    continue;
                }

                highlight.Modulate = NCardHighlight.gold;
                highlight.AnimShow();
            }
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"Prophet scry highlight patch failed: {e}");
        }
    }

    /// <summary>
    /// Whether this grid is hosted by the scry selection screen rather than one of its five siblings.
    ///
    /// Walks up to the nearest enclosing selection screen and lets that one decide. The derived type is
    /// tested FIRST on purpose: <see cref="NSimpleCardSelectScreen"/> derives from
    /// <see cref="NCardGridSelectionScreen"/>, so testing the base first would match every screen and
    /// silently turn this gate into a no-op.
    /// </summary>
    private static bool IsScryScreen(Node grid)
    {
        for (var node = grid; node != null; node = node.GetParent())
        {
            if (node is NSimpleCardSelectScreen)
            {
                return true;
            }

            if (node is NCardGridSelectionScreen)
            {
                return false;
            }
        }

        // No selection screen in the ancestry: not a scry, so do not highlight.
        return false;
    }
}
