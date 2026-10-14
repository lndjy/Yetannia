using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 净化视野 — 蓝卡（Uncommon），1 费技能：预见 2，将因此被弃置的牌[消耗]，然后抽 2（升级 3）张牌。
///
/// 被预见弃掉的牌先由 <c>ScryCmd</c> 放进弃牌堆，这里再把它们逐张消耗掉，
/// 走的是 <see cref="CardCmd.Exhaust"/>，所以消耗相关的钩子也会正常触发。
/// </summary>
public sealed class PurifyingVision : YetanniaCard
{
    private const int ScryAmount = 2;
    private const int CardsBase = 2;
    private const int CardsUpgrade = 1; // 2 -> 3

    public PurifyingVision()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new ScryVar(ScryAmount),
        new CardsVar(CardsBase)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var result = await Scry(choiceContext, ScryAmount);
        await ExhaustAll(choiceContext, result.Discarded);
        await CardPileCmd.Draw(choiceContext, DynamicVars.Cards.BaseValue, Owner);
    }

    protected override void OnUpgrade() => DynamicVars.Cards.UpgradeValueBy(CardsUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "抉择",
        "预见{Scry:diff()}。\n[gold]消耗[/gold]因此被弃置的牌。\n抽{Cards:diff()}张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Choice",
        "Scry {Scry:diff()}.\n[gold]Exhaust[/gold] the cards discarded this way.\nDraw {Cards:diff()} cards.");
}
