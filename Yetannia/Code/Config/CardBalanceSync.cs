using System.Reflection;
using HarmonyLib;
using MegaCrit.Sts2.Core.Daily;
using MegaCrit.Sts2.Core.Logging;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Multiplayer.Game;
using MegaCrit.Sts2.Core.Multiplayer.Game.Lobby;
using MegaCrit.Sts2.Core.Multiplayer.Serialization;
using MegaCrit.Sts2.Core.Multiplayer.Transport;
using MegaCrit.Sts2.Core.Runs;

namespace Yetannia.YetanniaCode.Config;

/// <summary>
/// 联机时把「卡牌数值」统一成主机的那一档。
///
/// WHY: the two drafts change the numbers of a handful of cards. Each peer builds its card models from
/// its own local setting when the game loads, so a host on 原版 and a client on 东尼测试版 play the same
/// card IDs with different damage/block values. The game's action-queue synchronisation then sees the
/// peers disagree and reports a desync. There is no way for the client to know the host's draft before
/// the lobby, and reloading models is not possible mid-session, so the exchange happens in
/// <see cref="StartRunLobby"/> — the object that exists BEFORE the run (and therefore before any run
/// card instance is created), and which already owns a connected <see cref="INetGameService"/>.
///
/// WIRE PROTOCOL (one byte of kind + one byte of mode):
///   client -> host : KindRequest   ("which draft are you on?")
///   host  -> all   : KindAnnounce  ("this is the draft everyone must use")
/// The host is authoritative; a client that receives a different draft adopts it and the mod clears the
/// cached <c>DynamicVars</c> of every Yetannia card model, so the run's card instances are built with the
/// host's numbers. Card TEXT is baked into the loc table at load time, so a sentence that differs between
/// drafts only changes on the next launch — the numbers (the part that desyncs) are already unified.
/// </summary>
internal sealed class CardBalanceSyncMessage : INetMessage
{
    internal const int KindRequest = 0;
    internal const int KindAnnounce = 1;

    /// <summary>KindRequest or KindAnnounce.</summary>
    public int Kind;

    /// <summary>The sender's <see cref="CardBalanceMode"/> as an int.</summary>
    public int Balance;

    public bool ShouldBroadcast => true;

    public NetTransferMode Mode => NetTransferMode.Reliable;

    public LogLevel LogLevel => LogLevel.Info;

    public bool ShouldBuffer => true;

    public void Serialize(PacketWriter writer)
    {
        writer.WriteInt(Kind, 8);
        writer.WriteInt(Balance, 8);
    }

    public void Deserialize(PacketReader reader)
    {
        Kind = reader.ReadInt(8);
        Balance = reader.ReadInt(8);
    }
}

/// <summary>
/// See <see cref="CardBalanceSyncMessage"/>. Host answers requests, clients adopt the host's draft before
/// the run starts. Everything is logged under one tag so a multiplayer report can be diagnosed from
/// <c>godot.log</c> alone.
/// </summary>
internal static class CardBalanceSync
{
    private static readonly HashSet<INetGameService> Installed = new();

    private static FieldInfo? _dynamicVarsField;

    internal static void OnLobbyCreated(StartRunLobby lobby)
    {
        try
        {
            var net = lobby.NetService;
            if (net == null)
            {
                return;
            }

            if (net.Type is not (NetGameType.Host or NetGameType.Client))
            {
                return;
            }

            if (!Installed.Add(net))
            {
                return;
            }

            // Capture the service: RunManager.Instance is still null while the lobby exists, so the
            // handler must not try to look it up again (that made the handshake a silent no-op).
            net.RegisterMessageHandler<CardBalanceSyncMessage>((message, senderId) => OnMessage(net, message, senderId));
            MainFile.Logger.Info(
                $"[mp] card balance sync armed on {net.Type} (local draft: {CardBalance.Mode})");

            // The host also announces immediately: harmless if no client is connected yet (a joiner sends
            // a request of its own as soon as its lobby exists).
            var kind = net.Type == NetGameType.Host
                ? CardBalanceSyncMessage.KindAnnounce
                : CardBalanceSyncMessage.KindRequest;
            net.SendMessage(new CardBalanceSyncMessage
            {
                Kind = kind,
                Balance = (int)CardBalance.Mode,
            });
        }
        catch (Exception e)
        {
            MainFile.Logger.Warn($"[mp] card balance sync could not be armed: {e.GetType().Name}: {e.Message}");
        }
    }

    private static void OnMessage(INetGameService net, CardBalanceSyncMessage message, ulong senderId)
    {
        try
        {

            if (message.Kind == CardBalanceSyncMessage.KindRequest)
            {
                if (net.Type != NetGameType.Host)
                {
                    return;
                }

                MainFile.Logger.Info($"[mp] card balance requested by peer {senderId}; announcing {CardBalance.Mode}");
                net.SendMessage(new CardBalanceSyncMessage
                {
                    Kind = CardBalanceSyncMessage.KindAnnounce,
                    Balance = (int)CardBalance.Mode,
                });
                return;
            }

            if (message.Kind != CardBalanceSyncMessage.KindAnnounce)
            {
                return;
            }

            if (net.Type == NetGameType.Host)
            {
                // Host is authoritative: ignore echoes of its own announcement.
                return;
            }

            var hostMode = (CardBalanceMode)message.Balance;
            if (hostMode != CardBalanceMode.Original && hostMode != CardBalanceMode.TonyTest)
            {
                MainFile.Logger.Warn($"[mp] host announced an unknown draft {(int)hostMode}; ignoring");
                return;
            }

            if (hostMode == CardBalance.Mode)
            {
                MainFile.Logger.Info($"[mp] card balance already matches the host ({hostMode})");
                return;
            }

            ApplyMode(hostMode);
        }
        catch (Exception e)
        {
            MainFile.Logger.Warn($"[mp] card balance sync message failed: {e.GetType().Name}: {e.Message}");
        }
    }

    /// <summary>
    /// Switches the draft for this session and drops the cached canonical <c>DynamicVars</c> of every
    /// Yetannia card model so they are rebuilt from <c>CanonicalVars</c> (which branch on <see cref="CardBalance.IsTony"/>)
    /// when the run creates its card instances.
    /// </summary>
    private static void ApplyMode(CardBalanceMode hostMode)
    {
        var previous = CardBalance.Mode;
        CardBalance.Mode = hostMode;

        _dynamicVarsField ??= typeof(CardModel).GetField(
            "_dynamicVars", BindingFlags.Instance | BindingFlags.NonPublic);

        var cleared = 0;
        if (_dynamicVarsField != null)
        {
            foreach (var card in ModelDb.All.OfType<CardModel>())
            {
                if (card.GetType().Namespace?.Contains("Yetannia", StringComparison.Ordinal) != true)
                {
                    continue;
                }

                if (_dynamicVarsField.GetValue(card) != null)
                {
                    _dynamicVarsField.SetValue(card, null);
                    cleared++;
                }
            }
        }

        MainFile.Logger.Info(
            $"[mp] adopted the host's card balance draft: {previous} -> {hostMode} " +
            $"(cleared cached vars on {cleared} card model(s); card text applies on the next launch)");
    }
}

/// <summary>
/// <see cref="StartRunLobby"/> is constructed on both peers before the run begins; hooking its two
/// constructors is what gives the client the host's draft early enough for the run's cards to be built
/// with it. Both constructors are patched because the second one is used for time-server (daily) runs.
/// </summary>
[HarmonyPatch(typeof(StartRunLobby), MethodType.Constructor,
    new[] { typeof(GameMode), typeof(INetGameService), typeof(IStartRunLobbyListener), typeof(int) })]
internal static class StartRunLobbyCtorPatch
{
    [HarmonyPostfix]
    private static void Postfix(StartRunLobby __instance) => CardBalanceSync.OnLobbyCreated(__instance);
}

[HarmonyPatch(typeof(StartRunLobby), MethodType.Constructor,
    new[] { typeof(GameMode), typeof(INetGameService), typeof(IStartRunLobbyListener), typeof(TimeServerResult), typeof(int) })]
internal static class StartRunLobbyDailyCtorPatch
{
    [HarmonyPostfix]
    private static void Postfix(StartRunLobby __instance) => CardBalanceSync.OnLobbyCreated(__instance);
}
