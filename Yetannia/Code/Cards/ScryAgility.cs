using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 后发先制 — 蓝卡（Uncommon），1 费能力：
/// 打出这张牌之后，每累计预见 7（升级 5）张牌，获得 1 点[敏捷]。**打出之前预见过的牌不算。**
///
/// Name is a placeholder (the request did not give one).
///
/// Only scries made *after* this power is in play count, so the power simply starts its counter at 0
/// and <see cref="ScryThresholdPower.AfterScryed"/> does the rest. <c>PowerCmd.Apply</c> treats an
/// amount of 0 as "no-op", so the power is applied with a floor of 1 and then reset to 0 via
/// <see cref="MegaCrit.Sts2.Core.Models.PowerModel.SetAmount"/>.
/// </summary>
public sealed class ScryAgility : YetanniaCard
{
    private const int BaseThreshold = 7;
    private const int ThresholdUpgrade = -2; // 7 -> 5

    public ScryAgility()
        : base(1, CardType.Power, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DynamicVar(ScryThresholdPower.ThresholdVarName, BaseThreshold)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var power = await PowerCmd.Apply<ScryAgilityPower>(
            choiceContext, Owner.Creature, 1, Owner.Creature, this);

        if (power != null)
        {
            power.SetThreshold((int)DynamicVars[ScryThresholdPower.ThresholdVarName].BaseValue);

            // Start counting from 0: pre-play scries don't count. SetAmount (not ModifyAmount)
            // avoids treating the 0 as "remove this power".
            power.SetAmount(0);
        }
    }

    protected override void OnUpgrade() =>
        DynamicVars[ScryThresholdPower.ThresholdVarName].UpgradeValueBy(ThresholdUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "后发先制",
        "打出后，每累计预见{Threshold:diff()}张牌，获得1点[gold]敏捷[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Strike Second, Strike First",
        "After you play this, every {Threshold:diff()} cards you scry, gain 1 [gold]Dexterity[/gold].");
}
