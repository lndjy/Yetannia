using BaseLib.Abstracts;
using BaseLib.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Character;
using Yetannia.YetanniaCode.Diagnostics;
using Yetannia.YetanniaCode.Relics;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// 先知头冠 / Prophet's Crown — 欧罗巴斯（Orobas）的「替换先古遗物」版本，即先知发饰的先古形态。
///
/// DISPLAY NAME ONLY, exactly as with <see cref="ProphetsEye"/>: the model id is still
/// <c>YETANNIA-PROPHETS_EYE_PLUS</c> and the class is still <see cref="ProphetsEyePlus"/>, because the
/// id is serialized into saves and drives every <c>relics</c> loc key.
///
/// 它通过 <see cref="CustomRelicModel.GetUpgradeReplacement"/> 接到游戏的
/// <c>TouchOfOrobas.GetUpgradedStarterRelic</c> 上：当玩家在欧罗巴斯处选择替换初始遗物时，
/// 先知发饰会变成这一枚，把「战斗开始时，预见5」升级为「预见10」。
/// </summary>
public sealed class ProphetsEyePlus : YetanniaRelic
{
    private const int ScryAmount = 10;

    public override RelicRarity Rarity => RelicRarity.Starter;

    protected override string IconBaseName => "prophets_eye_plus";

    public override List<(string, string)> Localization =>
        LocManager.Instance?.Language == "eng"
            ? new RelicLoc(
                "Prophet's Crown",
                $"At the start of combat, Scry {ScryAmount}.",
                "Worn, it makes even the unwritten page legible.")
            : new RelicLoc(
                "先知头冠",
                $"战斗开始时，预见{ScryAmount}。",
                "戴上它，尚未写下的那一页也清晰可见。");

    /// <summary>战斗开始时（第一回合抽起手牌之前）预见一次，理由同 <see cref="ProphetsEye"/>。</summary>
    public override async Task BeforeHandDraw(Player player, PlayerChoiceContext choiceContext, ICombatState combatState)
    {
        if (player != Owner) return;
        if (player.Creature.IsDead) return;
        if (player.PlayerCombatState?.TurnNumber != 1) return;

        Flash();
        await ScryTrace.Run(nameof(ProphetsEyePlus), choiceContext, player, ScryAmount);
    }
}
