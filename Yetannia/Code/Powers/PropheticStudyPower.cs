using BaseLib.Abstracts;
using BaseLib.Hooks;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 先知研习 — whenever you Scry, draw X card(s).
/// </summary>
public sealed class PropheticStudyPower : CustomPowerModel, IAfterScryed
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Counter;

    public async Task AfterScryed(PlayerChoiceContext ctx, Player player, int scryAmount, int discardAmount,
        List<CardModel> seen, List<CardModel> discarded)
    {
        // Traced because this power's entire job happens inside the scry hook, where a silent no-op is
        // indistinguishable from the hook never firing — the "未雨绸缪 没抽牌" report cannot be settled
        // from the outside. One line per scry makes it decidable: whether the hook arrived, what the
        // stack was, and how the piles moved.
        var mine = player == Owner.Player;
        MainFile.Logger.Info(
            $"[study] AfterScryed fired owner={mine} amount={Amount} seen={seen.Count} discarded={discarded.Count} " +
            $"hand={PileOf(player, PileType.Hand)} draw={PileOf(player, PileType.Draw)}");

        if (!mine) return;
        if (Amount <= 0) return;

        await CardPileCmd.Draw(ctx, Amount, player);

        MainFile.Logger.Info(
            $"[study] drew {Amount}: hand={PileOf(player, PileType.Hand)} draw={PileOf(player, PileType.Draw)}");
    }

    /// <summary>Pile size for the trace; -1 when there is no player to read from.</summary>
    private static int PileOf(Player? player, PileType pile)
    {
        if (player == null) return -1;
        try
        {
            return pile.GetPile(player).Cards.Count;
        }
        catch (Exception)
        {
            return -1;
        }
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/prophetic_study.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/prophetic_study.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "先知研习",
        "每当你预见时，抽 X 张牌。",
        "每当你预见时，抽 X 张牌。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Prophetic Study",
        "Whenever you Scry, draw X card(s).",
        "Whenever you Scry, draw X card(s).");
}
