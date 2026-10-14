using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 先见之明 — 蓝卡（Uncommon），0 费技能：[固有]、[消耗]。
/// 预见 3（升级 4），抽 2（升级 3）张牌。
///
/// The class is named <c>Prescience</c> rather than <c>Foresight</c> because 先见之明 was the old
/// display name of the card that is now 有条不紊 (<c>Foresight.cs</c>). Model IDs and class names
/// are left alone during renames so existing saves keep resolving; only the display name moved.
/// </summary>
public sealed class Prescience : YetanniaCard
{
    private const int BaseScry = 3;
    private const int ScryUpgrade = 1; // 3 -> 4
    private const int BaseCards = 2;
    private const int CardsUpgrade = 1; // 2 -> 3

    public Prescience()
        : base(0, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords =>
        [CardKeyword.Innate, CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new ScryVar(BaseScry),
        new CardsVar(BaseCards)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await Scry(choiceContext, DynamicVars["Scry"].BaseValue);
        await CardPileCmd.Draw(choiceContext, DynamicVars.Cards.BaseValue, Owner);
    }

    protected override void OnUpgrade()
    {
        DynamicVars["Scry"].UpgradeValueBy(ScryUpgrade);
        DynamicVars.Cards.UpgradeValueBy(CardsUpgrade);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "先见之明",
        "预见{Scry:diff()}。抽{Cards:diff()}张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Foresight",
        "Scry {Scry:diff()}. Draw {Cards:diff()} cards.");
}
