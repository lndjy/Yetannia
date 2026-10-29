using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 众志成城 — 白卡（Common），4 费技能（敲后 3 费）：
/// 获得 18 点[格挡]。每当你抽到这张牌时，它的耗能减少 1。
///
/// Name is a placeholder (the request did not give one).
///
/// The discount is <c>AddThisCombat</c>, so it accumulates for the rest of the combat and is not
/// reset when the card is played or shuffled back. The opening hand draw counts too — the card is
/// drawn like any other.
/// </summary>
public sealed class PatientBulwark : YetanniaCard
{
    private const int BlockAmount = 18;
    private const int CostReductionOnUpgrade = -1; // 4 -> 3
    private const int CostReductionPerDraw = -1;

    public PatientBulwark()
        : base(4, CardType.Skill, CardRarity.Common, TargetType.Self)
    {
    }

    public override bool GainsBlock => true;

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new BlockVar(BlockAmount, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);
    }

    /// <summary>每当你抽到这张牌时，它的耗能减少 1。</summary>
    public override Task AfterCardDrawn(PlayerChoiceContext choiceContext, CardModel card, bool fromHandDraw)
    {
        if (ReferenceEquals(card, this))
        {
            EnergyCost.AddThisCombat(CostReductionPerDraw);
        }

        return Task.CompletedTask;
    }

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(CostReductionOnUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "众志成城",
        "获得{Block:diff()}点[gold]格挡[/gold]。\n每当你抽到这张牌时，这张牌的耗能减少1。");

    private static readonly List<(string, string)> English = new CardLoc(
        "United We Stand",
        "Gain {Block:diff()} [gold]Block[/gold].\nWhenever you draw this card, it costs 1 less.");
}
