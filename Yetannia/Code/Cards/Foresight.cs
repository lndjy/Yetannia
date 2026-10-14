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
/// 先见之明 / Foresight — ported from Slay the Spire 1 (Watcher, Uncommon, 1 energy Power):
/// "At the start of your turn, Scry 3." Upgraded: Scry 4.
/// </summary>
public sealed class Foresight : YetanniaCard
{
    private const int ScryBase = 3;
    private const int ScryUpgrade = 1; // 3 -> 4

    public Foresight()
        : base(1, CardType.Power, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new PowerVar<ForesightPower>(ScryBase)];

    protected override IEnumerable<IHoverTip> ExtraHoverTips =>
        [HoverTipFactory.FromPower<ForesightPower>()];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<ForesightPower>(
            choiceContext, Owner.Creature, DynamicVars.Power<ForesightPower>().BaseValue, Owner.Creature, this);
    }

    protected override void OnUpgrade() => DynamicVars.Power<ForesightPower>().UpgradeValueBy(ScryUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    // Note: PowerVar<T> names its variable after the power type, so the placeholder has to be
    // {ForesightPower:...} rather than {Power:...}. (Shockwave in the base game can use {Power}
    // only because it declares a plain DynamicVar literally named "Power".)
    private static readonly List<(string, string)> Chinese = new CardLoc(
        "有条不紊",
        "在你的回合开始时，预见{ForesightPower:diff()}。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Methodical",
        "At the start of your turn, Scry {ForesightPower:diff()}.");
}
