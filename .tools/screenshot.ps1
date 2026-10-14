# Brings the Slay the Spire 2 window to the front (resizing it to fit the primary screen),
# optionally clicks a sequence of points, then captures the screen.
#
# Usage:
#   powershell -File screenshot.ps1 -Out shot.png [-WaitSeconds 90] [-Clicks "768,700;768,400"]
#
# ASCII only: Windows PowerShell 5.1 reads .ps1 files as ANSI unless they carry a UTF-8 BOM.
param(
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$WaitSeconds = 0,
    [string]$Clicks = ""
)

$ErrorActionPreference = 'Continue'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int ht, bool repaint);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int max);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool attach);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
    [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr h);

    public const uint LEFTDOWN = 0x0002, LEFTUP = 0x0004;
    public const int SW_RESTORE = 9, SW_SHOW = 5;

    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        System.Threading.Thread.Sleep(250);
        mouse_event(LEFTDOWN, 0, 0, 0, IntPtr.Zero);
        System.Threading.Thread.Sleep(80);
        mouse_event(LEFTUP, 0, 0, 0, IntPtr.Zero);
    }

    public static string ForegroundTitle() {
        var sb = new System.Text.StringBuilder(512);
        GetWindowText(GetForegroundWindow(), sb, sb.Capacity);
        return sb.ToString();
    }

    // Windows refuses SetForegroundWindow from a process that is not already foreground unless it
    // owns the foreground thread's input queue. Temporarily attaching to that thread lifts the
    // restriction; a synthetic ALT press makes the shell treat the call as user-initiated.
    public static void ForceForeground(IntPtr h) {
        keybd_event(0x12, 0, 0, UIntPtr.Zero);
        keybd_event(0x12, 0, 2, UIntPtr.Zero);

        IntPtr fg = GetForegroundWindow();
        uint fgPid;
        uint fgThread = GetWindowThreadProcessId(fg, out fgPid);
        uint myThread = GetCurrentThreadId();
        bool attached = false;
        if (fgThread != 0 && fgThread != myThread) attached = AttachThreadInput(myThread, fgThread, true);
        try {
            ShowWindow(h, SW_RESTORE);
            BringWindowToTop(h);
            SetForegroundWindow(h);
            SetFocus(h);
        } finally {
            if (attached) AttachThreadInput(myThread, fgThread, false);
        }
    }
}
"@

function Focus-Game {
    $proc = Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $proc) { Write-Host "game not running"; return $false }
    $hwnd = $proc.MainWindowHandle
    if ($hwnd -eq [IntPtr]::Zero) { Write-Host "game has no main window yet"; return $false }

    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    # The saved window is larger than the screen; shrink it so the whole UI is visible and
    # click coordinates are predictable.
    [Win]::ShowWindow($hwnd, [Win]::SW_RESTORE) | Out-Null
    [Win]::MoveWindow($hwnd, 0, 0, $screen.Width, $screen.Height, $true) | Out-Null
    Start-Sleep -Seconds 2
    [Win]::ForceForeground($hwnd)
    Start-Sleep -Seconds 2
    Write-Host "focused game window (foreground now: '$([Win]::ForegroundTitle())')"
    return $true
}

if ($WaitSeconds -gt 0) {
    Write-Host "waiting $WaitSeconds s for the game to finish loading..."
    Start-Sleep -Seconds $WaitSeconds
}

[void](Focus-Game)

if ($Clicks -ne "") {
    foreach ($pair in $Clicks.Split(';')) {
        if ($pair.Trim() -eq "") { continue }
        $xy = $pair.Split(',')
        $x = [int]$xy[0]; $y = [int]$xy[1]
        Write-Host "clicking $x,$y"
        [Win]::Click($x, $y)
        Start-Sleep -Seconds 3
    }
    Start-Sleep -Seconds 4
}

[void](Focus-Game)

$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)
$dir = Split-Path $Out -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$gfx.Dispose(); $bmp.Dispose()
Write-Host "saved $Out ($($bounds.Width)x$($bounds.Height))"
