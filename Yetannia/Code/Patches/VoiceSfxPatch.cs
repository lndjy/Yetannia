using System;
using System.Collections.Generic;
using HarmonyLib;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Nodes.Audio;
using Yetannia.YetanniaCode.Voice;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Plays Yetannia's voice lines in place of the FMOD events her character model points at.
///
/// The chain this sits on:
/// <code>
/// AttackCommand._attackerSfx
///   -&gt; SfxCmd.Play(string, float)                 &lt;- patched here
///   -&gt; NAudioManager.Instance.PlayOneShot(path, ...)
///   -&gt; _audioNode.Call(_playOneShot, path, ...)    &lt;- crosses into GDScript, FMOD only
/// </code>
/// There is no file fallback anywhere down that chain, and <c>NAudioManager</c> hands the string straight
/// to a GDScript node, so the only place a mod can substitute its own audio is here.
///
/// <c>YetanniaCharacter</c> points its SFX slots at event paths that do not exist;
/// <see cref="VoicePack.TryPlay"/> recognises those strings. Returning false skips the original (so no
/// pointless FMOD lookup happens for an event we know is absent), while a string we do not recognise
/// returns true and is played by the game exactly as before.
///
/// <b>This one patch is not sufficient on its own</b>, and the two other classes below are why:
///   * <c>NCreature.StartDeathAnim</c> reaches the death sound only for a Spine rig, and this character is a
///     Node2D flipbook — see <see cref="Voice.VoiceDeathMomentPatch"/>;
///   * even where the slot IS consulted, the sentinel has been observed going straight to
///     <c>NAudioManager.PlayOneShot</c> without passing through the patched method at all (the character
///     select screen, in the live log of the reported session). The same interception is therefore also
///     installed one level lower, on <see cref="NAudioManager"/> itself, where every managed caller must
///     pass whatever it believes it is doing.
/// </summary>
[HarmonyPatch(typeof(SfxCmd), nameof(SfxCmd.Play), new[] { typeof(string), typeof(float) })]
internal static class VoiceSfxPatch
{
    [HarmonyPrefix]
    private static bool Prefix(string sfx)
    {
        try
        {
            return !VoicePack.TryPlay(sfx);
        }
        catch (Exception e)
        {
            // Sound must never be able to break combat. On any surprise, let the original run.
            MainFile.Logger.Error($"[voice] SfxCmd.Play interception failed for '{sfx}': {e}");
            return true;
        }
    }
}

/// <summary>
/// The same sentinel interception, one level lower: <c>NAudioManager.PlayOneShot(string, float)</c>.
///
/// Why this exists: a sentinel reaching this method means the call did NOT go through
/// <c>SfxCmd.Play</c> — which is exactly what the reported session's log shows for the character-select
/// line (<c>event:/sfx/characters/yetannia/yetannia_select</c> appearing in RitsuLib's "FMOD event was not
/// found" warning, with no <c>[voice]</c> line from the SfxCmd patch). `SfxCmd.PlayDeath(Player)` is the
/// vanilla example of a caller that does this on purpose (SfxCmd.cs:94-100), so this is a supported shape
/// of call, not an anomaly.
///
/// It stays narrow on purpose: only our own four sentinel strings are touched, so every other sound —
/// music, UI, enemies, other mods — is handed to FMOD untouched.
/// </summary>
[HarmonyPatch(typeof(NAudioManager), nameof(NAudioManager.PlayOneShot), new[] { typeof(string), typeof(float) })]
internal static class VoiceAudioManagerPatch
{
    [HarmonyPrefix]
    private static bool Prefix(string path)
    {
        try
        {
            return !VoicePack.TryPlay(path);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] NAudioManager.PlayOneShot interception failed for '{path}': {e}");
            return true;
        }
    }
}

/// <summary>
/// The parameterised overload, because it is a *separate* method: <c>SfxCmd.Play(sfx, param, val, volume)</c>
/// calls this one directly and never passes through the two-argument overload, so patching only that one
/// would leave a second hole of exactly the kind the character-select line fell through.
/// </summary>
[HarmonyPatch(typeof(NAudioManager), nameof(NAudioManager.PlayOneShot), new[] { typeof(string), typeof(Dictionary<string, float>), typeof(float) })]
internal static class VoiceAudioManagerParamsPatch
{
    [HarmonyPrefix]
    private static bool Prefix(string path)
    {
        try
        {
            return !VoicePack.TryPlay(path);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[voice] NAudioManager.PlayOneShot(params) interception failed for '{path}': {e}");
            return true;
        }
    }
}
