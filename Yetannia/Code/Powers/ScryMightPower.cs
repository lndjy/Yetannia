using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>藏器待时 — every N cards scried while this power is up, gain 1 Strength.</summary>
public sealed class ScryMightPower : ScryThresholdPower
{
    /// <summary>Fallback when the card has not written its (possibly upgraded) value in yet.</summary>
    protected override int Threshold => 6;

    protected override Task Grant(PlayerChoiceContext choiceContext, int amount) =>
        PowerCmd.Apply<StrengthPower>(choiceContext, Owner, amount, Owner, null);

    public override string? CustomPackedIconPath => ModAssets.Image("powers/scry_might.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/scry_might.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "藏器待时",
        "打出后，每累计预见{Threshold:diff()}张牌，获得1点[gold]力量[/gold]。",
        "打出后，每累计预见{Threshold:diff()}张牌，获得1点[gold]力量[/gold]。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Bide One\u2019s Time",
        "After you play this, gain 1 [gold]Strength[/gold] for every {Threshold:diff()} cards you Scry.",
        "After you play this, gain 1 [gold]Strength[/gold] for every {Threshold:diff()} cards you Scry.");
}
