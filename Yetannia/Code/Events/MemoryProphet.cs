using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Events;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Relics;

namespace Yetannia.YetanniaCode.Events;

/// <summary>
/// 事件「记忆先知」（v1.1.0 新增，共享事件，任意层都可能遇到）。
///
/// A hooded stranger with a glimpse of blue hair offers two things: take the player's memories and
/// hand over <see cref="ProphetsBracelet"/> (whose normal relic-pool roll was removed in the same
/// version, so this event is now its only source), or accept a prayer and hand over 50 gold.
///
/// UI convention: each option's small description says what the choice DOES (vanilla style), while the
/// story narration lives on the page shown after the choice. So the initial page carries the scene and
/// the two one-line effects, and each result page carries the full narrative plus the concrete outcome.
/// </summary>
public sealed class MemoryProphet : CustomEventModel
{
    private const int GoldReward = 50;

    public override string CustomInitialPortraitPath => ModAssets.Image("events/memory_prophet.png");

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    protected override IReadOnlyList<EventOption> GenerateInitialOptions()
    {
        return new[]
        {
            Option(
                OfferMemory,
                L10NLookup(Id.Entry + ".pages.INITIAL.options.MEMORY.title"),
                L10NLookup(Id.Entry + ".pages.INITIAL.options.MEMORY.description")),
            Option(
                OfferPrayer,
                L10NLookup(Id.Entry + ".pages.INITIAL.options.PRAY.title"),
                L10NLookup(Id.Entry + ".pages.INITIAL.options.PRAY.description")),
        };
    }

    /// <summary>选项1：献上自己的记忆 → 获得事件遗物「先知的手链」。</summary>
    private async Task OfferMemory()
    {
        var owner = Owner;
        if (owner == null) return;

        await RelicCmd.Obtain(ModelDb.Relic<ProphetsBracelet>().ToMutable(), owner);
        SetEventFinished(L10NLookup(Id.Entry + ".pages.MEMORY.description"));
    }

    /// <summary>选项2：在先知周围祈祷 → 获得 50 金币。</summary>
    private async Task OfferPrayer()
    {
        var owner = Owner;
        if (owner == null) return;

        await PlayerCmd.GainGold(GoldReward, owner);
        SetEventFinished(L10NLookup(Id.Entry + ".pages.PRAY.description"));
    }

    private static readonly EventLoc Chinese = new(
        "记忆先知",
        new EventPageLoc(
            "INITIAL",
            "你们看到了一个披着斗篷的陌生人，从这里看不到它的脸，只能隐约看到一抹蓝色的头发。\n" +
            "\u201c来吧，到我这来吧……\u201d一个有些空灵而苍白的女声说道。\n" +
            "\u201c献上你/你们的记忆，我将给予你应得之物……\u201d\n" +
            "\u201c抑或是献上祈祷，我将给予你应许之物……\u201d\n" +
            "话音到这里便戛然而止了，那位先知没再多说什么，而是继续低下头，双手抚摸着她的斗篷。",
            new EventOptionLoc("MEMORY", "献上自己的记忆", "获得遗物「先知的手链」。"),
            new EventOptionLoc("PRAY", "在先知周围进行祈祷", $"获得 {GoldReward} 金币。")),
        new EventPageLoc(
            "MEMORY",
            "你开始回想起曾经的记忆——幸福的，苦痛的，仇恨的，难以忘怀的……" +
            "先知张开手，将那些记忆一一记录下来。\n" +
            "你感到那些记忆像是活了过来一样开始充斥在你的眼前和脑海之中，来回变换，让你有些眩晕感。\n" +
            "\u201c好了，就这样吧。\u201d\n" +
            "在你有些撑不住的前一瞬间，这种感觉顿时戛然而止，那些活灵活现的记忆也都消失了，再一次回到了你的心中。\n" +
            "\u201c收下这个吧……希望它能让你的记忆多一些快乐。\u201d先知说完便沉默了，没再继续搭理你/你们。\n" +
            "（获得遗物：先知的手链）"),
        new EventPageLoc(
            "PRAY",
            "你静默地在先知周围进行祈祷，在你持续祈祷的瞬间，你好像听到了其他人的祈祷的声音同样夹杂在你的脑海中。\n" +
            "\u201c它们都是我曾经的朋友……\u201d先知呢喃着，仿佛对这一现象并不奇怪。\n" +
            "在你祷告结束后，那些声音也一同消失了。\n" +
            "\u201c如此，希望这些经费能助你一臂之力。\u201d\n" +
            "\u201c简单而高效，对吧？呵呵呵……\u201d先知没再搭理你/你们，而是自己一个人笑了起来。\n" +
            $"（获得 {GoldReward} 金币）"));

    private static readonly EventLoc English = new(
        "Memory Prophet",
        new EventPageLoc(
            "INITIAL",
            "You see a hooded stranger. From here you cannot see her face — only a glimpse of blue hair.\n" +
            "\"Come, come closer...\" a hollow, pale woman's voice says.\n" +
            "\"Offer me your memories, and I shall give you what you deserve...\"\n" +
            "\"Or offer me a prayer, and I shall give you what was promised...\"\n" +
            "Her voice stops there. The prophet says nothing more, and lowers her head, both hands stroking her cloak.",
            new EventOptionLoc("MEMORY", "Offer your memories", "Gain the relic Prophet's Bracelet."),
            new EventOptionLoc("PRAY", "Pray beside the prophet", $"Gain {GoldReward} gold.")),
        new EventPageLoc(
            "MEMORY",
            "You begin to recall what you once lived through — happiness, pain, hatred, the unforgettable... " +
            "The prophet opens her hand and writes each memory down, one by one.\n" +
            "The memories seem to come alive, filling your eyes and your mind, shifting back and forth until you feel dizzy.\n" +
            "\"There. That will do.\"\n" +
            "Just before you cannot bear it any longer, it stops. The vivid memories vanish and settle back into your heart.\n" +
            "\"Take this... I hope it lets your memories hold a little more joy.\" The prophet falls silent and does not look at you again.\n" +
            "(Gain the relic Prophet's Bracelet.)"),
        new EventPageLoc(
            "PRAY",
            "You pray silently beside the prophet. As the prayer goes on, you hear other voices praying too, threading through your mind.\n" +
            "\"They were all friends of mine once...\" the prophet murmurs, as if this were no surprise at all.\n" +
            "When your prayer ends, the voices vanish with it.\n" +
            "\"So. I hope these funds will help you along.\"\n" +
            "\"Simple and efficient, no? Hehehe...\" The prophet pays you no more attention, and laughs to herself.\n" +
            $"(Gain {GoldReward} gold.)"));
}
