using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 未命名·奋起 的临时力量 — real Strength now, taken back at the end of the turn.
///
/// This is the base game's <c>TemporaryStrengthPower</c> family: subclassing it supplies the
/// origin model (for the title) and inherits the whole apply/grant-back cycle, so no custom logic
/// is needed here.
///
/// <see cref="ICustomPower"/> is implemented alongside it, which is the one thing the vanilla base
/// class cannot provide. BaseLib's icon patches key off that interface, so without it
/// <c>PowerModel.PackedIconPath</c> falls through to the game's atlas lookup for
/// <c>yetannia-temp_might_power.tres</c> — a sprite that cannot exist — and the buff row draws
/// vanilla's <c>missing_power.png</c> placeholder instead. ICustomPower carries default interface
/// implementations, so implementing it adds art and nothing else; the power's behaviour stays
/// exactly the vanilla temporary-strength cycle.
/// </summary>
public sealed class TempMightPower : TemporaryStrengthPower, ICustomPower
{
    public override AbstractModel OriginModel => ModelDb.Card<Cards.RisingMight>();

    public string? CustomPackedIconPath => ModAssets.Image("powers/temp_might.png");

    public string? CustomBigIconPath => ModAssets.Image("powers_big/temp_might.png");
}
