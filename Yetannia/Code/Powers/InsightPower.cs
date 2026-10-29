using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Diagnostics;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 她眼中的世界 的能力：每回合第一次打出攻击牌获得 1 费，第一次打出技能牌抽 1 张，
/// 第一次打出能力牌预见 2。三个「第一次」分别追踪，玩家回合开始时重置。
/// </summary>
public sealed class InsightPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    private bool _attackDone;
    private bool _skillDone;
    private bool _powerDone;

    public override async Task AfterCardPlayed(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        if (cardPlay.Player != Owner.Player) return;

        switch (cardPlay.Card.Type)
        {
            case CardType.Attack when !_attackDone:
                _attackDone = true;
                await PlayerCmd.GainEnergy(1, Owner.Player);
                break;
            case CardType.Skill when !_skillDone:
                _skillDone = true;
                await CardPileCmd.Draw(choiceContext, 1, Owner.Player);
                break;
            case CardType.Power when !_powerDone:
                _powerDone = true;
                await ScryTrace.Run(GetType().Name, choiceContext, Owner.Player, 2);
                break;
        }
    }

    public override Task AfterPlayerTurnStart(PlayerChoiceContext choiceContext, Player player)
    {
        if (player == Owner.Player)
        {
            _attackDone = false;
            _skillDone = false;
            _powerDone = false;
        }
        return Task.CompletedTask;
    }
    public override string? CustomPackedIconPath => ModAssets.Image("powers/insight.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/insight.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "她眼中的世界",
        "每回合第一次打出攻击牌时，获得" + Loc.EnergyIcon + "；第一次打出技能牌时，抽1张牌；第一次打出能力牌时，预见2。",
        "每回合第一次打出攻击牌时，获得" + Loc.EnergyIcon + "；第一次打出技能牌时，抽1张牌；第一次打出能力牌时，预见2。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "The World in Her Eyes",
        "Each turn, the first Attack you play grants " + Loc.EnergyIcon + "; the first Skill you play draws 1 card; the first Power you play Scries 2.",
        "Each turn, the first Attack you play grants " + Loc.EnergyIcon + "; the first Skill you play draws 1 card; the first Power you play Scries 2.");
}
