namespace Yetannia.YetanniaCode;

/// <summary>
/// Paths of assets shipped inside <c>Yetannia.pck</c>.
///
/// The game mounts the mod's pck at the project root, so everything this mod ships lives under
/// <c>res://Yetannia/</c>. Godot resource paths always use forward slashes.
///
/// Textures must be packed through Godot (they end up as imported <c>.ctex</c> data, which is what
/// <c>ResourceLoader.Load&lt;CompressedTexture2D&gt;</c> expects) — see <c>.tools/export-pck.ps1</c>
/// and <c>.tools/pckproject/</c>.
///
/// Deliberately not called <c>AssetPaths</c>: <c>CharacterModel</c> already exposes an inherited
/// <c>AssetPaths</c> property, which would shadow this type inside character subclasses.
/// </summary>
internal static class ModAssets
{
    public const string ModId = MainFile.ModId;

    public static string Root => $"res://{ModId}";

    /// <param name="relativePath">Path below the mod's <c>images/</c> folder, e.g. <c>charui/foo.png</c>.</param>
    public static string Image(string relativePath) => $"{Root}/images/{relativePath}";

    public static string CharUi(string fileName) => Image($"charui/{fileName}");

    /// <summary>
    /// One voice line, e.g. <c>Voice("jp", "attack")</c> -&gt;
    /// <c>res://Yetannia/audio/voice/jp/yetannia_attack.ogg</c>.
    ///
    /// <paramref name="lang"/> is "cn" or "jp". Kept here beside the other res:// construction so that
    /// renaming the folder cannot leave a stale path behind in the voice code.
    /// </summary>
    public static string Voice(string lang, string stem) => $"{Root}/audio/voice/{lang}/yetannia_{stem}.ogg";

    /// <summary>
    /// Path of a scene shipped in the pck. Godot scene paths keep their <c>.tscn</c> extension
    /// (the game's own <c>SceneHelper.GetScenePath</c> appends it too).
    /// Scenes live in <c>.tools/pckproject/Yetannia/scenes/</c>.
    /// </summary>
    /// <param name="relativePath">Path below the mod's <c>scenes/</c> folder, e.g. <c>creature_visuals/yetannia</c>.</param>
    public static string Scene(string relativePath) => $"{Root}/scenes/{relativePath}.tscn";
}
