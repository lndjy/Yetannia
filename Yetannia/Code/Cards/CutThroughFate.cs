using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 斩断命运 / Cut Through Fate — ported from Slay the Spire 1 (Watcher, Common, 1 energy Attack):
/// "Deal 7 damage. Scry 2. Draw 1 card." Upgraded: 9 damage, Scry 3.
///
/// Scry happens before the draw, exactly as in the original, so the player can choose what they draw.
/// </summary>
public sealed class CutThroughFate : YetanniaCard
{
    private const int DamageBase = 7;
    private const int DamageUpgrade = 2; // 7 -> 9
    private const int ScryBase = 2;
    private const int ScryUpgrade = 1; // 2 -> 3
    private const int CardsDrawn = 1;

    public CutThroughFate()
        : base(1, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(DamageBase, ValueProp.Move),
        new ScryVar(ScryBase),
        new CardsVar(CardsDrawn)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);

        await Scry(choiceContext, DynamicVars["Scry"].BaseValue);
        await CardPileCmd.Draw(choiceContext, CardsDrawn, Owner);
    }

    protected override void OnUpgrade()
    {
        DynamicVars.Damage.UpgradeValueBy(DamageUpgrade);
        DynamicVars["Scry"].UpgradeValueBy(ScryUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "先制",
        "造成{Damage:diff()}点伤害。\n预见{Scry:diff()}。\n抽{Cards:diff()}张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Preemptive Strike",
        "Deal {Damage:diff()} damage.\nScry {Scry:diff()}.\nDraw {Cards:diff()} card.");
}
