using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>未命名·焚灭 的能力：每当你消耗一张牌，对所有敌人造成 3（升级 4）点伤害。</summary>
public sealed class ExhaustBlastPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    /// <summary>
    /// Counter, not Single: the icon label is only filled in for Counter powers
    /// (<c>NPower.RefreshAmount</c> writes <c>DisplayAmount</c> alone otherwise), so a Single power
    /// showed the literal “X” from its text forever. The stack amount itself is never read here.
    /// </summary>
    public override PowerStackType StackType => PowerStackType.Counter;

    private int _damage = 3;
    private CardModel? _cardSource;

    /// <summary>The real damage, so the icon shows 3 or 4 rather than the amount the card applied (1).</summary>
    public override int DisplayAmount => _damage;

    public void MarkValues(CardModel cardSource, int damage)
    {
        _cardSource = cardSource;
        _damage = damage;
        InvokeDisplayAmountChanged();
    }

    public override async Task AfterCardExhausted(PlayerChoiceContext choiceContext, CardModel card, bool causedByEthereal)
    {
        if (card.Owner != Owner.Player) return;
        if (_cardSource == null) return;

        await DamageCmd.Attack(_damage)
            .FromCard(_cardSource, null)
            .TargetingAllOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }
    public override string? CustomPackedIconPath => ModAssets.Image("powers/exhaust_blast.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/exhaust_blast.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "未命名·焚灭",
        "每当你消耗一张牌，对所有敌人造成 X 点伤害。",
        "每当你消耗一张牌，对所有敌人造成 X 点伤害。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Unnamed (Immolate)",
        "Whenever you exhaust a card, deal X damage to ALL enemies.",
        "Whenever you exhaust a card, deal X damage to ALL enemies.");
}
