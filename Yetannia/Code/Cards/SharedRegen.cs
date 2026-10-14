using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using BaseLib.Extensions;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 天之恩典 — 白卡，0 费技能，多人专属，消耗。所有玩家获得 2（敲后 3）点再生。
///
/// 用的是原版 <c>RegenPower</c>：它自带 <c>ShouldScaleInMultiplayer</c>，
/// 联机下的数值缩放由它自己处理，这里不要另算。
/// </summary>
public sealed class SharedRegen : YetanniaCard
{
    private const int RegenBase = 2;
    private const int RegenUpgrade = 1; // 2 -> 3

    public SharedRegen()
        : base(0, CardType.Skill, CardRarity.Common, TargetType.AllAllies)
    {
    }

    public override CardMultiplayerConstraint MultiplayerConstraint =>
        CardMultiplayerConstraint.MultiplayerOnly;

    public override IEnumerable<CardKeyword> CanonicalKeywords => [CardKeyword.Exhaust];

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DynamicVar("Regen", RegenBase)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var teammates = Owner.Creature.CombatState
            .GetTeammatesOf(Owner.Creature)
            .Where(c => c != null && c.IsAlive && c.IsPlayer)
            .ToList();

        if (teammates.Count == 0) return;

        await PowerCmd.Apply<RegenPower>(
            choiceContext, teammates, DynamicVars["Regen"].BaseValue, Owner.Creature, this);
    }

    protected override void OnUpgrade() => DynamicVars["Regen"].UpgradeValueBy(RegenUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "天之恩典",
        "所有玩家获得{Regen:diff()}点[gold]再生[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Heaven's Grace",
        "All players gain {Regen:diff()} [gold]Regeneration[/gold].");
}
