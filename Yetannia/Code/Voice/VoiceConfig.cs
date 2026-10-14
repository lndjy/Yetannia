using BaseLib.Config;

namespace Yetannia.YetanniaCode.Voice;

/// <summary>
/// The 「语音语言」 setting, surfaced in the game's own settings screen.
///
/// BaseLib injects a mod's config into that screen (<c>InjectSettingsModConfigPatch</c>) and renders an
/// **enum-typed property as a dropdown**, which is why the three-way choice is one property rather than two
/// tickboxes. Option labels are looked up under <c>{modId}-{PropertyName}.{Value}</c>; the enum member names
/// are deliberately the plain words Chinese / Japanese / Off so that a missing localization entry degrades to
/// something readable rather than to a raw key.
///
/// The property is a thin passthrough onto <see cref="VoicePack.Language"/> rather than its own field: the
/// value is read on every single sound, so there is one source of truth and no chance of the config and the
/// player drifting apart.
///
/// **It must be a `static` property.** BaseLib's <c>ModConfig.CheckConfigProperties()</c> inspects the
/// properties of the concrete config type and skips every instance property with
/// <c>"Ignoring {mod} property {name}: only static properties are supported"</c>. With an instance property
/// the type therefore exposes zero settings, which makes <c>HasSettings</c>/<c>VisibleInModList</c> both
/// false — and <c>ModConfigRegistry.Register</c> begins with
/// <c>if (!HasSettings() &amp;&amp; !VisibleInModList()) return;</c>, so it silently does not register at all
/// and the row never appears in the settings screen. There is no exception and no error, which is exactly
/// what makes it easy to ship broken: the registration call still runs and still looks like it worked.
/// </summary>
internal sealed class VoiceConfig : SimpleModConfig
{
    // SimpleModConfig declares no constructor of its own, so the implicit one chains to ModConfig() and the
    // config file name is derived for us. Passing a name here does not compile.
    //
    // [ConfigHoverTip] is what makes the row's tooltip exist at all. SimpleModConfig builds a dropdown with
    // `addHoverTip: false` and then consults AddHoverTipToOptionRowIfEnabled, which only calls
    // row.AddHoverTip() when this attribute is present (its Enabled defaults to true) or the class carries
    // [ConfigHoverTipsByDefault]. Without it, the `.hover.title` / `.hover.desc` entries that
    // Patches.SettingsLocPatch injects are never read and the row has no tooltip.
    [ConfigHoverTip]
    [ConfigSection("语音 Voice")]
    public static VoiceLanguage VoiceLanguage
    {
        get => VoicePack.Language;
        set => VoicePack.Language = value;
    }
}
