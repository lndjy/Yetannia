using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 斩铁波 — 白卡（Common），0 费攻击：
/// 造成 4（升级 5）点伤害，获得 3（升级 5）点[格挡]。
///
/// Modelled on the classic Iron Wave: a cheap attack that also banks block.
/// </summary>
public sealed class IronWave : YetanniaCard
{
    private const int BaseDamage = 4;
    private const int DamageUpgrade = 1; // 4 -> 5
    private const int BaseBlock = 3;
    private const int BlockUpgrade = 2; // 3 -> 5

    public IronWave()
        : base(0, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(BaseDamage, ValueProp.Move),
        new BlockVar(BaseBlock, ValueProp.Move)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        await CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);
        DynamicVars.Block.UpgradeValueBy(BlockUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "斩铁波",
        "造成{Damage:diff()}点伤害，获得{Block:diff()}点[gold]格挡[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Iron Wave",
        "Deal {Damage:diff()} damage and gain {Block:diff()} [gold]Block[/gold].");
}
