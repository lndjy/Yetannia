using BaseLib.Abstracts;
using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Unlocks;
using Yetannia.YetanniaCode.Character;

namespace Yetannia.YetanniaCode.Character;

/// <summary>
/// Yetannia's card pool. Every card in this mod is attached to it via <c>[Pool]</c>.
/// </summary>
public class YetanniaCardPool : CustomCardPoolModel
{
    /// <summary>
    /// 状态牌（纯爱幻想/幻想纯爱）跟原版状态牌一样不进牌池：不出现于奖励、商店和卡牌图鉴。
    ///
    /// 在 <c>FilterThroughEpochs</c>（即 <c>GetUnlockedCards</c> 的入口）里过滤，而不是 <c>AllCards</c>：
    /// <c>CardModel.Pool</c> 靠 <c>AllCards</c>/<c>AllCardIds</c> 反查所属牌池，过滤掉它们会让「生成状态牌」
    /// 抛 "Card ... is not in any card pool!" 并把战斗卡死（转化 → 生成纯爱幻想 的报错）。
    /// </summary>
    protected override IEnumerable<CardModel> FilterThroughEpochs(UnlockState unlockState, IEnumerable<CardModel> cards)
        => base.FilterThroughEpochs(unlockState, cards).Where(c => c.Rarity != CardRarity.Status);

    /// <summary>Not a display name; used when resolving pooled card art.</summary>
    public override string Title => YetanniaCharacter.PoolTitle;

    /// <summary>
    /// Yetannia's own 能量 orb, shipped in the pck as 256×256 (BigEnergyIconPath) and 64×64
    /// (TextEnergyIconPath). Both are only consulted while <c>EnergyColorName</c> keeps the marker that
    /// BaseLib's energy-icon patches decode — see the note below.
    /// </summary>
    public override string? BigEnergyIconPath => ModAssets.Image("ui/energy_yetannia.png");

    public override string? TextEnergyIconPath => ModAssets.Image("ui/energy_yetannia_small.png");
    // EnergyColorName is deliberately NOT overridden any more.
    //
    // BaseLib routes custom energy art through that property: its default (CustomCardPoolModel)
    // returns an id encoded as "CATEGORY∴ENTRY", and BaseLib patches
    // EnergyIconHelper.GetPath and the EnergyIconsFormatter to decode that marker and substitute
    // BigEnergyIconPath / TextEnergyIconPath. The old override pinned the name to the vanilla
    // "colorless" orb, which carries no marker, so those patches fell through to the base game
    // texture and the two paths above were never consulted.

    // Leave CardFrameMaterialPath at its default ("card_frame_red") so BaseLib generates a
    // hue-shifted frame material from the HSV values below instead of needing a custom frame texture.
    public override float H => 0.75f; // purple
    public override float S => 0.45f;
    public override float V => 1.00f;

    public override Color DeckEntryCardColor => new("9b6bff");

    public override bool IsColorless => false;
}
