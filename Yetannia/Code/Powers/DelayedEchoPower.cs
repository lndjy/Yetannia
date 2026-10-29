using System.Collections.Generic;
using System.Linq;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Cards;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 未命名·回费 的延时复制 — at the end of the current turn, put a copy of the card that created
/// this power into its owner's discard pile, then remove this power.
///
/// The card itself exhausts on play, so it cannot carry this hook: an exhausted card leaves the
/// combat piles and stops being a hook listener. A power is the only thing that survives to the end
/// of the turn.
///
/// Deliberately does NOT park a pre-built clone. Two separate defects came out of doing that:
///
/// 1. A clone from <c>CardModel.CreateClone()</c> carries the source card's owner
///    (<c>CombatState.CloneCard</c> → <c>ClonePreservingMutability()</c>), and <c>CombatState.AddCard(card, owner)</c>
///    opens with <c>card.Owner = owner</c>, whose setter throws “Card X already has an owner.” for a
///    non-null owner. A parked clone therefore can never be registered later — attempting it turns a
///    conditional crash into an unconditional one.
/// 2. A parked clone can outlive the combat it was created in. This power’s queue has been observed to
///    survive a combat boundary (the turn ended before the queue could drain), after which a clone from
///    the *finished* combat was dropped into the live one. Being foreign to the current combat, it was
///    not in that combat’s card registry, and <c>CardPileCmd.Add</c> only enforces membership once the
///    card already sits in a combat pile — so the first add slipped through and the bomb only went off
///    later, when the discard pile was shuffled into the draw pile
///    (“YETANNIA-DELAYED_ECHO must be added to a CombatState before adding it to this pile”, thrown out
///    of ShuffleIfNecessary, killing the turn loop).
///
/// So the queue stores only what is needed to rebuild the copy — the upgrade state and the combat it was
/// played in — and the card is created fresh at the end of the turn through the same path 殚精竭虑 uses
/// for 晕眩 (<c>CreateCard</c>, which leaves Owner unset and registers the card with the combat state).
/// Anything queued in an earlier combat is dropped rather than resurrected.
/// </summary>
public sealed class DelayedEchoPower : CustomPowerModel
{
    /// <summary>
    /// One queued copy: whether it should be upgraded, and the combat it was played in.
    ///
    /// A list rather than a single slot: playing the card twice in one turn used to overwrite the first
    /// copy, so only one of the two landed. The power stays <see cref="PowerStackType.Single"/> because
    /// it is bookkeeping, not a stacking buff — a second play finds the same instance and appends to it.
    /// </summary>
    private List<(bool Upgraded, ICombatState? State)> _pending = [];

    /// <summary>
    /// Gives every mutable instance its own queue.
    ///
    /// <c>AbstractModel.MutableClone()</c> is <c>MemberwiseClone()</c> + <c>DeepCloneFields()</c>, and
    /// <c>PowerModel.DeepCloneFields()</c> copies only <c>_dynamicVars</c> and <c>_internalData</c>.
    /// Without this override the field is therefore shared between the canonical model and every live
    /// instance — the queue would be process-global state. A single-player game has one live instance so
    /// it looks harmless (and the stale-combat check above keeps it correct), but with two players
    /// holding this power, one player's turn-end drain would empty the other's queue and one player's
    /// copies would land in the other player's discard pile.
    /// </summary>
    protected override void DeepCloneFields()
    {
        base.DeepCloneFields();
        _pending = [.. _pending];
    }

    /// <summary>Queues one copy to be dropped when this turn ends.</summary>
    public void AddCopy(bool upgraded, ICombatState? state) => _pending.Add((upgraded, state));

    /// <summary>How many copies are queued (diagnostics only).</summary>
    public int PendingCount => _pending.Count;

    public override PowerType Type => PowerType.Buff;

    /// <summary>Not a stacking buff — a second copy just appends to this same instance's pending list.</summary>
    public override PowerStackType StackType => PowerStackType.Single;

    /// <summary>Bookkeeping only — nothing for the player to act on, so keep it out of the power bar.</summary>
    protected override bool IsVisibleInternal => false;

    public override async Task BeforeSideTurnEnd(
        PlayerChoiceContext choiceContext, CombatSide side, IEnumerable<Creature> participants)
    {
        if (side != CombatSide.Player) return;
        if (!participants.Contains(Owner)) return;

        var player = Owner.Player;
        var combatState = Owner.CombatState;
        var pending = _pending.ToList();
        _pending.Clear();
        await PowerCmd.Remove(this);

        if (player == null || combatState == null) return;

        foreach (var (upgraded, state) in pending)
        {
            // Queued in an earlier combat: that turn ended without draining the queue, and a copy
            // belonging to a finished combat must not be dropped into this one. Drop it instead of
            // trying to resurrect it.
            if (!ReferenceEquals(state, combatState))
            {
                MainFile.Logger.Info(
                    "[echo] dropping a copy queued in a previous combat instead of carrying it over");
                continue;
            }

            // CreateCard hands back a mutable card that is already registered with the combat state and
            // whose Owner is still unset — the only shape CardPileCmd.Add accepts. Cloning would fail
            // both of those.
            var copy = combatState.CreateCard<DelayedEcho>(player);
            if (upgraded && copy.MaxUpgradeLevel > 0)
            {
                // Both calls, exactly as CardCmd.Upgrade does: UpgradeInternal applies the new numbers,
                // FinalizeUpgradeInternal clears the state used for displaying an upgrade preview.
                copy.UpgradeInternal();
                copy.FinalizeUpgradeInternal();
            }

            await CardPileCmd.AddGeneratedCardToCombat(copy, PileType.Discard, player);
        }
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/delayed_echo.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/delayed_echo.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "回响",
        "回合结束时，将一张「水色睿智」的复制加入你的弃牌堆。",
        "回合结束时，将一张「水色睿智」的复制加入你的弃牌堆。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Echo",
        "At the end of your turn, add a copy of Azure Wisdom to your discard pile.",
        "At the end of your turn, add a copy of Azure Wisdom to your discard pile.");
}
