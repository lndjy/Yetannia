using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 她眼中的世界 — 金卡（Rare），2 费能力，[虚无]（敲后去掉虚无）：
/// 每回合第一次打出攻击牌时获得 1 费，第一次打出技能牌时抽 1 张牌，第一次打出能力牌时预见 2。
///
/// Name is a placeholder (the request did not give one).
/// </summary>
public sealed class Insight : YetanniaCard
{
    public Insight()
        : base(2, CardType.Power, CardRarity.Rare, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Ethereal];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<InsightPower>(choiceContext, Owner.Creature, 1, Owner.Creature, this);
    }

    /// <summary>敲后：去掉[虚无]。</summary>
    protected override void OnUpgrade() => RemoveKeyword(CardKeyword.Ethereal);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "她眼中的世界",
        "每回合第一次打出攻击牌时，获得" + Loc.EnergyIcon + "；第一次打出技能牌时，抽1张牌；第一次打出能力牌时，预见2。");

    private static readonly List<(string, string)> English = new CardLoc(
        "The World in Her Eyes",
        "The first time you play an Attack each turn, gain " + Loc.EnergyIcon + "; the first time you play a Skill each turn, draw 1 card; the first time you play a Power each turn, Scry 2.");
}
