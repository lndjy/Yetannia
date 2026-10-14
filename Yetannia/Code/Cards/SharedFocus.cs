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
/// 身先士卒 — 蓝卡，1 费（敲后 0 费）能力牌，多人专属。所有玩家获得 1 点敏捷。
///
/// 「所有玩家」照原版 <c>Rally</c> 的写法：<c>TargetType.AllAllies</c> 不做目标选择，
/// 再对 <c>GetTeammatesOf(自己)</c> 里所有存活玩家生效——它包含自己，所以「所有玩家」是真的所有人。
/// 这里用 <c>PowerCmd.Apply</c> 的集合重载一次施加，比逐个 await 更贴合原版的批量语义。
/// </summary>
public sealed class SharedFocus : YetanniaCard
{
    public SharedFocus()
        : base(1, CardType.Power, CardRarity.Uncommon, TargetType.AllAllies)
    {
    }

    public override CardMultiplayerConstraint MultiplayerConstraint =>
        CardMultiplayerConstraint.MultiplayerOnly;

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DynamicVar("Dexterity", 1)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        var teammates = AllLivingPlayers();
        if (teammates.Count == 0) return;

        await PowerCmd.Apply<DexterityPower>(
            choiceContext, teammates, DynamicVars["Dexterity"].BaseValue, Owner.Creature, this);
    }

    private List<Creature> AllLivingPlayers() =>
        Owner.Creature.CombatState
            .GetTeammatesOf(Owner.Creature)
            .Where(c => c != null && c.IsAlive && c.IsPlayer)
            .ToList();

    protected override void OnUpgrade() => EnergyCost.UpgradeBy(-1);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "身先士卒",
        "所有玩家获得{Dexterity:diff()}点[gold]敏捷[/gold]。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Lead the Charge",
        "All players gain {Dexterity:diff()} [gold]Dexterity[/gold].");
}
