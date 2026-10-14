using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>未命名·预见之敏 — every N cards scried this combat, gain 1 Dexterity.</summary>
public sealed class ScryAgilityPower : ScryThresholdPower
{
    /// <summary>Fallback when the card has not written its (possibly upgraded) value in yet.</summary>
    protected override int Threshold => 7;

    protected override Task Grant(PlayerChoiceContext choiceContext, int amount) =>
        PowerCmd.Apply<DexterityPower>(choiceContext, Owner, amount, Owner, null);

    public override string? CustomPackedIconPath => ModAssets.Image("powers/scry_agility.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/scry_agility.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "预见之敏",
        "打出后，每累计预见{Threshold:diff()}张牌，获得1点[gold]敏捷[/gold]。",
        "打出后，每累计预见{Threshold:diff()}张牌，获得1点[gold]敏捷[/gold]。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Foreseen Agility",
        "Every {Threshold:diff()} cards scried this combat, gain 1 [gold]Dexterity[/gold].",
        "Every {Threshold:diff()} cards scried this combat, gain 1 [gold]Dexterity[/gold].");
}
