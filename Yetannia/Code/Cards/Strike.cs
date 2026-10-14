using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 打击 — the character's basic Attack, a mechanical copy of the base game's Strike.
///
/// It is not the base game's <c>StrikeIronclad</c> because that card belongs to Ironclad and draws
/// Ironclad's portrait: <see cref="YetanniaCard.CustomPortraitPath"/> only applies to
/// <c>CustomCardModel</c> subclasses, and <c>StrikeIronclad</c> derives straight from <c>CardModel</c>.
/// Deriving our own copy is what lets the basic cards use the blank card face too.
///
/// Numbers, tag and rarity match the base game exactly (1 energy, 6 damage, +3 upgraded, Basic,
/// <see cref="CardTag.Strike"/>) so anything that counts Strike cards keeps working.
///
/// The class is named <c>Strike</c> rather than <c>YetanniaStrike</c> because the model ID is built
/// from the mod prefix plus the class name — the longer name produced the redundant
/// <c>YETANNIA-YETANNIA_STRIKE</c>.
/// </summary>
public sealed class Strike : YetanniaCard
{
    protected override HashSet<CardTag> CanonicalTags => [CardTag.Strike];

    public Strike()
        : base(1, CardType.Attack, CardRarity.Basic, TargetType.AnyEnemy)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new DamageVar(6m, ValueProp.Move)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        ArgumentNullException.ThrowIfNull(cardPlay.Target, "cardPlay.Target");

        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, cardPlay)
            .Targeting(cardPlay.Target)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(3m);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "打击",
        "造成{Damage:diff()}点伤害。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Strike",
        "Deal {Damage:diff()} damage.");
}
