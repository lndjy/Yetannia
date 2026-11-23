using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Events;
using MegaCrit.Sts2.Core.Factories;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Acts;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Events;

/// <summary>
/// 事件「调和仪式」（v1.1.0 新增，**第三层限定**，且只有所有玩家都带着「非永恒诅咒牌」时才会出现）。
///
/// Three design decisions worth writing down, because they are the difference between "works in a test
/// harness" and "works in a real run":
///
/// 1. <b>三层限定 via <see cref="Acts"/>, not only <see cref="IsAllowed"/>.</b> BaseLib inserts
///    act-attached custom events into that act's event pool; keeping the act check in
///    <see cref="IsAllowed"/> as well means a save loaded from another act still refuses it.
/// 2. <b>All players must carry a non-Eternal curse.</b> The option set is built from
///    <c>Owner.Deck</c>, which in co-op is only the local player's deck — so the gate has to look at
///    every player's deck, otherwise a client with no curses would open an event whose left option
///    silently does nothing.
/// 3. <b>Option 2 scales with the number of curses in the deck</b>: for every curse card, two random
///    upgraded cards are added to the deck. The cards are created from the player's own card pool with
///    the game's quiet-event options (<c>NoUpgradeRoll</c>) and then upgraded explicitly, so the result is
///    "upgraded" deterministically rather than "has a chance to be upgraded".
///
/// UI convention (vanilla): each option's small description is the mechanical EFFECT; the story
/// narration belongs to the page shown after the choice, together with the concrete outcome.
/// </summary>
public sealed class RitualOfHarmony : CustomEventModel
{
    /// <summary>Base game's third act.</summary>
    public override ActModel[] Acts => new[] { ModelDb.Act<Glory>() };

    public override string CustomInitialPortraitPath => ModAssets.Image("events/ritual_of_harmony.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    public override bool IsAllowed(IRunState runState)
    {
        if (runState == null) return false;
        if (runState.CurrentActIndex != 2) return false;
        return runState.Players.All(player => NonEternalCurses(player).Any());
    }

    protected override IReadOnlyList<EventOption> GenerateInitialOptions()
    {
        var hpLoss = CurrentHpLoss(Owner);

        return new[]
        {
            Option(
                    WalkIntoOrder,
                    L10NLookup(Id.Entry + ".pages.INITIAL.options.ORDER.title"),
                    L10NLookup(Id.Entry + ".pages.INITIAL.options.ORDER.description"))
                .ThatDoesDamage(hpLoss),
            Option(
                WalkIntoChaos,
                L10NLookup(Id.Entry + ".pages.INITIAL.options.CHAOS.title"),
                L10NLookup(Id.Entry + ".pages.INITIAL.options.CHAOS.description")),
        };
    }

    /// <summary>选项1（左侧·秩序）：移除随机一张非永恒诅咒牌，失去 10% 当前生命。</summary>
    private async Task WalkIntoOrder()
    {
        var owner = Owner;
        if (owner == null) return;

        var curses = NonEternalCurses(owner).ToList();
        if (curses.Count > 0)
        {
            var curse = Rng.NextItem(curses);
            await CardPileCmd.RemoveFromDeck(curse);
        }

        var hpLoss = CurrentHpLoss(owner);
        if (hpLoss > 0m)
        {
            var damage = new DamageVar("RitualHpLoss", hpLoss, ValueProp.Unblockable | ValueProp.Unpowered);
            await CreatureCmd.Damage(
                new ThrowingPlayerChoiceContext(), owner.Creature, damage, null, null, null);
        }

        SetEventFinished(L10NLookup(Id.Entry + ".pages.ORDER.description"));
    }

    /// <summary>选项2（右侧·混乱）：你每有一张诅咒牌，向卡组加入两张随机升级过的卡牌。</summary>
    private async Task WalkIntoChaos()
    {
        var owner = Owner;
        if (owner == null) return;

        var curseCount = owner.Deck.Cards.Count(card => card.Type == CardType.Curse);
        var cardCount = curseCount * 2;

        var result = L10NLookup(Id.Entry + ".pages.CHAOS.description");
        result.Add("Cards", cardCount);

        if (cardCount > 0)
        {
            // Quiet event generation: no upgrade roll, the explicit Upgrade below is the upgrade.
            var options = CardCreationOptions.ForNonCombatWithDefaultOdds(new[] { owner.Character.CardPool });
            var created = CardFactory.CreateForReward(owner, cardCount, options)
                .Select(creation => creation.Card)
                .Where(card => card != null)
                .ToList();

            foreach (var card in created)
            {
                CardCmd.Upgrade(card, CardPreviewStyle.None);
            }

            if (created.Count > 0)
            {
                await CardPileCmd.Add(created, PileType.Deck);
            }
        }

        SetEventFinished(result);
    }

    /// <summary>“失去 10% 当前生命”：向上取整且至少 1 点，避免低血量时四舍五入成 0 失去意义。</summary>
    private static decimal CurrentHpLoss(Player player)
    {
        if (player == null) return 0m;
        var currentHp = player.Creature?.CurrentHp ?? 0m;
        if (currentHp <= 0m) return 0m;
        return Math.Max(1m, Math.Ceiling(currentHp * 0.1m));
    }

    private static IEnumerable<CardModel> NonEternalCurses(Player player)
    {
        return (player?.Deck?.Cards ?? Enumerable.Empty<CardModel>())
            .Where(card => card.Type == CardType.Curse && !card.Keywords.Contains(CardKeyword.Eternal));
    }

    private static readonly EventLoc Chinese = new(
        "调和仪式",
        new EventPageLoc(
            "INITIAL",
            "眼前是一个仪式台——秩序与混乱的能量在左右两侧翻涌。\n" +
            "左侧的秩序能量会净化你们的诅咒，\n" +
            "而右侧的混乱能量会发生什么呢？\n" +
            "若是使用的话，只需要走向中间的魔法阵启动对应的能量就好了……",
            new EventOptionLoc(
                "ORDER",
                "走入左侧的秩序能量",
                "移除随机一张非永恒诅咒牌，失去 10% 当前生命。"),
            new EventOptionLoc(
                "CHAOS",
                "走入右侧的混乱能量",
                "你每有一张诅咒牌，向牌组加入两张随机升级过的卡牌。")),
        new EventPageLoc(
            "ORDER",
            "你将身躯张开，拥抱着逐渐开始凝聚在你周围的秩序能量。\n" +
            "神圣而闪耀的蓝金色光芒在你的周围和体内狂涌……\n" +
            "在一阵阵身体和灵魂上的疼痛后，那股挥之不去的诅咒消失了。\n" +
            "凡事都有代价，不是吗？\n" +
            "蓝金色的光缓缓散去，刺痛也随之消退。诅咒被净化了，而你付给仪式的代价已经融入了骨血。\n" +
            "秩序从不多取，也从不白白给予。\n" +
            "（随机移除一张非永恒诅咒牌，失去 10% 当前生命）"),
        new EventPageLoc(
            "CHAOS",
            "在你刚踏入其中的瞬间，一股阴冷的黑色气息包裹住了你。\n" +
            "它搂住你的脖颈，缠绕在你的身上，让你几乎要窒息。\n" +
            "但好在，最后你凭借顽强的体魄和意志抗住了它的\u201c祝福\u201d。\n" +
            "你身上的诅咒反而化身成了某种偏斜的力量为你所用。\n" +
            "拥抱苦痛何尝不是一种选择？\n" +
            "黑色的气息沉入你的影子里，那些诅咒化作了偏斜的力量，扭曲成你能够驾驭的形态。\n" +
            "{Cards}张升级过的卡牌被这份力量牵引，加入了你的卡组。"));

    private static readonly EventLoc English = new(
        "Ritual of Harmony",
        new EventPageLoc(
            "INITIAL",
            "Before you is a ritual dais — orderly and chaotic energies churn on either side.\n" +
            "The order on the left will cleanse your curses,\n" +
            "but what will the chaos on the right do?\n" +
            "To use it, you need only step into the sigil in the middle and wake the corresponding energy...",
            new EventOptionLoc(
                "ORDER",
                "Walk into the order energy",
                "Remove a random non-Eternal curse and lose 10% of your current HP."),
            new EventOptionLoc(
                "CHAOS",
                "Walk into the chaos energy",
                "For each curse in your deck, add two random upgraded cards to it.")),
        new EventPageLoc(
            "ORDER",
            "You open your arms and embrace the order gathering around you.\n" +
            "Holy, shining blue-gold light floods through you and around you...\n" +
            "After waves of pain in body and soul, the lingering curse is gone.\n" +
            "Everything has its price, doesn't it?\n" +
            "The blue-gold light fades, and the stinging goes with it. The curses are cleansed; the price the ritual took is already in your bones.\n" +
            "Order never takes more than it is owed, and never gives for free.\n" +
            "(Remove a random non-Eternal curse and lose 10% of your current HP.)"),
        new EventPageLoc(
            "CHAOS",
            "The instant you step in, a cold, shadowy breath wraps around you.\n" +
            "It takes your neck, coils around your body, and nearly chokes you.\n" +
            "But in the end your body and will endure its \u201cblessing\u201d.\n" +
            "The curses warp into a crooked strength you can wield.\n" +
            "Embracing pain is itself a choice, isn't it?\n" +
            "The dark breath sinks into your shadow. Your curses twist into a crooked strength, deformed into a shape you can hold.\n" +
            "{Cards} upgraded cards are drawn in by that strength and join your deck."));
}
