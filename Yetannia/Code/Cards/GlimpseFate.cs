using BaseLib.Abstracts;
using BaseLib.Cards.Variables;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 命运一瞥 — 白卡（Common），0 费技能：预见 1（升级 2），抽 1 张牌。
/// </summary>
public sealed class GlimpseFate : YetanniaCard
{
    private const int BaseScry = 1;
    private const int ScryUpgrade = 1; // 1 -> 2
    private const int CardsDrawn = 1;

    public GlimpseFate()
        : base(0, CardType.Skill, CardRarity.Common, TargetType.Self)
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
        "挥舞",
        "预见{Scry:diff()}。\n抽{Cards:diff()}张牌。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Brandish",
        "Scry {Scry:diff()}.\nDraw {Cards:diff()} card.");
}
