using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Relics;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// 希楠之约 — 普通遗物（v1.1.0 新增）：每当你消耗一张状态牌，获得 2 点格挡。
///
/// The trigger is the game's own combat hook <c>AfterCardExhausted</c>, the same one vanilla exhaust
/// relics use, so "exhausted" means exactly what the game means by it (played exhaust cards, Ethereal
/// burns, status cards burned by effects, and so on). Only <see cref="CardType.Status"/> cards count;
/// curses and normal exhausted cards do not.
///
/// The block is granted with <see cref="ValueProp.Unpowered"/> on purpose: it is relic block, not card
/// block, so it must not be scaled by the player's Dexterity — that is the same convention vanilla
/// relics such as Orichalcum follow.
/// </summary>
public sealed class XinansPact : YetanniaRelic
{
    private const int BlockGain = 2;

    public override RelicRarity Rarity => RelicRarity.Common;

    protected override string IconBaseName => "xinans_pact";

    public override async Task AfterCardExhausted(
        PlayerChoiceContext choiceContext, CardModel card, bool causedByEthereal)
    {
        if (card == null || card.Type != CardType.Status) return;
        if (Owner == null) return;

        // “每当**你**消耗一张状态牌” — another player's status leaving play must not give us block.
        // (In co-op every peer walks the same hook list, so this filter is what keeps the owner's relic
        // from reacting to a teammate's exhaust.)
        if (card.Owner != Owner) return;

        Flash();
        await CreatureCmd.GainBlock(Owner.Creature, BlockGain, ValueProp.Unpowered, null);
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new RelicLoc(
        "希楠之约",
        $"每当你消耗一张状态牌，获得{BlockGain}点格挡。",
        "以旧日的名字立下的小小约定，疼痛也愿替你挡下一部分。");

    private static readonly List<(string, string)> English = new RelicLoc(
        "Xinan's Pact",
        $"Whenever you Exhaust a Status card, gain {BlockGain} Block.",
        "A small promise made in an old name — it will take a share of the pain for you.");
}
