using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.HoverTips;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 涅槃 / Nirvana — ported from Slay the Spire 1 (Watcher, Uncommon, 1 energy Power):
/// "Whenever you Scry, gain 3 Block." Upgraded: 4 Block.
/// </summary>
public sealed class Nirvana : YetanniaCard
{
    private const int BlockBase = 3;
    private const int BlockUpgrade = 1; // 3 -> 4

    public Nirvana()
        : base(1, CardType.Power, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new PowerVar<NirvanaPower>(BlockBase)];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
        [HoverTipFactory.FromPower<NirvanaPower>()];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<NirvanaPower>(
            choiceContext, Owner.Creature, DynamicVars.Power<NirvanaPower>().BaseValue, Owner.Creature, this);
    }

    protected override void OnUpgrade() => DynamicVars.Power<NirvanaPower>().UpgradeValueBy(BlockUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    // See the note in Foresight.cs: PowerVar<T> names its variable after the power type.
    private static readonly List<(string, string)> Chinese = new CardLoc(
        "步步为营",
        "每当你[gold]预见[/gold]时，获得{NirvanaPower:diff()}点[gold]格挡[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Cautious Advance",
        "Whenever you [gold]Scry[/gold], gain {NirvanaPower:diff()} [gold]Block[/gold].");
}
