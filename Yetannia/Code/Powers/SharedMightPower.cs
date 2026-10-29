using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;
using Yetannia.YetanniaCode.Cards;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 回应愿景之心 的能力，挂在**目标队友**身上：当来源（打出这张牌的玩家）获得力量/敏捷时，
/// 目标也获得等量。
///
/// 「不因此牌」：反射时把 <c>cardSource</c> 换成共感牌本身，并在入口判断
/// <c>cardSource is SharedMight</c> 直接跳过——这样两侧都挂共感时不会互相反射叠成无限。
/// </summary>
public sealed class SharedMightPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    private Creature? _source;
    private CardModel? _cardSource;

    public void SetSource(Creature source, CardModel cardSource)
    {
        _source = source;
        _cardSource = cardSource;
    }

    public override async Task AfterPowerAmountChanged(
        PlayerChoiceContext choiceContext, PowerModel power, decimal amount, Creature? applier, CardModel? cardSource)
    {
        if (_source == null) return;
        if (amount <= 0) return;
        if (cardSource is SharedMight) return; // 不因此牌
        if (!ReferenceEquals(power.Owner, _source)) return;

        if (power is StrengthPower)
        {
            await PowerCmd.Apply<StrengthPower>(choiceContext, Owner, amount, applier, _cardSource);
        }
        else if (power is DexterityPower)
        {
            await PowerCmd.Apply<DexterityPower>(choiceContext, Owner, amount, applier, _cardSource);
        }
    }
    public override string? CustomPackedIconPath => ModAssets.Image("powers/shared_might.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/shared_might.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "回应愿景之心",
        "本场战斗中，当你获得[gold]力量[/gold]或[gold]敏捷[/gold]时（不因此牌），该角色获得等量的[gold]力量[/gold]或[gold]敏捷[/gold]。",
        "本场战斗中，当你获得[gold]力量[/gold]或[gold]敏捷[/gold]时（不因此牌），该角色获得等量的[gold]力量[/gold]或[gold]敏捷[/gold]。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Heart Answering a Vision",
        "This combat, whenever you gain [gold]Strength[/gold] or [gold]Dexterity[/gold] from another source, they gain the same amount of it.",
        "This combat, whenever you gain [gold]Strength[/gold] or [gold]Dexterity[/gold] from another source, they gain the same amount of it.");
}
