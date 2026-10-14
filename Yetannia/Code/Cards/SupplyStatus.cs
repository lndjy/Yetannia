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

/// <summary>火中白花 — 白卡（Common），1 费技能：获得 10（升级 13）点格挡，将一张纯爱幻想加入你的手牌。</summary>
public sealed class SupplyStatus : YetanniaCard
{
    private const int BaseBlock = 10;
    private const int BlockUpgrade = 3; // 10 -> 13

    public SupplyStatus()
        : base(1, CardType.Skill, CardRarity.Common, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [new BlockVar(BaseBlock, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);

        var copy = CardFactory.GetForCombat(
            Owner, [ModelDb.Card<StrikeStrike>()], 1, Owner.RunState.Rng.CombatCardGeneration).First();
        await CardPileCmd.AddGeneratedCardToCombat(copy, PileType.Hand, Owner);
    }

    protected override void OnUpgrade() => DynamicVars.Block.UpgradeValueBy(BlockUpgrade);

    /// <summary>
    /// 纯爱幻想 / 幻想纯爱 are generated cards, so hovering this shows their faces — the same thing the
    /// base game does for cards that name 灵魂 (CaptureSpirit uses HoverTipFactory.FromCard&lt;Soul&gt;()).
    /// Without this the text named a card the player had no way to look up.
    /// </summary>
    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
    [
        HoverTipFactory.FromCard<StrikeStrike>()
    ];
    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "火中白花", "获得{Block:diff()}点[gold]格挡[/gold]，将一张纯爱幻想加入你的手牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "White Flower in Fire", "Gain {Block:diff()} [gold]Block[/gold]. Add a Pure Love Fantasy to your hand.");
}
