using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 占卜 — 白卡（Common），1 费技能：预见 3（升级 4），抽 2 张牌。
/// </summary>
public sealed class Divination : YetanniaCard
{
    private const int BaseScry = 3;
    private const int ScryUpgrade = 1; // 3 -> 4
    private const int CardsDrawn = 2;

    public Divination()
        : base(1, CardType.Skill, CardRarity.Common, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new ScryVar(BaseScry),
        new CardsVar(CardsDrawn)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await Scry(choiceContext, DynamicVars["Scry"].BaseValue);
        await CardPileCmd.Draw(choiceContext, CardsDrawn, Owner);
    }

    protected override void OnUpgrade() => DynamicVars["Scry"].UpgradeValueBy(ScryUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "高举旗帜",
        "预见{Scry:diff()}。\n抽{Cards:diff()}张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Raise the Banner",
        "Scry {Scry:diff()}.\nDraw {Cards:diff()} cards.");
}
