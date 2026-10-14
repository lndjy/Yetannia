using BaseLib.Patches.Content;
using MegaCrit.Sts2.Core.Entities.Cards;

namespace Yetannia.YetanniaCode.Keywords;

/// <summary>
/// Custom card keywords for Yetannia.
///
/// BaseLib generates the actual <see cref="CardKeyword"/> value from the field marked with
/// <see cref="CustomEnumAttribute"/>, and names it "&lt;ROOT NAMESPACE&gt;-&lt;NAME&gt;". With this
/// mod's root namespace ("Yetannia") that yields the localization key <c>YETANNIA-PROPHET</c>,
/// which <see cref="KeywordLocPatch"/> injects into the game's <c>card_keywords</c> table.
/// </summary>
public static class YetanniaKeywords
{
    /// <summary>
    /// 先知 (Prophet): when this card moves from the draw pile to the discard pile, its Prophet
    /// effect triggers.
    ///
    /// <see cref="AutoKeywordPosition.None"/> keeps BaseLib from appending the keyword name to card
    /// descriptions automatically, because Yetannia's cards spell the Prophet effect out inline
    /// ("先知：..."). The keyword still gets its hover tooltip and its <c>card_keywords</c> entries.
    /// </summary>
    [CustomEnum("Prophet")]
    [KeywordProperties(AutoKeywordPosition.None)]
    public static CardKeyword Prophet;
}
