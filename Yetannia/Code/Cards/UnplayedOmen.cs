using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using Yetannia.YetanniaCode.Keywords;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 未卜之兆 — 蓝卡（Uncommon），不能被打出。
/// 先知：抽 2（升级 3）张牌。
/// </summary>
public sealed class UnplayedOmen : YetanniaCard
{
    private const int BaseCards = 2;
    private const int CardsUpgrade = 1; // 2 -> 3

    public UnplayedOmen()
        : base(0, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords =>
        [CardKeyword.Unplayable, YetanniaKeywords.Prophet];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new CardsVar(BaseCards)];

    protected override async Task OnProphet(PlayerChoiceContext choiceContext)
    {
        // The amount is logged because this card's whole Prophet effect is a draw: the pile numbers
        // around it in the ResolveProphet trace then show whether the draw actually happened, instead of
        // leaving "did nothing" and "never ran" looking identical.
        var wanted = (int)DynamicVars.Cards.BaseValue;
        MainFile.Logger.Info($"[prophet] UnplayedOmen drawing {wanted}");
        await CardPileCmd.Draw(choiceContext, wanted, Owner);
    }

    protected override void OnUpgrade() => DynamicVars.Cards.UpgradeValueBy(CardsUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "引蛇出洞",
        "[gold]先知[/gold]：抽{Cards:diff()}张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Lure the Snake Out",
        "[gold]Prophet[/gold]: Draw {Cards:diff()} cards.");
}
