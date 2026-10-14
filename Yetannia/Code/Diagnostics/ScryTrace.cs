using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Diagnostics;

/// <summary>
/// The single funnel every 预见 (scry) in this mod goes through, purely so a hang leaves evidence.
///
/// A scry is a *player choice*: <see cref="ScryCmd"/> opens a card-selection screen and awaits it.
/// When that await never comes back the played card stays frozen in the middle of the screen, which
/// is the reported symptom — and the log used to say nothing at all about it, because the failure is
/// a task that simply never completes rather than an exception that gets caught.
///
/// So every scry now logs a matched BEGIN/END pair, and a watchdog logs a loud error if the await is
/// still pending after <see cref="WatchdogSeconds"/> seconds — 30s rather than 10 because a real player
/// alt-tabbing away (the game throttles to 30 FPS in the background) made 10s fire on a scry that
/// then completed normally. The BEGIN line carries everything
/// needed to identify the situation: which card, how many cards, the concrete
/// <see cref="PlayerChoiceContext"/> type, the turn, the draw pile size, and how many scries were
/// already in flight. That last number matters: two overlapping scries would each wait for the other
/// one's selection screen to close.
///
/// Behaviour is unchanged — this only observes. Nothing is skipped, clamped or swallowed.
/// </summary>
internal static class ScryTrace
{
    private const int WatchdogSeconds = 30;

    private static int _sequence;
    private static int _inFlight;

    /// <summary>
    /// One scry's claim on the in-flight counter, released exactly once by whichever of the two
    /// finishers gets there first — the scry returning, or the watchdog giving up on it.
    ///
    /// This exists because a scry that never returns used to pin <see cref="InFlight"/> above zero for
    /// the rest of the session. That is not just a cosmetic counter: two separate behaviours read it,
    /// and both broke. <c>ConditionalHighlightPatch</c> gold-glowed 先知 cards in every later card grid
    /// (deck view, combat piles, the campfire), and <c>YetanniaCard.AfterCardChangedPiles</c> deferred
    /// every later 先知 trigger into the queue instead of resolving it immediately, so 先知 effects
    /// stopped firing on discard until the next scry happened to drain them.
    ///
    /// Releasing on the watchdog is the right call rather than leaving it stuck: after 30 seconds the
    /// screen is already broken for the player, so the honest thing is to stop letting that one failure
    /// corrupt everything after it. If the scry does eventually return, the counter is not decremented
    /// a second time.
    /// </summary>
    private sealed class InFlightSlot
    {
        private int _released;

        /// <summary>True for the first caller only.</summary>
        public bool Release() => Interlocked.Exchange(ref _released, 1) == 0;
    }

    /// <summary>
    /// How many scries are in flight right now. The scripted checks use this to wait for an unrelated
    /// scry (the combat-start relic one, say) to settle before they start, so their result cannot be
    /// contaminated by an overlap they caused themselves.
    /// </summary>
    internal static int InFlight => Volatile.Read(ref _inFlight);

    /// <summary>
    /// Runs one scry under observation. The return value and the exceptions are passed straight
    /// through, so callers cannot tell the difference.
    /// </summary>
    public static async Task<ScryResult> Run(
        string label, PlayerChoiceContext choiceContext, Player player, int amount)
    {
        var id = Interlocked.Increment(ref _sequence);
        var inFlight = Interlocked.Increment(ref _inFlight);
        var slot = new InFlightSlot();

        var contextName = choiceContext?.GetType().Name ?? "<null>";
        var turn = player?.PlayerCombatState?.TurnNumber.ToString() ?? "<none>";
        var drawPile = CountDrawPile(player);

        MainFile.Logger.Info(
            $"[scry] #{id} BEGIN {label} amount={amount} drawPile={drawPile} " +
            $"ctx={contextName} turn={turn} inFlight={inFlight}");

        using var cancellation = new CancellationTokenSource();
        _ = Watchdog(id, label, amount, drawPile, contextName, turn, inFlight, slot, cancellation.Token);

        var stopwatch = Stopwatch.StartNew();
        try
        {
            var result = await ScryCmd.Execute(choiceContext, player, amount);

            // The discards are committed; release any 先知 triggers they queued (see ProphetQueue).
            // This funnel is the reason the deferral can be exact rather than time-based: every scry in
            // this mod passes through here, so there is a single, unambiguous end-of-discards point.
            await Cards.ProphetQueue.DrainAsync();

            stopwatch.Stop();

            // ScryResult is a value type, so Discarded is always readable here.
            MainFile.Logger.Info(
                $"[scry] #{id} END {label} elapsed={stopwatch.ElapsedMilliseconds}ms " +
                $"discarded={result.Discarded.Count}");

            return result;
        }
        catch (Exception e)
        {
            stopwatch.Stop();
            MainFile.Logger.Error(
                $"[scry] #{id} THREW {label} after {stopwatch.ElapsedMilliseconds}ms: {e}");

            // The scry failed, so its discards may be half-applied. Drop anything they queued rather than
            // firing it against a board we cannot vouch for — and rather than leaking it into the next scry.
            var dropped = Cards.ProphetQueue.DropPending();
            if (dropped > 0)
            {
                MainFile.Logger.Error(
                    $"[prophet] dropped {dropped} queued trigger(s) because scry #{id} threw");
            }

            throw;
        }
        finally
        {
            cancellation.Cancel();

            // The normal path. The watchdog may have released this already; only the first release
            // decrements, so a scry that hangs and then returns cannot take the counter negative.
            if (slot.Release())
            {
                Interlocked.Decrement(ref _inFlight);
            }
        }
    }

    /// <summary>
    /// Fires only when the scry never returned. This is the line to look for: it proves the hang is
    /// inside the scry itself and not somewhere after it in the card's <c>OnPlay</c>.
    /// </summary>
    private static async Task Watchdog(
        int id, string label, int amount, int drawPile, string contextName, string turn, int inFlight,
        InFlightSlot slot, CancellationToken token)
    {
        try
        {
            await Task.Delay(TimeSpan.FromSeconds(WatchdogSeconds), token);
        }
        catch (OperationCanceledException)
        {
            return; // The scry finished in time, which is the normal case.
        }

        MainFile.Logger.Error(
            $"[scry] #{id} STILL PENDING after {WatchdogSeconds}s: {label} amount={amount} " +
            $"drawPile={drawPile} ctx={contextName} turn={turn} inFlight={inFlight} " +
            "— the scry never returned, so the selection screen was never answered (or never shown)");

        // Give up the claim so one hung scry cannot poison the rest of the session. See InFlightSlot
        // for what reading a stuck counter broke.
        if (slot.Release())
        {
            MainFile.Logger.Error(
                $"[scry] #{id} released its in-flight slot (inFlight is now {InFlight}). A scry that never " +
                "returns used to pin this counter for the rest of the session, which made every later card " +
                "grid highlight 先知 cards and made every later 先知 trigger wait for the next scry.");
        }
    }

    private static int CountDrawPile(Player player)
    {
        try
        {
            return player == null ? -1 : PileType.Draw.GetPile(player).Cards.Count;
        }
        catch (Exception)
        {
            // Diagnostics must never be the thing that breaks a card.
            return -1;
        }
    }
}
