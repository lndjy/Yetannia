using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.CardRewardAlternatives;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;
using MegaCrit.Sts2.Core.TestSupport;
using Yetannia.YetanniaCode.Cards;

namespace Yetannia.YetanniaCode.Diagnostics;

/// <summary>
/// Answers card-selection prompts automatically, so a scry (which is a *player choice*) can be driven
/// without a human at the keyboard. This is the same hook the game's own tests and AutoSlay use:
/// <see cref="CardSelectCmd.UseSelector"/> swaps the selector for the duration of a scope.
///
/// For a scry the prompt asks for 0..N cards to discard, so returning the first <c>minSelect</c>
/// options discards nothing — the friendliest default, and enough to prove the choice completes.
/// </summary>
// Qualified on purpose: the node namespace pulled in below declares its own ICardSelector, and the one
// this harness implements is the TestSupport one that CardSelectCmd consumes.
internal sealed class AutoCardSelector : MegaCrit.Sts2.Core.TestSupport.ICardSelector
{
    public Task<IEnumerable<CardModel>> GetSelectedCards(
        IEnumerable<CardModel> options, int minSelect, int maxSelect)
    {
        var picked = options.Take(Math.Max(0, minSelect)).ToList();
        return Task.FromResult<IEnumerable<CardModel>>(picked);
    }

    public CardRewardSelection GetSelectedCardReward(
        IReadOnlyList<CardCreationResult> options,
        IReadOnlyList<CardRewardAlternative> alternatives) =>
        throw new NotSupportedException("card rewards are not part of this harness");
}

/// <summary>
/// Holds the most recently created REAL selection screen so the self-driving check can answer it.
///
/// The screen is captured where the game creates it (<c>CardSelectCmd.FromSimpleGrid</c> does
/// <c>NSimpleCardSelectScreen.Create(...)</c> then <c>NOverlayStack.Push(...)</c> then awaits
/// <c>CardsSelected()</c>), which is the branch that is skipped entirely whenever a selector is
/// installed — and AutoSlay installs one for the whole run, so the UI path never opens under the bot.
/// </summary>
internal static class RealSelectScreenProbe
{
    private static NSimpleCardSelectScreen? _latest;

    /// <summary>Set by the harness while a play is expected to open a real screen that we must answer.</summary>
    internal static bool Drive;

    /// <summary>How many grid entries the driver should press before confirming.</summary>
    internal static int Clicks = 2;

    /// <summary>Whether the driver managed to release this screen (button press or completion).</summary>
    internal static bool Answered;

    internal static void Register(NSimpleCardSelectScreen screen)
    {
        _latest = screen;
        MainFile.Logger.Info(
            "[scrycheck] REAL selection screen created — the UI path is open (grid population, click " +
            "handlers and completion are now being exercised)");

        // Started from here rather than polled for, because this postfix is already the exact moment the
        // screen exists — polling only added a wait that had to be correct, and the first version's was
        // not (Cmd.Wait is a no-op under AutoSlay; see the note on RealYields).
        if (Drive) RealSelectScreenDriver.BeginDrive(screen, Clicks);
    }

    internal static NSimpleCardSelectScreen? Take()
    {
        var screen = _latest;
        _latest = null;
        return screen;
    }
}

[HarmonyPatch(
    typeof(NSimpleCardSelectScreen),
    "Create",
    new[] { typeof(IReadOnlyList<CardModel>), typeof(CardSelectorPrefs) })]
internal static class RealSelectScreenPatch
{
    [HarmonyPostfix]
    private static void Postfix(NSimpleCardSelectScreen __result)
    {
        try
        {
            if (__result != null) RealSelectScreenProbe.Register(__result);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] could not capture the selection screen: {e.Message}");
        }
    }
}

/// <summary>
/// Drives the real selection screen the way a player does: presses grid entries through the grid's own
/// <c>HolderPressed</c> signal (the exact path a mouse press takes — the screen's <c>OnCardClicked</c>
/// is wired to it) and then presses the confirm button.
///
/// This exists because the one path never covered by the bot is the real one: with a selector installed
/// <c>CardSelectCmd.FromSimpleGrid</c> never reaches its UI branch, so the screen that historically hung
/// was never created at all in any automated run. Driving via the signal rather than by setting private
/// state keeps the click wiring, the highlight calls and the confirm gating inside the test.
/// </summary>
internal static class RealSelectScreenDriver
{
    /// <summary>Starts answering a screen that has just been created.</summary>
    internal static void BeginDrive(NSimpleCardSelectScreen screen, int wantedClicks)
    {
        TaskHelper.RunSafely(DriveAsync(screen, wantedClicks));
    }

    private static async Task DriveAsync(NSimpleCardSelectScreen screen, int wantedClicks)
    {
        try
        {
            // Every node this driver touches is assigned in _Ready(), which runs when the screen enters
            // the tree — i.e. AFTER Create() returned and this task was started. A null here therefore
            // means "not ready yet", not "broken", and it has to be waited for: reading the fields once at
            // Register time found a null grid, quit immediately, and left the scry awaiting a selection
            // that nothing would ever make.
            //
            // Both nodes are waited for, not just the grid: _confirmButton is also a _Ready product, and
            // falling through to the CompleteSelection fallback would be weaker evidence than pressing it.
            NCardGrid grid = null;
            NClickableControl confirm = null;
            for (var tick = 0; tick < 100 && (grid == null || confirm == null); tick++)
            {
                await Task.Delay(50);
                grid = Field<NCardGrid>(screen, typeof(NCardGridSelectionScreen), "_grid");
                confirm = Field<NClickableControl>(screen, typeof(NSimpleCardSelectScreen), "_confirmButton");
            }

            if (grid == null || confirm == null)
            {
                MainFile.Logger.Error(
                    "[scrycheck] drive: screen nodes never became ready within 5s " +
                    $"(grid={grid != null}, confirm={confirm != null})");
                return;
            }

            // The grid is wired to HolderPressed in the same _Ready(), so by this point a press reaches
            // the screen's OnCardClicked.
            //
            // The wait below deliberately uses Task.Delay and NOT Cmd.Wait: Cmd.Wait opens with
            // `if (!NonInteractiveMode.IsActive && …)`, and NonInteractiveMode.IsActive is true for the
            // entire run under --autoslay, so every Cmd.Wait returns without yielding at all. That is what
            // made this harness "wait 20s" for a player and finish in zero milliseconds. Task.Delay
            // genuinely yields; the game's own WaitHelper.Until is built on it for the same reason.
            var holders = grid.CurrentlyDisplayedCardHolders?.ToList();
            for (var tick = 0; tick < 100 && (holders == null || holders.Count == 0); tick++)
            {
                await Task.Delay(50);
                holders = grid.CurrentlyDisplayedCardHolders?.ToList();
            }

            if (holders == null || holders.Count == 0)
            {
                MainFile.Logger.Error("[scrycheck] drive: grid never populated within 5s");
                return;
            }

            var clicks = Math.Min(wantedClicks, holders.Count);
            MainFile.Logger.Info(
                $"[scrycheck] drive: grid shows {holders.Count} card(s), pressing {clicks} through HolderPressed");

            foreach (var holder in holders.Take(clicks))
            {
                grid.EmitSignal(NCardGrid.SignalName.HolderPressed, holder);
                await Task.Delay(150);
            }

            MainFile.Logger.Info($"[scrycheck] drive: selection now holds {SelectedCount(screen)} card(s)");

            if (PressConfirm(screen))
            {
                RealSelectScreenProbe.Answered = true;
                MainFile.Logger.Info("[scrycheck] drive: pressed the confirm button");
                return;
            }

            // No pressable button: finish through the screen's own completion path so the awaiting scry is
            // still released. Logged as such rather than dressed up as a button press.
            var completed = Invoke(screen, "CompleteSelection");
            RealSelectScreenProbe.Answered = completed;
            MainFile.Logger.Info(
                $"[scrycheck] drive: confirm button unavailable, CompleteSelection invoked={completed}");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] drive: threw {e.GetType().Name}: {e.Message}");
        }
    }

    private static T? Field<T>(object target, Type declaring, string name) where T : class
    {
        try
        {
            return declaring
                .GetField(name, BindingFlags.NonPublic | BindingFlags.Instance)
                ?.GetValue(target) as T;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] drive: could not read {declaring.Name}.{name}: {e.Message}");
            return null;
        }
    }

    private static int SelectedCount(NSimpleCardSelectScreen screen)
    {
        try
        {
            var value = screen
                .GetType()
                .GetField("_selectedCards", BindingFlags.NonPublic | BindingFlags.Instance)
                ?.GetValue(screen);

            if (value == null)
            {
                MainFile.Logger.Info("[scrycheck] drive: _selectedCards unreadable (field missing or null)");
                return -1;
            }

            // Counted through IEnumerable, not the non-generic ICollection: HashSet<T> does not implement
            // the latter, so the first version of this reported -1 for a perfectly healthy selection set —
            // the same cast-that-cannot-succeed shape as the BaseButton bug.
            if (value is System.Collections.IEnumerable sequence)
            {
                var count = 0;
                foreach (var _ in sequence) count++;
                return count;
            }

            MainFile.Logger.Info(
                $"[scrycheck] drive: _selectedCards has unexpected type {value.GetType().Name}");
            return -1;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] drive: could not count _selectedCards: {e.Message}");
            return -1;
        }
    }

    private static bool PressConfirm(NSimpleCardSelectScreen screen)
    {
        try
        {
            var button = Field<NClickableControl>(screen, typeof(NSimpleCardSelectScreen), "_confirmButton");
            if (button == null) return false;

            // NClickableControl.Released, NOT Godot's BaseButton.pressed.
            //
            // The screen connects its confirm handler to NClickableControl.SignalName.Released
            // (NSimpleCardSelectScreen.cs:168), and NConfirmButton's chain is
            // NConfirmButton -> NButton -> NClickableControl -> Godot.Control — there is no
            // Godot.BaseButton anywhere in it, which is also why casting the field to BaseButton returned
            // null even when the field was perfectly fine.
            // WITH the argument. Released is declared as ReleasedEventHandler(NClickableControl button)

            // and the game emits it the same way (EmitSignal(SignalName.Released, this)); a callable that

            // expects one argument does not run when the signal is emitted with none, so omitting it left

            // CompleteSelection unreached while every preceding line reported success.

            button.EmitSignal(NClickableControl.SignalName.Released, button);
            return true;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] drive: confirm press failed: {e.Message}");
            return false;
        }
    }

    private static bool Invoke(NSimpleCardSelectScreen screen, string method)
    {
        try
        {
            var info = screen
                .GetType()
                .GetMethod(method, BindingFlags.NonPublic | BindingFlags.Instance);
            if (info == null) return false;

            info.Invoke(screen, null);
            return true;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] drive: {method} failed: {e.Message}");
            return false;
        }
    }
}

/// <summary>
/// A scripted, self-running gameplay check. Enable it by creating an empty file in
/// <c>mods/Yetannia/</c>; the next combat then runs the scenario once and logs the result. Nothing is
/// driven from outside the game, so no UI automation is involved.
///
/// Three modes, in increasing order of what they prove:
///
/// <list type="bullet">
/// <item><c>scrycheck.flag</c> — swaps in an auto selector. Proves the scry *logic* completes.</item>
/// <item><c>scrycheck.ui.flag</c> — no swap, so the real selection screen must appear and be answered
/// by a human. This is the mode that reproduces the reported hang in place: if it never appears or never
/// returns, the log ends on the matching begin line with no end.</item>
/// <item><c>scrycheck.uidrive.flag</c> — no swap <em>and</em> the screen is answered automatically by
/// pressing grid entries through the grid's own signal and then the confirm button. Same coverage as the
/// ui mode, but it can run unattended.</item>
/// </list>
///
/// For the last two the installed selector has to come off first: AutoSlay installs one for the whole
/// run and <c>CardSelectCmd.FromSimpleGrid</c> only reaches its UI branch when no selector is active.
/// <see cref="CardSelectCmd.SuspendSelectorForTest"/> is the game's own supported way to do that.
/// </summary>
[HarmonyPatch(typeof(NCombatRoom), nameof(NCombatRoom._Ready))]
internal static class ScryCheckHarness
{
    private const string AutoFlagFileName = "scrycheck.flag";
    private const string UiFlagFileName = "scrycheck.ui.flag";
    private const string UiDriveFlagFileName = "scrycheck.uidrive.flag";
    private static bool _ran;

    [HarmonyPostfix]
    private static void Postfix()
    {
        if (_ran) return;

        var auto = FlagExists(AutoFlagFileName);
        var ui = FlagExists(UiFlagFileName);
        var drive = FlagExists(UiDriveFlagFileName);
        if (!auto && !ui && !drive)
        {
            MainFile.Logger.Info(
                $"[scrycheck] disabled (create mods/Yetannia/{AutoFlagFileName} for the headless run, " +
                $"{UiFlagFileName} to exercise the real selection screen, or {UiDriveFlagFileName} to " +
                "exercise it and answer it automatically)");
            return;
        }

        _ran = true;
        TaskHelper.RunSafely(RunAsync(useRealSelectionScreen: ui || drive, driveScreen: drive));
    }

    private static bool FlagExists(string fileName)
    {
        try
        {
            var modDir = Godot.ProjectSettings.GlobalizePath("res://");
            var path = System.IO.Path.Combine(modDir, "mods", "Yetannia", fileName);
            return System.IO.File.Exists(path);
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] could not probe {fileName}: {e.Message}");
            return false;
        }
    }

    private static async Task RunAsync(bool useRealSelectionScreen, bool driveScreen)
    {
        try
        {
            // NCombatRoom._Ready can fire before the local player exists, so wait for it instead of
            // giving up - otherwise the scenario silently never runs and a "no local player" error is
            // all the log shows.
            //
            // The wait MUST yield real frames. It used to be `await Cmd.Wait(0.5f)`, which under
            // --autoslay never yields (NonInteractiveMode.IsActive is true for the whole run), so all 40
            // attempts ran inside the synchronous _Ready callback and the "after 20s" message actually
            // meant "after zero milliseconds". Task.Delay is the same primitive the game's own
            // WaitHelper.Until uses.
            Player player = null;
            for (var attempt = 0; attempt < 40 && player == null; attempt++)
            {
                var state = CombatManager.Instance?.DebugOnlyGetState();
                player = state == null ? null : LocalContext.GetMe(state);
                if (player == null) await Task.Delay(500);
            }

            if (player == null)
            {
                // Let a later combat try again rather than burning the whole run on one early failure.
                _ran = false;
                MainFile.Logger.Error("[scrycheck] no local player after 20s; will retry in the next combat");
                return;
            }

            RealSelectScreenProbe.Drive = driveScreen;

            MainFile.Logger.Info(
                $"[scrycheck] === scenario start (real selection screen: {useRealSelectionScreen}, " +
                $"auto-driven: {driveScreen}) ===");

            // 1) A plain scry card (挥舞 / GlimpseFate: Scry 1, draw 1).
            var returned = 0;
            if (await PlayScryCard<GlimpseFate>(player, "GlimpseFate", useRealSelectionScreen, driveScreen)) returned++;

            // 2) A bigger scry that also opens a *second* screen afterwards (破釜沉舟: scry 6, then
            //    exhaust what was discarded) - a good stress case for nested choices.
            if (await PlayScryCard<GrandProphecy>(player, "GrandProphecy", useRealSelectionScreen, driveScreen)) returned++;

            MainFile.Logger.Info(
                returned == 2
                    ? "[scrycheck] === scenario finished: both scries returned ==="
                    : $"[scrycheck] === scenario finished: only {returned}/2 scries returned — see the begin/end pairs above ===");
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] scenario threw: {e}");
        }
    }

    /// <summary>Returns true only when the play actually came back; a begin with no matching end is false.</summary>
    private static async Task<bool> PlayScryCard<T>(
        Player player, string label, bool useRealSelectionScreen, bool driveScreen)
        where T : CardModel
    {
        CardModel card = null;
        try
        {
            card = player.Creature.CombatState.CreateCard<T>(player);
            await CardPileCmd.AddGeneratedCardToCombat(card, PileType.Hand, player);

            var context = new BlockingPlayerChoiceContext();
            RealSelectScreenProbe.Answered = false;

            MainFile.Logger.Info($"[scrycheck] {label}: begin (ctx={context.GetType().Name})");

            if (useRealSelectionScreen)
            {
                // No selector may be active or the UI branch is skipped. AutoSlay installs one for the
                // whole run, so it has to come off here - and go back on afterwards, or the bot's own
                // card-reward and event choices would start waiting for a human.
                using var suspendedGlobal = CardSelectCmd.SuspendSelectorForTest();
                using var suspendedLocal = CardSelectCmd.SuspendSelectorForTest(localOnly: true);

                // The driver is triggered from the screen-creation postfix, not polled for here: that
                // postfix runs at the exact moment the screen exists, so there is no wait to get wrong.
                var task = CardCmd.AutoPlay(context, card, null);
                await task;

                MainFile.Logger.Info($"[scrycheck] {label}: real screen answered={RealSelectScreenProbe.Answered}");
            }
            else
            {
                // The selector swap is what lets the scry's choice resolve without a human.
                using (CardSelectCmd.UseSelector(new AutoCardSelector(), localOnly: true))
                {
                    var task = CardCmd.AutoPlay(context, card, null);
                    await task;
                }
            }

            MainFile.Logger.Info($"[scrycheck] {label}: end (returned)");
            return true;
        }
        catch (Exception e)
        {
            MainFile.Logger.Error($"[scrycheck] {label}: threw {e.GetType().Name}: {e.Message}");
            return false;
        }
        finally
        {
            if (card != null && card.Pile != null)
            {
                await CardPileCmd.RemoveFromCombat(card);
            }
        }
    }
}
