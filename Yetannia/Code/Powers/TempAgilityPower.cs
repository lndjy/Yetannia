using System.Collections.Generic;
using System.Threading.Tasks;
using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Powers;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Powers;

/// <summary>
/// 未命名·从容 的临时敏捷 — see <see cref="TempMightPower"/>.
///
/// The vanilla base class it derives from removes the temporary dexterity at the first
/// <c>AfterSideTurnEnd</c> where the owner is among the participants, and it subtracts the power's
/// *whole stack* (<c>-Sign * Amount</c>) rather than what any single application added. That is fine on
/// its own, but it interacts with 从容's second half — the permanent dexterity granted at the end of the
/// ENEMY's turn — so the removal is traced. Which of the two listeners runs first decides whether the
/// permanent grant survives, and that ordering is not something either class can see.
///
/// <see cref="ICustomPower"/> supplies the art that the vanilla base class has no seam for; see
/// <see cref="TempMightPower"/> for why it is needed. It is a pure addition — the inherited
/// apply/remove cycle is untouched.
/// </summary>
public sealed class TempAgilityPower : TemporaryDexterityPower, ICustomPower
{
    public override AbstractModel OriginModel => ModelDb.Card<Cards.SteadyAgility>();

    public string? CustomPackedIconPath => ModAssets.Image("powers/temp_agility.png");

    public string? CustomBigIconPath => ModAssets.Image("powers_big/temp_agility.png");

    public override async Task AfterSideTurnEnd(
        PlayerChoiceContext choiceContext, CombatSide side, IEnumerable<Creature> participants)
    {
        var owner = Owner;
        var participates = owner != null && participants.Contains(owner);

        MainFile.Logger.Info(
            $"[dextrack] TempAgility.AfterSideTurnEnd side={side} ownerInParticipants={participates} " +
            $"stack={Amount} dexBefore={DexterityOf(owner)}");

        await base.AfterSideTurnEnd(choiceContext, side, participants);

        MainFile.Logger.Info($"[dextrack] TempAgility.AfterSideTurnEnd done: dexAfter={DexterityOf(owner)}");
    }

    /// <summary>Current Dexterity on the creature, for the trace. -1 when there is nothing to read.</summary>
    internal static int DexterityOf(Creature? creature)
        => creature?.GetPower<DexterityPower>()?.Amount ?? 0;
}
