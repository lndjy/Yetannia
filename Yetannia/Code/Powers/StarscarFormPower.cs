using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 星痕化 的延时结算：在下个回合开始时给玩家 1 层<see cref="IntangiblePower">无实体</see>，然后自己移除。
///
/// 卡面写的是「下个回合获得」，所以无实体不能在打出时立刻生效——本能力只是把这件事挂到下一个回合开始。
/// <see cref="IntangiblePower"/> 自己会在回合结束时按层数退掉，所以给 1 层即「下个回合有 1 层」。
///
/// Visible on purpose: it is the only sign the player has that a delayed 无实体 is pending. The icon is
/// temporarily the same art as 未命名·额外回合 (both are "something happens next turn"); swapping it for
/// its own art is a one-line change once that art exists.
/// </summary>
public sealed class StarscarFormPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    /// <summary>Not a stacking buff — playing the card twice is still one pending 无实体 per turn.</summary>
    public override PowerStackType StackType => PowerStackType.Single;

    public override async Task AfterPlayerTurnStart(PlayerChoiceContext choiceContext, Player player)
    {
        if (player != Owner.Player) return;

        // Removed before granting, so a nested dispatch cannot pay this out twice.
        await PowerCmd.Remove(this);
        await PowerCmd.Apply<IntangiblePower>(choiceContext, Owner, 1m, Owner, null);
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/starscar_form.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/starscar_form.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "星痕化",
        "下个回合开始时，获得1层[gold]无实体[/gold]。",
        "下个回合开始时，获得1层[gold]无实体[/gold]。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Starscar Form",
        "At the start of your next turn, gain 1 [gold]Intangible[/gold].",
        "At the start of your next turn, gain 1 [gold]Intangible[/gold].");
}
