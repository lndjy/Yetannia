using BaseLib.Abstracts;
using BaseLib.Utils;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Character;

namespace Yetannia.YetanniaCode.Relics;

/// <summary>
/// Base class for Yetannia's relics. The <see cref="PoolAttribute"/> ties every subclass to
/// <see cref="YetanniaRelicPool"/>, so individual relics only need to set their rarity and effects.
/// </summary>
[Pool(typeof(YetanniaRelicPool))]
public abstract class YetanniaRelic : CustomRelicModel
{
    /// <summary>
    /// File-name stem of this relic's art, shipped in the mod's pck as
    /// <c>images/relics/&lt;IconBaseName&gt;.png</c> (64×64, the top-bar/inventory icon) and
    /// <c>images/relics_big/&lt;IconBaseName&gt;.png</c> (256×256, the inspect screen).
    ///
    /// The base game resolves relic art through a shared texture atlas whose entries are keyed by this
    /// same name, and a mod cannot add entries to a shipped atlas — so the three icon getters below are
    /// redirected at our own loose textures instead. <c>IconBaseName</c> therefore names *our* files,
    /// not a vanilla atlas entry.
    /// </summary>
    protected override string IconBaseName => "prophets_eye";

    public override string PackedIconPath => ModAssets.Image($"relics/{IconBaseName}.png");

    /// <summary>
    /// Vanilla reads a matching silhouette from <c>relic_outline_atlas</c>, which we also cannot extend.
    /// The main icon doubles as the outline layer: the highlight effect keeps working without a second
    /// piece of art per relic, at the cost of the glow being a copy of the icon itself.
    /// </summary>
    protected override string PackedIconOutlinePath => ModAssets.Image($"relics/{IconBaseName}.png");

    protected override string BigIconPath => ModAssets.Image($"relics_big/{IconBaseName}.png");

    /// <summary>
    /// The 256×256 inspect-screen path, exposed for the startup self-check only.
    ///
    /// <see cref="RelicModel"/> keeps <c>BigIconPath</c> protected and its public surface
    /// (<c>BigIcon</c>) loads through a cache that hides a miss behind the missing-icon placeholder, so
    /// the check cannot otherwise tell "our texture loaded" from "fell back to the placeholder". Reading
    /// the real path is what makes the check meaningful.
    /// </summary>
    public string BigIconPathForCheck => BigIconPath;
}
