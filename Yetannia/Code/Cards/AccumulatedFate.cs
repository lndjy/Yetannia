using BaseLib.Abstracts;
using BaseLib.Extensions;
using BaseLib.Utils;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 宿命累积 — 蓝卡（Uncommon），1 费攻击，目标为所有敌人：
/// 对所有敌人造成 6（升级 9）点伤害。
/// 本场战斗中每触发过一次先知效果，此牌伤害 +3（升级 +4）。
///
/// The running count comes from <c>ProphetTallyPower</c>, which
/// <see cref="YetanniaCard"/> keeps up to date on every Prophet trigger (including this card's own
/// trigger while it sits in the discard pile).
///
/// The damage is a <see cref="CalculatedDamageVar"/> rather than a plain <see cref="DamageVar"/> on
/// purpose. A plain DamageVar only ever holds the printed base number, so the card face kept showing
/// 6 no matter how many Prophets had triggered — the bonus was only ever applied inside
/// <c>OnPlay</c> and was therefore invisible. <see cref="CalculatedVar.UpdateCardPreview"/> re-runs
/// the multiplier every time the card is drawn, which is what makes the face show
/// "6 + 3 × triggers" (highlighted green, since the preview exceeds the base value).
/// This mirrors the base game's own scaling attacks (<c>PerfectedStrike</c>, <c>AshenStrike</c>).
/// </summary>
public sealed class AccumulatedFate : YetanniaCard
{
    private const int BaseDamage = 6;
    private const int BaseDamageUpgrade = 3; // 6 -> 9
    private const int BaseBonusPerTrigger = 3;
    private const int BonusUpgrade = 1; // 3 -> 4

    public AccumulatedFate()
        : base(1, CardType.Attack, CardRarity.Uncommon, TargetType.AllEnemies)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new CalculationBaseVar(BaseDamage),
        new ExtraDamageVar(BaseBonusPerTrigger),
        new TallyVar(),

        // Must be a *static* lambda: WithMultiplier rejects a delegate whose Target is an
        // AbstractModel, which an instance-capturing lambda would be. The helper is qualified with
        // the type name because an unqualified inherited member counts as a `this` reference, which
        // a static lambda is not allowed to contain.
        new CalculatedDamageVar(ValueProp.Move).WithMultiplier(
            static (CardModel card, Creature _) => (decimal)YetanniaCard.ProphetTallyOf(card))
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await Strike(choiceContext, cardPlay);
    }

    /// <summary>先知（无额外描述）：效果与打出相同。</summary>
    protected override Task OnProphet(PlayerChoiceContext choiceContext) =>
        Strike(choiceContext, null);

    private async Task Strike(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        // AttackCommand recomputes CalculatedDamage per hit, so the tally is read at resolution time
        // rather than at play time (which matters for the Prophet trigger, where the pile change
        // itself may still be bumping the counter).
        await DamageCmd.Attack(DynamicVars.CalculatedDamage)
            .FromCard(this, cardPlay)
            .TargetingAllOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.CalculationBase.UpgradeValueBy(BaseDamageUpgrade);
        DynamicVars.ExtraDamage.UpgradeValueBy(BonusUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "厚积薄发",
        "对所有敌人造成{CalculatedDamage:diff()}点伤害。\n本场战斗中每触发过一次[gold]先知[/gold]效果，此牌伤害+{ExtraDamage:diff()}。\n（本场已触发先知 {Tally} 次）\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Building Momentum",
        "Deal {CalculatedDamage:diff()} damage to ALL enemies.\nDeals {ExtraDamage:diff()} additional damage for each [gold]Prophet[/gold] effect triggered this combat.\n({Tally} triggered so far this combat)\n[gold]Prophet[/gold].");

    /// <summary>
    /// Surfaces the 先知 tally on this card's face.
    ///
    /// The tally used to be drawn as a counter under the character, which meant a number that only
    /// matters here occupied the power bar for the whole combat. 先知累积 is now hidden, and this is
    /// where the player reads it — recomputed on every card preview, the same cadence as the damage.
    ///
    /// <c>CalculatedVar</c> is not reused because it multiplies by a paired "extra" var; a bare count
    /// has no extra part, so the value is written straight into <c>BaseValue</c>.
    /// </summary>
    private sealed class TallyVar : DynamicVar
    {
        public TallyVar()
            : base("Tally", 0m)
        {
        }

        public override void UpdateCardPreview(
            CardModel card, CardPreviewMode previewMode, Creature? target, bool runGlobalHooks)
        {
            base.UpdateCardPreview(card, previewMode, target, runGlobalHooks);
            BaseValue = YetanniaCard.ProphetTallyOf(card);
        }
    }
}
