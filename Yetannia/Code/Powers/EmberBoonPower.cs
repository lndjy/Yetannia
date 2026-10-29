using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.Factories;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 归途终尽之景 的持续效果 — 被指定的那名角色在本场战斗中每消耗一张牌，就随机生成一张牌加入其手牌。
///
/// 挂在**被指定的玩家**身上（<c>Owner</c> 是那名玩家的生物），所以判归属时用
/// <c>card.Owner == Owner.Player</c>，而生成用的也是那名玩家自己的角色牌池与随机数——
/// 借用同一个 <c>Rng</c> 之外的随机源会让联机下的结果分叉。
///
/// 参考原版「树枝」<c>BurningSticks</c>：同一个 <c>AfterCardExhausted</c> 钩子，
/// 生成后用 <c>CardPileCmd.AddGeneratedCardToCombat</c> 放进那名玩家的手牌。
/// 「不可叠加」靠 <see cref="PowerStackType.Single"/> + 施放前查重（见 <see cref="Cards.EmberBoon"/>），
/// 后者是必需的：Single 只能防止同一枚能力叠层，防不住「基础版和升级版同时存在」。
/// </summary>
public sealed class EmberBoonPower : CustomPowerModel
{
    private bool _upgraded;

    /// <summary>
    /// Whether the generated cards come out upgraded: set by <see cref="Cards.EmberBoon"/> when the copy
    /// of the card that applied this power was upgraded, read on every exhaust.
    ///
    /// Deliberately NOT saved, and not a <c>SavedSpireField</c> either. BaseLib only saves a value whose
    /// *holder* is a card, relic, enchantment or modifier (<c>SavePatchUtils.IsHolderTypeBaseSupported</c>),
    /// and a power is neither one of those nor one of the types <c>ExtendedSaveTypes.RegisterSavedValue</c>
    /// can attach to (cards, relics, potions, enchantments, players, rewards, the run state) — so
    /// <c>[SavedProperty]</c> here was rejected with "will not work on type EmberBoonPower" and a
    /// SavedSpireField would be rejected too. Nothing is lost by that: the game never persists a power's
    /// own state (a power is written to the wire as <c>{id, amount}</c> and nothing else) and never persists
    /// an in-progress combat, so this flag has no save/load to survive. It is per-combat state by
    /// construction; after a load the combat room is rebuilt from scratch and the power only comes back if
    /// the card is played again, which sets this again.
    ///
    /// Set through <see cref="MarkUpgraded"/>, which is called immediately after the power is applied and
    /// so always finds it mutable; anything thrown from here would land in the middle of another card's
    /// exhaust.
    /// </summary>
    private bool Upgraded
    {
        get => _upgraded;
        set
        {
            AssertMutable();
            _upgraded = value;
        }
    }

    public override PowerType Type => PowerType.Buff;

    public override PowerStackType StackType => PowerStackType.Single;

    public void MarkUpgraded() => Upgraded = true;

    public override async Task AfterCardExhausted(
        PlayerChoiceContext choiceContext, CardModel card, bool causedByEthereal)
    {
        var player = Owner?.Player;
        if (player == null) return;
        if (card?.Owner != player) return;

        var pool = player.Character.CardPool
            .GetUnlockedCards(player.UnlockState, player.RunState.CardMultiplayerConstraint)
            .ToList();

        if (pool.Count == 0) return;

        var generated = CardFactory
            .GetForCombat(player, pool, 1, player.RunState.Rng.CombatCardGeneration)
            .FirstOrDefault();

        if (generated == null) return;

        if (_upgraded)
        {
            CardCmd.Upgrade(generated);
        }
        await CardPileCmd.AddGeneratedCardToCombat(generated, PileType.Hand, player);
    }

    public override string? CustomPackedIconPath => ModAssets.Image("powers/ember_boon.png");
    public override string? CustomBigIconPath => ModAssets.Image("powers_big/ember_boon.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "归途终尽之景",
        "本场战斗中，该角色每消耗一张牌，随机生成一张牌加入其手牌。",
        "本场战斗中，该角色每消耗一张牌，随机生成一张牌加入其手牌。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "The View at Journey\u2019s End",
        "This combat, whenever this character exhausts a card, generate a random card into their hand.",
        "This combat, whenever this character exhausts a card, generate a random card into their hand.");
}
