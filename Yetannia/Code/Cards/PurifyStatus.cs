using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>趁势而动 — 蓝卡（Uncommon），1 费能力：每回合你抽到状态牌的前 1（升级 2）次，将它消耗。</summary>
public sealed class PurifyStatus : YetanniaCard
{
    public PurifyStatus()
        : base(1, CardType.Power, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var power = await PowerCmd.Apply<PurifyStatusPower>(
            choiceContext, Owner.Creature, 1, Owner.Creature, this);
        if (power != null && IsUpgraded) power.MarkUpgraded();
    }

    protected override void OnUpgrade()
    {
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "趁势而动", "每回合你抽到状态牌的前{IfUpgraded:show:2|1}次，将它消耗。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Seize the Moment", "The first {IfUpgraded:show:2|1} time(s) you draw a Status card each turn, exhaust it.");
}
