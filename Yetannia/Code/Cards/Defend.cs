using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 防御 — the character's basic Skill, a mechanical copy of the base game's Defend.
///
/// Custom copy for the same reason as <see cref="Strike"/>: the base game's <c>DefendIronclad</c> is
/// a plain <c>CardModel</c> and therefore cannot pick up
/// <see cref="YetanniaCard.CustomPortraitPath"/>. Numbers, tag and rarity are identical to the base
/// game (1 energy, 5 Block, +3 upgraded, Basic, <see cref="CardTag.Defend"/>).
///
/// Named <c>Defend</c> rather than <c>YetanniaDefend</c> so the model ID is <c>YETANNIA-DEFEND</c>
/// instead of the redundant <c>YETANNIA-YETANNIA_DEFEND</c>.
/// </summary>
public sealed class Defend : YetanniaCard
{
    public override bool GainsBlock => true;

    protected override HashSet<CardTag> CanonicalTags => [CardTag.Defend];

    public Defend()
        : base(1, CardType.Skill, CardRarity.Basic, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new BlockVar(5m, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await CreatureCmd.GainBlock(Owner.Creature, DynamicVars.Block, cardPlay);
    }

    protected override void OnUpgrade() => DynamicVars.Block.UpgradeValueBy(3m);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "防御",
        "获得{Block:diff()}点[gold]格挡[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Defend",
        "Gain {Block:diff()} Block.");
}
