using System;
using BaseLib.Abstracts;
using BaseLib.Hooks;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// Shared body for 藏器待时 / 后发先制: every <see cref="Threshold"/> cards scried
/// this combat, grant one point of the relevant stat.
///
/// <c>Amount</c> is the running count of cards scried while this power has been up. The number of
/// grants is derived purely from the count *before* and *after* each scry
/// (<c>newTotal / threshold - oldTotal / threshold</c>), so no separate "already granted" counter is
/// needed and nothing can drift.
///
/// The threshold is written into <c>DynamicVars</c> by the card right after the power is applied,
/// because the card's upgrade lowers it (6→4 / 7→5) and powers get their vars from
/// <c>CanonicalVars</c>, which is per type rather than per instance.
/// </summary>
public abstract class ScryThresholdPower : CustomPowerModel, IAfterScryed
{
    /// <summary>
    /// Name of the dynamic var holding the per-grant threshold. Public so the cards can write their
    /// (possibly upgraded) value into the power right after applying it.
    /// </summary>
    public const string ThresholdVarName = "Threshold";

    /// <summary>How many scried cards are needed per granted point.</summary>
    protected abstract int Threshold { get; }

    /// <summary>Hand out <paramref name="amount"/> points of this power's stat.</summary>
    protected abstract Task Grant(PlayerChoiceContext choiceContext, int amount);

    public override PowerType Type => PowerType.Buff;

    /// <summary>Amount is the scried-card counter.</summary>
    public override PowerStackType StackType => PowerStackType.Counter;

    /// <summary>
    /// The threshold MUST be a real dynamic var here. It is referenced by this power's own tooltip,
    /// and the cards write their (possibly upgraded) value into it after applying the power.
    ///
    /// Without this override the var simply does not exist, and BOTH the card's write and
    /// <see cref="AfterScryed"/>'s read throw <c>KeyNotFoundException</c>. The read one is the
    /// dangerous half: it runs *inside* <c>ScryCmd</c>, so the exception unwinds straight out of the
    /// card play and the played card is left frozen in the middle of the screen — the "预见牌卡住
    /// 不结算" report.
    /// </summary>
    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DynamicVar(ThresholdVarName, Threshold)];

    /// <summary>
    /// Stores the threshold the card is actually using (its upgraded value, if upgraded).
    /// Cannot throw — a failure here would abort the card that just applied this power.
    /// </summary>
    /// <summary>
    /// Renders this power's description with its own variables already substituted.
    ///
    /// The engine has two rendering paths and only one of them adds a model's <c>DynamicVars</c>. The
    /// "dumb" path — <c>HoverTipFactory.FromPower&lt;T&gt;()</c> → <c>GetDumbHoverTip</c> — adds only
    /// Amount / singleStarIcon / energyPrefix, so a description that names {Threshold:diff()} renders the
    /// literal braces there. Overriding <c>Description</c> is the only seam available for that: the getter
    /// is public virtual, while <c>GetDumbHoverTip</c> is not virtual and its AddDumbVariablesToDescription
    /// is private. Doing it here is why this power reads correctly on both paths instead of only the smart one.
    ///
    /// Safe to run even where the caller also adds the variables (as the mod's own self-check does):
    /// <c>AddTo</c> sets the same keys to the same values.
    /// </summary>
    public override LocString Description
    {
        get
        {
            var text = base.Description;
            DynamicVars.AddTo(text);
            return text;
        }
    }
    public void SetThreshold(int value)
    {
        if (value <= 0) return;
        try
        {
            DynamicVars[ThresholdVarName].BaseValue = value;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scry] {GetType().Name}: could not store threshold {value}: {e.Message}");
        }
    }

    /// <summary>
    /// Reads the threshold, falling back to the subclass default. Deliberately cannot throw: an
    /// exception from here propagates out through <c>ScryCmd</c> and strands the card being played.
    /// </summary>
    private int ThresholdOf()
    {
        try
        {
            var value = (int)DynamicVars[ThresholdVarName].BaseValue;
            return value > 0 ? value : Threshold;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scry] {GetType().Name}: threshold var missing, using {Threshold}: {e.Message}");
            return Threshold;
        }
    }

    public async Task AfterScryed(
        PlayerChoiceContext choiceContext,
        Player player,
        int scryAmount,
        int discardAmount,
        List<CardModel> seen,
        List<CardModel> discarded)
    {
        if (player != Owner.Player) return;

        // Cards actually looked at, which is what "累计预见 N 张牌" is counting. Scries that
        // resolved to nothing never reach this hook at all.
        var gained = seen.Count;
        if (gained <= 0) return;

        var threshold = ThresholdOf();
        if (threshold <= 0) threshold = Threshold;

        var before = Amount;
        var after = before + gained;

        await PowerCmd.ModifyAmount(choiceContext, this, gained, Owner, null);

        var grants = after / threshold - before / threshold;
        if (grants > 0)
        {
            await Grant(choiceContext, grants);
        }
    }
}
