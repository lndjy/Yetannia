using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Patches;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// 先知的手链 — 普通遗物：在所有**问号事件**里新增一个选项：跳过该事件并获得 50 金币。
///
/// The extra option itself is injected by <see cref="EventSkipOptionPatch"/>, which postfixes
/// <c>EventModel.GenerateInitialOptionsWrapper</c> — the stable wrapper every event's options go
/// through. This relic is just the marker that patch looks for, so the option only appears for a
/// player who actually holds it.
/// </summary>
public sealed class ProphetsBracelet : YetanniaRelic
{
    private const int GoldReward = 50;

    public override RelicRarity Rarity => RelicRarity.Common;

    protected override string IconBaseName => "prophets_bracelet";

    /// <summary>Gold granted by the injected option.</summary>
    public static int SkipReward => GoldReward;

    /// <summary>Whether the given player is carrying this relic (what the patch gates on).</summary>
    public static bool IsHeldBy(Player player) =>
        player != null && player.Relics.Any(relic => relic is ProphetsBracelet);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new RelicLoc(
        "先知的手链",
        $"在所有问号事件中新增选项：跳过该事件并获得{GoldReward}金币。",
        "有些未来不值得看，有些价钱值得收。");

    private static readonly List<(string, string)> English = new RelicLoc(
        "Prophet's Bracelet",
        $"Adds an option to every ? event: skip it and gain {GoldReward} gold.",
        "Some futures are not worth watching. Some prices are.");
}
