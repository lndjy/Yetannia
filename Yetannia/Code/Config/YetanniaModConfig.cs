using BaseLib.Config;
using Yetannia.YetanniaCode.Voice;

namespace Yetannia.YetanniaCode.Config;

/// <summary>
/// Everything this mod surfaces in the game's own settings screen.
///
/// <para><b>One config per mod — this is a hard constraint, not a style choice.</b> BaseLib's
/// <c>ModConfigRegistry</c> stores configs in a <c>Dictionary&lt;string, ModConfig&gt;</c> keyed by the
/// mod id, so a second <c>Register(ModId, …)</c> call does not add a second page, it <b>overwrites the
/// first</b> — registering a separate card-balance config would silently have deleted the voice dropdown
/// that already shipped. Both settings therefore live on this one class, each with its own
/// <see cref="ConfigSectionAttribute"/>; <c>SimpleModConfig</c> starts a new section every time that
/// attribute's name changes while it walks the properties, so they render as two separate blocks.</para>
///
/// <para><b>Every property must be <c>static</c>.</b> <c>ModConfig.CheckConfigProperties</c> skips
/// instance properties with "only static properties are supported", and a config that exposes zero
/// settings makes <c>HasSettings()</c>/<c>VisibleInModList()</c> both false — at which point
/// <c>ModConfigRegistry.Register</c> returns immediately and the page silently never appears.</para>
///
/// <para><b>Renaming this class does not move the config file.</b> The file name is derived from the
/// type's <i>root namespace</i> (<c>ModConfig</c>'s constructor slug-strips <c>GetRootNamespace()</c>),
/// which is still <c>Yetannia</c>, and the saved values are keyed by property name. The class was called
/// <c>VoiceConfig</c> when the voice setting shipped alone; it was renamed here because it is no longer
/// about voice, and existing players' saved voice choice still loads because the property name did not
/// change.</para>
/// </summary>
internal sealed class YetanniaModConfig : SimpleModConfig
{
    // SimpleModConfig declares no constructor of its own, so the implicit one chains to ModConfig() and
    // the config file name is derived for us. Passing a name here does not compile.

    /// <summary>
    /// The 「语音语言」 dropdown.
    ///
    /// An enum-typed property renders as a dropdown, which is why the three-way choice is one property
    /// rather than two tickboxes. Option labels are looked up under <c>{modId}-{PropertyName}.{Value}</c>
    /// and are supplied by <c>Patches.SettingsLocPatch</c>.
    ///
    /// A passthrough onto <see cref="VoicePack.Language"/> rather than its own field: the value is read on
    /// every single sound, so there is one source of truth and no chance of the config and the player
    /// drifting apart.
    ///
    /// <c>[ConfigHoverTip]</c> is what makes the row's tooltip exist at all — <c>SimpleModConfig</c> builds
    /// the dropdown with <c>addHoverTip: false</c> and only calls <c>AddHoverTip()</c> when this attribute
    /// is present. Without it the <c>.hover.title</c>/<c>.hover.desc</c> entries injected by
    /// <c>SettingsLocPatch</c> are never read and the row has no tooltip.
    /// </summary>
    [ConfigHoverTip]
    [ConfigSection("语音 Voice")]
    public static VoiceLanguage VoiceLanguage
    {
        get => VoicePack.Language;
        set => VoicePack.Language = value;
    }

    /// <summary>
    /// The 「卡牌数值」 dropdown: 原版 / 东尼测试版.
    ///
    /// Read by every card that differs between the two balance drafts through
    /// <see cref="CardBalance.IsTony"/>, which is where the "why" of the numbers lives.
    ///
    /// The value is applied when the game loads the cards, because a card's dynamic vars, energy cost and
    /// upgrade behaviour are all fixed while the model is constructed — and the card *text* is baked into
    /// the loc table at the same time (see <see cref="CardBalance"/>), so a restart is required for the
    /// switch to take effect. The tooltip says exactly that.
    /// </summary>
    [ConfigHoverTip]
    [ConfigSection("卡牌 Cards")]
    public static CardBalanceMode CardBalanceMode
    {
        get => CardBalance.Mode;
        set => CardBalance.Mode = value;
    }
}
