using System.Reflection;
using BaseLib.Config;
using HarmonyLib;
using MegaCrit.Sts2.Core.Logging;
using MegaCrit.Sts2.Core.Modding;

namespace Yetannia.YetanniaCode;

/// <summary>
/// Mod entry point. BaseLib's auto-registration (cards, relics, pools, keywords) is driven by
/// attributes on the model classes, so there is nothing to register manually here beyond
/// applying our own Harmony patches.
/// </summary>
[ModInitializer(nameof(Initialize))]
public static class MainFile
{
    public const string ModId = "Yetannia";

    public static Logger Logger { get; } = new(ModId, LogType.Generic);

    public static void Initialize()
    {
        Logger.Info("Yetannia: initializing");
        var harmony = new Harmony(ModId);
        harmony.PatchAll(Assembly.GetExecutingAssembly());

        // The 「语音语言」 dropdown. BaseLib injects a registered config into the game's own settings screen,
        // so this has to happen before that screen is built. Registered here rather than in a static field
        // initialiser so that the one place a reader looks for "what this mod installs" is this method.
        ModConfigRegistry.Register(ModId, new Voice.VoiceConfig());

        // "effective", not "default": VoiceConfig's constructor has already applied the saved config file
        // by the time this line runs, so calling this value the default printed "default Chinese" on a
        // machine whose built-in default is Japanese (the VoicePack.Language initializer).
        Logger.Info($"Yetannia: voice setting registered (effective voice pack: {Voice.VoicePack.Language})");

        Logger.Info("Yetannia: initialized");
    }
}
