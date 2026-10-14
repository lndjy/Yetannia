using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Powers;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 韬光养晦 — 蓝卡（Uncommon），1 费技能：
/// 在本回合保留你的手牌；将手牌中任意数量牌置于抽牌堆顶；下回合获得 1（升级 2）点[能量]。
///
/// The steps run in the order the request lists them, which matters: retain is applied first so the
/// end-of-turn discard is skipped, then the player picks what to put back, then the energy is banked.
/// The card does *not* end the turn (an earlier version did; the request removed that clause).
///
/// Retain uses <c>CardCmd.ApplySingleTurnRetain</c> (the base game's Expertise helper) rather than
/// adding the Retain keyword, so it wears off on its own.
/// </summary>
public sealed class BideTime : YetanniaCard
{
    private const int BaseEnergy = 1;
    private const int EnergyUpgrade = 1; // 1 -> 2

    public BideTime()
        : base(1, CardType.Skill, CardRarity.Uncommon, TargetType.Self)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
        [new EnergyVar(BaseEnergy)];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        // 1) Retain the hand through the end of this turn.
        foreach (var card in PileType.Hand.GetPile(Owner).Cards.ToList())
        {
            CardCmd.ApplySingleTurnRetain(card);
        }

        // 2) Put any number of them back on top of the draw pile.
        var handSize = PileType.Hand.GetPile(Owner).Cards.Count;
        if (handSize > 0)
        {
            var prefs = new CardSelectorPrefs(SelectionScreenPrompt, 0, handSize);
            var chosen = (await CardSelectCmd.FromHand(
                prefs: prefs,
                context: choiceContext,
                player: Owner,
                filter: null,
                source: this)).ToList();

            if (chosen.Count > 0)
            {
                // Top == index 0, so reversing keeps the chosen order.
                await CardPileCmd.Add(chosen.AsEnumerable().Reverse(), PileType.Draw, CardPilePosition.Top);
            }
        }

        // 3) Bank energy for next turn.
        await PowerCmd.Apply<EnergyNextTurnPower>(
            choiceContext, Owner.Creature, DynamicVars.Energy.BaseValue, Owner.Creature, this);
    }

    protected override void OnUpgrade() => DynamicVars.Energy.UpgradeValueBy(EnergyUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "韬光养晦",
        "在本回合保留你的手牌。将手牌中任意数量的牌置于抽牌堆顶。下回合获得{Energy:energyIcons()}。",
        ("selectionScreenPrompt", "选择要放到抽牌堆顶的牌。"));

    private static readonly List<(string, string)> English = new CardLoc(
        "Bide Time",
        "Retain your hand this turn. Put any number of cards from your hand on top of your draw pile. Gain {Energy:energyIcons()} next turn.",
        ("selectionScreenPrompt", "Choose cards to put on top of your draw pile."));
}
