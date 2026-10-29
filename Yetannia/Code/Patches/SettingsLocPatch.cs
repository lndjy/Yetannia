using System.Collections.Generic;
using System.Runtime.CompilerServices;
using HarmonyLib;
using MegaCrit.Sts2.Core.Localization;
using Yetannia.YetanniaCode.Config;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Injects the text for this mod's settings rows into the game's <c>settings_ui</c> table.
///
/// Without this the settings are fully functional but read badly to a player: BaseLib resolves every
/// label from <c>settings_ui</c> and, finding nothing, falls back to raw identifiers — the rows show
/// the bare property names <c>VoiceLanguage</c> / <c>CardBalanceMode</c> and the choices show the
/// enum names <c>Chinese / Japanese / Off</c> and <c>Original / TonyTest</c>. Verified by a QA run
/// that walked the real UI-building path.
///
/// The exact keys are not guessable from the attribute names, so they are recorded here, each with
/// the BaseLib member that computes it:
/// <list type="bullet">
/// <item><c>ModConfig.cs</c> — row title: <c>ModPrefix + identifier + ".title"</c></item>
/// <item><c>NConfigDropdown.cs</c> — option label: <c>ModPrefix + identifier + "." + value</c></item>
/// <item><c>NConfigOptionRow.AddHoverTip</c> — tooltip: <c>ModPrefix + slug + ".hover.title"</c> and
/// <c>".hover.desc"</c>. These two are only read if a tooltip is requested at all, which requires
/// <c>[ConfigHoverTip]</c> on the property (or <c>[ConfigHoverTipsByDefault]</c> on the class) — see
/// <see cref="YetanniaModConfig"/>. Without that attribute <c>SimpleModConfig</c> builds the dropdown
/// with <c>addHoverTip: false</c> and <c>AddHoverTipToOptionRowIfEnabled</c> never calls
/// <c>AddHoverTip()</c>, so these keys sit unread. (If <c>AddHoverTip()</c> does run and
/// <c>".hover.desc"</c> is absent, BaseLib logs <c>"... skipping HoverTip."</c> and shows nothing —
/// that is the failure mode, not the current state.)</item>
/// <item><c>NModConfigSubmenu.cs</c> — the mod-list button uses a dot rather than the prefix dash:
/// <c>"YETANNIA" + ".mod_title"</c>. Missing, it warns and falls back to the root namespace.</item>
/// </list>
/// <c>Slugify</c> upper-cases and underscore-separates, which is why the property
/// <c>VoiceLanguage</c> keys on <c>VOICE_LANGUAGE</c> and <c>CardBalanceMode</c> on
/// <c>CARD_BALANCE_MODE</c>.
///
/// Patching <see cref="LocManager.GetTable"/> rather than table loading keeps this order-independent
/// and re-applies on every language switch (each switch produces a fresh
/// <see cref="LocTable"/>). Same mechanism as <c>Keywords.KeywordLocPatch</c>.
/// </summary>
[HarmonyPatch(typeof(LocManager), nameof(LocManager.GetTable))]
internal static class SettingsLocPatch
{
    private const string SettingsTable = "settings_ui";
    private const string VoiceKey = "YETANNIA-VOICE_LANGUAGE";
    private const string BalanceKey = "YETANNIA-CARD_BALANCE_MODE";
    /// <summary>
    /// The 「语音 Voice」 section header. <c>[ConfigSection("语音 Voice")]</c> is passed through
    /// <c>StringHelper.Slugify</c>, which keeps ASCII, upper-cases it and underscores the spaces, so
    /// the Chinese characters are dropped and the leading space becomes a leading underscore — hence
    /// the odd-looking key. If BaseLib's slugging ever changes this key simply stops matching and the
    /// header degrades to the raw section name, which is the current behaviour anyway.
    /// </summary>
    private const string VoiceSectionKey = "YETANNIA-_VOICE";
    /// <summary>Same derivation for <c>[ConfigSection("卡牌 Cards")]</c>.</summary>
    private const string CardsSectionKey = "YETANNIA-_CARDS";
    private const string ModTitleKey = "YETANNIA.mod_title";

    private static readonly IReadOnlyDictionary<string, string> Chinese = new Dictionary<string, string>
    {
        [$"{VoiceKey}.title"] = "语音语言",
        [$"{VoiceKey}.hover.title"] = "语音语言",
        [$"{VoiceKey}.hover.desc"] = "选择耶坦尼娅的战斗语音。「关闭」后角色不出声，游戏原版音效不受影响。",
        [$"{VoiceKey}.Chinese"] = "中文",
        [$"{VoiceKey}.Japanese"] = "日语",
        [$"{VoiceKey}.Off"] = "关闭",
        [$"{VoiceSectionKey}.title"] = "语音",

        [$"{BalanceKey}.title"] = "卡牌数值",
        [$"{BalanceKey}.hover.title"] = "卡牌数值",
        [$"{BalanceKey}.hover.desc"] =
            "「原版」是正式发布的数值；「东尼测试版」有部分卡牌按测试草案调整（详见更新说明）。" +
            "切换后需要重启游戏才会生效（卡面文字和数值都会跟着变）。",
        [$"{BalanceKey}.Original"] = "原版",
        [$"{BalanceKey}.TonyTest"] = "东尼测试版",
        [$"{CardsSectionKey}.title"] = "卡牌",

        [ModTitleKey] = "耶坦尼娅",
    };

    private static readonly IReadOnlyDictionary<string, string> English = new Dictionary<string, string>
    {
        [$"{VoiceKey}.title"] = "Voice Language",
        [$"{VoiceKey}.hover.title"] = "Voice Language",
        [$"{VoiceKey}.hover.desc"] = "Which dub Yetannia speaks in. \"Off\" leaves her silent; the base game's own audio is unaffected.",
        [$"{VoiceKey}.Chinese"] = "Chinese",
        [$"{VoiceKey}.Japanese"] = "Japanese",
        [$"{VoiceKey}.Off"] = "Off",
        [$"{VoiceSectionKey}.title"] = "Voice",

        [$"{BalanceKey}.title"] = "Card Numbers",
        [$"{BalanceKey}.hover.title"] = "Card Numbers",
        [$"{BalanceKey}.hover.desc"] =
            "\"Original\" is the released balance. \"Tony's Test Build\" applies a draft that changes a handful of cards " +
            "(see the changelog). A restart is required for the switch to take effect — both the card text and the numbers.",
        [$"{BalanceKey}.Original"] = "Original",
        [$"{BalanceKey}.TonyTest"] = "Tony's Test Build",
        [$"{CardsSectionKey}.title"] = "Cards",

        [ModTitleKey] = "Yetannia",
    };

    // Reference-keyed so each freshly loaded LocTable (i.e. each language switch) is patched once.
    private static readonly ConditionalWeakTable<LocTable, object> Injected = new();

    [HarmonyPostfix]
    private static void InjectSettingsText(string name, LocTable __result)
    {
        if (__result == null || name != SettingsTable)
        {
            return;
        }

        if (Injected.TryGetValue(__result, out _))
        {
            return;
        }

        Injected.Add(__result, null);

        var isChinese = LocManager.Instance?.Language == "zhs";
        __result.MergeWith(new Dictionary<string, string>(isChinese ? Chinese : English));
    }
}
