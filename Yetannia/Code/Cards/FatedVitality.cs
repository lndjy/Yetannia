using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 积厚成势 — 金卡（Rare），1 费技能，[消耗]：
/// 打出时获得**卡面上显示的数字**点生命上限。
/// [先知]：把卡面上这个数字抬高 2（升级 3），本场战斗最多累计到 8（升级 12）。
///
/// The request's wording is precise here: the Prophet trigger must **not** grant Max HP by itself —
/// it raises the number *printed on the card*, and playing the card is what grants that accumulated
/// number. So the accumulator is the card's own <c>MaxHp</c> dynamic var, which is exactly what the
/// card face renders; there is no longer a bookkeeping power behind it.
/// </summary>
public sealed class FatedVitality : YetanniaCard
{
    private const int BaseGain = 2;
    private const int GainUpgrade = 1; // 2 -> 3

    private const int BaseStep = 2;
    private const int StepUpgrade = 1; // +2 -> +3 per Prophet trigger

    private const int BaseCap = 8;
    private const int CapUpgrade = 4; // 8 -> 12

    private const string StepVar = "ProphetStep";
    private const string CapVar = "MaxHpCap";

    public FatedVitality()
        : base(1, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords =>
        [YetanniaKeywords.Prophet, CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new MaxHpVar(BaseGain),
        new DynamicVar(StepVar, BaseStep),
        new DynamicVar(CapVar, BaseCap)
    ];

    /// <summary>打出：把卡面上累计的数字变成生命上限。</summary>
    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var amount = DynamicVars.MaxHp.BaseValue;
        if (amount <= 0) return;

        await CreatureCmd.GainMaxHp(Owner.Creature, amount);
    }

    /// <summary>先知：只抬高卡面数字，不给生命上限。</summary>
    protected override Task OnProphet(PlayerChoiceContext choiceContext)
    {
        var cap = DynamicVars[CapVar].BaseValue;
        var raised = Math.Min(DynamicVars.MaxHp.BaseValue + DynamicVars[StepVar].BaseValue, cap);
        DynamicVars.MaxHp.BaseValue = raised;
        return Task.CompletedTask;
    }

    protected override void OnUpgrade()
    {
        DynamicVars.MaxHp.UpgradeValueBy(GainUpgrade);
        DynamicVars[StepVar].UpgradeValueBy(StepUpgrade);
        DynamicVars[CapVar].UpgradeValueBy(CapUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "积厚成势",
        "获得{MaxHp:diff()}点生命上限。\n[gold]先知[/gold]：上面的数字+{ProphetStep:diff()}，最多累计为{MaxHpCap:diff()}。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Accumulate Might",
        "Gain {MaxHp:diff()} Max HP.\n[gold]Prophet[/gold]: increase that number by {ProphetStep:diff()}, up to a total of {MaxHpCap:diff()}.");
}
