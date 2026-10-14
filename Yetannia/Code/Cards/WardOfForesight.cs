using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 预见之壁 — 白卡（Common），2 费技能：获得 7（升级 10）点格挡。先知：效果相同。
/// </summary>
public sealed class WardOfForesight : YetanniaCard
{
    private const int BaseBlock = 7;
    private const int BlockUpgrade = 3; // 7 -> 10

    public WardOfForesight()
        : base(2, CardType.Skill, CardRarity.Common, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new BlockVar(BaseBlock, ValueProp.Move)];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay) =>
        CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);

    /// <summary>先知（无额外描述）：效果与打出相同。</summary>
    protected override Task OnProphet(PlayerChoiceContext choiceContext) =>
        CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block.BaseValue, ValueProp.Move, null);

    protected override void OnUpgrade() => DynamicVars.Block.UpgradeValueBy(BlockUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "后撤",
        "获得{Block:diff()}点[gold]格挡[/gold]。\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Fall Back",
        "Gain {Block:diff()} [gold]Block[/gold].\n[gold]Prophet[/gold].");
}
