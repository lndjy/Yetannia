using System;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;

namespace Yetannia.YetanniaCode.Patches;

/// <summary>
/// Makes <see cref="NMerchantCharacter"/> usable with a flipbook merchant instead of a Spine one.
///
/// WHY THIS IS NEEDED AT ALL. <c>NMerchantCharacter._Ready</c> is literally:
/// <code>
/// this.RunWhenSpineReady(new MegaSprite(GetChild(0)), delegate { PlayAnimation("relaxed_loop", true); });
/// </code>
/// and <c>new MegaSprite(node)</c> throws <c>InvalidOperationException("Expected BoundObject to be a
/// SpineSprite, but it is a {type}!")</c> for anything else (MegaSpineBinding.cs:119-143). Stock
/// Godot 4.5.1 has no <c>SpineSprite</c>, so a mod CANNOT satisfy that: a <c>SpineSprite</c> node in a
/// mod .tscn degrades to a placeholder Node.
///
/// The mod ships an animated <c>Node2D</c> merchant, so EVERY shop visit logged
/// <c>ERROR: System.InvalidOperationException: Expected BoundObject to be a SpineSprite, but it is a
/// Node2D!</c> -- observed in the round-39 verification run at the Act 2 Floor 12 shop, and for the old
/// <c>Sprite2D</c> merchant in the round-38 logs (godot2026-10-12T22.48.06.log:3943 and :7191). Godot
/// logs and swallows it, so the figure did render -- but a permanent ERROR on every shop visit is not
/// something to ship.
///
/// BaseLib cannot fix this for us. <c>MerchantCharacterAnimPatch</c> exists for exactly this case but
/// is dead code on the real path: it is guarded by <c>NodeFactory.CreatedFromFactory</c>, which is set
/// only in <c>CreateFromResource</c> (NodeFactory.cs:404) and <c>CreateFromScene</c> (:435), while the
/// game converts through the <c>PackedScene.Instantiate</c> postfix <c>TryAutoConvert</c> (:226-283),
/// which never sets it. These two prefixes are the mod's own version of that patch.
///
/// TWO SEPARATE CLASSES ON PURPOSE. Each carries the <c>[HarmonyPatch]</c> attribute on the CLASS.
/// A helper class with the attribute only on its methods is skipped silently by <c>PatchAll</c> --
/// which is exactly what happened on the first attempt here (the error kept appearing while the code
/// was demonstrably inside the shipped dll). The same pitfall is recorded in
/// <c>ModSelfCheck.cs</c>'s header for the same reason, and <c>ModSelfCheck</c> now also reports
/// whether these two attachments landed, so this can never regress silently again.
///
/// Both prefixes deliberately do nothing when child #0 IS a SpineSprite, so vanilla merchants (and any
/// other Spine-based mod's) are untouched.
/// </summary>
internal static class MerchantCharacterPatch
{
    /// <summary>The animation names the game asks a merchant for, mapped onto ours.</summary>
    internal static string? MapAnimation(string anim) => anim switch
    {
        "relaxed_loop" or "relaxed" or "idle" or "Idle" => "idle",
        "die" or "Die" or "dead" or "Dead" => "die",
        _ => null,
    };

    /// <summary>
    /// The flipbook merchant's <see cref="AnimationPlayer"/>, or null when child #0 is a SpineSprite
    /// (i.e. a vanilla merchant, which must be left alone).
    /// </summary>
    internal static AnimationPlayer? PlayerOf(Node merchant)
    {
        if (merchant is null || merchant.GetChildCount() == 0)
        {
            return null;
        }
        var first = merchant.GetChild(0);
        if (first is null || first.GetClass() == "SpineSprite")
        {
            return null;
        }
        return FindPlayer(first);
    }

    private static AnimationPlayer? FindPlayer(Node n)
    {
        if (n is AnimationPlayer ap)
        {
            return ap;
        }
        foreach (var child in n.GetChildren())
        {
            var got = FindPlayer(child);
            if (got is not null)
            {
                return got;
            }
        }
        return null;
    }
}

/// <summary>
/// Skips <c>NMerchantCharacter._Ready</c> for our own merchant. The original body is ONLY the
/// Spine-registration call above, so skipping it loses no other setup.
/// </summary>
[HarmonyPatch(typeof(NMerchantCharacter), nameof(NMerchantCharacter._Ready))]
internal static class MerchantCharacterReadyPatch
{
    [HarmonyPrefix]
    private static bool Prefix(NMerchantCharacter __instance)
    {
        try
        {
            var ap = MerchantCharacterPatch.PlayerOf(__instance);
            if (ap is null)
            {
                return true;                 // not ours: run the original (Spine) path untouched
            }
            if (!ap.IsPlaying())
            {
                ap.Play("idle");
            }
            return false;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"Merchant _Ready skip failed: {e}");
            return true;
        }
    }
}

/// <summary>
/// Redirects the merchant's animation requests (idle on ready, <c>"die"</c> from
/// NGameOverScreen.cs:982 when the player dies in a shop) onto our AnimationPlayer.
/// </summary>
[HarmonyPatch(typeof(NMerchantCharacter), nameof(NMerchantCharacter.PlayAnimation))]
internal static class MerchantCharacterPlayAnimationPatch
{
    [HarmonyPrefix]
    private static bool Prefix(NMerchantCharacter __instance, string anim)
    {
        try
        {
            var ap = MerchantCharacterPatch.PlayerOf(__instance);
            if (ap is null)
            {
                return true;
            }
            var mapped = MerchantCharacterPatch.MapAnimation(anim);
            if (mapped is null || !ap.HasAnimation(mapped))
            {
                // Unknown request: do not silently swallow it, let the game try (and log) as before.
                return true;
            }
            ap.Play(mapped);
            return false;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"Merchant PlayAnimation redirect failed: {e}");
            return true;
        }
    }
}
