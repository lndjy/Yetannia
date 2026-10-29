using System;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Ancients;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Events;
using Yetannia.YetanniaCode.Character;

namespace Yetannia.YetanniaCode.Ancients;

/// <summary>
/// Runtime evidence for the Ancient dialogue, printed once into the game log from a second postfix on
/// <see cref="ModelDb.Init"/> (the mod's own <c>ModSelfCheck</c> uses the same hook; two postfixes on
/// one method are fine).
///
/// Loading without an exception proves nothing here, and three separate things can silently fail:
/// the patch may not be attached at all (PatchAll skips classes it cannot read), the loc keys may not
/// be in the table (a missing key throws <c>LocException</c> inside <c>NAncientEventLayout</c> when the
/// button label is resolved), and the structure may be attached to the wrong visit index so the player
/// never reaches it. Each of those gets its own line below.
///
/// Reading <c>DialogueSet</c> here builds and caches each set early, which is the same object the event
/// uses later; it is a read-only diagnostic.
/// </summary>
[HarmonyPatch(typeof(ModelDb), nameof(ModelDb.Init))]
internal static class AncientDialogueSelfCheck
{
    [HarmonyPostfix]
    private static void Report()
    {
        try
        {
            var log = MainFile.Logger;

            var chinese = YetanniaAncientDialoguePlan.LocEntries(false);
            var english = YetanniaAncientDialoguePlan.LocEntries(true);
            var active = Loc.IsEnglish ? english : chinese;
            var unresolved = active.Keys.Where(k => !LocString.Exists(YetanniaAncientDialoguePlan.Table, k)).ToList();
            log.Info($"self-check talk keys  : defined={active.Count} chinese={chinese.Count} english={english.Count} " +
                     $"resolved={active.Count - unresolved.Count}/{active.Count} language={LocManager.Instance?.Language}");
            if (unresolved.Count > 0)
            {
                log.Error($"self-check MISSING talk keys ({unresolved.Count}): {string.Join(", ", unresolved.Take(8))}");
            }

            // The English column is generated data, not authored in C#, so a bad merge (missing line,
            // Chinese left in the English slot, the columns swapped) compiles fine and only shows up as
            // Chinese text on an English client. Prove the columns line up in both directions and that
            // the English one is really English. Lines whose Chinese is punctuation only ("......")
            // legitimately translate to the same string, so the identity test is gated on the Chinese
            // actually containing a Han character.
            var missingEnglish = chinese.Keys.Where(k => !english.ContainsKey(k)).ToList();
            var extraEnglish = english.Keys.Where(k => !chinese.ContainsKey(k)).ToList();
            if (missingEnglish.Count > 0)
            {
                log.Error($"self-check talk EN    : {missingEnglish.Count} key(s) have no English column: {string.Join(", ", missingEnglish.Take(8))}");
            }
            if (extraEnglish.Count > 0)
            {
                log.Error($"self-check talk EN    : {extraEnglish.Count} English-only key(s): {string.Join(", ", extraEnglish.Take(8))}");
            }

            var badEnglish = english.Where(kv =>
                {
                    if (string.IsNullOrWhiteSpace(kv.Value) || HasCjk(kv.Value)) return true;
                    var zh = chinese.TryGetValue(kv.Key, out var value) ? value : string.Empty;
                    return HasCjk(zh) && string.Equals(kv.Value, zh, StringComparison.Ordinal);
                })
                .Select(kv => kv.Key).ToList();
            if (badEnglish.Count > 0)
            {
                log.Error($"self-check talk EN    : {badEnglish.Count} English line(s) empty, still Chinese, or identical " +
                          $"to the Chinese: {string.Join(", ", badEnglish.Take(8))}");
            }

            // End-to-end: the live table must hold the ACTIVE language's column verbatim. This is what
            // proves LocEntries(true/false) is what actually got injected, and that a mid-session
            // language switch re-filled the table instead of leaving stale text behind.
            var wrongLanguage = new List<string>();
            foreach (var pair in active)
            {
                var loc = new LocString(YetanniaAncientDialoguePlan.Table, pair.Key);
                try
                {
                    if (loc.Exists() && loc.GetFormattedText() != pair.Value) wrongLanguage.Add(pair.Key);
                }
                catch (Exception e)
                {
                    wrongLanguage.Add($"{pair.Key} <{e.GetType().Name}>");
                }
            }
            if (wrongLanguage.Count > 0)
            {
                log.Error($"self-check talk lang  : {wrongLanguage.Count} live row(s) do not match the " +
                          $"{(Loc.IsEnglish ? "English" : "Chinese")} column: {string.Join(", ", wrongLanguage.Take(8))}");
            }

            var characterEntry = YetanniaAncientDialoguePlan.CharacterEntry;
            log.Info($"self-check talk char  : entry={characterEntry ?? "<unresolved>"}");

            // Attachment, checked positively rather than assumed.
            var populate = AccessTools.Method(typeof(AncientDialogueSet), nameof(AncientDialogueSet.PopulateLocKeys));
            var populatePatches = populate == null ? null : Harmony.GetPatchInfo(populate);
            var getTable = AccessTools.Method(typeof(LocManager), nameof(LocManager.GetTable));
            var getTablePatches = getTable == null ? null : Harmony.GetPatchInfo(getTable);
            var getValid = AccessTools.Method(typeof(AncientDialogueSet), nameof(AncientDialogueSet.GetValidDialogues));
            var getValidPatches = getValid == null ? null : Harmony.GetPatchInfo(getValid);
            log.Info($"self-check talk patch : populateLocKeys={populate != null} postfixes={populatePatches?.Postfixes?.Count ?? 0} " +
                     $"getTable={getTable != null} postfixes={getTablePatches?.Postfixes?.Count ?? 0} " +
                     $"getValidDialogues={getValid != null} postfixes={getValidPatches?.Postfixes?.Count ?? 0}");

            var characterId = ModelDb.Character<YetanniaCharacter>().Id;

            // One base-game character, used below to show positively that
            // AncientDialogueVanillaAgnosticFilterPatch leaves vanilla characters alone. ModelDb.AllCharacters
            // is exactly the five vanilla characters (Core/Models/ModelDb.cs:145-152) and the first of
            // them is not on any Ancient's AnyCharacterDialogueBlacklist.
            var vanillaCharacter = ModelDb.AllCharacters.FirstOrDefault(c => c.Id.Entry != characterEntry);

            // Every ancient model, including The Architect (which is not an AncientEventModel).
            foreach (var ancient in ModelDb.All.OfType<AncientEventModel>().Cast<object>().Concat(ModelDb.All.OfType<TheArchitect>()))
            {
                ReportAncient(ancient, characterId, characterEntry, vanillaCharacter, log);
            }

            // The global once-per-save dialogue is vanilla's and is character-agnostic; say so
            // explicitly, because it is the one visit that will NOT show the user's text even when the
            // very first Ancient visit ever happens to be Yetannia's.
            log.Info("self-check talk global: firstVisitEver is vanilla and character-agnostic; it wins when totalVisits == 0");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"self-check talk failed: {e}");
        }
    }

    private static void ReportAncient(object ancient, ModelId characterId, string characterEntry, CharacterModel vanillaCharacter, MegaCrit.Sts2.Core.Logging.Logger log)
    {
        var entry = AncientEntryOf(ancient);
        try
        {
            var set = DialogueSetOf(ancient);
            var hasOurs = characterEntry != null && set.CharacterDialogues.ContainsKey(characterEntry);

            if (!hasOurs)
            {
                log.Info($"self-check talk       : {entry} ours=False (vanilla only)");
                return;
            }

            var ours = set.CharacterDialogues[characterEntry];
            var shape = string.Join(", ", ours.Select((d, i) =>
                $"{i}:{d.Lines.Count}L/v{(d.VisitIndex.HasValue ? d.VisitIndex.Value.ToString() : "null")}{(d.IsRepeating ? "r" : "")}"));
            log.Info($"self-check talk       : {entry} ours=True dialogues={ours.Count} [{shape}]");

            // Every line must resolve to real text and a real speaker, or the dialogue line throws
            // (or renders a raw key) in game.
            var bad = new List<string>();
            foreach (var dialogue in ours)
            {
                for (var i = 0; i < dialogue.Lines.Count; i++)
                {
                    var line = dialogue.Lines[i];
                    if (line.LineText == null) { bad.Add($"{entry}#{i} null LineText"); continue; }
                    if (!line.LineText.Exists()) { bad.Add($"{entry}#{i} missing {line.LineText.LocEntryKey}"); continue; }
                    if (LocString.IsNullOrWhitespace(line.LineText)) { bad.Add($"{entry}#{i} empty {line.LineText.LocEntryKey}"); }
                    if (line.Speaker == AncientDialogueSpeaker.None) { bad.Add($"{entry}#{i} speaker None"); }
                    if (i < dialogue.Lines.Count - 1 && line.NextButtonText == null) { bad.Add($"{entry}#{i} null NextButtonText"); }
                }
            }
            if (bad.Count > 0)
            {
                log.Error($"self-check talk BAD   : {entry} {string.Join(" | ", bad.Take(6))}");
            }

            // The Architect's 2nd-win line is authored in code rather than in the user's draft, and it is
            // the only thing standing between "silent empty dialogue" and a working one, so spell out
            // everything the renderer reads: the line count, the visit it is exact-matched on, the
            // speaker, the next-button resolution (null on the last line => the event's plain PROCEED
            // option, which resolves no loc key and therefore cannot throw), and the live text.
            if (entry == "THE_ARCHITECT")
            {
                var repeat = ours.FirstOrDefault(d => d.VisitIndex == 1);
                if (repeat == null)
                {
                    log.Error("self-check talk arch   : THE_ARCHITECT has no 2nd-win (VisitIndex 1) dialogue");
                }
                else
                {
                    var line = repeat.Lines[0];
                    var speaker = line.Speaker.ToString();
                    var text = line.LineText == null || LocString.IsNullOrWhitespace(line.LineText)
                        ? "<empty>"
                        : line.LineText.GetFormattedText();
                    var next = line.NextButtonText == null ? "<null: last line, PROCEED>" : line.NextButtonText.LocEntryKey;
                    log.Info($"self-check talk arch   : THE_ARCHITECT repeat lines={repeat.Lines.Count} visit={repeat.VisitIndex} " +
                             $"repeating={repeat.IsRepeating} speaker={speaker} next={next} text={text}");
                }
            }

            // Which dialogue the event would actually pick, per visit count. This is the check that
            // proves the docx heading -> visit state mapping: `candidates` is how many entries the
            // random pick chooses from, `ours` how many of them are the user's, and `vanilla` how many
            // of them are vanilla's character-agnostic (ANY) lines that `AncientDialogueVanillaAgnosticFilterPatch`
            // is meant to remove. From the 4th visit on, `vanilla` must be 0.
            for (var visits = 0; visits <= 4; visits++)
            {
                var allowAny = !AncientBlacklistContains(ancient);
                var candidates = set.GetValidDialogues(characterId, visits, totalVisits: 1, allowAny).ToList();
                var ourCount = candidates.Count(d => d.Lines.Count > 0 && d.Lines[0].LineText != null
                                                     && d.Lines[0].LineText.LocEntryKey.StartsWith("YETANNIA-TALK.", StringComparison.Ordinal));
                var first = candidates.Count == 0 || candidates[0].Lines.Count == 0 || candidates[0].Lines[0].LineText == null
                    ? "<none>"
                    : candidates[0].Lines[0].LineText.LocEntryKey;
                log.Info($"self-check talk pick  : {entry} charVisits={visits} candidates={candidates.Count} ours={ourCount} vanilla={candidates.Count - ourCount} first={first}");
            }

            // The other half of the filter's contract: a vanilla character must be untouched. Asking the
            // same patched method as a base-game character at the first visit whose pool contains
            // vanilla's repeating ANY entries must still return them (`ours=0 vanilla>0`) — if the filter
            // ever engaged for a vanilla character this line would read `vanilla=0`.
            if (vanillaCharacter != null)
            {
                var vanillaAllowAny = !AncientBlacklistContains(ancient, vanillaCharacter);
                var vanillaCandidates = set.GetValidDialogues(vanillaCharacter.Id, 3, totalVisits: 1, vanillaAllowAny).ToList();
                var vanillaOurs = vanillaCandidates.Count(d => d.Lines.Count > 0 && d.Lines[0].LineText != null
                                                              && d.Lines[0].LineText.LocEntryKey.StartsWith("YETANNIA-TALK.", StringComparison.Ordinal));
                log.Info($"self-check talk vanilla: {entry} as {vanillaCharacter.Id.Entry} charVisits=3 candidates={vanillaCandidates.Count} ours={vanillaOurs} vanilla={vanillaCandidates.Count - vanillaOurs}");
            }
        }
        catch (Exception e)
        {
            // DeprecatedAncientEvent.DefineDialogues throws NotImplementedException by design, so a
            // failure here is reported rather than allowed to abort the whole self-check.
            log.Info($"self-check talk       : {entry} <{e.GetType().Name}: {e.Message}>");
        }
    }

    private static string AncientEntryOf(object ancient) =>
        ancient is AbstractModel model ? model.Id.Entry : ancient.GetType().Name;

    private static AncientDialogueSet DialogueSetOf(object ancient) => ancient switch
    {
        AncientEventModel ancientModel => ancientModel.DialogueSet,
        TheArchitect architect => architect.DialogueSet,
        _ => throw new InvalidOperationException($"no DialogueSet on {ancient.GetType().Name}"),
    };

    /// <summary>Mirrors <c>NEventRoom.SetupLayout</c>'s own <c>allowAnyCharacterDialogues</c> argument.</summary>
    private static bool AncientBlacklistContains(object ancient) =>
        AncientBlacklistContains(ancient, ModelDb.Character<YetanniaCharacter>());

    private static bool AncientBlacklistContains(object ancient, CharacterModel character) =>
        ancient is AncientEventModel ancientModel &&
        ancientModel.AnyCharacterDialogueBlacklist.Contains(character);

    /// <summary>
    /// True when <paramref name="text"/> still contains a Han character or CJK punctuation. Used to
    /// prove the English column is really translated: a blank, copied-over or half-translated line
    /// would otherwise render Chinese text on an English client without a single error.
    /// </summary>
    private static bool HasCjk(string text)
    {
        foreach (var ch in text)
        {
            if (ch >= '\u3000' && ch <= '\u303F') return true; // CJK symbols and punctuation
            if (ch >= '\u3400' && ch <= '\u4DBF') return true; // CJK unified ideographs extension A
            if (ch >= '\u4E00' && ch <= '\u9FFF') return true; // CJK unified ideographs
            if (ch >= '\uF900' && ch <= '\uFAFF') return true; // CJK compatibility ideographs
            if (ch >= '\uFF00' && ch <= '\uFFEF') return true; // halfwidth and fullwidth forms
        }
        return false;
    }
}
