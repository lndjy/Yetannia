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
/// 未命名·共感 的能力，挂在**目标队友**身上：当来源（打出这张牌的玩家）获得力量/敏捷时，
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
        "未命名·共感",
        "本场战斗中，当你获得力量和敏捷时（不因此牌），该角色获得等量力量和敏捷。",
        "本场战斗中，当你获得力量和敏捷时（不因此牌），该角色获得等量力量和敏捷。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Unnamed (Resonance)",
        "This combat, whenever you gain Strength or Dexterity (not from this card), they gain the same amount.",
        "This combat, whenever you gain Strength or Dexterity (not from this card), they gain the same amount.");
}
