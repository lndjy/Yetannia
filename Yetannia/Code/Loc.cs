using MegaCrit.Sts2.Core.Localization;

namespace Yetannia.YetanniaCode;

/// <summary>
/// Tiny helper for the in-code localization this mod uses (it ships no JSON loc tables, because
/// those would require a .pck).
/// </summary>
internal static class Loc
{
    public static bool IsEnglish => LocManager.Instance?.Language == "eng";

    public static T Pick<T>(T chinese, T english) => IsEnglish ? english : chinese;

    /// <summary>
    /// The inline energy icon, written the way the game's own <c>EnergyIconsFormatter</c> writes it.
    ///
    /// Cards that grant a variable amount of energy just write <c>{Energy:energyIcons()}</c> and let the
    /// formatter do this. A card or power whose amount is a hard-coded constant has no <c>EnergyVar</c>
    /// for the formatter to read, so it splices the tag in directly instead — that is the only reason
    /// this exists, and it keeps the wording in the vanilla shape (the icon carries the meaning, rather
    /// than writing out "2 点能量" beside a separate icon).
    ///
    /// The path is single-sourced through <see cref="ModAssets"/> so renaming the asset cannot leave a
    /// stale <c>res://</c> string behind in a localization table.
    /// </summary>
    public static readonly string EnergyIcon =
        $"[img]{ModAssets.Image("ui/energy_yetannia_small.png")}[/img]";

    /// <summary>
    /// That icon repeated <paramref name="amount"/> times, matching vanilla: <c>EnergyIconsFormatter</c>
    /// repeats the icon once per point for 1–3 and only switches to "N" plus a single icon from 4 up.
    /// </summary>
    public static string EnergyIcons(int amount)
    {
        if (amount < 1) return string.Empty;
        if (amount > 3) return amount.ToString() + EnergyIcon;
        return string.Concat(Enumerable.Repeat(EnergyIcon, amount));
    }
}
