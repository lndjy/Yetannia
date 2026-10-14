using System;
using System.Collections.Generic;
using MegaCrit.Sts2.Core.Entities.Ancients;
using MegaCrit.Sts2.Core.Localization;
using MegaCrit.Sts2.Core.Models;
using Yetannia.YetanniaCode.Character;

namespace Yetannia.YetanniaCode.Ancients;

/// <summary>
/// Attaches Yetannia's own dialogue to the Ancients, and turns the user's draft into loc entries.
///
/// HOW THE GAME KEYS ANCIENT DIALOGUE (read from the decompiled build, not guessed):
///
///   * <c>AncientDialogueSet.CharacterDialogues</c> is a
///     <c>Dictionary&lt;string, IReadOnlyList&lt;AncientDialogue&gt;&gt;</c> keyed by the character's
///     <c>ModelId.Entry</c> (see <c>AncientDialogueSet.GetValidDialogues</c>: it looks up
///     <c>characterId.Entry</c>). Vanilla fills it for IRONCLAD / SILENT / DEFECT / NECROBINDER /
///     REGENT only — a mod character is absent, so before this class existed Yetannia fell through to
///     the character-agnostic pool and heard vanilla's generic Ancient line.
///   * Each <c>AncientDialogue</c> carries <c>VisitIndex</c> (which visit to that Ancient it belongs
///     to) and <c>IsRepeating</c>; <c>GetValidDialogues</c> picks a *visit-exact* group first and only
///     falls back to the repeating pool, then picks one entry from the group at random
///     (<c>NEventRoom.SetupLayout</c>, <c>Rng.Chaotic.NextItem(validDialogues)</c>). Two entries with
///     the same <c>VisitIndex</c> are therefore alternate branches of the same visit.
///   * The speaker of a line comes from <c>AncientDialogueSpeaker</c>; vanilla derives it by probing
///     which of <c>&lt;key&gt;.ancient</c> / <c>&lt;key&gt;.char</c> exists in the <c>ancients</c>
///     table (<c>AncientDialogue.PopulateLines</c>). Deriving it that way would make our speakers
///     depend on table load order, so this class sets <c>LineText</c>/<c>Speaker</c>/<c>NextButtonText</c>
///     explicitly instead, under this mod's own key namespace.
///
/// WHERE THIS HOOKS IN: <c>AncientDialogueSet.PopulateLocKeys(string ancientEntry)</c>. Both entry
/// points call it immediately after building the set and before the set is ever read —
/// <c>AncientEventModel.DialogueSet</c> and <c>TheArchitect.DialogueSet</c> (which is why one patch
/// covers all nine Ancients, including the Architect, whose <c>DialogueSet</c> lives on a different
/// base class). Running there means vanilla's own per-index key derivation has already finished and
/// never sees our entries at all.
///
/// MAPPING OF THE USER'S DRAFT ONTO THESE STATES — see <see cref="Slots"/>. The draft's own section
/// headings are the authority; where the code has no exact counterpart the choice is stated in the
/// comment on the slot.
///
/// ENGLISH: the user wrote Chinese only. <see cref="LocEntries"/> registers that same Chinese under
/// every language, so no raw key can appear in any of the game's 16 languages; the English lines are
/// the Chinese text pending English copy.
/// </summary>
internal static class YetanniaAncientDialoguePlan
{
    internal const string Table = "ancients";

    /// <summary>This mod's own key namespace inside the <c>ancients</c> table.</summary>
    private const string KeyPrefix = "YETANNIA-TALK";

    private const string ArchitectEntry = "THE_ARCHITECT";

    /// <summary>
    /// Generic button labels that the vanilla <c>ancients</c> table ships for every one of the 16
    /// languages (measured: `THE_ARCHITECT.CONTINUE` is non-empty in all of them). Reusing them means
    /// no new UI wording is authored here.
    /// </summary>
    private const string ContinueKey = "THE_ARCHITECT.CONTINUE";
    private const string RespondKey = "THE_ARCHITECT.RESPOND";

    private static readonly LocString ContinueButton = new(Table, ContinueKey);
    private static readonly LocString RespondButton = new(Table, RespondKey);

    private sealed class Slot
    {
        internal Slot(string id, int index, int? visitIndex, bool repeating,
            YetanniaAncientDialogueData.DraftLine[] authored = null)
        {
            Id = id;
            Index = index;
            VisitIndex = visitIndex;
            Repeating = repeating;
            AuthoredLines = authored;
        }

        /// <summary>The draft heading this slot came from (see the generated data file).</summary>
        internal readonly string Id;

        /// <summary>Position in <c>CharacterDialogues[&lt;character&gt;]</c>; part of the loc key.</summary>
        internal readonly int Index;

        /// <summary>
        /// Which visit this dialogue is exact-matched on. <c>null</c> means "never exact-matched, only
        /// reachable through the repeating pool" — which is exactly what the base game does for its own
        /// character-agnostic lines.
        /// </summary>
        internal readonly int? VisitIndex;

        internal readonly bool Repeating;

        /// <summary>
        /// Lines that are NOT in the user's <c>.docx</c> — written later and kept here so that
        /// re-running <c>.tools/gen-ancient-dialogue.py</c> (which owns the generated data file) cannot
        /// drop them. <c>null</c> for every slot whose text comes from the draft.
        /// </summary>
        internal readonly YetanniaAncientDialogueData.DraftLine[] AuthoredLines;
    }

    /// <summary>
    /// The eight Ancients that the user wrote the full section set for.
    ///
    /// VisitIndex / Repeating are a *mechanical* mapping of the draft's headings, chosen so that
    /// <c>GetValidDialogues</c> (see the class comment) shows them when the heading says:
    ///
    ///   初次见面 (+ 分支1)  -> VisitIndex 0, not repeating. Exact match on the 1st visit; the two
    ///                          entries are the two branches that visit can pick from.
    ///   重复拜访 / 重复拜访1 -> VisitIndex 1, repeating. Exact match on the 2nd visit; stays in the
    ///   重复拜访2             repeating pool for every later visit (that is what IsRepeating does).
    ///   第三次及其以后 (+分支1/分支2) -> VisitIndex 2, repeating. Exact match on the 3rd visit, and
    ///                          -- because the heading says 及其以后, "and after" -- it stays in the
    ///                          repeating pool afterwards. Vanilla instead puts its third authored
    ///                          dialogue at VisitIndex 4 and leaves it out of the pool; the draft's
    ///                          wording is followed here rather than vanilla's spacing.
    ///   通用1 / 通用2        -> VisitIndex **null**, repeating. These are the draft's
    ///                          character-agnostic flavour lines. They get the same treatment the base
    ///                          game gives its own agnostic lines (`AgnosticDialogues`, all
    ///                          `VisitIndex = null` + repeating): `<c>GetValidDialogues</c>` exact-matches
    ///                          `d.VisitIndex == charVisits`, and `null == n` is never true, so they can
    ///                          never win a visit-exact group and only ever appear from the repeating
    ///                          pool -- i.e. once no authored visit group applies (4th visit onward
    ///                          with this slot layout). An earlier version gave them VisitIndex 1,
    ///                          which the self-check's pick probe caught: `charVisits=1 candidates=4`
    ///                          meant the 2nd visit had a 50 % chance of a generic one-liner instead
    ///                          of the authored 重复拜访 dialogue.
    ///
    ///                          Vanilla keeps these in `AgnosticDialogues` keyed
    ///                          `&lt;ANCIENT&gt;.talk.ANY.&lt;n&gt;`; appending there was rejected for two
    ///                          measured reasons: it renumbers vanilla's existing `ANY.{n}` keys, and
    ///                          `GetValidDialogues` feeds the agnostic pool to *every* character, so
    ///                          Yetannia's lines would start appearing for the vanilla cast.
    /// </summary>
    private static readonly Slot[] Slots =
    [
        new("first", 0, visitIndex: 0, repeating: false),
        new("first@branch1", 1, visitIndex: 0, repeating: false),
        new("repeat1", 2, visitIndex: 1, repeating: true),
        new("repeat2", 3, visitIndex: 1, repeating: true),
        new("late", 4, visitIndex: 2, repeating: true),
        new("late@branch1", 5, visitIndex: 2, repeating: true),
        new("late@branch2", 6, visitIndex: 2, repeating: true),
        new("generic1", 7, visitIndex: null, repeating: true),
        new("generic2", 8, visitIndex: null, repeating: true),
    ];

    /// <summary>
    /// The Architect's file has no headings at all — one flat 13-line conversation — so it becomes a
    /// single first-visit dialogue (slot <c>architect-main</c>, 13 lines, <c>VisitIndex 0</c>,
    /// non-repeating; unchanged). Round 44 measured that nothing followed it: on a 2nd win
    /// <c>GetValidDialogues</c> returned 0 candidates — the Architect has no agnostic pool and
    /// <c>LoadDialogue</c> passes <c>allowAnyCharacterDialogues: false</c> — so
    /// <see cref="Patches.ArchitectNullDialoguePatch"/> supplied an empty dialogue and the run ended
    /// silently. <c>architect-repeat</c> replaces that silence with the user's line.
    ///
    /// <c>architect-repeat</c> is the 2nd-win-and-later line. It is NOT in the draft: the user wrote it
    /// as a follow-up ("建筑师第二次以后改成建筑师：『回去吧，耶坦尼娅。』然后直接结束"), so it lives
    /// here rather than in the generated data file, and it is not translated — the Chinese is the user's
    /// text and is registered for every language exactly like the draft's lines (see
    /// <see cref="LocEntries"/>). It is speaker <c>"ancient"</c>, which is the game's own speaker
    /// mechanism for him: <c>TheArchitect.GetSpeaker</c> maps <c>AncientDialogueSpeaker.Ancient</c> to
    /// the Architect creature and the line is drawn as his speech bubble
    /// (<c>Core/Models/Events/TheArchitect.cs:508-521</c>) — the same speaker the 13-line conversation's
    /// Architect lines use.
    ///
    /// <c>VisitIndex = 1</c> + <c>IsRepeating = true</c> means "shown on the 2nd win, then kept in the
    /// pool for every later one", which is precisely vanilla's own shape for him (measured: IRONCLAD's
    /// Architect entries are <c>VisitIndex 0/1/2</c> and all three are still candidates at
    /// <c>charVisits=3</c>). At <c>charVisits == 0</c> the first-visit dialogue wins its exact-match
    /// group first, so the 1st conversation is untouched. One line, so no <c>.next</c> key is needed:
    /// <c>AncientDialogueSet.PopulateLocKeys</c> derives <c>.next</c> only for lines before the last one
    /// (<c>:162-172</c>), and the Architect's last line is closed by the plain PROCEED option
    /// (<c>TheArchitect.cs:318-331</c>), which resolves no loc key of ours.
    /// </summary>
    private static readonly Slot[] ArchitectOnly =
    [
        new("architect-main", 0, visitIndex: 0, repeating: false),
        new("architect-repeat", 1, visitIndex: 1, repeating: true,
            authored:
            [
                new YetanniaAncientDialogueData.DraftLine("ancient", "回去吧，耶坦尼娅。"),
            ]),
    ];

    private static readonly Dictionary<string, YetanniaAncientDialogueData.DraftAncient> ByEntry = BuildIndex();

    private static string _characterEntry;

    private static Dictionary<string, YetanniaAncientDialogueData.DraftAncient> BuildIndex()
    {
        var index = new Dictionary<string, YetanniaAncientDialogueData.DraftAncient>(StringComparer.Ordinal);
        foreach (var ancient in YetanniaAncientDialogueData.Ancients)
        {
            index[ancient.Entry] = ancient;
        }
        return index;
    }

    /// <summary>
    /// The mod character's <c>ModelId.Entry</c> — the key <c>CharacterDialogues</c> is looked up by.
    /// Resolved from the model database rather than hard-coded, and cached: <see cref="Attach"/> only
    /// runs when an Ancient event is built, long after <c>ModelDb.Init</c>.
    /// </summary>
    internal static string CharacterEntry
    {
        get
        {
            if (_characterEntry != null) return _characterEntry;
            try
            {
                _characterEntry = ModelDb.Character<YetanniaCharacter>().Id.Entry;
            }
            catch (Exception e)
            {
                MainFile.Logger.Error($"ancient dialogue: cannot resolve Yetannia's character id: {e.Message}");
                return null;
            }
            return _characterEntry;
        }
    }

    private static Slot[] SlotsFor(string entry) =>
        entry == ArchitectEntry ? ArchitectOnly : Slots;

    /// <summary>
    /// Adds Yetannia's dialogues to the set and points every one of her lines at this mod's own loc
    /// keys. Idempotent; leaves vanilla characters and vanilla keys completely untouched.
    /// </summary>
    internal static void Attach(AncientDialogueSet set, string ancientEntry)
    {
        if (set == null) return;
        if (!ByEntry.TryGetValue(ancientEntry, out var draft)) return;

        var characterEntry = CharacterEntry;
        if (string.IsNullOrEmpty(characterEntry))
        {
            // Without the id there is no way to key the dictionary. Nothing is worse than before this
            // class existed: the character keeps hearing vanilla's agnostic line at the eight Ancients,
            // and the Architect falls back to ArchitectNullDialoguePatch.
            return;
        }

        if (set.CharacterDialogues.ContainsKey(characterEntry)) return;

        var slots = SlotsFor(ancientEntry);
        var dialogues = new List<AncientDialogue>(slots.Length);

        foreach (var slot in slots)
        {
            var lines = LinesFor(draft, slot);
            if (lines == null)
            {
                // The draft did not have this heading; do not invent one. The dialogue index is the
                // slot's own number, so the remaining keys stay aligned.
                MainFile.Logger.Warn($"ancient dialogue: {ancientEntry} has no '{slot.Id}' section in the draft");
                continue;
            }

            var sfx = new string[lines.Length];

            // EndAttackers is init-only, so the Architect's value has to be part of the initializer.
            // His conversation ends with him challenging the player, and every single vanilla Architect
            // entry uses Both at every visit index, so mirror that; without it the run would end with
            // no attack animation at all.
            var dialogue = ancientEntry == ArchitectEntry
                ? new AncientDialogue(sfx)
                {
                    VisitIndex = slot.VisitIndex,
                    IsRepeating = slot.Repeating,
                    EndAttackers = ArchitectAttackers.Both,
                }
                : new AncientDialogue(sfx)
                {
                    VisitIndex = slot.VisitIndex,
                    IsRepeating = slot.Repeating,
                };

            for (var i = 0; i < lines.Length; i++)
            {
                var line = lines[i];
                var target = dialogue.Lines[i];
                target.Speaker = IsCharacter(line.Speaker)
                    ? AncientDialogueSpeaker.Character
                    : AncientDialogueSpeaker.Ancient;
                target.LineText = new LocString(Table, LineKey(ancientEntry, slot.Id, i, line.Speaker));
                if (i < lines.Length - 1)
                {
                    var nextIsCharacter = IsCharacter(lines[i + 1].Speaker);
                    target.NextButtonText = NextButton(nextIsCharacter);
                }
            }

            dialogues.Add(dialogue);
        }

        if (dialogues.Count == 0)
        {
            MainFile.Logger.Error($"ancient dialogue: nothing to attach for {ancientEntry}");
            return;
        }

        set.CharacterDialogues[characterEntry] = dialogues;
    }

    private static bool IsCharacter(string speaker) => speaker == "character";

    /// <summary>
    /// The lines of one slot: the draft's own section when the user wrote one, otherwise the lines
    /// authored on the slot itself (see <see cref="Slot.AuthoredLines"/>). <c>null</c> means the slot has
    /// neither and must be skipped.
    /// </summary>
    private static YetanniaAncientDialogueData.DraftLine[] LinesFor(
        YetanniaAncientDialogueData.DraftAncient draft, Slot slot) =>
        FindSection(draft, slot.Id)?.Lines ?? slot.AuthoredLines;

    private static YetanniaAncientDialogueData.DraftSection FindSection(
        YetanniaAncientDialogueData.DraftAncient draft, string slot)
    {
        foreach (var section in draft.Sections)
        {
            if (section.Slot == slot) return section;
        }
        return null;
    }

    /// <summary>
    /// The "next line" button for a line whose successor is spoken by <paramref name="nextIsCharacter"/>.
    /// Falls back to Continue when the vanilla Respond label is empty in the active language (measured:
    /// Thai ships `THE_ARCHITECT.RESPOND` as an empty string, which would draw a blank button).
    /// </summary>
    private static LocString NextButton(bool nextIsCharacter)
    {
        if (!nextIsCharacter) return ContinueButton;
        try
        {
            if (LocString.IsNullOrWhitespace(RespondButton)) return ContinueButton;
        }
        catch
        {
            return ContinueButton;
        }
        return RespondButton;
    }

    /// <summary>The loc key of one line: <c>YETANNIA-TALK.&lt;ANCIENT&gt;.&lt;slot&gt;.&lt;line&gt;.&lt;speaker&gt;</c>.</summary>
    internal static string LineKey(string ancientEntry, string slot, int lineIndex, string speaker) =>
        $"{KeyPrefix}.{ancientEntry}.{slot}.{lineIndex}.{speaker}";

    /// <summary>
    /// Every loc entry this mod owns in the <c>ancients</c> table.
    ///
    /// The SAME text is returned for every language on purpose: the user's dialogue is Chinese only,
    /// and registering it for `eng` (and every other language) is what keeps a raw key from being
    /// rendered. When English copy arrives, this is the single place a per-language branch goes.
    /// </summary>
    internal static Dictionary<string, string> LocEntries(bool english)
    {
        // `english` is deliberately unused today -- kept so the call site already threads the
        // language through and adding the English column is a one-line change here.
        _ = english;

        var entries = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var draft in YetanniaAncientDialogueData.Ancients)
        {
            foreach (var slot in SlotsFor(draft.Entry))
            {
                var lines = LinesFor(draft, slot);
                if (lines == null) continue;

                for (var i = 0; i < lines.Length; i++)
                {
                    entries[LineKey(draft.Entry, slot.Id, i, lines[i].Speaker)] = lines[i].Text;
                }
            }
        }

        return entries;
    }
}
