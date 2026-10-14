using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 归途终尽之景 — 金卡，1 费技能，多人专属，指向一名队友。
///
/// 显示名里的「尽」是**用户确认过的错别字修正**（原来写的是「竟」，卡图文件名一直叫
/// 归途终尽之景.png）。只改了下面 <see cref="Chinese"/> 里的显示字符串；类名、命名空间、
/// 模型 id（YETANNIA-EMBER_BOON）与本地化键都保持不变——id 会写进存档。
///
/// 该角色本场战斗中每消耗一张牌，随机生成一张牌加入其手牌；敲后生成的是已升级的牌。
/// 「不可叠加」在这里落实：施放前先看目标身上有没有 <see cref="EmberBoonPower"/>，
/// 有就什么都不做——只靠能力的 Single 叠层类型挡不住「基础版与升级版各挂一个」。
/// </summary>
public sealed class EmberBoon : YetanniaCard
{
    public EmberBoon()
        : base(1, CardType.Skill, CardRarity.Rare, TargetType.AnyAlly)
    {
    }

    public override CardMultiplayerConstraint MultiplayerConstraint =>
        CardMultiplayerConstraint.MultiplayerOnly;

    /// <summary>
    /// 消耗. Declared here and NOT repeated in the description: the card face appends keyword text
    /// itself, so writing 消耗 into the loc string as well renders it twice (see 天之恩典).
    /// </summary>
    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var target = cardPlay.Target;
        if (target == null) return;

        if (target.GetPower<EmberBoonPower>() != null) return;

        var power = await PowerCmd.Apply<EmberBoonPower>(
            choiceContext, target, 1, Owner.Creature, this);

        if (power != null && IsUpgraded)
        {
            power.MarkUpgraded();
        }
    }

    /// <summary>Nothing numeric changes; the upgrade is passed to the power at play time.</summary>
    protected override void OnUpgrade()
    {
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "归途终尽之景",
        "选择一名队友。本场战斗中，该角色每消耗一张牌，随机生成一张{IfUpgraded:show:已升级的|}牌加入其手牌。此效果不可叠加。");

    private static readonly List<(string, string)> English = new CardLoc(
        "The View at Journey\u2019s End",
        "Choose a teammate. This combat, whenever they exhaust a card, generate a random {IfUpgraded:show:upgraded |}card into their hand. Does not stack.");
}
