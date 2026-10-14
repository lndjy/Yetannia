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

/// <summary>风中笑颜 — 白卡（Common），1 费攻击：造成 11（升级 15）点伤害，将一张幻想纯爱加入你的手牌。</summary>
public sealed class ReinforceStatus : YetanniaCard
{
    private const int BaseDamage = 11;
    private const int DamageUpgrade = 4; // 11 -> 15

    public ReinforceStatus()
        : base(1, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DamageVar(BaseDamage, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        var copy = CardFactory.GetForCombat(
            Owner, [ModelDb.Card<DefendDefend>()], 1, Owner.RunState.Rng.CombatCardGeneration).First();
        await CardPileCmd.AddGeneratedCardToCombat(copy, PileType.Hand, Owner);
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
        "风中笑颜", "造成{Damage:diff()}点伤害，将一张幻想纯爱加入你的手牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Smile in the Wind", "Deal {Damage:diff()} damage. Add a Fantasy of Pure Love to your hand.");
}
