using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Factories;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 先知的指引 — 金卡，1 费技能，多人专属。
///
/// 从三张随机能力牌中选一张加入手牌并本回合免费打出；敲后那三张是已升级的。
/// 然后**这张牌本身**进入随机一名队友的弃牌堆。
///
/// 两半分别照搬原版的两张多人牌：
/// - 「选一张、免费、入手」= 富足 <c>Abundance</c>（<c>CardFactory.GetDistinctForCombat</c> →
///   <c>CardSelectCmd.FromChooseACardScreen</c> → <c>SetToFreeThisTurn</c> →
///   <c>CardPileCmd.AddGeneratedCardToCombat</c>）。敲后升级选项也是它的做法。
/// - 「打完之后去别人那儿」= 魔球 <c>TheBall</c> 覆写 <c>GetResultLocationForCardPlay</c>。
///   魔球是把牌送去队友的抽牌堆，这里按需求改成弃牌堆。
/// </summary>
public sealed class GuidanceOfTheProphet : YetanniaCard
{
    private const int Choices = 3;

    public GuidanceOfTheProphet()
        : base(1, CardType.Skill, CardRarity.Rare, TargetType.Self)
    {
    }

    public override CardMultiplayerConstraint MultiplayerConstraint =>
        CardMultiplayerConstraint.MultiplayerOnly;

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var pool = Owner.Character.CardPool
            .GetUnlockedCards(Owner.UnlockState, Owner.RunState.CardMultiplayerConstraint)
            .Where(c => c.Type == CardType.Power)
            .ToList();

        if (pool.Count == 0) return;

        var options = CardFactory
            .GetDistinctForCombat(Owner, pool, Choices, Owner.RunState.Rng.CombatCardGeneration)
            .ToList();

        if (options.Count == 0) return;

        if (IsUpgraded)
        {
            foreach (var option in options)
            {
                CardCmd.Upgrade(option);
            }
        }

        var chosen = await CardSelectCmd.FromChooseACardScreen(choiceContext, options, Owner);
        if (chosen == null) return;

        chosen.SetToFreeThisTurn();
        await CardPileCmd.AddGeneratedCardToCombat(chosen, PileType.Hand, Owner);
    }

    /// <summary>
    /// Sends the played copy to a random teammate's discard pile instead of the owner's.
    ///
    /// Returns the untouched location in singleplayer (no other players) — the card is marked
    /// multiplayer-only, but the gallery and the dev console can still create it outside a real
    /// multiplayer run, and it must not crash there.
    /// </summary>
    protected override CardLocation GetResultLocationForCardPlay()
    {
        var location = base.GetResultLocationForCardPlay();

        var combatState = Owner?.Creature?.CombatState;
        if (combatState == null) return location;

        var teammates = combatState.GetTeammatesOf(Owner.Creature)
            .Where(c => c != null && c.IsAlive && c.IsPlayer && c.Player != Owner)
            .ToList();

        if (teammates.Count == 0) return location;

        location.player = Owner.RunState.Rng.CombatTargets.NextItem(teammates).Player;
        location.pileType = PileType.Discard;
        location.position = CardPilePosition.Random;
        return location;
    }

    /// <summary>Nothing numeric changes; the upgrade is read from <see cref="CardModel.IsUpgraded"/>.</summary>
    protected override void OnUpgrade()
    {
    }

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "先知的指引",
        "从三张随机{IfUpgraded:show:已升级的|}能力牌中选择一张加入手牌，本回合免费打出。\n将此牌放入随机一名队友的弃牌堆。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Prophet's Guidance",
        "Choose 1 of 3 random {IfUpgraded:show:upgraded |}Power cards to add to your hand and play for free this turn.\nPut this card into a random teammate's discard pile.");
}
