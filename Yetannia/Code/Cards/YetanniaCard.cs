using System.Threading;
using BaseLib.Abstracts;
using BaseLib.Commands;
using BaseLib.Utils;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Powers;
using Yetannia.YetanniaCode.Character;
using Yetannia.YetanniaCode.Diagnostics;
using Yetannia.YetanniaCode.Keywords;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// Base class for Yetannia's cards. The <see cref="PoolAttribute"/> puts every subclass into
/// <see cref="YetanniaCardPool"/>.
///
/// This class implements the shared 先知 (Prophet) trigger, so an individual card only has to
/// override <see cref="OnProphet"/> to say what its Prophet effect does, plus a couple of helpers
/// the cards share.
/// </summary>
[Pool(typeof(YetanniaCardPool))]
public abstract class YetanniaCard : CustomCardModel
{
    protected YetanniaCard(int cost, CardType type, CardRarity rarity, TargetType target)
        : base(cost, type, rarity, target)
    {
    }

    /// <summary>
    /// Card face art, from the mod's own .pck.
    ///
    /// The file is <c>images/card_portraits/&lt;entry&gt;.png</c>, where <c>&lt;entry&gt;</c> is the
    /// model id with the mod prefix removed and lower-cased — <c>YETANNIA-EMBER_BOON</c> becomes
    /// <c>ember_boon.png</c>, the same stem the power and relic art already uses. The id is used rather
    /// than the class name because <c>Id</c> is assigned in the constructor (<c>AbstractModel</c>), so
    /// the stem is fixed by the game's own slugifier instead of being re-implemented here.
    ///
    /// Art is delivered a few cards at a time, so a card whose file is not in the pack yet falls back
    /// to the rarity placeholder. The check is not optional: BaseLib's portrait patches hand the path
    /// straight to <c>ResourceLoader.Load&lt;Texture2D&gt;</c> and then dereference the result
    /// (<c>CustomCardPortraitPath</c> reads <c>.ResourcePath</c> with no null check), so a path that
    /// does not load throws inside the card render rather than drawing nothing.
    ///
    /// Setting <c>CustomPortraitPath</c> (rather than overriding <c>PortraitPath</c>) also feeds
    /// BaseLib's <c>PortraitPngPath</c> patch, so the card library and the in-combat card both show
    /// the same art.
    /// </summary>
    public override string CustomPortraitPath => _portraitPath ??= ResolvePortraitPath();

    /// <summary>
    /// The two shared faces used by every card that has no art of its own yet. Kept as the previous
    /// round's rarity split (金卡 vs everything else) so a card without art looks exactly as it did
    /// before this file learned about per-card art.
    /// </summary>
    private string PortraitPlaceholder =>
        Rarity == CardRarity.Rare
            ? ModAssets.Image("card_portraits/test2.png")
            : ModAssets.Image("card_portraits/test.png");

    /// <summary>
    /// Resolves this card's own art once and remembers it for the life of the instance. Cached per
    /// instance deliberately: model instances are created and rendered on the main thread, so a static
    /// cache would add shared mutable state for no measurable gain.
    /// </summary>
    private string ResolvePortraitPath()
    {
        var entry = Id.Entry;
        var stem = entry.ToLowerInvariant();
        var prefix = MainFile.ModId.ToLowerInvariant() + "-";
        if (stem.StartsWith(prefix, StringComparison.Ordinal))
        {
            stem = stem.Substring(prefix.Length);
        }

        var path = ModAssets.Image($"card_portraits/{stem}.png");
        return Godot.ResourceLoader.Exists(path) ? path : PortraitPlaceholder;
    }

    private string _portraitPath;

    /// <summary>
    /// The card's 先知 effect: what happens when this card is moved from the draw pile into the
    /// discard pile. Override it on every card that carries the Prophet keyword.
    /// </summary>
    protected virtual Task OnProphet(PlayerChoiceContext choiceContext) => Task.CompletedTask;

    /// <summary>
    /// Shared Prophet trigger.
    ///
    /// Every <see cref="CardModel"/> sitting in a combat pile is itself a hook listener, so a card
    /// gets told about its own pile changes. "Draw pile -&gt; discard pile" is exactly
    /// <paramref name="oldPileType"/> being <see cref="PileType.Draw"/> while
    /// <see cref="CardModel.Pile"/> is now <see cref="PileType.Discard"/>. Note that being discarded
    /// straight out of hand does not fire this, which is what the keyword asks for.
    ///
    /// A pile change is not a player action, so there is no real choice context to pass down; a
    /// <see cref="ThrowingPlayerChoiceContext"/> is used instead, which is the documented pattern for
    /// hook-driven effects that must not prompt the player. A Prophet effect therefore must not ask
    /// for a player choice (Scry, for instance, would be unsafe here).
    /// </summary>
    public sealed override async Task AfterCardChangedPiles(CardModel card, PileType oldPileType, AbstractModel clonedBy)
    {
        if (!ReferenceEquals(card, this)) return;
        if (oldPileType != PileType.Draw) return;
        if (Pile?.Type != PileType.Discard) return;
        if (!Keywords.Contains(YetanniaKeywords.Prophet)) return;

        // 背水一战's 东尼测试版 scries without triggering the discarded cards: its scry silences this
        // player's triggers for the duration, and the discard hook is what would otherwise fire them
        // regardless of what the card itself does. Checked before the queue so nothing is even deferred.
        if (ProphetQueue.IsSuppressedFor(Owner)) return;

        // Stamped BEFORE resolving, so anyone who snapshotted the token before discarding this card can
        // tell that the automatic trigger did fire. 背水一战 uses this to top up only the discards this
        // hook missed instead of re-triggering every one of them (which double-fired the effect).
        LastProphetToken = Interlocked.Increment(ref _prophetToken);

        // While a scry is still discarding, queue instead of resolving. ScryCmd discards one card at a
        // time and each one lands here, so resolving immediately lets a Prophet that DRAWS shuffle the
        // pile the scry is still filling — the player's own discards come back and the effect looks inert.
        // ProphetQueue releases these together once the scry has committed all of its discards.
        if (Diagnostics.ScryTrace.InFlight > 0)
        {
            ProphetQueue.Enqueue(this);
            return;
        }

        await ResolveProphet(new ThrowingPlayerChoiceContext());

        // Playing a Power card sends it to Limbo (PileType.None) rather than the discard pile, so it
        // can never be drawn and played a second time — see CardModel.OnPlayWrapper's PileType.None
        // branch, which calls RemoveFromCombat. A Prophet trigger has to do the same, otherwise the
        // power got its effect *and* stayed in the discard pile ready to be played again for a
        // second helping.
        if (Type == CardType.Power)
        {
            await CardPileCmd.RemoveFromCombat(this);
        }
    }

    /// <summary>
    /// Monotonic counter bumped once per automatic Prophet trigger, across all cards.
    ///
    /// The automatic Draw→Discard hook occasionally fails to fire (observed ~10% of discards, and it
    /// predates this field). Without a way to tell "already fired" from "was missed", an effect that
    /// must guarantee the trigger has only two bad options: fire it again (double effect) or hope
    /// (silently lost effect). This token makes the distinction possible.
    /// </summary>
    private static int _prophetToken;

    /// <summary>Current value of the automatic-trigger counter.</summary>
    internal static int CurrentProphetToken => Volatile.Read(ref _prophetToken);

    /// <summary>
    /// Value of <see cref="CurrentProphetToken"/> at this card's most recent automatic trigger.
    /// A caller that snapshots <see cref="CurrentProphetToken"/> before a discard can compare: a value
    /// greater than the snapshot means the automatic hook fired for that discard.
    /// </summary>
    internal int LastProphetToken { get; private set; }

    /// <summary>
    /// Runs this card's Prophet effect the way a real play would: once per play, where a card with
    /// Replay N is played N+1 times. Also keeps the per-combat Prophet counter up to date.
    ///
    /// Shared with effects that fire a *different* card's Prophet trigger (背水一战 exhausting the
    /// cards it discarded). Callers that are discarding this card also handle the Power-card Limbo
    /// move; callers that are exhausting it do not need to, because exhausting already takes the card
    /// out of the play.
    /// </summary>
    internal async Task ResolveProphet(PlayerChoiceContext choiceContext)
    {
        var creature = Owner?.Creature;

        var resolutions = GetEnchantedReplayCount() + 1;
        for (var i = 0; i < resolutions; i++)
        {
            // Traced because this path had no output at all, which made "the effect did nothing" and
            // "the effect never ran" indistinguishable from the log — and a Prophet that draws can shuffle
            // the very discard pile a scry is still walking, so the piles are worth watching here.
            MainFile.Logger.Info(
                $"[prophet] {Id.Entry} {i + 1}/{resolutions} begin ctx={choiceContext?.GetType().Name} " +
                $"hand={PileSize(PileType.Hand)} draw={PileSize(PileType.Draw)} " +
                $"discard={PileSize(PileType.Discard)} tally={ProphetTallyOf(this)} " +
                $"overOrEnding={OverOrEnding()}");

            var ok = true;
            try
            {
                await OnProphet(choiceContext);
            }
            catch (Exception e)
            {
                // Isolated per card, deliberately. This runs from inside the pile-change hook, so an
                // escaping exception aborts the whole dispatch and every *remaining* Prophet card in the
                // same batch silently does nothing — one broken card taking its neighbours with it. Logged
                // in full so the failure is never invisible, then the batch carries on.
                ok = false;
                MainFile.Logger.Error($"[prophet] {Id.Entry} {i + 1}/{resolutions} OnProphet threw: {e}");
            }

            if (ok)
            {
                // Counted per resolution, so a Replay trigger counts as several Prophet effects.
                if (creature != null)
                {
                    await PowerCmd.Apply<ProphetTallyPower>(choiceContext, creature, 1m, creature, this);
                }
            }

            MainFile.Logger.Info(
                $"[prophet] {Id.Entry} {i + 1}/{resolutions} {(ok ? "done" : "FAILED")} " +
                $"hand={PileSize(PileType.Hand)} draw={PileSize(PileType.Draw)} " +
                $"discard={PileSize(PileType.Discard)} tally={ProphetTallyOf(this)} " +
                $"overOrEnding={OverOrEnding()}");
        }
    }

    /// <summary>
    /// Whether the engine has already started ending the combat. Logged alongside every Prophet
    /// resolution because the engine gates hooks and commands behind this flag: a trigger that reports
    /// "done" while its effect and its tally both fail to move is the signature of that gate rather than
    /// of anything in the Prophet path, and without the flag the two are indistinguishable in the log.
    /// </summary>
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

    /// <summary>Pile size for the Prophet trace; -1 when the pile cannot be read.</summary>
    private int PileSize(PileType pile)
    {
        try
        {
            var owner = Owner;
            return owner == null ? -1 : pile.GetPile(owner).Cards.Count;
        }
        catch (Exception)
        {
            return -1;
        }
    }

    /// <summary>
    /// How many 先知 effects have triggered this combat (0 when none have).
    /// </summary>
    protected int ProphetTally() => ProphetTallyOf(this);

    /// <summary>
    /// Same count, reachable from a static context.
    ///
    /// <see cref="MegaCrit.Sts2.Core.Localization.DynamicVars.CalculatedVar.WithMultiplier"/> rejects a
    /// delegate whose <c>Target</c> is an <c>AbstractModel</c>, so a card that wants its face to
    /// recalculate off the tally cannot pass an instance-capturing lambda and has to go through a
    /// static helper like this one.
    /// </summary>
    internal static int ProphetTallyOf(CardModel card)
    {
        var power = card?.Owner?.Creature?.GetPower<ProphetTallyPower>();
        return power == null ? 0 : power.Amount;
    }

    /// <summary>
    /// How many 先知 cards the owner currently has in play (all combat piles), reachable from a
    /// static context for the same reason as <see cref="ProphetTallyOf"/>.
    ///
    /// The counted set follows the base game's scaling attacks (PerfectedStrike / AshenStrike), which
    /// read <c>PlayerCombatState.AllCards</c>: hand, draw pile, discard pile, exhaust pile and play
    /// pile. A scaling card therefore counts itself, which is how those base game cards behave too.
    /// </summary>
    internal static int ProphetCardCount(CardModel card)
    {
        var combatState = card?.Owner?.PlayerCombatState;
        if (combatState == null) return 0;

        return combatState.AllCards.Count(c => c.Keywords.Contains(YetanniaKeywords.Prophet));
    }

    /// <summary>
    /// Runs the shared 预见 (Scry) mechanic via BaseLib's <see cref="ScryCmd"/>. Everything that
    /// scries must go through here so scry listeners (步步为营, 未雨绸缪, 回马枪) can react.
    /// </summary>
    protected Task<ScryResult> Scry(PlayerChoiceContext choiceContext, decimal amount) =>
        ScryTrace.Run(GetType().Name, choiceContext, Owner, (int)amount);

    /// <summary>
    /// Exhausts a set of cards. Used by the cards that exhaust whatever the player discarded while
    /// scrying; going through <see cref="CardCmd.Exhaust"/> keeps the exhaust hooks firing.
    /// </summary>
    protected static async Task ExhaustAll(PlayerChoiceContext choiceContext, IReadOnlyList<CardModel> cards)
    {
        foreach (var card in cards)
        {
            await CardCmd.Exhaust(choiceContext, card);
        }
    }
}
