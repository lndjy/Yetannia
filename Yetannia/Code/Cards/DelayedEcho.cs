using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 水色睿智 — 蓝卡（Uncommon），0 费技能，[消耗]：
/// 获得 2（升级 3）点[能量]；本回合结束时，将这张牌的一张复制加入你的弃牌堆。
///
/// Name is a placeholder (the request did not give one) — rename by editing
/// <see cref="Chinese"/> / <see cref="English"/>.
///
/// The copy is NOT built here. This card is exhausted on play and leaves the combat piles, so it cannot
/// carry the end-of-turn hook itself; it hands <see cref="DelayedEchoPower"/> the *recipe* for the copy
/// (upgrade state + which combat it was played in) and the power builds a fresh card at end of turn.
/// See <see cref="DelayedEchoPower"/> for why parking a pre-made clone cannot work.
/// </summary>
public sealed class DelayedEcho : YetanniaCard
{
    private const int BaseEnergy = 2;
    private const int EnergyUpgrade = 1; // 2 -> 3

    public DelayedEcho()
        : base(0, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new EnergyVar(BaseEnergy)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PlayerCmd.GainEnergy(DynamicVars.Energy.BaseValue, Owner);

        // Reuse the power if one is already armed rather than relying on Apply's return value: with
        // StackType.Single a second play must append to the *existing* instance, otherwise the first
        // copy is lost and only one of the two cards ever lands.
        var power = Owner.Creature.GetPower<DelayedEchoPower>()
                    ?? await PowerCmd.Apply<DelayedEchoPower>(
                        choiceContext, Owner.Creature, 1m, Owner.Creature, this);

        // Queue the *recipe*, not a clone: the copy is built at end of turn from the current combat's
        // own card factory. See DelayedEchoPower for why a parked clone cannot work.
        power?.AddCopy(CurrentUpgradeLevel > 0, Owner.Creature.CombatState);
    }

    protected override void OnUpgrade() => DynamicVars.Energy.UpgradeValueBy(EnergyUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "水色睿智",
        "获得{Energy:energyIcons()}。本回合结束时，将这张牌的一张复制加入你的弃牌堆。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Azure Wisdom",
        "Gain {Energy:energyIcons()}. At the end of this turn, add a copy of this card into your discard pile.");
}
