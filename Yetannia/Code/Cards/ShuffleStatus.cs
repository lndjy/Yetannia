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

/// <summary>常备不懈 — 白卡（Common），0 费攻击：造成 7（升级 10）点伤害，随机将一张纯爱幻想或幻想纯爱放入你的抽牌堆。</summary>
public sealed class ShuffleStatus : YetanniaCard
{
    private const int BaseDamage = 7;
    private const int DamageUpgrade = 3; // 7 -> 10

    public ShuffleStatus()
        : base(0, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
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

        var canonical = Owner.RunState.Rng.CombatCardGeneration.NextItem(
            new CardModel[] { ModelDb.Card<StrikeStrike>(), ModelDb.Card<DefendDefend>() });
        var copy = CardFactory.GetForCombat(Owner, [canonical], 1, Owner.RunState.Rng.CombatCardGeneration).First();
        await CardPileCmd.AddGeneratedCardToCombat(copy, PileType.Draw, Owner, CardPilePosition.Random);
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    /// <summary>
    /// 纯爱幻想 / 幻想纯爱 are generated cards, so hovering this shows their faces — the same thing the
    /// base game does for cards that name 灵魂 (CaptureSpirit uses HoverTipFactory.FromCard&lt;Soul&gt;()).
    /// Without this the text named a card the player had no way to look up.
    /// </summary>
    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromCard<StrikeStrike>(),
        HoverTipFactory.FromCard<DefendDefend>()
    ];
    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "常备不懈", "造成{Damage:diff()}点伤害，随机将一张纯爱幻想或幻想纯爱放入你的抽牌堆。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Ever Ready", "Deal {Damage:diff()} damage. Put a random Pure Love Fantasy or Fantasy of Pure Love into your draw pile.");
}
