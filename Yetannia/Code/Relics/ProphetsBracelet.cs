using BaseLib.Abstracts;
using BaseLib.Utils;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.RelicPools;
using Yetannia.YetanniaCode.Patches;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// 先知的手链 — **事件遗物**（v1.1.0 起）：只在事件「记忆先知」的「献上自己的记忆」选项中获得，
/// 不再出现在普通遗物掉落里。效果不变：在所有**问号事件**里新增一个选项——跳过该事件并获得 50 金币。
///
/// It sits in the base game's <see cref="EventRelicPool"/> (event relics' home pool) rather than
/// <see cref="YetanniaRelicPool"/>. That is what "event relic" means mechanically here: the relic can only
/// be handed out by events — ours grants it directly — and it stops appearing in normal chest/elite/boss
/// relic rolls. <see cref="YetanniaRelicBase"/> (not <see cref="YetanniaRelic"/>) is the base class for
/// exactly that reason: the pool attribute is inherited, so a second attribute on the relic itself would
/// be rejected by BaseLib.
///
/// The extra option itself is injected by <see cref="EventSkipOptionPatch"/>, which postfixes
/// <c>EventModel.GenerateInitialOptionsWrapper</c> — the stable wrapper every event's options go
/// through. This relic is just the marker that patch looks for, so the option only appears for a
/// player who actually holds it.
/// </summary>
[Pool(typeof(EventRelicPool))]
public sealed class ProphetsBracelet : YetanniaRelicBase
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
        $"在所有问号事件中新增选项：跳过该事件，获得{GoldReward}金币。",
        "有些未来不值得看，有些价钱值得收。");

    private static readonly List<(string, string)> English = new RelicLoc(
        "Prophet's Bracelet",
        $"Adds an option to every ? event: skip it and gain {GoldReward} gold.",
        "Some futures are not worth watching. Some prices are.");
}
