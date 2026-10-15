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
            // Presentation first, and deliberately before the in-flight gate: centring the row has nothing
            // to do with whether a scry happens to be pending right now.
            CentrePartialRow(__instance);

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
    /// Centres the visible cards when a scry reveals fewer than a full row.
    ///
    /// THE MEASURED DEFECT THIS FIXES. <c>NCardGrid.UpdateGridPositions</c> puts the first card at
    /// <c>(scrollContainer.Width - GetContainedCardsSize().Width) / 2 + cardSize.X / 2</c>, and
    /// <c>GetContainedCardsSize()</c> is computed from <c>Columns</c> -- the grid's <em>capacity</em> -- not
    /// from how many cards are actually being shown. The origin therefore never moves, so a partial row is
    /// left-aligned inside a full-width box.
    ///
    /// Measured on a real scry: <c>cardSize=(240, 337.6)</c>, <c>columns=5</c>, <c>scrollW=1570</c>,
    /// <c>cardPadding=40</c> gives a box of 5*240+4*40 = 1360 and an origin of (1570-1360)/2 + 120 = 225 --
    /// and the holder's own Position read exactly 225 for a 5-card scry <em>and</em> for a 1-card scry. The
    /// card pitch was exactly cardSize.X + padding = 280. So a scry revealing one card drew it at x=375 on a
    /// 1920-wide screen: hard against the left, with most of the screen empty. That is the reported
    /// 「预见时界面位置不对」, and it reproduces in single player too, so it was never a multiplayer fault.
    ///
    /// SCOPE: only a grid hosted by the scry screen, and only while the row is partial -- so no other card
    /// grid in the game (deck view, campfire, library, ...) changes its layout, and a full row is left
    /// exactly as vanilla computed it.
    ///
    /// SAFE TO RUN EVERY FRAME: <c>InitGrid</c> recomputes every position from scratch on each call, so the
    /// shift is applied to freshly computed positions rather than accumulating frame over frame.
    /// </summary>
    private static void CentrePartialRow(NCardGrid grid)
    {
        try
        {
            if (!IsScryScreen(grid))
            {
                return;
            }

            var holders = grid.CurrentlyDisplayedCardHolders?.ToList();
            if (holders == null || holders.Count == 0)
            {
                return;
            }

            // AccessTools walks the base types, which plain reflection would not do for inherited
            // non-public members.
            var columns = (int)(AccessTools.Property(typeof(NCardGrid), "Columns")?.GetValue(grid) ?? 0);
            if (columns <= 0 || holders.Count >= columns)
            {
                return; // A full row fills the box the engine already centred.
            }

            var cardSize = AccessTools.Field(typeof(NCardGrid), "_cardSize")?.GetValue(grid) is Vector2 size
                ? size
                : Vector2.Zero;
            var padding = AccessTools.Property(typeof(NCardGrid), "CardPadding")?.GetValue(grid) is float p
                ? p
                : 0f;

            var shift = (columns - holders.Count) * (cardSize.X + padding) * 0.5f;
            if (shift <= 0f)
            {
                return;
            }

            foreach (var holder in holders)
            {
                holder.Position += new Vector2(shift, 0f);
            }
        }
        catch (Exception e)
        {
            // Presentation only: never let this be the thing that breaks a scry screen.
            MainFile.Logger.Error($"Scry grid centring failed: {e}");
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
