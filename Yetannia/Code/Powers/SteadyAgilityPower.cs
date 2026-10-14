using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 未命名·从容 的结算器：临时敏捷在打出时由 <see cref="TempAgilityPower"/> 提供（本回合结束时自动
/// 收回），这个能力等到**敌人打完**（敌方回合结束）再检查「本回合是否受过伤害」——没受伤就把敏捷
/// 永久化并给下回合能量，受伤就什么都不做。
/// </summary>
public sealed class SteadyAgilityPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    private int DexterityAmount;
    private int EnergyReward;

    /// <summary>
    /// Whether the player had already been damaged during their own turn by the time the card was played.
    ///
    /// 从容's 「本回合未受到过伤害」 has to cover the whole round, but this resolver runs at the END of the
    /// enemy's turn, and a combat-history entry records the side it happened on — <c>HappenedThisTurn</c>
    /// compares that against the *current* side, so damage taken during the player's own turn is
    /// invisible from here. The card evaluates it at play time, where the player side is the current one,
    /// and hands the answer over. Without this the card face said "you were hit" (glow off) while the
    /// resolver still granted the permanent dexterity.
    /// </summary>
    private bool AlreadyDamaged;

    public void MarkValues(int dexterity, int energy, bool alreadyDamaged)
    {
        // Accumulates rather than overwrites. The card says the temporary dexterity "becomes permanent",
        // so every point the temp power is about to take back has to be granted here — and the temp power
        // subtracts its whole stack, not what one play added. Overwriting meant a second 从容 in the same
        // turn only ever converted the printed 2: the temp side went +4 -> 0 while this side granted a
        // flat +2, so 2 dexterity vanished (QA-RETEST7 caught it).
        DexterityAmount += dexterity;
        EnergyReward += energy;
        AlreadyDamaged |= alreadyDamaged;
    }

    public override async Task AfterSideTurnEnd(
        PlayerChoiceContext choiceContext, CombatSide side, IEnumerable<Creature> participants)
    {
        // Player-side window — evaluated FIRST, and it is not a no-op.
        //
        // The predicate has to cover the whole round, but a history entry records the side it happened on
        // while HappenedThisTurn compares that against the *current* side. Player-turn damage is therefore
        // only readable while the current side is still the player's, which is true exactly twice: at play
        // time (the card evaluates it there and hands the answer over) and here. This second reading is
        // what covers damage that landed AFTER the card was played — neither of the other two windows can
        // see it, and that ordering converted when it should not (QA-RETEST9 §3.3).
        if (side == CombatSide.Player)
        {
            if (DamageTakenOnCurrentSide())
            {
                AlreadyDamaged = true;
                MainFile.Logger.Info(
                    "[dextrack] SteadyAgility: player-turn damage seen at the player side turn end -> will not convert");
            }

            return;
        }

        // 只在敌方回合结束后结算（即“回合结束、敌人攻击完”）。玩家回合结束那次直接跳过。
        if (side != CombatSide.Enemy) return;

        var tookDamage = TookDamageThisTurn();

        // Traced because the outcome depends on listener ordering this class cannot see: the
        // temporary-dexterity power (TempAgilityPower, via vanilla TemporaryDexterityPower) removes its
        // whole stack at a side turn end too, so if it runs after this grant it eats the permanent
        // dexterity that was just added. These two lines plus TempAgilityPower's make that decidable
        // from a log instead of from guesses about ordering.
        MainFile.Logger.Info(
            $"[dextrack] SteadyAgility.AfterSideTurnEnd side={side} tookDamageThisTurn={tookDamage} " +
            $"grant={DexterityAmount} dexBefore={TempAgilityPower.DexterityOf(Owner)} " +
            $"tempStillUp={Owner?.GetPower<TempAgilityPower>() != null}");

        if (!tookDamage)
        {
            await PowerCmd.Apply<DexterityPower>(choiceContext, Owner, DexterityAmount, Owner, null);
            MainFile.Logger.Info(
                $"[dextrack] SteadyAgility granted +{DexterityAmount} permanent: dexAfter={TempAgilityPower.DexterityOf(Owner)}");
            await PowerCmd.Apply<EnergyNextTurnPower>(choiceContext, Owner, EnergyReward, Owner, null);
        }

        await PowerCmd.Remove(this);
    }

    /// <summary>
    /// Whether the player took damage at any point in the round the card was played in.
    ///
    /// Assembled from three readings, each taken where it is actually observable: the card's play-time
    /// answer (covers damage before the play), the player side's own turn end (covers damage after it),
    /// and the scan below, which at the enemy-side turn end sees the enemy's attacks.
    /// </summary>
    private bool TookDamageThisTurn() => AlreadyDamaged || DamageTakenOnCurrentSide();

    /// <summary>
    /// Real HP loss recorded against the current side.
    ///
    /// "未受到过伤害" has to mean the attack actually got through, not that an attack was aimed here — a
    /// hit fully absorbed by block still writes a <c>DamageReceivedEntry</c>, so counting those made a
    /// blocked turn look like a damaged one and refused to convert 从容 into permanent dexterity, which
    /// is exactly the "第一回合没给我破盾扣血" report. <c>UnblockedDamage</c> is the HP actually lost.
    /// </summary>
    private bool DamageTakenOnCurrentSide()
    {
        var history = CombatManager.Instance.History;
        var combatState = Owner?.CombatState;
        if (history == null || combatState == null) return false;

        return history.Entries
            .OfType<DamageReceivedEntry>()
            .Any(e => e.Receiver == Owner
                      && e.HappenedThisTurn(combatState)
                      && e.Result.UnblockedDamage > 0);
    }
    public override string? CustomPackedIconPath => ModAssets.Image("powers/steady_agility.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/steady_agility.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "未命名·从容",
        "回合结束时，若本回合未受到过伤害，将临时敏捷变为永久，并在下回合额外获得" + Loc.EnergyIcons(2) + "。",
        "回合结束时，若本回合未受到过伤害，将临时敏捷变为永久，并在下回合额外获得" + Loc.EnergyIcons(2) + "。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Unnamed (Steady Agility)",
        "At the end of the turn, if you took no damage this turn, your temporary Dexterity becomes permanent and you gain an extra " + Loc.EnergyIcons(2) + " next turn.",
        "At the end of the turn, if you took no damage this turn, your temporary Dexterity becomes permanent and you gain an extra " + Loc.EnergyIcons(2) + " next turn.");
}