using BaseLib.Abstracts;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Commands;
using BaseLib.Hooks;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// 未命名·预见 — 罕见遗物：本场战斗中每累计预见 10 张牌，获得 1 点[能量]。
///
/// Name is a placeholder (the request did not give one).
///
/// Relics are <see cref="AbstractModel"/>s, so this listens on BaseLib's
/// <see cref="IAfterScryed"/> exactly like 步步为营 / 未雨绸缪 do. The count keeps the remainder
/// (mod 10) so progress towards the next point is visible as the relic's counter.
///
/// The interface MUST be on the class declaration. BaseLib dispatches scry hooks through
/// <c>Hook.IterateCombatHookListeners(...).OfType&lt;IAfterScryed&gt;()</c>, so a model that merely
/// declares a matching <c>AfterScryed</c> method is never in that filtered set and the method is never
/// called — which silently made this entire relic dead (counter pinned at 0, no energy ever granted).
/// </summary>
public sealed class ForesightCharm : YetanniaRelic, IAfterScryed
{
    private const int CardsPerEnergy = 10;

    private int _scried;

    public override RelicRarity Rarity => RelicRarity.Uncommon;

    protected override string IconBaseName => "foresight_charm";

    public override bool ShowCounter => true;

    public override int DisplayAmount => _scried % CardsPerEnergy;

    public async Task AfterScryed(
        MegaCrit.Sts2.Core.GameActions.Multiplayer.PlayerChoiceContext choiceContext,
        Player player,
        int scryAmount,
        int discardAmount,
        List<CardModel> seen,
        List<CardModel> discarded)
    {
        if (player != Owner) return;

        var gained = seen.Count;
        if (gained <= 0) return;

        var before = _scried;
        _scried += gained;
        InvokeDisplayAmountChanged();

        var energy = _scried / CardsPerEnergy - before / CardsPerEnergy;
        if (energy > 0)
        {
            await PlayerCmd.GainEnergy(energy, player);
        }
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new RelicLoc(
        "未命名·预见",
        $"本场战斗中每累计预见{CardsPerEnergy}张牌，获得" + Loc.EnergyIcon + "。",
        "珠子每转过一圈，就多看清一分。");

    private static readonly List<(string, string)> English = new RelicLoc(
        "Unnamed (Foresight)",
        $"Every {CardsPerEnergy} cards scried this combat, gain " + Loc.EnergyIcon + ".",
        "Each turn of the beads buys a little more clarity.");
}
