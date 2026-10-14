using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 纯爱药丸 — 金卡（Rare），1 费技能，[消耗]：
/// 获得 10（升级 14）点[格挡]，获得 1 层[人工制品]。
/// </summary>
public sealed class PureLovePill : YetanniaCard
{
    private const int BaseBlock = 10;
    private const int BlockUpgrade = 4; // 10 -> 14
    private const int ArtifactAmount = 1;

    public PureLovePill()
        : base(1, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    public override bool GainsBlock => true;

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new BlockVar(BaseBlock, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var creature = Owner.Creature;
        await CreatureCmd.GainBlock(creature, DynamicVars.Block, cardPlay);
        await PowerCmd.Apply<ArtifactPower>(choiceContext, creature, ArtifactAmount, creature, this);
    }

    protected override void OnUpgrade() => DynamicVars.Block.UpgradeValueBy(BlockUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "纯爱药丸",
        "获得{Block:diff()}点[gold]格挡[/gold]。获得1层[gold]人工制品[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Pure Love Pill",
        "Gain {Block:diff()} [gold]Block[/gold]. Gain 1 [gold]Artifact[/gold].");
}
