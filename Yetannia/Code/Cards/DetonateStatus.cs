using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>破釜沉舟 — 蓝卡（Uncommon），2 费攻击：消耗你手中全部状态牌，造成 16（升级 22）点伤害。</summary>
public sealed class DetonateStatus : YetanniaCard
{
    private const int BaseDamage = 16;
    private const int DamageUpgrade = 6; // 16 -> 22

    public DetonateStatus()
        : base(2, CardType.Attack, CardRarity.Uncommon, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DamageVar(BaseDamage, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        var hand = PileType.Hand.GetPile(Owner);
        foreach (var status in hand.Cards.Where(c => c.Rarity == CardRarity.Status).ToList())
        {
            await CardCmd.Exhaust(choiceContext, status);
        }

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "破釜沉舟", "消耗你手中全部状态牌，造成{Damage:diff()}点伤害。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Burn the Boats", "Exhaust all Status cards in your hand, then deal {Damage:diff()} damage.");
}
