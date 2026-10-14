using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 霜色华斩 — 白卡（Common），4 费攻击（敲后 3 费）：
/// 造成 26 点伤害。你每抽到一次这张牌，它的耗能 -1。
///
/// Name is a placeholder (the request did not give one). Same per-draw discount as
/// <see cref="PatientBulwark"/>; no damage upgrade was specified, so the upgrade is the cost only.
/// </summary>
public sealed class PatientStrike : YetanniaCard
{
    private const int DamageAmount = 26;
    private const int CostReductionOnUpgrade = -1; // 4 -> 3
    private const int CostReductionPerDraw = -1;

    public PatientStrike()
        : base(4, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(DamageAmount, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    /// <summary>你每抽到一次这张牌，它的耗能 -1。</summary>
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
        "霜色华斩",
        "造成{Damage:diff()}点伤害。\n你每抽到一次这张牌，这张牌的耗能-1。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Frostbound Slash",
        "Deal {Damage:diff()} damage.\nWhenever you draw this card, it costs 1 less.");
}
