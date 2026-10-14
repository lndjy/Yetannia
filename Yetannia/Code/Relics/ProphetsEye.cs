using BaseLib.Abstracts;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Diagnostics;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// 先知发饰 / Prophet's Hair Ornament — Yetannia's starting relic.
///
/// DISPLAY NAME ONLY. The model id is still <c>YETANNIA-PROPHETS_EYE</c> and the class is still
/// <see cref="ProphetsEye"/>: the id is serialized into saves and is the mount point of every
/// <c>relics</c> loc key, so renaming it would break existing saves and every localization entry.
/// Only the two name strings below (and the comment) changed.
///
/// "战斗开始时，预见5。" (At the start of combat, Scry 5.)
///
/// Relics are <see cref="AbstractModel"/>s and therefore receive combat hooks directly.
/// <see cref="AbstractModel.BeforeHandDraw"/> is the only hook that runs before the opening hand is
/// drawn, which is what "at the start of combat" means here: you scry, then draw. It fires on every
/// turn, so the turn number is checked to keep the effect to the first turn only.
/// </summary>
public sealed class ProphetsEye : YetanniaRelic
{
    private const int ScryAmount = 5;

    public override RelicRarity Rarity => RelicRarity.Starter;

    protected override string IconBaseName => "prophets_eye";

    public override List<(string, string)> Localization =>
        LocManager.Instance?.Language == "eng"
            ? new RelicLoc(
                "Prophet's Hair Ornament",
                $"At the start of combat, Scry {ScryAmount}.",
                "Every strand it settles is a memory that has already happened.")
            : new RelicLoc(
                "先知发饰",
                $"战斗开始时，预见{ScryAmount}。",
                "理清的每一缕，都是已经发生过的记忆。");

    /// <summary>
    /// 战斗开始时（第一回合抽起手牌之前）预见一次。
    /// `Hook.AfterPlayerTurnStart` 整段都发生在 SetupPlayerTurn 的抽牌之后，
    /// 抽牌前能用的钩子是 <see cref="AbstractModel.BeforeHandDraw"/>。
    /// </summary>
    public override async Task BeforeHandDraw(Player player, PlayerChoiceContext choiceContext, ICombatState combatState)
    {
        if (player != Owner) return;
        if (player.Creature.IsDead) return;

        // TurnNumber starts at 1 and increments each of the player's turns, so this is the
        // "first turn of this combat" test — it resets naturally on the next combat.
        if (player.PlayerCombatState?.TurnNumber != 1) return;

        Flash();
        await ScryTrace.Run(nameof(ProphetsEye), choiceContext, player, ScryAmount);
    }

    /// <summary>
    /// 欧罗巴斯（Orobas）的「替换先古遗物」：<c>TouchOfOrobas</c> 会通过 BaseLib 的补丁调用这里，
    /// 把先知发饰换成预见 2 的超越版本（先知头冠）。
    /// </summary>
    public override RelicModel GetUpgradeReplacement() => ModelDb.Relic<ProphetsEyePlus>();
}
