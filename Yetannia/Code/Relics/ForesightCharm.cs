using BaseLib.Abstracts;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Commands;
using BaseLib.Hooks;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Saves.Runs;

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

    public override int DisplayAmount => Scried % CardsPerEnergy;

    /// <summary>
    /// 已预见牌数。**<c>[SavedProperty]</c> 是必须的**，理由与
    /// <see cref="AgatePotionBelt.PotionsUsed"/> 完全相同：这是决定「什么时候发能量」的计数器，而能量
    /// 是校验和里的一项。普通私有字段不参与同步与序列化，两端一旦不同步，就先到阈值的那一端单独发能量
    /// ——那是一次货真价实的状态分歧（energy 就在 checksum 里）。
    ///
    /// 原版 46 个遗物都是这么写的（见 <c>PaelsWing.RewardsSacrificed</c>），并且只有写成
    /// <c>[SavedProperty]</c> 才会出现在分歧报告的 <c>savedProperties.netIdMap</c> 里。
    /// </summary>
    [SavedProperty]
    public int Scried
    {
        get => _scried;
        set
        {
            AssertMutable();
            _scried = value;
            InvokeDisplayAmountChanged();
        }
    }

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

        var before = Scried;
        Scried += gained;

        var energy = Scried / CardsPerEnergy - before / CardsPerEnergy;
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
