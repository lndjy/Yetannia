using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 第三只眼 / Third Eye — ported from Slay the Spire 1 (Watcher, Common, 1 energy Skill):
/// "Gain 7 Block. Scry 3." Upgraded: 9 Block, Scry 5.
/// </summary>
public sealed class ThirdEye : YetanniaCard
{
    private const int BlockBase = 7;
    private const int BlockUpgrade = 2; // 7 -> 9
    private const int ScryBase = 3;
    private const int ScryUpgrade = 2; // 3 -> 5

    public ThirdEye()
        : base(1, CardType.Skill, CardRarity.Common, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new BlockVar(BlockBase, ValueProp.Move),
        new ScryVar(ScryBase)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);
        await Scry(choiceContext, DynamicVars["Scry"].BaseValue);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Block.UpgradeValueBy(BlockUpgrade);
        DynamicVars["Scry"].UpgradeValueBy(ScryUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "修顿",
        "获得{Block:diff()}点[gold]格挡[/gold]。\n预见{Scry:diff()}。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Xiudun",
        "Gain {Block:diff()} [gold]Block[/gold].\nScry {Scry:diff()}.");
}
