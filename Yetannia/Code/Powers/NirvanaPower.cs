using BaseLib.Abstracts;
using BaseLib.Hooks;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 涅槃 / Nirvana (ported from Slay the Spire 1's Watcher card of the same name):
/// whenever you Scry, gain X Block.
///
/// Scry notifications come from BaseLib's <see cref="IAfterScryed"/> hook, which is dispatched by
/// <see cref="ScryCmd"/>. Any scry this mod performs therefore has to go through ScryCmd for this
/// power (and Weave) to notice it.
/// </summary>
public sealed class NirvanaPower : CustomPowerModel, IAfterScryed
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Counter;

    public Task AfterScryed(PlayerChoiceContext ctx, Player player, int scryAmount, int discardAmount,
        List<CardModel> seen, List<CardModel> discarded)
    {
        if (player != Owner.Player) return Task.CompletedTask;
        if (Amount <= 0) return Task.CompletedTask;

        return CreatureCmd.GainBlock(Owner, Amount, ValueProp.Move, null);
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/nirvana.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/nirvana.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "涅槃",
        "每当你预见时，获得 X 点格挡。",
        "每当你预见时，获得 X 点格挡。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Nirvana",
        "Whenever you Scry, gain X Block.",
        "Whenever you Scry, gain X Block.");
}
