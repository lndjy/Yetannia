using System;
using System.Linq;
using BaseLib.Abstracts;
using BaseLib.Utils.NodeFactories;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.RestSite;
using MegaCrit.Sts2.Core.Nodes.Screens.MainMenu;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;
using Yetannia.YetanniaCode.Cards;
using Yetannia.YetanniaCode.Character;
using Yetannia.YetanniaCode.Keywords;
using Yetannia.YetanniaCode.Powers;
using Yetannia.YetanniaCode.Relics;

namespace Yetannia.YetanniaCode;

/// <summary>
/// Logs what the mod actually managed to register once the content database is built.
/// Loading without an exception does not prove that the character, cards, relic and keyword all
/// made it into <see cref="ModelDb"/>, and this check makes that visible in the game log.
/// It is a read-only diagnostic; delete it if you do not want the extra log lines.
///
/// Split into two patch classes on purpose: Harmony reliably picks up patch classes that carry the
/// [HarmonyPatch] attribute on the *class*, but a class with the attribute only on its methods can
/// be skipped silently by PatchAll (which is exactly what happened when both lived here).
/// </summary>
[HarmonyPatch(typeof(ModelDb), nameof(ModelDb.Init))]
internal static class ModSelfCheck
{
    [HarmonyPostfix]
    private static void Report()
    {
        try
        {
            var log = MainFile.Logger;

            log.Info($"self-check character  : registered={Registered(typeof(YetanniaCharacter))}");
            log.Info($"self-check pools      : card={Registered(typeof(YetanniaCardPool))} relic={Registered(typeof(YetanniaRelicPool))} potion={Registered(typeof(YetanniaPotionPool))}");
            log.Info($"self-check cards      : testAttack={Registered(typeof(TestAttack))} testSkill={Registered(typeof(TestSkill))} ward={Registered(typeof(ForesightWard))} decree={Registered(typeof(OminousDecree))}");
            log.Info($"self-check relic      : prophetsEye={Registered(typeof(ProphetsEye))} prophetsEyePlus={Registered(typeof(ProphetsEyePlus))}");
            log.Info($"self-check ancients   : transcendence={Registered(typeof(OminousDecreeTranscendent))} darvTome={Registered(typeof(DarvsProphecy))}");
            log.Info($"self-check powers     : tally={Registered(typeof(ProphetTallyPower))} foresight={Registered(typeof(ForesightPower))} nirvana={Registered(typeof(NirvanaPower))} study={Registered(typeof(PropheticStudyPower))} cycle={Registered(typeof(CycleOfProphecyPower))} pureLove={Registered(typeof(PureLoveFormPower))} echo={Registered(typeof(DelayedEchoPower))} delayedScry={Registered(typeof(DelayedScryPower))} might={Registered(typeof(ScryMightPower))} agility={Registered(typeof(ScryAgilityPower))} judgement={Registered(typeof(JudgementPower))} tempMight={Registered(typeof(TempMightPower))} tempAgility={Registered(typeof(TempAgilityPower))}");
            log.Info($"self-check keyword    : prophet=(CardKeyword){(int)YetanniaKeywords.Prophet}");

            log.Info($"self-check keyword loc: title={LocString.Exists("card_keywords", "YETANNIA-PROPHET.title")} description={LocString.Exists("card_keywords", "YETANNIA-PROPHET.description")}");
            log.Info($"self-check char loc   : title={ExistsIn("characters", typeof(YetanniaCharacter), ".title")} unlockText={ExistsIn("characters", typeof(YetanniaCharacter), ".unlockText")}");

            var pool = ModelDb.CardPool<YetanniaCardPool>();
            var poolCards = pool.AllCards.ToList();
            log.Info($"self-check card pool  : {poolCards.Count} card(s)");
            ReportComposition(poolCards, log);
            var unresolved = new List<string>();
            foreach (var card in poolCards)
            {
                log.Info($"self-check card       : {card.Id.Entry} [{card.Rarity} {card.Type}] cost={card.EnergyCost.Canonical} keywords={DescribeKeywords(card)}");
                log.Info($"self-check card loc   : {card.Id.Entry} title={LocString.Exists("cards", card.Id.Entry + ".title")} desc={LocString.Exists("cards", card.Id.Entry + ".description")}");
                log.Info($"self-check base vars  : {card.Id.Entry} {DescribeVars(card)}");

                // Render the description the way the card library does. A {Placeholder} that does not
                // match any DynamicVar is left in the text verbatim, so surface those loudly.
                var rendered = RenderDescription(card);
                log.Info($"self-check desc       : {card.Id.Entry} {rendered}");
                if (IsUnresolved(rendered))
                {
                    unresolved.Add(card.Id.Entry);
                }
            }
            if (unresolved.Count > 0)
            {
                log.Error($"self-check UNRESOLVED placeholders in: {string.Join(", ", unresolved)}");
            }

            log.Info($"self-check relic pool : {ModelDb.RelicPool<YetanniaRelicPool>().AllRelics.Count()} relic(s)");
            log.Info($"self-check relic loc  : title={ExistsIn("relics", typeof(ProphetsEye), ".title")} description={ExistsIn("relics", typeof(ProphetsEye), ".description")}");

            var character = ModelDb.Character<YetanniaCharacter>();
            var deck = character.StartingDeck.ToList();
            log.Info($"self-check starting deck ({deck.Count}): {string.Join(", ", deck.Select(c => c.Id.Entry))}");
            log.Info($"self-check starting relic: {string.Join(", ", character.StartingRelics.Select(r => r.Id.Entry))}");

            // Relic text is built in code (the numbers are interpolated), so render it and eyeball it.
            foreach (var relic in ModelDb.RelicPool<YetanniaRelicPool>().AllRelics)
            {
                log.Info($"self-check relic desc : {relic.Id.Entry} {DescribeRelic(relic)}");

                // Relic art: YetanniaRelic redirects PackedIconPath / PackedIconOutlinePath / BigIconPath
                // at our own pck textures (the vanilla atlas cannot be extended by a mod).
                //
                // Read the paths off the relic itself rather than rebuilding them from the id: in this
                // game ModelId.Entry carries the "YETANNIA-" prefix, so id-derived file names do not
                // match the art names and a rebuilt path reports a false miss.
                var relicIcon = (relic as YetanniaRelic)?.IconPath ?? string.Empty;
                var relicBig = (relic as YetanniaRelic)?.BigIconPathForCheck ?? string.Empty;
                log.Info(
                    $"self-check relic icon : {relic.Id.Entry} {relicIcon} " +
                    $"packed={Exists(relicIcon)}/{Describe(LoadTexture(relicIcon))} " +
                    $"big={Exists(relicBig)}/{Describe(LoadTexture(relicBig))}");
            }

            // The relic display names and the character blurb are pure loc strings with no other
            // runtime check anywhere: a rename that missed one language, or a key that no longer
            // exists, would otherwise only be visible on the relics screen / select screen. Print
            // what actually resolves, in the language that is loaded right now.
            foreach (var relicType in new[] { typeof(ProphetsEye), typeof(ProphetsEyePlus) })
            {
                var relicId = ModelDb.GetId(relicType).Entry;
                log.Info($"self-check relic name : {relicId} {Resolve("relics", relicId + ".title")}");
                log.Info($"self-check relic flavor: {relicId} {Resolve("relics", relicId + ".flavor")}");
            }
            log.Info($"self-check char blurb : {Resolve("characters", ModelDb.GetId(typeof(YetanniaCharacter)).Entry + ".description")}");

            // Powers get their own pass because PowerModel has NO DynamicDescription: it assembles
            // its tooltip by hand in HoverTips. A power whose text names a var it never declares
            // therefore fails only when its tooltip is first opened — in game, mid-combat. That is
            // exactly how the {Threshold} bug (cards frozen mid-screen) reached a tester.
            //
            // ToMutable() is required, but NOT for the reason this comment used to give. It claimed the
            // canonical instance's DynamicVars throw CanonicalModelException; that is wrong. Grepping the
            // game, CanonicalModelException is thrown from exactly one place — AbstractModel.AssertMutable,
            // when !IsMutable — and reading DynamicVars does not go through it. Measured: 983 canonical
            // power renders completed without throwing, so the read is safe.
            //
            // The real reason is that ToMutable() is what the runtime itself hands to the UI, so rendering
            // the clone is the closer match to what the player actually sees; and the check stays strictly
            // read-only with respect to the registered models, so nothing it does can perturb a live run.
            var unresolvedPowers = new List<string>();
            var unresolvedIcons = new List<string>();
            var unresolvedDumbPowers = new List<string>();
            // Enumerated from ModelDb rather than hand-listed. The hand-written version silently missed
            // every power added after it was written — StarscarFormPower was shipped without its icon ever
            // being checked, and a missing icon in this list is not a crash, it is a placeholder the
            // self-check is supposed to catch. Filtered to this mod's own namespace so vanilla powers
            // (whose art lives in the game's own atlas) are not reported as failures.
            foreach (var power in ModelDb.AllPowers
                         // "Yetannia." with the dot, deliberately. A bare "Yetannia" prefix also matches any
                         // namespace that merely *begins* with those letters — QA's own scaffolding mod uses
                         // YetanniaQA.*, so this filter swept up its test power and the self-check reported
                         // "MISSING power icons" against a power that is not ours. Noisy while testing, and
                         // misleading in a player's log if any third-party mod ever picks a similar prefix.
                         .Where(p => p.GetType().Namespace?.StartsWith("Yetannia.", StringComparison.Ordinal) == true)
                         .Select(p => p.ToMutable()))
            {
                var rendered = DescribePower(power);
                log.Info($"self-check power desc : {power.Id.Entry} {rendered}");
                if (IsUnresolved(rendered))
                {
                    unresolvedPowers.Add(power.Id.Entry);
                }

                // Power art: BaseLib patches PowerModel.PackedIconPath / BigIconPath / BigBetaIconPath to
                // return CustomPackedIconPath / CustomBigIconPath / CustomBigBetaIconPath. Those two are
                // the 64×64 the combat buff row draws and the 256×256 inspect art, so both must actually
                // load — a path that exists but fails to import renders as nothing.
                //
                // Only this mod's powers are checked. Vanilla powers keep their art in the game's own
                // atlas, where ResourceLoader.Exists reports false even though the texture loads fine, so
                // including them would be pure false noise.
                //
                // NOTE: this must test the INTERFACE, not CustomPowerModel. BaseLib's icon patches key off
                // `is ICustomPower`, and ICustomPower carries default interface implementations, so a power
                // is free to inherit a *vanilla* base class (e.g. TemporaryStrengthPower) and still supply
                // its own art. Reading `as CustomPowerModel` here silently skipped exactly those powers —
                // which is how TEMP_MIGHT_POWER / TEMP_AGILITY_POWER shipped drawing vanilla's
                // missing_power.png placeholder in the buff row while this check reported nothing at all.
                var custom = power as ICustomPower;
                var packedIcon = custom?.CustomPackedIconPath ?? string.Empty;
                var bigIcon = custom?.CustomBigIconPath ?? string.Empty;
                if (string.IsNullOrEmpty(packedIcon))
                {
                    // A visible mod power with no icon path falls through to the game's atlas lookup for
                    // "<mod>-<id>", which cannot exist, so it renders missing_power.png. That is a real
                    // shipped defect, not a benign omission — say so instead of skipping in silence.
                    if (power.IsVisible)
                    {
                        log.Error(
                            "self-check NO ICON PATH: " + power.Id.Entry +
                            " is a visible mod power with no CustomPackedIconPath; it renders the vanilla " +
                            "missing_power.png placeholder in the buff row. Either give it art via " +
                            "ICustomPower, or hide it (IsVisibleInternal => false).");
                        unresolvedIcons.Add($"{power.Id.Entry} (no custom icon path — vanilla placeholder)");
                    }
                }
                else
                {
                    // Exists() returns a printable string, so the pass/fail test is spelled out here.
                    var packedOk = Godot.ResourceLoader.Exists(packedIcon) && LoadTexture(packedIcon) != null;
                    var bigOk = !string.IsNullOrEmpty(bigIcon)
                                && Godot.ResourceLoader.Exists(bigIcon)
                                && LoadTexture(bigIcon) != null;
                    log.Info(
                        $"self-check icon       : {power.Id.Entry} " +
                        $"packed={Exists(packedIcon)}/{Describe(LoadTexture(packedIcon))} " +
                        $"big={Exists(bigIcon)}/{Describe(LoadTexture(bigIcon))}");
                    if (!packedOk)
                    {
                        unresolvedIcons.Add($"{power.Id.Entry} (packed {packedIcon})");
                    }
                    if (!bigOk)
                    {
                        unresolvedIcons.Add($"{power.Id.Entry} (big {bigIcon})");
                    }
                }

                // Engine-口径 render, deliberately separate from DescribePower above. Runs for every mod
                // power, with or without art, so a power that is missing its icon still gets its
                // description checked.
                //
                // DescribePower adds the model's DynamicVars itself, which makes it the UNION of the
                // engine's two rendering paths — and therefore structurally incapable of noticing a
                // description that only renders correctly on one of them. HoverTipFactory.FromPower<T>()
                // goes through GetDumbHoverTip, which adds far fewer variables, so it is rendered on its
                // own here. This is the check that would have caught {Threshold:diff()} rendering as
                // literal braces on 预见之力 / 预见之敏.
                var dumb = DescribeDumbPower(power);
                if (dumb.Contains('{'))
                {
                    unresolvedDumbPowers.Add($"{power.Id.Entry}: {dumb}");
                }
            }
            if (unresolvedPowers.Count > 0)
            {
                log.Error($"self-check UNRESOLVED placeholders in powers: {string.Join(", ", unresolvedPowers)}");
            }
            if (unresolvedIcons.Count > 0)
            {
                log.Error($"self-check MISSING power icons: {string.Join(", ", unresolvedIcons)}");
            }
            foreach (var dumbPower in unresolvedDumbPowers)
            {
                log.Error(
                    "self-check DUMB PATH placeholder left in a power (renders fine in the power bar but " +
                    $"literally in HoverTipFactory.FromPower<> tips): {dumbPower}");
            }

            // The Architect's WinRun dereferences a null Dialogue for characters without one, so a
            // Harmony patch has to be attached for the run to be finishable. PatchAll silently skips
            // patch classes it cannot read, so verify the attachment rather than assuming it.
            var architectWinRun = AccessTools.Method(typeof(MegaCrit.Sts2.Core.Models.Events.TheArchitect), "WinRun");
            var architectPatches = architectWinRun == null ? null : Harmony.GetPatchInfo(architectWinRun);
            log.Info($"self-check architect  : target={architectWinRun != null} prefixes={architectPatches?.Prefixes?.Count ?? 0}");

            // 未命名·反击's strict per-target gate lives on CanPlayTargeting; verify it is attached.
            var canPlayTargeting = AccessTools.Method(typeof(CardModel), nameof(CardModel.CanPlayTargeting));
            var counterPatches = canPlayTargeting == null ? null : Harmony.GetPatchInfo(canPlayTargeting);
            log.Info($"self-check counter    : target={canPlayTargeting != null} postfixes={counterPatches?.Postfixes?.Count ?? 0}");

            // 先知的手链 injects an option into every event through this wrapper postfix.
            var optionsWrapper = AccessTools.Method(typeof(MegaCrit.Sts2.Core.Models.EventModel), "GenerateInitialOptionsWrapper");
            var eventPatches = optionsWrapper == null ? null : Harmony.GetPatchInfo(optionsWrapper);
            log.Info($"self-check event skip : target={optionsWrapper != null} postfixes={eventPatches?.Postfixes?.Count ?? 0}");

            // 条件高亮：先知牌在预见时发金光，挂在 NCardGrid.InitGrid()（无参重载）上。
            var highlightTarget = AccessTools.Method(typeof(NCardGrid), "InitGrid", Type.EmptyTypes);
            var highlightPatches = highlightTarget == null ? null : Harmony.GetPatchInfo(highlightTarget);
            log.Info($"self-check highlight  : target={highlightTarget != null} postfixes={highlightPatches?.Postfixes?.Count ?? 0}");

            // The merchant figure is an animated Node2D while NMerchantCharacter._Ready wraps GetChild(0)
            // in `new MegaSprite(...)`, which throws for anything but a SpineSprite. MerchantCharacterPatch
            // prefixes _Ready and PlayAnimation to take over for a non-Spine child; report the attachment
            // here because the failure mode is silent (the first version of that patch used method-level
            // [HarmonyPatch] attributes, which PatchAll skips, and the ERROR kept appearing in game).
            var merchantReady = AccessTools.Method(typeof(NMerchantCharacter), nameof(NMerchantCharacter._Ready));
            var merchantReadyPatches = merchantReady == null ? null : Harmony.GetPatchInfo(merchantReady);
            var merchantPlay = AccessTools.Method(typeof(NMerchantCharacter), nameof(NMerchantCharacter.PlayAnimation));
            var merchantPlayPatches = merchantPlay == null ? null : Harmony.GetPatchInfo(merchantPlay);
            log.Info($"self-check merchant   : readyTarget={merchantReady != null} readyPrefixes={merchantReadyPatches?.Prefixes?.Count ?? 0} playTarget={merchantPlay != null} playPrefixes={merchantPlayPatches?.Prefixes?.Count ?? 0}");

            // Art comes from Yetannia.pck; a missing .pck silently yields null textures, so check them.
            log.Info($"self-check art        : selectIcon={Describe(character.CharacterSelectIcon)} locked={Describe(character.CharacterSelectLockedIcon)} hud={Describe(character.IconTexture)}");
            log.Info($"self-check art paths  : {character.CustomCharacterSelectIconPath} | {character.CustomIconTexturePath}");

            // The multiplayer-only "this is me" colours (the map quill's ink, a map ping, and the line
            // drawn to whatever I am aiming at). Nothing in a single-player run reads them, so no other
            // check in this file can cover them — printing the resolved values is what turns "the class
            // overrides MapDrawingColor" into something a QA log can assert on.
            //
            // Read through a CharacterModel reference on purpose: these are virtuals whose base
            // implementation is Colors.Black, so a silently-absent override shows up here as 000000
            // instead of as a cheerful echo of what this file believes it wrote. (That was the actual
            // state until now: BaseLib 3.4.7 does not mention any of the three, and BaseLib is what the
            // arm textures and SFX slots come from, so there was nothing to derive them from.)
            var asBaseModel = (CharacterModel)character;
            log.Info(
                $"self-check mp colours : draw={asBaseModel.MapDrawingColor.ToHtml(false)} " +
                $"targeting={asBaseModel.RemoteTargetingLineColor.ToHtml(false)} " +
                $"outline={asBaseModel.RemoteTargetingLineOutline.ToHtml(false)} " +
                $"name={asBaseModel.NameColor.ToHtml(false)}");

            // Scene-based models (combat figure / campfire / merchant / select backdrop).
            // They are only *registered* later (BaseLib registers them from a ModelDb.Preload
            // postfix), so the actual instantiation check lives in ReportSceneConversions below.
            log.Info($"self-check scenes     : visuals={Exists(character.CustomVisualPath)} rest={Exists(character.CustomRestSiteAnimPath)} merchant={Exists(character.CustomMerchantAnimPath)} selectBg={Exists(character.CustomCharacterSelectBg)}");

            // Card faces: 白/蓝 cards share one texture and 金 cards use another, both from the pck.
            // BaseLib re-routes CardModel.Portrait / .PortraitPath / .PortraitPngPath through
            // CustomPortraitPath, and it loads PortraitPath with ResourceLoader.Load<Texture2D>(...)
            // without a null check — so Exists() alone is not enough, the texture has to actually load.
            log.Info($"self-check card art   : normal={Exists(ModAssets.Image("card_portraits/test.png"))}/{Describe(LoadTexture(ModAssets.Image("card_portraits/test.png")))} rare={Exists(ModAssets.Image("card_portraits/test2.png"))}/{Describe(LoadTexture(ModAssets.Image("card_portraits/test2.png")))}");
            log.Info($"self-check card art by: common={FirstPortraitOf(CardRarity.Common)} uncommon={FirstPortraitOf(CardRarity.Uncommon)} rare={FirstPortraitOf(CardRarity.Rare)} basic={FirstPortraitOf(CardRarity.Basic)} ancient={FirstPortraitOf(CardRarity.Ancient)}");

            // The rect a card portrait is drawn into depends on the card's RARITY, and that is the whole
            // reason this mod's card art has a per-rarity size. NCard.UpdatePortrait
            // (Core/Nodes/Cards/NCard.cs:1244-1266) puts Model.Portrait into `%Portrait` for every rarity
            // except Ancient, and into `%AncientPortrait` for Ancient (`_ancientPortrait.Texture =
            // portrait`, :1262); NCard._Setup (:1186-1190) is what toggles which of the two is visible.
            //
            // Read both out of the *real* scene instead of restating their numbers: the node has to be
            // found by the same `%` name the game uses, and its stretch mode decides whether an aspect
            // mismatch is a visible distortion or harmless. The numeric enum value is printed next to the
            // name on purpose -- a `.tscn` stores the number, and `stretch_mode = 5` in the shipped
            // card.tscn is what earlier notes in this project recorded as "KEEP_ASPECT_COVERED" without
            // checking which member 5 actually is.
            var rects = ReadPortraitRects(log);
            var ancientCards = 0;
            var stretchedCards = new List<string>();

            // Per-card art. Read the *patched* PortraitPath / Portrait properties rather than rebuilding
            // the path from the id: those two are exactly what NCard.UpdatePortrait() hands to the card's
            // TextureRect, so a stem mismatch between the file on disk and the model id shows up here as
            // "still on the placeholder" instead of silently drawing the wrong thing. Art is delivered a
            // few cards at a time, so "the png exists in the repository" proves nothing about whether the
            // pck has it -- this pass is the check.
            var placeholderCards = new List<string>();
            var brokenPortraits = new List<string>();
            foreach (var card in poolCards)
            {
                string portraitPath;
                Texture2D portraitTexture;
                try
                {
                    portraitPath = card.PortraitPath ?? string.Empty;
                    portraitTexture = card.Portrait;
                }
                catch (Exception e)
                {
                    // Isolated: a portrait property that throws would otherwise abort the whole
                    // self-check, hiding every line after it.
                    log.Error($"self-check portrait   : {card.Id.Entry} <reading the portrait threw {e.GetType().Name}: {e.Message}>");
                    brokenPortraits.Add($"{card.Id.Entry} (threw {e.GetType().Name})");
                    continue;
                }

                var file = string.IsNullOrEmpty(portraitPath) ? "<unset>" : Path.GetFileName(portraitPath);
                log.Info($"self-check portrait   : {card.Id.Entry} {file} {Describe(portraitTexture)}");

                if (portraitTexture == null)
                {
                    brokenPortraits.Add($"{card.Id.Entry} ({file})");
                }
                else if (file is "test.png" or "test2.png")
                {
                    placeholderCards.Add($"{card.Id.Entry} ({file})");
                }

                // Does the art fit the rect it actually lands in? Only a rect that stretches to fill can
                // distort, so that is the gate; %Portrait keeps the aspect and is safe with any texture.
                // Checked for every card, reported for the ones where it can matter, so a future Ancient
                // card without portrait art shows up here instead of only on screen.
                var rect = card.Rarity == CardRarity.Ancient ? rects.Ancient : rects.Normal;
                if (rect.Fills)
                {
                    ancientCards++;
                    if (portraitTexture != null)
                    {
                        var texAspect = (float)portraitTexture.GetWidth() / portraitTexture.GetHeight();
                        var err = Mathf.Abs(texAspect / rect.Aspect - 1f);
                        var verdict = err > 0.01f ? "STRETCHED" : "ok";
                        log.Info(
                            $"self-check portrait fit : {card.Id.Entry} tex={Describe(portraitTexture)} " +
                            $"ar={texAspect:F5} rect={rect.Size.X:0}x{rect.Size.Y:0} ar={rect.Aspect:F5} " +
                            $"{rect.Name} stretch-to-fill diff={err * 100f:+0.0000;-0.0000}% {verdict}");
                        if (err > 0.01f)
                        {
                            stretchedCards.Add($"{card.Id.Entry} ({Describe(portraitTexture)} in {rect.Name})");
                        }
                    }
                    else
                    {
                        stretchedCards.Add($"{card.Id.Entry} (no texture at all)");
                    }
                }
            }
            log.Info($"self-check portrait ok: {poolCards.Count - placeholderCards.Count - brokenPortraits.Count}/{poolCards.Count} card(s) draw their own art");
            log.Info($"self-check portrait fit: {ancientCards} card(s) draw into a stretch-to-fill rect; {ancientCards - stretchedCards.Count} match its aspect, {stretchedCards.Count} would be distorted");
            if (stretchedCards.Count > 0)
            {
                log.Error($"self-check STRETCHED card portraits (the rect does not keep the texture's aspect, so the art is squashed): {string.Join(", ", stretchedCards)}");
            }
            if (brokenPortraits.Count > 0)
            {
                log.Error($"self-check BROKEN card portraits (path present but the texture did not load): {string.Join(", ", brokenPortraits)}");
            }
            if (placeholderCards.Count > 0)
            {
                log.Info($"self-check placeholder: {placeholderCards.Count} card(s) still on the shared face: {string.Join(", ", placeholderCards)}");
            }

            // The energy orb is the one piece of pool art routed through EnergyColorName instead of a
            // model's own icon property: BaseLib substitutes BigEnergyIconPath / TextEnergyIconPath only
            // while that name carries the "CATEGORY∴ENTRY" marker its patches decode. Overriding the name
            // back to a vanilla colour (which this pool used to do) silently reverts the orb to the base
            // game texture with no error anywhere — so check the pair, and log the name it resolved from.
            var cardPool = ModelDb.CardPool<YetanniaCardPool>();
            var orbBig = cardPool.BigEnergyIconPath ?? string.Empty;
            var orbText = cardPool.TextEnergyIconPath ?? string.Empty;
            log.Info(
                $"self-check energy icon: big={Exists(orbBig)}/{Describe(LoadTexture(orbBig))} " +
                $"text={Exists(orbText)}/{Describe(LoadTexture(orbText))} colorName={cardPool.EnergyColorName}");

            // Upgraded numbers matter too, so report them as well.
            foreach (var card in poolCards)
            {
                // Some cards are deliberately unupgradable (MaxUpgradeLevel 0); upgrading those throws.
                if (card.MaxUpgradeLevel <= 0)
                {
                    log.Info($"self-check upgraded   : {card.Id.Entry} (not upgradable)");
                    continue;
                }

                var upgraded = card.ToMutable();
                upgraded.UpgradeInternal();
                log.Info($"self-check upgraded   : {upgraded.Id.Entry} cost={upgraded.EnergyCost.GetWithModifiers(CostModifiers.All)} {DescribeVars(upgraded)}");

                // Render the upgraded text too. Some cards express the upgrade as a *text* branch
                // ({IfUpgraded:show:upgraded|normal}) rather than a number, and that branch is never
                // reached by the base render above — a typo in it would otherwise ship unseen.
                var renderedUpgraded = RenderDescription(upgraded);
                log.Info($"self-check desc up    : {upgraded.Id.Entry} {renderedUpgraded}");
                if (renderedUpgraded.Contains('{') || renderedUpgraded.Contains(":diff"))
                {
                    unresolved.Add($"{upgraded.Id.Entry} (upgraded)");
                }
            }
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"self-check failed: {e}");
        }
    }

    private static string DescribeVars(CardModel card) =>
        string.Join(" ", card.DynamicVars.Select(entry => $"{entry.Key}={entry.Value.BaseValue}"));

    /// <summary>
    /// One portrait rect of the card scene, as the engine computes it.
    /// <see cref="Fills"/> is the property that matters: Godot's <c>STRETCH_SCALE</c> (the default when a
    /// <c>TextureRect</c> has no <c>stretch_mode</c> set, which is the case for <c>%AncientPortrait</c>)
    /// resamples the texture to the rect regardless of aspect, so art of the wrong aspect is geometrically
    /// distorted there. Every other mode keeps the aspect and can only crop or letterbox.
    /// </summary>
    private readonly struct PortraitRect
    {
        public PortraitRect(string name, Vector2 size, Vector2 scale, Vector2 span, int stretch, int expand)
        {
            Name = name;
            Scale = scale;
            Size = size.X > 0f && size.Y > 0f ? size : span;
            Stretch = stretch;
            Expand = expand;
        }

        public string Name { get; }
        public Vector2 Size { get; }
        public Vector2 Scale { get; }
        public int Stretch { get; }
        public int Expand { get; }
        public float Aspect => Size.Y > 0f ? Size.X / Size.Y : 0f;
        public bool Fills => Stretch == (int)TextureRect.StretchModeEnum.Scale;

        public string StretchName => Stretch switch
        {
            0 => "Scale",
            1 => "Tile",
            2 => "Keep",
            3 => "KeepCentered",
            4 => "KeepAspect",
            5 => "KeepAspectCentered",
            6 => "KeepAspectCovered",
            _ => "?",
        };

        public string ExpandName => Expand switch
        {
            0 => "KeepSize",
            1 => "IgnoreSize",
            2 => "FitWidth",
            3 => "FitWidthProportional",
            4 => "FitHeight",
            5 => "FitHeightProportional",
            _ => "?",
        };

        public string Describe() =>
            $"{Name}={Size.X:0}x{Size.Y:0} drawn={Size.X * Scale.X:0}x{Size.Y * Scale.Y:0} " +
            $"ar={Aspect:F5} stretch={StretchName}({Stretch}) expand={ExpandName}({Expand})";
    }

    private readonly struct PortraitRects
    {
        public PortraitRects(PortraitRect normal, PortraitRect ancient)
        {
            Normal = normal;
            Ancient = ancient;
        }

        public PortraitRect Normal { get; }
        public PortraitRect Ancient { get; }
    }

    /// <summary>
    /// Measures the two portrait rects out of the game's own card scene.
    ///
    /// The scene is instantiated but never added to the tree, so its <c>_Ready</c> does not run and nothing
    /// is bound to live combat state; the nodes are read and freed. Both rects are printed because
    /// "the Ancient art is at the portrait aspect" is only half the claim -- the other half is that the
    /// rect it lands in has that aspect too, and that the rect is stretch-to-fill (otherwise a mismatch
    /// would be harmless and the whole per-rarity size would be pointless).
    /// </summary>
    private static PortraitRects ReadPortraitRects(MegaCrit.Sts2.Core.Logging.Logger log)
    {
        PortraitRect normal = default, ancient = default;
        Node scene = null;
        try
        {
            var packed = ResourceLoader.Load<PackedScene>("res://scenes/cards/card.tscn");
            scene = packed?.Instantiate();
            if (scene == null)
            {
                log.Error("self-check portrait rect: res://scenes/cards/card.tscn did not load");
                return new PortraitRects(normal, ancient);
            }

            normal = ReadRect(scene, "%Portrait");
            ancient = ReadRect(scene, "%AncientPortrait");
            log.Info($"self-check portrait rect: {normal.Describe()}");
            log.Info($"self-check portrait rect: {ancient.Describe()}");
            if (!ancient.Fills)
            {
                log.Error(
                    "self-check portrait rect: %AncientPortrait is NOT stretch-to-fill any more, so the " +
                    "per-rarity art size no longer prevents a distortion (it would now crop instead) -- " +
                    "re-check RULES in .tools/cardart-import.py.");
            }
        }
        catch (Exception e)
        {
            log.Error($"self-check portrait rect failed: {e.GetType().Name}: {e.Message}");
        }
        finally
        {
            scene?.Free();
        }

        return new PortraitRects(normal, ancient);
    }

    private static PortraitRect ReadRect(Node scene, string uniqueName)
    {
        var r = scene.GetNodeOrNull<TextureRect>(uniqueName);
        if (r == null)
        {
            return new PortraitRect(uniqueName, Vector2.Zero, Vector2.One, Vector2.Zero, -1, -1);
        }

        // The offset span is the fallback for Size: the parent Control of these nodes is 0x0 in the shipped
        // scene (that is why %Frame, anchored at the card's centre, comes out exactly NCard.defaultSize),
        // so the offsets are already the full size. Printing both makes the reading checkable when the
        // engine reports a rect of zero for a node that is not in the tree.
        var span = new Vector2(
            Mathf.Abs(r.OffsetRight - r.OffsetLeft),
            Mathf.Abs(r.OffsetBottom - r.OffsetTop));
        return new PortraitRect(uniqueName, r.Size, r.Scale, span, (int)r.StretchMode, (int)r.ExpandMode);
    }


    /// <summary>
    /// Prints the Attack/Skill/Power split so the card pool can be compared against the base game's
    /// characters (roughly 36% / 43% / 21%, and no Power cards at Common rarity).
    /// </summary>
    private static void ReportComposition(List<CardModel> cards, MegaCrit.Sts2.Core.Logging.Logger log)
    {
        var total = cards.Count;
        var byType = cards.GroupBy(c => c.Type)
            .OrderByDescending(g => g.Count())
            .Select(g => $"{g.Key} {g.Count()} ({(g.Count() * 100.0 / total):F0}%)");
        log.Info($"self-check type split : {string.Join(", ", byType)}");

        var byRarity = cards.GroupBy(c => c.Rarity)
            .OrderByDescending(g => g.Count())
            .Select(g =>
            {
                var inner = g.GroupBy(c => c.Type)
                    .OrderByDescending(t => t.Count())
                    .Select(t => $"{t.Key} {t.Count()}");
                return $"{g.Key} {g.Count()} [{string.Join("/", inner)}]";
            });
        log.Info($"self-check by rarity  : {string.Join(", ", byRarity)}");
    }

    /// <summary>Renders a card's description exactly as the card library would.</summary>
    private static string RenderDescription(CardModel card)
    {
        try
        {
            return card.GetDescriptionForPile(PileType.None)
                .Replace("\n", " \\n ")
                .Trim();
        }
        catch (Exception e)
        {
            return $"<render failed: {e.GetType().Name}: {e.Message}>";
        }
    }

    /// <summary>Reports whether a texture actually resolved out of the mod's pck.</summary>
    private static string Describe(Godot.Texture2D texture) =>
        texture == null ? "NULL" : $"{texture.GetWidth()}x{texture.GetHeight()}";

    /// <summary>Renders a relic's description so its wording shows up in the log.</summary>
    private static string DescribeRelic(RelicModel relic)
    {
        try { return relic.DynamicDescription.GetFormattedText() ?? "<null>"; }
        catch (Exception e) { return $"<{e.GetType().Name}: {e.Message}>"; }
    }

    /// <summary>
    /// True when a rendered description did not come out clean.
    ///
    /// There are two ways to fail and the second is easy to forget: placeholders can survive
    /// formatting, OR the render itself can throw — in which case the placeholder text never got a
    /// chance to appear at all, so a brace-only test would quietly report success on a description
    /// that cannot be rendered.
    /// </summary>
    private static bool IsUnresolved(string rendered) =>
        rendered.Contains('{') || rendered.Contains(":diff") || rendered.Contains("render failed");

    /// <summary>
    /// Renders a power's description the way <c>PowerModel.HoverTips</c> does.
    ///
    /// <c>PowerModel</c> has no <c>DynamicDescription</c> — its comment says as much ("Unlike other
    /// models' DynamicDescription, this doesn't include any variables") — so the text has to be
    /// assembled by hand: take the <c>powers</c> loc entry, hand it the instance's dynamic vars,
    /// then format it. A <c>{Placeholder}</c> that resolves to nothing is left in the text verbatim,
    /// which is what the caller looks for.
    /// </summary>
    /// <summary>
    /// Renders a power the way <c>HoverTipFactory.FromPower&lt;T&gt;()</c> does — through the engine's
    /// "dumb" tip path rather than the smart description path.
    /// </summary>
    private static string DescribeDumbPower(PowerModel power)
    {
        try
        {
            // DumbHoverTip is the public entry (GetDumbHoverTip itself is not), and HoverTip is a record
            // struct whose Description is already a rendered string.
            var tip = power.DumbHoverTip;
            return (tip.Description ?? "<null>").Replace("\n", " \\n ").Trim();
        }
        catch (Exception e)
        {
            return $"<dumb render failed: {e.GetType().Name}: {e.Message}>";
        }
    }

    /// <summary>
    /// Renders a card's keywords by name.
    ///
    /// The mod's own 先知 is a BaseLib-registered <c>CardKeyword</c> that has no named member in the
    /// vanilla enum, so plain <c>ToString()</c> printed a raw number for it (<c>-84745803</c>) and the
    /// self-check line became impossible to assert on: every Prophet card read as an opaque integer.
    /// Values the enum cannot name are spelled out here instead.
    /// </summary>
    private static string DescribeKeywords(CardModel card)
    {
        try
        {
            return string.Join(
                ",",
                card.Keywords.Select(k => k == YetanniaKeywords.Prophet ? "Prophet" : k.ToString()));
        }
        catch (Exception e)
        {
            return $"<keywords failed: {e.GetType().Name}>";
        }
    }

    private static string DescribePower(PowerModel power)
    {
        try
        {
            var description = power.Description;
            power.DynamicVars.AddTo(description);

            // The same "dumb" variables HoverTips feeds in, when there is an owner to read them from.
            if (power.Owner != null)
            {
                description.Add("Amount", power.Amount);
                description.Add("OnPlayer", power.Owner.IsPlayer);
            }

            return (description.GetFormattedText() ?? "<null>").Replace("\n", " \\n ").Trim();
        }
        catch (Exception e)
        {
            return $"<render failed: {e.GetType().Name}: {e.Message}>";
        }
    }

    /// <summary>
    /// Which portrait a card of the given rarity actually resolves to.
    /// <c>CustomPortraitPath</c> lives on BaseLib's CustomCardModel, so read the base game's
    /// <c>PortraitPath</c> instead — BaseLib patches that getter to route through it.
    /// </summary>
    private static string FirstPortraitOf(CardRarity rarity)
    {
        try
        {
            var card = ModelDb.CardPool<YetanniaCardPool>().AllCards.FirstOrDefault(c => c.Rarity == rarity);
            return card == null ? "<none>" : Path.GetFileName(card.PortraitPath);
        }
        catch (Exception e) { return $"<{e.GetType().Name}>"; }
    }

    /// <summary>Loads a texture the way BaseLib does, so a resource that exists but fails to load shows up.</summary>
    private static Texture2D LoadTexture(string path)
    {
        try { return string.IsNullOrEmpty(path) ? null : ResourceLoader.Load<Texture2D>(path); }
        catch (Exception e)
        {
            MainFile.Logger.Error($"self-check texture load failed for '{path}': {e.Message}");
            return null;
        }
    }

    /// <summary>Whether a res:// path shipped in the mod's pck is present.</summary>
    private static string Exists(string path) =>
        string.IsNullOrEmpty(path) ? "<unset>" : Godot.ResourceLoader.Exists(path).ToString();

    /// <summary>
    /// Reports the resource path a shipped scene actually loads as, plus its root node type.
    ///
    /// This is the check that matters: BaseLib's <c>NodeFactory.TryAutoConvert</c> looks the scene up
    /// in its registry with <c>scene.ResourcePath</c>, and it registers the path we pass it
    /// ("res://Yetannia/scenes/x.tscn", see the "Registered scene ..." log lines). So the conversion
    /// only fires when the loaded ResourcePath equals that registered path. When Godot exported the
    /// scene as binary it reported "res://.godot/exported/..." instead, the lookup missed, and the
    /// conversion silently did nothing. Printing the path makes that failure obvious.
    ///
    /// Deliberately loads the packed scene directly instead of calling
    /// <c>NodeFactory&lt;T&gt;.CreateFromScene</c>: this half only proves the lookup key matches.
    /// <see cref="TryConvert"/> runs the actual factory conversion as a dry run.
    /// </summary>
    internal static string TryScene(string path)
    {
        if (string.IsNullOrEmpty(path)) return "<unset>";
        try
        {
            var packed = Godot.ResourceLoader.Load<Godot.PackedScene>(path);
            if (packed == null) return "NULL-scene";

            var node = packed.Instantiate();
            var typeName = node?.GetType().Name ?? "NULL-node";
            node?.Free();

            var loaded = packed.ResourcePath.SimplifyPath();
            var expected = path.SimplifyPath();
            var match = loaded == expected ? "ok" : $"MISMATCH(expected {expected})";
            return $"{typeName}@{loaded}[{match}]";
        }
        catch (Exception e)
        {
            return $"<{e.GetType().Name}: {e.Message}>";
        }
    }

    /// <summary>
    /// Dry-runs BaseLib's real scene conversion and reports the node it produced plus whether the
    /// unique-named children the game's <c>_Ready</c> will <c>GetNode</c> actually resolve.
    ///
    /// A matching ResourcePath proves the registry lookup hits; this proves the factory can also
    /// <em>build</em> the node. That is a separate failure mode: the factories call
    /// <c>ConvertNodeType</c>, whose base implementation throws when a scene provides a named node of
    /// the wrong type (e.g. a plain Node2D where a Marker2D is required), and BaseLib rethrows so the
    /// conversion dies mid-way. The produced node is never added to the tree, so <c>_Ready</c> does not
    /// run and nothing is bound to live combat/room state; it is freed again immediately.
    /// </summary>
    private static string TryConvert<T>(string path, params string[] requiredNodes) where T : Node, new()
    {
        if (string.IsNullOrEmpty(path)) return "<unset>";
        Node node = null;
        try
        {
            node = NodeFactory<T>.CreateFromScene(path);
            if (node is not T)
            {
                return $"<factory returned {node.GetType().Name}, not {typeof(T).Name}>";
            }

            var missing = requiredNodes.Where(n => node.GetNodeOrNull(n) == null).ToList();
            var built = $"{node.GetType().Name}, {node.GetChildCount()} child(ren)";
            return missing.Count == 0
                ? $"{built}[all {requiredNodes.Length} named nodes resolve]"
                : $"{built}[MISSING {string.Join(", ", missing)}]";
        }
        catch (Exception e)
        {
            return $"<{e.GetType().Name}: {e.Message}>";
        }
        finally
        {
            node?.Free();
        }
    }

    /// <summary>Combat figure: the names NCreatureVisuals._Ready resolves.</summary>
    internal static string TryConvertVisuals(string path) =>
        TryConvert<NCreatureVisuals>(path, "%Visuals", "%Bounds", "%IntentPos", "%CenterPos");

    /// <summary>Campfire figure: the names NRestSiteCharacter._Ready resolves.</summary>
    internal static string TryConvertRest(string path) =>
        TryConvert<NRestSiteCharacter>(path, "ControlRoot", "%Hitbox", "%SelectionReticle", "%ThoughtBubbleLeft", "%ThoughtBubbleRight");

    /// <summary>Merchant figure: NMerchantCharacter has no required named nodes.</summary>
    internal static string TryConvertMerchant(string path) =>
        TryConvert<NMerchantCharacter>(path);

    private static string Registered(Type type) => ModelDb.Contains(type).ToString();

    /// <summary>
    /// Renders a loc entry by table + key, so the log shows the text a player would see rather than a
    /// boolean. A missing key (a rename that dropped an entry) and a formatting failure both come back
    /// as a bracketed diagnostic instead of throwing, which keeps the rest of the check running.
    /// </summary>
    private static string Resolve(string table, string key)
    {
        try
        {
            var text = new LocString(table, key).GetFormattedText();
            return string.IsNullOrEmpty(text) ? "<empty>" : text.Replace("\n", " \\n ");
        }
        catch (Exception e)
        {
            return $"<{e.GetType().Name}: {e.Message}>";
        }
    }

    private static string ExistsIn(string table, Type type, string suffix)
    {
        try { return LocString.Exists(table, ModelDb.GetId(type).Entry + suffix).ToString(); }
        catch (Exception e) { return $"<{e.GetType().Name}>"; }
    }
}

/// <summary>
/// Second half of the self-check: load the custom character scenes the way BaseLib does and report
/// the resource path they resolve to. A path that matches the one BaseLib logged as
/// "Registered scene '...' for auto-conversion to X" means the conversion will fire; a
/// "MISMATCH" means BaseLib's lookup will miss (which is what happened while the pck still shipped
/// binary scenes) and the model silently falls back to placeholder art.
///
/// Runs on <c>NMainMenu._Ready</c> rather than on <c>ModelDb.Preload</c>: BaseLib registers the scene
/// conversions from a Preload postfix, and hooking the main menu guarantees both that the registration
/// has happened and that content loading is finished.
/// </summary>
[HarmonyPatch(typeof(NMainMenu), nameof(NMainMenu._Ready))]
internal static class ModSelfCheckSceneConversions
{
    private static bool _reported;

    [HarmonyPostfix]
    private static void ReportSceneConversions()
    {
        if (_reported) return;
        _reported = true;

        try
        {
            var character = ModelDb.Character<YetanniaCharacter>();

            // Half 1: does the loaded ResourcePath match what BaseLib registered?
            MainFile.Logger.Info(
                $"self-check scene load : visuals={ModSelfCheck.TryScene(character.CustomVisualPath)} " +
                $"rest={ModSelfCheck.TryScene(character.CustomRestSiteAnimPath)} " +
                $"merchant={ModSelfCheck.TryScene(character.CustomMerchantAnimPath)} " +
                $"selectBg={ModSelfCheck.TryScene(character.CustomCharacterSelectBg)}");

            // Half 2: can the factory actually build the node from that scene?
            // The names listed are the ones the game's own _Ready resolves, so a MISSING entry here
            // means the in-game model would throw on the frame it appears.
            MainFile.Logger.Info(
                $"self-check convert    : visuals={ModSelfCheck.TryConvertVisuals(character.CustomVisualPath)} " +
                $"rest={ModSelfCheck.TryConvertRest(character.CustomRestSiteAnimPath)} " +
                $"merchant={ModSelfCheck.TryConvertMerchant(character.CustomMerchantAnimPath)}");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"self-check scene load failed: {e}");
        }
    }
}
