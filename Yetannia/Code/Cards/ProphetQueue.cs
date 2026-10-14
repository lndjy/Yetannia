using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// Holds 先知 triggers that fired while a 预见 (scry) was still discarding, and releases them once the
/// scry has committed all of its discards.
///
/// Why defer at all: <c>ScryCmd</c> discards its cards one at a time, and each discard immediately lands
/// in <see cref="YetanniaCard.AfterCardChangedPiles"/>. Resolving there means a Prophet effect that
/// <em>draws</em> runs while the discard pile is still being filled — and drawing from an empty draw pile
/// shuffles that very discard pile back into the draw pile. The player's just-discarded cards come straight
/// back, so a card like 引蛇出洞 looks like it did nothing while actually undoing the scry.
///
/// Deferring separates the two phases: every discard is committed first, then the triggers fire against a
/// settled board. The shuffle can still happen — that part is standard draw-from-empty behaviour and is not
/// ours to change — but it no longer interleaves with the discards it is reacting to.
///
/// Order within a batch is the order the discards happened, and the drain loops so a deferred effect that
/// itself discards a Prophet card is picked up too.
///
/// <para>
/// EXPECTED BEHAVIOUR — a batch can end early, and that is the engine, not this queue. If a damage-dealing
/// Prophet card in the batch kills the last enemy, <c>CombatManager.IsOverOrEnding</c> flips to true during
/// that card's own resolution, and from then on every effect command early-returns: <c>PowerCmd.Apply</c>,
/// <c>CardPileCmd.DrawInternal</c>, <c>DamageCmd</c> and friends are all gated on it. The remaining cards in
/// the batch therefore log <c>begin</c>/<c>done</c> with no exception, no effect and no tally movement —
/// "ran and did nothing", not "failed". Measured over two runs: 76 such resolutions, all with the gate true,
/// and 341 resolutions with the gate false, all of which advanced the tally. There were no counterexamples.
/// The <c>overOrEnding=</c> field on every <c>[prophet]</c> line is what makes that readable at a glance.
/// </para>
/// </summary>
internal static class ProphetQueue
{
    private static readonly List<YetanniaCard> _pending = [];

    /// <summary>How many triggers are waiting (diagnostics only).</summary>
    internal static int PendingCount => _pending.Count;

    internal static void Enqueue(YetanniaCard card) => _pending.Add(card);

    private static bool OverOrEnding()
    {
        try
        {
            return MegaCrit.Sts2.Core.Combat.CombatManager.Instance?.IsOverOrEnding ?? false;
        }
        catch (Exception)
        {
            return false;
        }
    }

    /// <summary>
    /// Throws away everything queued and returns how many. Used when a scry failed: its discards may be
    /// half-applied, so firing the triggers against that board is worse than not firing them — and leaving
    /// them queued would be worst of all, since they would then fire at the end of an unrelated later scry.
    /// </summary>
    internal static int DropPending()
    {
        var dropped = _pending.Count;
        _pending.Clear();
        return dropped;
    }

    /// <summary>
    /// Fires everything queued during a scry, now that its discards are done. Called from the scry funnel
    /// (<see cref="Diagnostics.ScryTrace"/>) — the single place every scry in this mod passes through.
    /// </summary>
    internal static async Task DrainAsync()
    {
        if (_pending.Count == 0) return;

        // Bounded loop rather than a single pass: a deferred effect can itself discard a Prophet card,
        // which enqueues again. The bound is a guard against a genuinely cyclic effect, not an expected case.
        for (var pass = 0; pass < 8 && _pending.Count > 0; pass++)
        {
            var batch = _pending.ToList();
            _pending.Clear();

            MainFile.Logger.Info(
                $"[prophet] scry finished its discards; firing {batch.Count} deferred trigger(s) " +
                $"[pass {pass + 1}] overOrEnding={OverOrEnding()}: {string.Join(", ", batch.Select(c => c.Id.Entry))}");

            foreach (var card in batch)
            {
                try
                {
                    await card.ResolveProphet(new ThrowingPlayerChoiceContext());

                    // The same Power-card Limbo move the immediate path performs: a Power would otherwise
                    // stay in the discard pile and could be played a second time.
                    if (card.Type == CardType.Power)
                    {
                        await CardPileCmd.RemoveFromCombat(card);
                    }
                }
                catch (Exception e)
                {
                    // Isolated per card: one deferred trigger failing must not take the rest of the batch
                    // with it, and it must never be silent.
                    MainFile.Logger.Error($"[prophet] deferred trigger for {card.Id.Entry} threw: {e}");
                }
            }
        }
    }
}
