using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>冰刃连斩 — 蓝卡（Uncommon），1 费能力：每当你消耗一张牌，对所有敌人造成 3（升级 4）点伤害。</summary>
public sealed class ExhaustBlast : YetanniaCard
{
    private const int BaseDamage = 3;
    private const int DamageUpgrade = 1; // 3 -> 4

    public ExhaustBlast()
        : base(1, CardType.Power, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var power = await PowerCmd.Apply<ExhaustBlastPower>(
            choiceContext, Owner.Creature, 1, Owner.Creature, this);
        power?.MarkValues(this, (int)DynamicVars["Damage"].BaseValue);
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DynamicVar("Damage", BaseDamage)];

    protected override void OnUpgrade() => DynamicVars["Damage"].UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "冰刃连斩", "每当你消耗一张牌，对所有敌人造成{Damage:diff()}点伤害。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Ice Blade Barrage", "Whenever you exhaust a card, deal {Damage:diff()} damage to ALL enemies.");
}
