using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Combat.History.Entries;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using Yetannia.YetanniaCode.Config;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 临危不乱 — 蓝卡（Uncommon），1 费技能：
/// 获得 2（升级 3）点**临时**[敏捷]；如果本回合**没有受到过伤害**，
/// 改为**永久**获得敏捷，并且下回合额外获得 2 点[能量]。
/// 东尼测试版（<see cref="CardBalanceMode.TonyTest"/>）额外给它[消耗]：打出后进消耗堆，原版没有。
/// (Original: 2 temporary Dexterity, upgraded 3, no Exhaust. Tony draft: the same numbers plus
/// Exhaust, so the card leaves play after being played.)
///
/// Name is a placeholder (the request did not give one). Mirrors <see cref="RisingMight"/>;
/// "took no damage this turn" is read from combat history's damage entries.
/// </summary>
public sealed class SteadyAgility : YetanniaCard
{
    private const int BaseAmount = 2;
    private const int AmountUpgrade = 1; // 2 -> 3
    private const int EnergyReward = 2;

    public SteadyAgility()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    /// <summary>
    /// 东尼测试版增加[gold]消耗[/gold]；原版没有这个关键词。关键词只在模型构造时取一次，所以和数值
    /// 一样，切换模式后要重启才生效。
    /// </summary>
    public override IEnumerable<CardKeyword> CanonicalKeywords =>
        CardBalance.IsTony ? [CardKeyword.Exhaust] : Array.Empty<CardKeyword>();

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new PowerVar<DexterityPower>(BaseAmount)];

    /// <summary>
    /// 高亮：本回合未受到过伤害（即将永久获得敏捷）时，手牌里的这张牌发金光。
    /// Driven by <c>NHandCardHolder.UpdateCard</c>, re-evaluated after every combat state change.
    /// </summary>
    protected override bool ShouldGlowGoldInternal =>
        Owner != null && !TookDamageThisTurn();

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var creature = Owner.Creature;
        var amount = (int)DynamicVars.Dexterity.BaseValue;

        // 临时敏捷现在生效（本回合结束自动收回）；结算器在敌人打完之后再把没受伤的敏捷永久化。
        await PowerCmd.Apply<TempAgilityPower>(choiceContext, creature, amount, creature, this);

        // Reuse the resolver if this turn already played one. It accumulates the amounts it will convert
        // (the temp power takes back its whole stack, so both plays' worth has to be handed over), and a
        // second Apply on a Single-stack power is not guaranteed to return the existing instance.
        var resolver = creature.GetPower<SteadyAgilityPower>()
                       ?? await PowerCmd.Apply<SteadyAgilityPower>(choiceContext, creature, 1, creature, this);

        // The damage answer is computed HERE, not inside the resolver: right now the current side is the
        // player's, so damage already taken this turn is visible. By the time the resolver runs (end of
        // the enemy's turn) those entries are on the wrong side to be seen.
        resolver?.MarkValues(amount, EnergyReward, TookDamageThisTurn());
    }

    private bool TookDamageThisTurn()
    {
        var history = CombatManager.Instance.History;
        var combatState = CombatState;
        if (history == null || combatState == null) return false;

        // Only real HP loss counts — a hit fully absorbed by block still writes an entry, and treating
        // that as "受到过伤害" made the card refuse to convert. Kept in step with the resolver's copy.
        return history.Entries
            .OfType<DamageReceivedEntry>()
            .Any(e => e.Receiver == Owner.Creature
                      && e.HappenedThisTurn(combatState)
                      && e.Result.UnblockedDamage > 0);
    }

    protected override void OnUpgrade() => DynamicVars.Dexterity.UpgradeValueBy(AmountUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "临危不乱",
        "获得{DexterityPower:diff()}点临时[gold]敏捷[/gold]。如果本回合未受到过伤害，改为永久获得，并且下回合额外获得" + Loc.EnergyIcons(2) + "。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Unshaken",
        "Gain {DexterityPower:diff()} temporary [gold]Dexterity[/gold]. If you took no damage this turn, gain it permanently instead and gain an extra " + Loc.EnergyIcons(2) + " next turn.");
}
