using BaseLib.Abstracts;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Localization.DynamicVars;
using MegaCrit.Sts2.Core.ValueProps;

namespace Yetannia.YetanniaCode.Cards;

/// <summary>
/// 冰刃轮舞 — 金卡（Rare），2 费攻击：
/// 对所有敌人造成 5 点伤害，4（升级 5）次。
/// 本场战斗中你每洗牌一次，这张牌获得重放 1。
///
/// Name is a placeholder (the request did not give one).
///
/// Replay is <c>CardModel.BaseReplayCount</c>: the card is played <c>BaseReplayCount + 1</c> times,
/// which for this card means the whole 4/5-hit volley happens again. It is raised from
/// <c>AfterShuffle</c>, a hook cards in combat piles receive directly.
///
/// Note that the shuffle at the start of combat also fires this hook, so the card typically enters
/// the first turn already at Replay 1.
/// </summary>
public sealed class ShuffleReplay : YetanniaCard
{
    private const int BaseDamage = 5;
    private const int BaseHits = 4;
    private const int HitsUpgrade = 1; // 4 -> 5

    public ShuffleReplay()
        : base(2, CardType.Attack, CardRarity.Rare, TargetType.AllEnemies)
    {
    }

    protected override IEnumerable<DynamicVar> CanonicalVars =>
    [
        new DamageVar(BaseDamage, ValueProp.Move),
        new RepeatVar(BaseHits)
    ];

    protected override async Task OnPlay(PlayerChoiceContext choiceContext, CardPlay cardPlay)
    {
        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .WithHitCount(DynamicVars.Repeat.IntValue)
            .FromCard(this, cardPlay)
            .TargetingAllOpponents(CombatState)
            .WithHitFx("vfx/vfx_attack_slash")
            .Execute(choiceContext);
    }

    /// <summary>本场战斗中每洗牌一次，此牌获得重放 1。</summary>
    public override Task AfterShuffle(PlayerChoiceContext choiceContext, Player shuffler)
    {
        if (shuffler != Owner) return Task.CompletedTask;

        BaseReplayCount += 1;
        return Task.CompletedTask;
    }

    protected override void OnUpgrade() => DynamicVars.Repeat.UpgradeValueBy(HitsUpgrade);

    public override List<(string, string)> Localization => Loc.Pick(Chinese, English);

    private static readonly List<(string, string)> Chinese = new CardLoc(
        "冰刃轮舞",
        "对所有敌人造成{Damage:diff()}点伤害，{Repeat:diff()}次。\n本场战斗中你每洗牌一次，这张牌获得重放1。");

    private static readonly List<(string, string)> English = new CardLoc(
        "Ice Blade Waltz",
        "Deal {Damage:diff()} damage to ALL enemies {Repeat:diff()} times.\nWhenever you shuffle this combat, this card gains Replay 1.");
}
