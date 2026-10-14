using BaseLib.Abstracts;
using Godot;

namespace Yetannia.YetanniaCode.Character;

/// <summary>
/// Yetannia's relic pool.
/// </summary>
public class YetanniaRelicPool : CustomRelicPoolModel
{
    public override Color LabOutlineColor => YetanniaCharacter.Color;

    /// <summary>Base game energy colour; avoids shipping energy icon art.</summary>
    public override string EnergyColorName => "colorless";
}
