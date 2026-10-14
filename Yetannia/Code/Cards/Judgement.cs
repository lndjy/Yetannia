using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.ValueProps;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 星光破晓之刻 — 金卡（Rare），1 费能力（敲后[固有]）：
/// 拥有[易伤]的敌人受到的伤害 +25%；拥有[虚弱]的敌人造成的伤害 -15%。
///
/// Name is a placeholder (the request did not give one); the mechanic lives in
/// <see cref="JudgementPower"/>.
/// </summary>
public sealed class Judgement : YetanniaCard
{
    public Judgement()
        : base(1, CardType.Power, CardRarity.Rare, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars => [];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await PowerCmd.Apply<JudgementPower>(
            choiceContext, Owner.Creature, 1m, Owner.Creature, this);
    }

    protected override void OnUpgrade() => AddKeyword(CardKeyword.Innate);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "星光破晓之刻",
        "拥有[gold]易伤[/gold]的敌人受到的伤害增加25%。拥有[gold]虚弱[/gold]的敌人造成的伤害减少15%。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Starlight at Dawn",
        "Enemies with [gold]Vulnerable[/gold] take 25% more damage. Enemies with [gold]Weak[/gold] deal 15% less damage.");
}
