using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 横扫 — 白卡（Common），1 费攻击：对所有敌人造成 10（升级 14）点伤害。先知：效果相同。
/// </summary>
public sealed class PropheticCleave : YetanniaCard
{
    private const int BaseDamage = 10;
    private const int DamageUpgrade = 4; // 10 -> 14

    public PropheticCleave()
        : base(1, CardType.Attack, CardRarity.Common, TargetType.AllEnemies)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(BaseDamage, ValueProp.Move)];

    protected override Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay) =>
        StrikeAllEnemies(choiceContext);

    /// <summary>先知（无额外描述）：效果与打出相同。</summary>
    protected override Task OnProphet(PlayerChoiceContext choiceContext) =>
        StrikeAllEnemies(choiceContext);

    private async Task StrikeAllEnemies(PlayerChoiceContext choiceContext)
    {
        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, null)
            .TargetingAllOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "横扫",
        "对所有敌人造成{Damage:diff()}点伤害。\n[gold]先知[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Sweep",
        "Deal {Damage:diff()} damage to ALL enemies.\n[gold]Prophet[/gold].");
}
