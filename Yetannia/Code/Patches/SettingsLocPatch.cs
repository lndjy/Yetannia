using System.Collections.Generic;
using System.Runtime.CompilerServices;
using HarmonyLib;
using MegaCrit.Sts2.Core.Localization;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Injects the text for the 「语音 Voice」 setting into the game's <c>settings_ui</c> table.
///
/// Without this the setting is fully functional but reads badly to a player: BaseLib resolves every
/// label from <c>settings_ui</c> and, finding nothing, falls back to raw identifiers — the row shows
/// the bare property name <c>VoiceLanguage</c> and the three choices show the enum names
/// <c>Chinese / Japanese / Off</c>. Verified by a QA run that walked the real UI-building path.
///
/// The exact keys are not guessable from the attribute names, so they are recorded here, each with
/// the BaseLib member that computes it:
/// <list type="bullet">
/// <item><c>ModConfig.cs</c> — row title: <c>ModPrefix + identifier + ".title"</c></item>
/// <item><c>NConfigDropdown.cs</c> — option label: <c>ModPrefix + identifier + "." + value</c></item>
/// <item><c>NConfigOptionRow.AddHoverTip</c> — tooltip: <c>ModPrefix + slug + ".hover.title"</c> and
/// <c>".hover.desc"</c>. These two are only read if a tooltip is requested at all, which requires
/// <c>[ConfigHoverTip]</c> on the property (or <c>[ConfigHoverTipsByDefault]</c> on the class) — see
/// <see cref="VoiceConfig"/>. Without that attribute <c>SimpleModConfig</c> builds the dropdown with
/// <c>addHoverTip: false</c> and <c>AddHoverTipToOptionRowIfEnabled</c> never calls
/// <c>AddHoverTip()</c>, so these keys sit unread. (If <c>AddHoverTip()</c> does run and
/// <c>".hover.desc"</c> is absent, BaseLib logs <c>"... skipping HoverTip."</c> and shows nothing —
/// that is the failure mode, not the current state.)</item>
/// <item><c>NModConfigSubmenu.cs</c> — the mod-list button uses a dot rather than the prefix dash:
/// <c>"YETANNIA" + ".mod_title"</c>. Missing, it warns and falls back to the root namespace.</item>
/// </list>
/// <c>Slugify</c> upper-cases and underscore-separates, which is why the property
/// <c>VoiceLanguage</c> keys on <c>VOICE_LANGUAGE</c>.
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
    /// <summary>
    /// The section header. <c>[ConfigSection("语音 Voice")]</c> is passed through
    /// <c>StringHelper.Slugify</c>, which keeps ASCII, upper-cases it and underscores the spaces, so
    /// the Chinese characters are dropped and the leading space becomes a leading underscore — hence
    /// the odd-looking key. If BaseLib's slugging ever changes this key simply stops matching and the
    /// header degrades to the raw section name, which is the current behaviour anyway.
    /// </summary>
    private const string SectionKey = "YETANNIA-_VOICE";
    private const string ModTitleKey = "YETANNIA.mod_title";

    private static readonly IReadOnlyDictionary<string, string> Chinese = new Dictionary<string, string>
    {
        [$"{VoiceKey}.title"] = "语音语言",
        [$"{VoiceKey}.hover.title"] = "语音语言",
        [$"{VoiceKey}.hover.desc"] = "选择耶坦尼娅的战斗语音。「关闭」后角色不出声，游戏原版音效不受影响。",
        [$"{VoiceKey}.Chinese"] = "中文",
        [$"{VoiceKey}.Japanese"] = "日语",
        [$"{VoiceKey}.Off"] = "关闭",
        [$"{SectionKey}.title"] = "语音",
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
        [$"{SectionKey}.title"] = "Voice",
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
