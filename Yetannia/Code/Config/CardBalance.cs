namespace Yetannia.YetanniaCode.Config;

/// <summary>
/// Which set of numbers the cards use. Surfaced in the game's settings screen as 「卡牌数值」 with the
/// two choices below, so a tester can flip a whole balance draft on and off without a rebuild.
///
/// The member names are deliberately ASCII words rather than Chinese: BaseLib falls back to the bare
/// enum name when a localization entry is missing, and an ASCII fallback stays readable. The Chinese
/// labels live in <see cref="Yetannia.YetanniaCode.Patches.SettingsLocPatch"/>.
/// </summary>
internal enum CardBalanceMode
{
    /// <summary>The shipped numbers — what every release before this setting had.</summary>
    Original,

    /// <summary>
    /// 东尼测试版 — 东尼's balance draft. Only the cards listed in the v1.0.4 changelog differ; every
    /// other card behaves exactly as in <see cref="Original"/>.
    /// </summary>
    TonyTest,
}

/// <summary>
/// The single source of truth for the balance draft, read by the individual cards.
///
/// Same shape as the voice setting: the persisted value lives in a static field here and
/// <see cref="YetanniaModConfig"/> is a thin passthrough onto it, so the card code never has to know
/// about BaseLib's config machinery. Reading a static field is also what makes this cheap enough to
/// call from <c>CanonicalVars</c> and from the localization getters.
///
/// <para><b>When a change takes effect.</b> Card models are built once, while the mod loads, and
/// <c>CanonicalVars</c>/<c>OnUpgrade</c> run at that moment — so the numbers, the energy costs and the
/// upgrade behaviour all come from the mode that was selected <i>when the game started</i>. Switching
/// the dropdown therefore applies on the next launch; the tooltip says so, and the setting is written to
/// disk immediately (BaseLib saves it on quit as well as on change). Card text is baked the same way:
/// <c>Patches.ModelLocReloadPatch</c> copies each card's <c>Localization</c> into the game's loc table
/// when that table is built (and rebuilt on a language switch), so a sentence that differs between the
/// drafts also only changes on the next launch. The whole mode is therefore restart-to-apply, which is
/// what the setting's tooltip and the README say — better to state that than to have a player flip the
/// dropdown, see the numbers stay put and file it as a bug.</para>
/// </summary>
internal static class CardBalance
{
    /// <summary>Currently selected mode. Persisted by <see cref="YetanniaModConfig"/>.</summary>
    internal static CardBalanceMode Mode { get; set; } = CardBalanceMode.Original;

    /// <summary>
    /// True when the 东尼测试版 numbers are in force. Every card that differs between the two drafts
    /// branches on this one property, so the list of divergent cards is exactly "who reads IsTony".
    /// </summary>
    internal static bool IsTony => Mode == CardBalanceMode.TonyTest;
}
