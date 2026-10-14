using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>未命名·续行 的能力：当你消耗一张状态牌时，抽一张牌。</summary>
public sealed class StatusDrawPower : CustomPowerModel
{
    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    public override async Task AfterCardExhausted(PlayerChoiceContext choiceContext, CardModel card, bool causedByEthereal)
    {
        if (card.Owner != Owner.Player) return;
        if (card.Rarity != CardRarity.Status) return;

        await CardPileCmd.Draw(choiceContext, 1, Owner.Player);
    }
    public override string? CustomPackedIconPath => ModAssets.Image("powers/status_draw.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/status_draw.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "未命名·续行",
        "当你消耗一张状态牌时，抽一张牌。",
        "当你消耗一张状态牌时，抽一张牌。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Unnamed (Continuance)",
        "Whenever you exhaust a Status card, draw 1 card.",
        "Whenever you exhaust a Status card, draw 1 card.");
}
