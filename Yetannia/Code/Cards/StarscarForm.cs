using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 星痕化 — 金卡（Rare），2 费技能（升级 1 费），[消耗]：
/// 下个回合，获得 1 层[无实体]。
///
/// The Intangible is granted at the start of the NEXT turn rather than now, so the card parks a marker
/// power (<see cref="StarscarFormPower"/>) that pays out on the following turn start. The marker is
/// visible on purpose: it is the only thing telling the player that a delayed 无实体 is pending.
/// </summary>
public sealed class StarscarForm : YetanniaCard
{
    private const int CostReductionOnUpgrade = -1; // 2 -> 1

    public StarscarForm()
        : base(2, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<StarscarFormPower>(choiceContext, Owner.Creature, 1m, Owner.Creature, this);
    }

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(CostReductionOnUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "星痕化",
        "下个回合，获得1层[gold]无实体[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Starscar Form",
        "Next turn, gain 1 [gold]Intangible[/gold].");
}
