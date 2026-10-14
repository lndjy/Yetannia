using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 银铃响起之时 — 蓝卡（Uncommon），1 费技能：
/// 获得 3（升级 4）点**临时**[力量]；如果本回合已经打出**超过 2 张**攻击牌，
/// 改为**永久**获得力量，并且下回合额外抽 2 张牌。
///
/// Name is a placeholder (the request did not give one).
///
/// Temporary Strength is the base game's <c>TemporaryStrengthPower</c> family: it applies real
/// Strength and takes it back at end of turn. <see cref="TempMightPower"/> is that family's
/// per-card subclass.
///
/// The attack count comes from combat history, filtered to this turn and this player — the same
/// <c>HappenedThisTurn</c> filter the base game's own turn-based cards use.
/// </summary>
public sealed class RisingMight : YetanniaCard
{
    private const int BaseAmount = 3;
    private const int AmountUpgrade = 1; // 3 -> 4
    private const int AttackThreshold = 2; // 超过两张 => 3 张或更多
    private const int DrawReward = 2;

    public RisingMight()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new PowerVar<StrengthPower>(BaseAmount)];

    /// <summary>
    /// 高亮：本回合已经打出超过 2 张攻击牌（即将永久获得力量）时，手牌里的这张牌发金光。
    /// The base game drives this through <c>NHandCardHolder.UpdateCard</c>, which re-evaluates after
    /// every combat state change, so the glow turns on/off live as attacks are played.
    /// </summary>
    protected override bool ShouldGlowGoldInternal =>
        Owner != null && AttacksPlayedThisTurn() > AttackThreshold;

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var creature = Owner.Creature;
        var amount = DynamicVars.Strength.BaseValue;

        // Logged because "permanent Strength doesn't work" cannot be told apart from "the condition
        // was false" without knowing which branch ran and what the count actually was.
        var attacks = AttacksPlayedThisTurn();
        var permanent = attacks > AttackThreshold;
        MainFile.Logger.Info(
            $"[rising] attacks this turn={attacks} (permanent needs >{AttackThreshold}) -> " +
            $"{(permanent ? "PERMANENT" : "temporary")} Strength {amount}");

        if (permanent)
        {
            await PowerCmd.Apply<StrengthPower>(choiceContext, creature, amount, creature, this);
            await PowerCmd.Apply<DrawCardsNextTurnPower>(choiceContext, creature, DrawReward, creature, this);
            MainFile.Logger.Info(
                $"[rising] applied: Strength={creature.GetPowerAmount<StrengthPower>()} " +
                $"(temp={creature.GetPowerAmount<TempMightPower>()})");
            return;
        }

        await PowerCmd.Apply<TempMightPower>(choiceContext, creature, amount, creature, this);
        MainFile.Logger.Info(
            $"[rising] applied: Strength={creature.GetPowerAmount<StrengthPower>()} " +
            $"(temp={creature.GetPowerAmount<TempMightPower>()})");
    }

    private int AttacksPlayedThisTurn()
    {
        var history = CombatManager.Instance.History;
        var combatState = CombatState;
        if (history == null || combatState == null) return 0;

        return history.Entries
            .OfType<CardPlayFinishedEntry>()
            .Count(e => e.CardPlay.Player == Owner
                        && e.CardPlay.Card.Type == CardType.Attack
                        && e.HappenedThisTurn(combatState));
    }

    protected override void OnUpgrade() => DynamicVars.Strength.UpgradeValueBy(AmountUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "银铃响起之时",
        "获得{StrengthPower:diff()}点临时[gold]力量[/gold]。如果本回合已经打出超过2张攻击牌，改为永久获得，并且下回合额外抽2张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "When the Silver Bell Rings",
        "Gain {StrengthPower:diff()} temporary [gold]Strength[/gold]. If you have played more than 2 Attack cards this turn, gain it permanently instead and draw 2 extra cards next turn.");
}
