using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>幻想纯爱 — 状态牌，1 费：当此牌被消耗时，获得 4 点格挡。[消耗]</summary>
public sealed class DefendDefend : YetanniaCard
{
    public override int MaxUpgradeLevel => 0;

    public DefendDefend()
        : base(1, CardType.Status, CardRarity.Status, TargetType.None)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars => [new BlockVar(4, ValueProp.Move)];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay) => Task.CompletedTask;

    public override async Task AfterCardExhausted(PlayerChoiceContext choiceContext, CardModel card, bool causedByEthereal)
    {
        if (!ReferenceEquals(card, this)) return;
        var block = DynamicVars.Block.BaseValue;
        if (Owner.Creature.GetPower<DoubleStatusPower>() != null) block *= 2;
        await CreatureCmd.GainBlock(Owner.Creature, block, DynamicVars.Block.Props, null);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "幻想纯爱", "当此牌被消耗时，获得4点格挡。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Fantasy of Pure Love", "When this card is exhausted, gain 4 Block.");
}
