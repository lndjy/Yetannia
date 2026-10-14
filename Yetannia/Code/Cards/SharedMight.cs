using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 回应愿景之心 — 蓝卡（Uncommon），1 费能力，多人专属，指定一名队友（敲后[固有]）：
/// 当你获得力量和敏捷时，该队友获得等量力量和敏捷。
///
/// Name is a placeholder (the request did not give one). Mirrors 薪火's target-a-teammate pattern.
/// </summary>
public sealed class SharedMight : YetanniaCard
{
    public SharedMight()
        : base(1, CardType.Power, CardRarity.Uncommon, TargetType.AnyAlly)
    {
    }

    public override CardMultiplayerConstraint MultiplayerConstraint =>
        CardMultiplayerConstraint.MultiplayerOnly;

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var target = cardPlay.Target;
        if (target == null) return;

        var power = await PowerCmd.Apply<SharedMightPower>(
            choiceContext, target, 1, Owner.Creature, this);

        power?.SetSource(Owner.Creature, this);
    }

    /// <summary>敲后：[固有]。</summary>
    protected override void OnUpgrade() => AddKeyword(CardKeyword.Innate);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "回应愿景之心",
        "选择一名队友。本场战斗中，当你获得[gold]力量[/gold]和[gold]敏捷[/gold]时（不因此牌），其获得等量[gold]力量[/gold]和[gold]敏捷[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Heart Answering a Vision",
        "Choose a teammate. This combat, whenever you gain [gold]Strength[/gold] or [gold]Dexterity[/gold] (not from this card), they gain the same amount.");
}
