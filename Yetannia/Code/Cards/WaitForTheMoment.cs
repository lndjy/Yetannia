using BaseLib.Abstracts;
using BaseLib.Hooks;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 伺机而动 — 白卡（Common），2 费攻击：
/// 造成 12（升级 16）点伤害；如果你在本回合内[预见]过牌，获得 2 点[能量]。
///
/// "Scried this turn" is tracked on the card itself: the card sits in a combat pile, so
/// <c>IterateHookListeners</c> hands it BaseLib's <see cref="IAfterScryed"/> dispatch. Comparing the
/// recorded <c>PlayerCombatState.TurnNumber</c> against the current one at resolution time means no
/// reset hook and no extra bookkeeping power is needed — a stale record simply stops matching.
/// </summary>
public sealed class WaitForTheMoment : YetanniaCard, IAfterScryed
{
    private const int BaseDamage = 12;
    private const int DamageUpgrade = 4; // 12 -> 16
    private const int EnergyGain = 2;

    private int _scriedOnTurn = -1;

    public WaitForTheMoment()
        : base(2, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(BaseDamage, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        if (ScriedThisTurn)
        {
            await PlayerCmd.GainEnergy(EnergyGain, Owner);
        }
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public Task AfterScryed(
        PlayerChoiceContext choiceContext,
        Player player,
        int scryAmount,
        int discardAmount,
        List<CardModel> seen,
        List<CardModel> discarded)
    {
        if (player != Owner) return Task.CompletedTask;

        _scriedOnTurn = Owner.PlayerCombatState?.TurnNumber ?? -1;
        return Task.CompletedTask;
    }

    private bool ScriedThisTurn
    {
        get
        {
            var combatState = Owner.PlayerCombatState;
            return combatState != null && _scriedOnTurn == combatState.TurnNumber;
        }
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "伺机而动",
        "造成{Damage:diff()}点伤害。如果你在本回合内[gold]预见[/gold]过牌，获得" + Loc.EnergyIcons(2) + "。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Wait for the Moment",
        "Deal {Damage:diff()} damage. If you Scried this turn, gain " + Loc.EnergyIcons(2) + ".");
}
