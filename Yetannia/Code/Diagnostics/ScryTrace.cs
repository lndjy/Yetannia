using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Diagnostics;

/// <summary>
/// The single funnel every 预见 (scry) in this mod goes through.
///
/// A scry is a *player choice*: <see cref="ScryCmd"/> opens a card-selection screen and awaits it.
/// When that await never comes back the played card stays frozen in the middle of the screen, which
/// is the reported symptom — and the log used to say nothing at all about it, because the failure is
/// a task that simply never completes rather than an exception that gets caught.
///
/// THE FREEZE, AND WHY THIS FUNNEL IS WHERE IT IS FIXED. In multiplayer the choice is delivered through
/// the action queue: the card play (or the power/relic hook) is parked in <c>GatheringPlayerChoice</c>
/// until the owning player's client answers it. But when the killing blow lands,
/// <c>ActionQueueSynchronizer</c> calls <c>ActionQueueSet.CombatEnded()</c>, which cancels every combat
/// action that is not currently <c>Executing</c> — and an action waiting on a scry is merely
/// <c>GatheringPlayerChoice</c>, so its action is cancelled as well. Nothing then ever answers the
/// reserved choice id, so every peer's <c>WaitForRemoteChoice</c> stays pending forever,
/// <see cref="ScryCmd.Execute"/> never returns, and the card sits frozen for the rest of the session.
///
/// This was measured, not guessed: in a real three-player run every one of the three hangs sits on the
/// line immediately after <c>"&lt;character&gt; fought &lt;encounter&gt; for the first time and WON"</c> and
/// <c>"Combat ended. Cancelling all non-executing combat actions in all queues"</c>, and the choice id it
/// was waiting on is never answered by anyone (332 <c>Awaiting remote choice</c> against 329
/// <c>Finished waiting</c> — exactly the three hangs).
///
/// So a scry that is still awaiting its choice when the fight stops being playable is abandoned instead
/// of awaited forever. The engine already defines that condition — <c>CombatManager.IsOverOrEnding</c>,
/// which it documents as the correct test for "skip an effect because combat is not in progress" — and a
/// scry started after it is true is a no-op in vanilla anyway (<c>CardSelectCmd.FromSimpleGrid</c> returns
/// empty while <c>IsEnding</c>). Abandoning therefore produces the result the engine intended, and the
/// alternative is a permanently frozen card.
///
/// Every scry logs a matched BEGIN/END pair, and a watchdog logs a loud error if the await is still
/// pending after <see cref="WatchdogSeconds"/> seconds. The BEGIN line carries what is needed to identify
/// the situation: which card, how many cards, the concrete <see cref="PlayerChoiceContext"/> type, the
/// turn, the draw pile size, and how many scries were already in flight.
/// </summary>
internal static class ScryTrace
{
    /// <summary>
    /// How long a scry may sit unanswered before the watchdog calls it a hang.
    ///
    /// RAISED 30 -> 300 (five minutes). The 30s value was chosen from single-player reasoning only ("a
    /// player alt-tabbing away throttles the game to 30 FPS, so 10s was too tight") and it was measured
    /// firing on scries that then completed perfectly normally: the live multiplayer log has four of
    /// them, every one with <c>ctx=HookPlayerChoiceContext</c> or <c>BranchingPlayerChoiceContext</c> —
    /// i.e. the scry was waiting for a *human* to answer a card-selection screen, and in multiplayer
    /// that human can be a teammate on the other side of the internet. Waiting on a real person is not a
    /// hang, and a timeout that fires while somebody is simply thinking is worse than useless: it makes
    /// the log lie, and it hands the in-flight slot back early (see <see cref="InFlightSlot"/>).
    ///
    /// Five minutes is deliberately far past any plausible human decision — the game's own turn timer
    /// and every multiplayer pause mechanic live well inside it — so this is now a genuine-hang
    /// detector rather than a slow-player detector. The cost of the change is only that a real hang is
    /// reported later; the benefit is that the line means what it says.
    /// </summary>
    private const int WatchdogSeconds = 300;

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
    /// Releasing on the watchdog is the right call rather than leaving it stuck: after
    /// <see cref="WatchdogSeconds"/> the screen is already broken for the player, so the honest thing is
    /// to stop letting that one failure corrupt everything after it. If the scry does eventually return,
    /// the counter is not decremented a second time.
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

        var begin = $"[scry] #{id} BEGIN {label} amount={amount} drawPile={drawPile} " +
                    $"ctx={contextName} turn={turn} inFlight={inFlight}";
        MainFile.Logger.Info(begin);

        using var cancellation = new CancellationTokenSource();
        _ = Watchdog(id, label, amount, drawPile, contextName, turn, inFlight, slot, cancellation.Token);

        // Do not even reserve a player choice for a fight that is already over. Vanilla's
        // CardSelectCmd.FromSimpleGrid answers nothing while the combat is ending, so a choice opened here
        // could only be thrown away -- and reserving it costs a choice id that has to stay in step with
        // every other peer.
        if (IsOverOrEnding())
        {
            MainFile.Logger.Info(
                $"[scry] #{id} SKIPPED {label}: the combat is already over or ending (no choice reserved)");
            return default;
        }

        var stopwatch = Stopwatch.StartNew();
        try
        {
            // Race the scry against the fight becoming unplayable. See the class doc: the engine cancels
            // the action that owns this choice the moment the combat ends, and nothing ever answers the
            // choice after that -- awaiting it is precisely the reported freeze.
            //
            // The real result wins whenever it is already available, so a scry that completed at the same
            // instant is not thrown away.
            var scryTask = ScryCmd.Execute(choiceContext, player, amount);
            var combatOver = WatchForCombatEnd(cancellation.Token);

            if (await Task.WhenAny(scryTask, combatOver) != scryTask && !scryTask.IsCompleted)
            {
                stopwatch.Stop();
                var elapsed = stopwatch.ElapsedMilliseconds;
                MainFile.Logger.Info(
                    $"[scry] #{id} ABANDONED {label} after {elapsed}ms: the combat ended while its player " +
                    "choice was outstanding, so the engine cancelled the action that owns that choice and " +
                    "no peer will answer it. Waiting longer is the reported freeze; nothing was discarded.");

                // It can still be answered -- the owning player may have confirmed as the fight ended. Let
                // it finish in the background rather than stranding whatever its discards queue.
                _ = FinishAbandonedAsync(scryTask, id, label);
                return default;
            }

            var result = await scryTask;

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

    /// <summary>
    /// Whether the fight this scry belongs to has ended or is in the process of ending.
    ///
    /// <c>IsOverOrEnding</c> and not <c>IsEnding</c> or <c>!IsInProgress</c>: the engine documents those two
    /// as returning "unexpected results at certain boundary points", and this is the flag the rest of this
    /// mod already gates on (see <c>ProphetQueue</c>, <c>Retrospect</c>).
    /// </summary>
    private static bool IsOverOrEnding()
    {
        try
        {
            return CombatManager.Instance?.IsOverOrEnding ?? false;
        }
        catch (Exception)
        {
            // Never let a diagnostic gate be the thing that breaks a card.
            return false;
        }
    }

    /// <summary>
    /// Completes as soon as the fight stops being playable, which is the moment the engine stops promising
    /// to answer outstanding player choices.
    ///
    /// It only treats "not in progress" as an end once it has actually seen the combat running, so a scry
    /// raised during set-up cannot be mistaken for one raised after the fight.
    /// </summary>
    private static async Task WatchForCombatEnd(CancellationToken token)
    {
        var sawCombat = false;
        while (!token.IsCancellationRequested)
        {
            try
            {
                var combat = CombatManager.Instance;
                if (combat == null) return;

                if (combat.IsOverOrEnding) return;
                if (combat.IsInProgress) sawCombat = true;

                await Task.Delay(100, token);
            }
            catch (OperationCanceledException)
            {
                return; // The scry finished first, which is the normal case.
            }
            catch (Exception)
            {
                return; // Diagnostics must never be the thing that breaks a card.
            }
        }
    }

    /// <summary>
    /// Lets an abandoned scry finish in the background instead of being forgotten.
    ///
    /// It may still be answered (the owning player can confirm as the fight ends), and when it is, its
    /// discards queue 先知 triggers that would otherwise be stranded until the next scry happened to drain
    /// them.
    /// </summary>
    private static async Task FinishAbandonedAsync(Task<ScryResult> scryTask, int id, string label)
    {
        try
        {
            var result = await scryTask;
            await Cards.ProphetQueue.DrainAsync();
            MainFile.Logger.Info(
                $"[scry] #{id} LATE {label}: the abandoned choice was answered after all " +
                $"(discarded={result.Discarded.Count})");
        }
        catch (Exception e)
        {
            MainFile.Logger.Warn($"[scry] #{id} abandoned {label}, then threw: {e.Message}");
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
