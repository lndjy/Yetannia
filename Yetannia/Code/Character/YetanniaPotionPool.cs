using BaseLib.Abstracts;
using Godot;

namespace Yetannia.YetanniaCode.Character;

/// <summary>
/// Yetannia's potion pool. Empty for now; a character still needs one.
/// </summary>
public class YetanniaPotionPool : CustomPotionPoolModel
{
    public override Color LabOutlineColor => YetanniaCharacter.Color;

    /// <summary>Base game energy colour; avoids shipping energy icon art.</summary>
    public override string EnergyColorName => "colorless";
}
