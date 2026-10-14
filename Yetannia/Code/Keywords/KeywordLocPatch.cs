using System.Collections.Generic;
using System.Runtime.CompilerServices;
using HarmonyLib;
using MegaCrit.Sts2.Core.Localization;

namespace Yetannia.YetanniaCode.Keywords;

/// <summary>
/// Injects localization the mod needs but cannot ship as a model: the 先知 keyword's two entries in
/// <c>card_keywords</c>, and the extra event option's text in <c>events</c>.
///
/// BaseLib only knows how to inject localization for registered <em>models</em>
/// (see its <c>ModelLocPatch</c>), and shipping a JSON file would require packing a <c>.pck</c>
/// specifically for it. This mod is code-only, so instead we merge the keys into each table the
/// first time the game hands it to us.
///
/// Patching <see cref="LocManager.GetTable"/> rather than table loading keeps this working no
/// matter whether the mod initializes before or after localization is loaded, and it re-applies
/// automatically whenever the player switches language (new <see cref="LocTable"/> instances).
/// </summary>
[HarmonyPatch(typeof(LocManager), nameof(LocManager.GetTable))]
internal static class KeywordLocPatch
{
    private const string KeywordTable = "card_keywords";
    private const string EventTable = "events";
    private const string ProphetKey = "YETANNIA-PROPHET";
    private const string SkipEventKey = "YETANNIA-SKIP_EVENT";

    private static readonly IReadOnlyDictionary<string, string> ChineseKeywords = new Dictionary<string, string>
    {
        [$"{ProphetKey}.title"] = "先知",
        [$"{ProphetKey}.description"] = "当此牌从抽牌堆进入弃牌堆时，触发本牌的先知效果。",
    };

    private static readonly IReadOnlyDictionary<string, string> EnglishKeywords = new Dictionary<string, string>
    {
        [$"{ProphetKey}.title"] = "Prophet",
        [$"{ProphetKey}.description"] = "When this card moves from your draw pile to your discard pile, trigger its Prophet effect.",
    };

    // 先知的手链 injects this option into every ? event; the text has to come from somewhere.
    private static readonly IReadOnlyDictionary<string, string> ChineseEvents = new Dictionary<string, string>
    {
        [$"{SkipEventKey}.title"] = "跳过",
        [$"{SkipEventKey}.description"] = "跳过这个事件，获得 50 金币。",
    };

    private static readonly IReadOnlyDictionary<string, string> EnglishEvents = new Dictionary<string, string>
    {
        [$"{SkipEventKey}.title"] = "Skip",
        [$"{SkipEventKey}.description"] = "Skip this event and gain 50 gold.",
    };

    // Reference-keyed so that each freshly loaded LocTable (i.e. each language switch) is patched once.
    private static readonly ConditionalWeakTable<LocTable, object> Injected = new();

    [HarmonyPostfix]
    private static void InjectKeywordText(string name, LocTable __result)
    {
        if (__result == null) return;

        IReadOnlyDictionary<string, string> entries;
        var language = LocManager.Instance?.Language;
        var isChinese = language == "zhs";

        if (name == KeywordTable)
        {
            entries = isChinese ? ChineseKeywords : EnglishKeywords;
        }
        else if (name == EventTable)
        {
            entries = isChinese ? ChineseEvents : EnglishEvents;
        }
        else
        {
            return;
        }

        if (Injected.TryGetValue(__result, out _)) return;

        Injected.Add(__result, null);
        __result.MergeWith(new Dictionary<string, string>(entries));
    }
}
