using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 潜伏之力 — 蓝卡（Uncommon），不能被打出。
/// 先知：获得 1（升级 2）点能量。
/// </summary>
public sealed class LatentPower : YetanniaCard
{
    private const int BaseEnergy = 1;
    private const int EnergyUpgrade = 1; // 1 -> 2

    public LatentPower()
        : base(0, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords =>
        [CardKeyword.Unplayable, YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new EnergyVar(BaseEnergy)];

    protected override Task OnProphet(PlayerChoiceContext choiceContext) =>
        PlayerCmd.GainEnergy(DynamicVars.Energy.BaseValue, Owner);

    protected override void OnUpgrade() => DynamicVars.Energy.UpgradeValueBy(EnergyUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "蓄势待发",
        "[gold]先知[/gold]：获得{Energy:energyIcons()}。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Poised",
        "[gold]Prophet[/gold]: Gain {Energy:energyIcons()}.");
}
