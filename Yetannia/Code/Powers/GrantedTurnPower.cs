using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 未命名·时之礼 挂给目标玩家的「本回合结束时再来一个回合」。
///
/// 额外回合在原版不是命令，而是挂在模型上的两个钩子（见 <c>CombatManager</c> 收尾回合时
/// 询问 <c>Hook.ShouldTakeExtraTurn</c>）：<see cref="ShouldTakeExtraTurn"/> 说「该我了」，
/// 然后 <see cref="AfterTakingExtraTurn"/> 里把这份「欠账」还掉。原版的最小范例是
/// <c>MockExtraTurnPower</c>；这里是一次性的，所以直接 Remove 而不是 Decrement。
///
/// <c>Owner</c> 是**被指定玩家**的生物，所以两个钩子都拿 <c>player == Owner.Player</c> 判定——
/// 这份能力必须挂在他身上，挂在自己身上就变成给自己额外回合了。
/// </summary>
public sealed class GrantedTurnPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    /// <summary>One-shot: a second copy has nothing to add.</summary>
    public override PowerStackType StackType => PowerStackType.Single;

    public override bool ShouldTakeExtraTurn(Player player) => player == Owner?.Player;

    public override async Task AfterTakingExtraTurn(Player player)
    {
        if (player != Owner?.Player) return;

        await PowerCmd.Remove(this);
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/granted_turn.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/granted_turn.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "时之礼",
        "本回合结束时，该角色获得一个额外回合。",
        "本回合结束时，该角色获得一个额外回合。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Gift of Time",
        "At the end of this turn, this character takes an extra turn.",
        "At the end of this turn, this character takes an extra turn.");
}
