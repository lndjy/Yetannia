using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Factories;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>凛冽冰轮 — 金卡（Rare），2 费攻击：对全体敌人造成 21（升级 28）点伤害，将两张幻想纯爱加入你的弃牌堆。</summary>
public sealed class MassDefendDefend : YetanniaCard
{
    private const int BaseDamage = 21;
    private const int DamageUpgrade = 7; // 21 -> 28

    public MassDefendDefend()
        : base(2, CardType.Attack, CardRarity.Rare, TargetType.AllEnemies)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DamageVar(BaseDamage, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .TargetingAllOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        var copies = CardFactory.GetForCombat(
            Owner, [ModelDb.Card<DefendDefend>()], 2, Owner.RunState.Rng.CombatCardGeneration);
        foreach (var copy in copies)
        {
            await CardPileCmd.AddGeneratedCardToCombat(copy, PileType.Discard, Owner);
        }
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    /// <summary>
    /// 纯爱幻想 / 幻想纯爱 are generated cards, so hovering this shows their faces — the same thing the
    /// base game does for cards that name 灵魂 (CaptureSpirit uses HoverTipFactory.FromCard&lt;Soul&gt;()).
    /// Without this the text named a card the player had no way to look up.
    /// </summary>
    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromCard<DefendDefend>()
    ];
    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "凛冽冰轮", "对全体敌人造成{Damage:diff()}点伤害，将两张幻想纯爱加入你的弃牌堆。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Piercing Frost Wheel", "Deal {Damage:diff()} damage to ALL enemies. Add 2 Fantasies of Pure Love to your discard pile.");
}
