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

        // The settings page: 「语音语言」 and 「卡牌数值」. BaseLib injects a registered config into the
        // game's own settings screen, so this has to happen before that screen is built. Registered here
        // rather than in a static field initialiser so that the one place a reader looks for "what this
        // mod installs" is this method.
        //
        // Exactly one config per mod: ModConfigRegistry keys its dictionary by mod id, so registering a
        // second one would replace this one outright. Both settings live on the same class.
        ModConfigRegistry.Register(ModId, new Config.YetanniaModConfig());

        // "effective", not "default": the config's constructor has already applied the saved config file by
        // the time this line runs, so calling this value the default printed "default Chinese" on a machine
        // whose built-in default is Japanese (the VoicePack.Language initializer). The balance mode is
        // logged for the same reason: it is what the cards will actually be built with this session.
        Logger.Info(
            $"Yetannia: settings registered (effective voice pack: {Voice.VoicePack.Language}, " +
            $"card balance: {Config.CardBalance.Mode})");

        Logger.Info("Yetannia: initialized");
    }
}
