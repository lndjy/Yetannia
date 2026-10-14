using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.Factories;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;
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

    public override int DisplayAmount => _potionsUsed % PotionsPerReward;

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

        _potionsUsed++;
        InvokeDisplayAmountChanged();

        if (_potionsUsed % PotionsPerReward != 0) return;

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
