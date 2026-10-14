using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 因果切断 — 金卡（Rare），2 费攻击，[消耗]：
/// 造成 13（升级 16）点伤害；如果这一击**击杀了目标**，**永久**升级你打出的上一张牌
/// （等同于在火堆敲了那张牌）。
///
/// Name is a placeholder (the request did not give one).
///
/// "The previous card you played" is read from combat history: the entry for this card is only
/// appended once its play finishes, so while <c>OnPlay</c> runs the last finished play by this
/// player is the one before it.
///
/// **The upgrade has to be applied to the card's <c>DeckVersion</c>, not to the card that was
/// played.** During combat, piles hold mutable copies of the deck cards; <c>CardCmd.Upgrade</c>
/// upgrades whichever instance it is handed, so upgrading the combat copy would only last until the
/// end of the fight. <c>DeckVersion</c> is the link back to the persistent deck card, and upgrading
/// that is exactly what the Smith rest site does — including recording it in the map history.
///
/// If the previous card has no <c>DeckVersion</c> it did not come from the deck, so there is nothing
/// to upgrade permanently and the effect does not fire at all.
/// </summary>
public sealed class FatalInsight : YetanniaCard
{
    private const int BaseDamage = 13;
    private const int DamageUpgrade = 3; // 13 -> 16

    public FatalInsight()
        : base(2, CardType.Attack, CardRarity.Rare, TargetType.AnyEnemy)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(BaseDamage, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");
        var target = cardPlay.Target;

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        if (!target.IsDead) return;

        var previous = LastCardPlayedBeforeThis();
        if (previous == null)
        {
            MainFile.Logger.Info(
                "[fatal] kill, but no finished card play by this player was found in the history");
            return;
        }

        // Upgrade the *deck* copy, which is what makes it permanent (a Smith upgrade).
        // The instance that was played is a per-combat mutable copy; upgrading that alone would be
        // forgotten the moment the fight ends.
        //
        // No deck copy means the previous card did not come from the deck (it was generated,
        // duplicated or otherwise temporary) — then there is nothing to upgrade permanently, and the
        // effect does not fire at all.
        var persistent = previous.DeckVersion;
        if (persistent == null || ReferenceEquals(persistent, previous))
        {
            // Logged loudly on purpose: from the player's seat this is indistinguishable from the
            // effect being broken, and it is the most likely shape of the "sometimes it doesn't
            // upgrade" report. A generated card (先知的指引 / 薪火 hand them out) has no deck copy.
            MainFile.Logger.Info(
                $"[fatal] kill, but previous card {previous.Id.Entry} has no deck copy " +
                $"(deckVersionNull={persistent == null}) -> nothing to upgrade permanently");
            return;
        }

        var alreadyUpgraded = persistent.IsUpgraded;

        // CardCmd.Upgrade no-ops while CombatManager.Instance.IsEnding, and a FatalInsight kill is
        // very often the killing blow that ends the combat — exactly when the upgrade must still land.
        // Do it by hand instead: mirror CardCmd.Upgrade minus that guard (and minus its preview VFX,
        // which is pointless while combat is ending). The previous log line said "took effect" but the
        // guard had actually skipped it; that is the "斩悟敲牌不生效" report.
        if (persistent.IsUpgradable)
        {
            if (persistent.Pile?.Type == PileType.Deck)
            {
                persistent.Owner.RunState.CurrentMapPointHistoryEntry
                    ?.GetEntry(persistent.Owner.NetId).UpgradedCards.Add(persistent.Id);
            }
            persistent.UpgradeInternal();
            persistent.FinalizeUpgradeInternal();
        }

        // Keep the in-combat copy in step for the rest of this fight.
        if (previous.IsUpgradable)
        {
            previous.UpgradeInternal();
            previous.FinalizeUpgradeInternal();
        }

        MainFile.Logger.Info(
            $"[fatal] kill -> deck card {persistent.Id.Entry}: alreadyUpgraded={alreadyUpgraded} " +
            $"(so this upgrade {(alreadyUpgraded ? "changed nothing visible" : "took effect")})");
    }

    /// <summary>The most recently finished card play by this card's owner, excluding this card.</summary>
    private CardModel LastCardPlayedBeforeThis()
    {
        var history = CombatManager.Instance.History;
        if (history == null) return null;

        var entries = history.Entries.ToList();
        for (var i = entries.Count - 1; i >= 0; i--)
        {
            if (entries[i] is not CardPlayFinishedEntry entry) continue;
            if (entry.CardPlay.Card == this) continue;
            if (entry.CardPlay.Player != Owner) continue;
            return entry.CardPlay.Card;
        }

        return null;
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "因果切断",
        "造成{Damage:diff()}点伤害。如果击杀目标，永久升级你打出的上一张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Sever the Thread",
        "Deal {Damage:diff()} damage. If this kills the target, permanently upgrade the last card you played.");
}
