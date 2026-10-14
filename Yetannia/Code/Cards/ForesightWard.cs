using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 预知之壁 / Foresight Ward — Yetannia's starter block card.
///
/// 0 energy: 获得 3 点格挡（升级后 4）。
/// [gold]先知[/gold]：获得 4 点格挡（升级后 6）。
///
/// The card carries two separate block values: <c>Block</c> for the normal play, and a second
/// named <see cref="BlockVar"/> (<see cref="ProphetBlockVar"/>) for the Prophet effect, so the two
/// can upgrade by different amounts. Both go through <see cref="CreatureCmd.GainBlock"/>, so block
/// modifiers such as Dexterity still apply to either one.
/// </summary>
public sealed class ForesightWard : YetanniaCard
{
    private const int BaseBlock = 3;
    private const int BlockUpgrade = 1; // 3 -> 4

    private const int BaseProphetBlock = 4;
    private const int ProphetBlockUpgrade = 2; // 4 -> 6

    private const string ProphetBlockVar = "ProphetBlock";

    public ForesightWard()
        : base(0, CardType.Skill, CardRarity.Basic, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new BlockVar(BaseBlock, ValueProp.Move),
        new BlockVar(ProphetBlockVar, BaseProphetBlock, ValueProp.Move)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);
    }

    /// <summary>先知：获得格挡。There is no card play behind this, so the card play argument is null.</summary>
    protected override async Task OnProphet(PlayerChoiceContext choiceContext)
    {
        var prophetBlock = (BlockVar)DynamicVars[ProphetBlockVar];
        await CreatureCmd.GainBlock(Owner.Creature, prophetBlock.BaseValue, prophetBlock.Props, null);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Block.UpgradeValueBy(BlockUpgrade);
        DynamicVars[ProphetBlockVar].UpgradeValueBy(ProphetBlockUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "回避",
        "获得{Block:diff()}点[gold]格挡[/gold]。\n[gold]先知[/gold]：获得{ProphetBlock:diff()}点[gold]格挡[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Evade",
        "Gain {Block:diff()} [gold]Block[/gold].\n[gold]Prophet[/gold]: Gain {ProphetBlock:diff()} [gold]Block[/gold].");
}
