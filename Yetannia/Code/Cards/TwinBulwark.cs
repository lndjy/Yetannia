using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 交叉防御 — 白卡（Common），1 费技能：获得 5（升级 7）点[格挡]，2 次。
///
/// Name is a placeholder (the request did not give one). The two grants are separate
/// <c>GainBlock</c> calls rather than one doubled amount, so anything that reacts to a single
/// block gain (or caps one) sees two events, which is what "2 次" asks for.
/// </summary>
public sealed class TwinBulwark : YetanniaCard
{
    private const int BaseBlock = 5;
    private const int BlockUpgrade = 2; // 5 -> 7
    private const int Times = 2;

    public TwinBulwark()
        : base(1, CardType.Skill, CardRarity.Common, TargetType.Self)
    {
    }

    public override bool GainsBlock => true;

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new BlockVar(BaseBlock, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        for (var i = 0; i < Times; i++)
        {
            await CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);
        }
    }

    protected override void OnUpgrade() => DynamicVars.Block.UpgradeValueBy(BlockUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "交叉防御",
        "获得{Block:diff()}点[gold]格挡[/gold]，2次。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Cross Defense",
        "Gain {Block:diff()} [gold]Block[/gold], 2 times.");
}
