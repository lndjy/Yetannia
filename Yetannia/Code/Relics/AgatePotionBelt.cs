using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.Factories;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves.Runs;
using Yetannia.YetanniaCode.Character;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// 玛瑙的药水腰带 — 稀有遗物：
/// 拾起时获得 1 个药水栏位；之后每当你使用 3 瓶药水，随机获得一瓶药水。
///
/// The slot uses the same call the base game's potion-slot rewards use
/// (<c>PlayerCmd.GainMaxPotionCount</c>). The counter is the relic's own display amount, so the
/// player can see progress towards the next potion.
/// </summary>
public sealed class AgatePotionBelt : YetanniaRelic
{
    private const int PotionsPerReward = 3;

    private int _potionsUsed;

    public override RelicRarity Rarity => RelicRarity.Rare;

    protected override string IconBaseName => "agate_potion_belt";

    public override bool ShowCounter => true;

    public override int DisplayAmount => PotionsUsed % PotionsPerReward;

    /// <summary>
    /// 已使用药水数。**<c>[SavedProperty]</c> 在这里是必须的，不是装饰。**
    ///
    /// MEASURED, in a real 3-player online run: leaving this as a plain private field caused a genuine
    /// state divergence (RitsuLib reported checksum #797 differing by exactly these fields —
    /// <c>players[2].potions</c> extra <c>POTION.SWIFT_POTION</c> on the peer that fired, and
    /// <c>rng.run.rngs.CombatPotionGeneration</c> counter 2 vs 0 with all four state words different).
    ///
    /// Why: <see cref="AfterPotionUsed"/> is dispatched through
    /// <c>Hook.AfterPotionUsed</c> -&gt; <c>runState.IterateHookListeners</c>, which runs on every peer
    /// for every potion used by anyone, so the count is *meant* to stay identical everywhere. But a bare
    /// field is not part of the state that gets serialized and compared, so nothing keeps the peers in
    /// step: the moment the two copies disagree, the lucky one reaches the threshold first, draws from
    /// the SHARED <c>Rng.CombatPotionGeneration</c>, and hands its owner a potion the other peer never
    /// sees. A synchronized counter is what makes the grant happen on both peers at the same time.
    ///
    /// This is the base game's own idiom, not an invention: 46 of the vanilla relics declare their
    /// counters exactly like this (see <c>PaelsWing.RewardsSacrificed</c>), which is also why a vanilla
    /// relic's progress shows up under <c>savedProperties.netIdMap</c> in the divergence report while
    /// this relic's did not.
    /// </summary>
    [SavedProperty]
    public int PotionsUsed
    {
        get => _potionsUsed;
        set
        {
            AssertMutable();
            _potionsUsed = value;
            InvokeDisplayAmountChanged();
        }
    }

    /// <summary>拾起时：获得 1 个药水栏位。</summary>
    public override async Task AfterObtained()
    {
        var player = Owner;
        if (player == null) return;

        await PlayerCmd.GainMaxPotionCount(1, player);
    }

    /// <summary>每使用 3 瓶药水，随机获得一瓶药水。</summary>
    public override async Task AfterPotionUsed(PotionModel potion, MegaCrit.Sts2.Core.Entities.Creatures.Creature target)
    {
        var player = Owner;
        if (player == null) return;
        if (potion.Owner != player) return;

        PotionsUsed++;

        if (PotionsUsed % PotionsPerReward != 0) return;

        // Draw from the game's real potion pool. This used to read this mod's own
        // YetanniaPotionPool — which is empty, because this mod defines no potions at all — so
        // `candidates.Count == 0` returned early and the relic silently granted nothing, forever.
        // PotionFactory is what the base game's own potion relics use.
        var chosen = PotionFactory.CreateRandomPotionOutOfCombat(
            player, player.RunState.Rng.CombatPotionGeneration);
        if (chosen == null) return;

        await PotionCmd.TryToProcure(chosen.ToMutable(), player);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new RelicLoc(
        "玛瑙的药水腰带",
        "拾起时，获得1个药水栏位。每当你使用3瓶药水，随机获得一瓶药水。",
        "腰带内侧缝着一圈小环，每一个都还记得装过什么。");

    private static readonly List<(string, string)> English = new RelicLoc(
        "Agate's Potion Belt",
        "When picked up, gain 1 potion slot. Every 3 potions you use, gain a random potion.",
        "A ring of little loops stitched inside, each one remembering what it held.");
}
