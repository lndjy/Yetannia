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
///
/// <see cref="ILocalizationProvider"/> is here for the same "mod model with no vanilla loc entry"
/// reason: a mod power gets a <c>YETANNIA-…</c> id, so vanilla's <c>powers</c> table has no
/// <c>.title</c> for it and BaseLib logs <c>Key 'YETANNIA-TEMP_MIGHT_POWER.title' not found</c>
/// (visible in a release self-check until v1.1.1). The description happened to render from the
/// vanilla base class's own text, but the title did not.
/// </summary>
public sealed class TempMightPower : TemporaryStrengthPower, ICustomPower, ILocalizationProvider
{
    public override AbstractModel OriginModel => ModelDb.Card<Cards.RisingMight>();

    public string? CustomPackedIconPath => ModAssets.Image("powers/temp_might.png");

    public string? CustomBigIconPath => ModAssets.Image("powers_big/temp_might.png");

    public List<(string, string)>? Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new PowerLoc(
        "临时力量",
        "在本回合结束前获得[gold]力量[/gold]。",
        "在本回合结束前获得[gold]力量[/gold]。");

    private static readonly List<(string, string)> English = new PowerLoc(
        "Temporary Strength",
        "Gain [gold]Strength[/gold] until the end of this turn.",
        "Gain [gold]Strength[/gold] until the end of this turn.");
}
