using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 先知累积 — how many 先知 effects have triggered this combat.
///
/// Pure bookkeeping: the count exists so 厚积薄发 (<c>AccumulatedFate</c>) can scale its damage off it,
/// and that card's face already shows the live total. It is deliberately NOT drawn in the power bar —
/// see <see cref="IsVisibleInternal"/>.
///
/// It is maintained by <see cref="Cards.YetanniaCard"/>: every Prophet trigger applies one more
/// stack. <see cref="PowerStackType.Counter"/> means re-applying simply adds to the amount.
/// </summary>
public sealed class ProphetTallyPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Counter;

    /// <summary>
    /// Kept out of the power bar.
    ///
    /// Showing it put a permanent counter under the character for the whole combat, for a number that
    /// only ever mattered on one card. The count is surfaced on 厚积薄发's face instead, which is the
    /// only place a player can act on it.
    /// </summary>
    protected override bool IsVisibleInternal => false;

    public override string? CustomPackedIconPath => ModAssets.Image("powers/prophet_tally.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/prophet_tally.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "先知累积",
        "本场战斗中，先知效果已触发 X 次。",
        "本场战斗中，先知效果已触发 X 次。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Prophet Tally",
        "Prophet effects have triggered X time(s) this combat.",
        "Prophet effects have triggered X time(s) this combat.");
}
