# Game window input + screenshot helper for automated in-game testing.
#
# ASCII-only on purpose: Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI.
#
# Same-integrity launch is required (see start-game.ps1 / steam_appid.txt); with a Steam-launched
# game the harness cannot send input at all. The remaining obstacle is the Windows *foreground lock*,
# which Focus-Game defeats with AttachThreadInput + a synthetic ALT press.
#
# Every input and capture function re-focuses first. Without that, a click whose coordinates miss the
# game hands the foreground to whatever is behind it, and the next capture silently records that
# window instead of the game -- which is how an earlier attempt "lost" the game.
#
# Usage (dot-source):
#   . .tools\game-input.ps1
#   Start-Game                     # launch directly and wait for the main menu
#   Send-ConsoleCommand 'card strike'
#   Save-Shot -Path shot.png

Add-Type -AssemblyName System.Drawing

# This box runs at 125% display scaling (physical 1920x1080, window DPI 120) while a plain
# PowerShell host is DPI-*unaware*: it sees a virtualised 1536x864 desktop, GetWindowRect and
# CopyFromScreen work in that shrunken space, and -- the killer -- SetCursorPos/mouse_event take
# PHYSICAL pixels without scaling. So a click aimed at a screenshot coordinate landed 25% short and
# silently missed the button. Switching this thread to per-monitor-v2 makes every coordinate in this
# harness physical, which is also what the game (DPI aware) uses, so screenshot pixels == click
# coordinates again.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DpiAware {
  [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr ctx);
  [DllImport("user32.dll")] public static extern IntPtr GetThreadDpiAwarenessContext();
  [DllImport("user32.dll")] public static extern int GetAwarenessFromDpiAwarenessContext(IntPtr c);
  public static int MakePerMonitorV2() {
    SetThreadDpiAwarenessContext(new IntPtr(-4));  // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    return GetAwarenessFromDpiAwarenessContext(GetThreadDpiAwarenessContext());
  }
}
"@
[DpiAware]::MakePerMonitorV2() | Out-Null

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class GIn {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);`n  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int ht, bool repaint);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);`n  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint mapType);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, int dx, int dy, uint data, UIntPtr extra);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
}
"@

$script:GameDir = "D:\SteamLibrary\steamapps\common\Slay the Spire 2"
$script:ShotDir = "D:\桌面\sts2mod\.tools\shots"
$script:LastShotSize = $null   # width,height of the last full screenshot (for coord conversion)

function Get-GameWindow {
  $p = Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $p) { return [IntPtr]::Zero }
  return $p.MainWindowHandle
}

function Focus-Game {
  $h = Get-GameWindow
  if ($h -eq [IntPtr]::Zero) { throw "game window not found" }

  if ([GIn]::GetForegroundWindow() -eq $h) { return $true }

  [GIn]::ShowWindow($h, 9) | Out-Null   # SW_RESTORE

  $pid_ = 0
  $fgThread = [GIn]::GetWindowThreadProcessId([GIn]::GetForegroundWindow(), [ref]$pid_)
  $myThread = [GIn]::GetCurrentThreadId()

  # A key event seen by the foreground thread releases the foreground lock.
  [GIn]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero)
  [GIn]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)

  [GIn]::AttachThreadInput($myThread, $fgThread, $true) | Out-Null
  [GIn]::BringWindowToTop($h) | Out-Null
  [GIn]::SetForegroundWindow($h) | Out-Null
  [GIn]::AttachThreadInput($myThread, $fgThread, $false) | Out-Null

  Start-Sleep -Milliseconds 350
  return ([GIn]::GetForegroundWindow() -eq $h)
}

function Start-Game {
  param([int]$TimeoutSeconds = 180)
  if (-not (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue)) {
    $ud = Join-Path $env:APPDATA "SlayTheSpire2\logs"
    Remove-Item (Join-Path $ud "godot.log") -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath (Join-Path $script:GameDir "SlayTheSpire2.exe") -WorkingDirectory $script:GameDir | Out-Null
  }
  $ud = Join-Path $env:APPDATA "SlayTheSpire2\logs"
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $n = Get-ChildItem $ud -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($n -and (Select-String -Path $n.FullName -Pattern 'main menu loaded' -Encoding utf8 -ErrorAction SilentlyContinue)) {
      Start-Sleep -Seconds 3
      Focus-Game | Out-Null
      return $true
    }
  }
  return $false
}

function Save-Shot {
  param([string]$Path, [switch]$NoFocus)
  if (-not $NoFocus) { Focus-Game | Out-Null }
  Start-Sleep -Milliseconds 250
  $h = Get-GameWindow
  if ($h -eq [IntPtr]::Zero) { throw "game window not found" }
  # Capture the CLIENT area only: a window-rect capture includes the title bar and borders, which
  # shifts every coordinate read off the image away from the click position.
  $cr = New-Object GIn+RECT
  [GIn]::GetClientRect($h, [ref]$cr) | Out-Null
  $origin = New-Object GIn+POINT
  $origin.X = 0; $origin.Y = 0
  [GIn]::ClientToScreen($h, [ref]$origin) | Out-Null
  $w = $cr.R - $cr.L; $ht = $cr.B - $cr.T
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  # $origin is the client area's top-left in screen space; capturing from (0,0) silently grabs
  # whatever sits at the top-left of the desktop instead of the game.
  $g.CopyFromScreen($origin.X, $origin.Y, 0, 0, (New-Object System.Drawing.Size($w, $ht)))
  $g.Dispose()
  New-Item -ItemType Directory -Force -Path (Split-Path $Path) | Out-Null
  $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  $script:LastShotSize = @($w, $ht)
  return $Path
}

# Screenshots are shown to the model as a *downscaled preview*, so any coordinate read off one has to
# be scaled back up before it can be used as a click position. This prints the factor to divide by.
function Get-ShotScale {
  param([int]$PreviewWidth, [int]$PreviewHeight)
  if (-not $script:LastShotSize) { throw "take a shot first" }
  $sx = $script:LastShotSize[0] / $PreviewWidth
  $sy = $script:LastShotSize[1] / $PreviewHeight
  return @($sx, $sy)
}

function Send-Key {
  param([int]$VirtualKey, [int]$HoldMs = 40, [switch]$NoFocus)
  if (-not $NoFocus) { Focus-Game | Out-Null }
  $scan = [byte]([GIn]::MapVirtualKey([uint32]$VirtualKey, 0))
  [GIn]::keybd_event([byte]$VirtualKey, $scan, 0, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds $HoldMs
  [GIn]::keybd_event([byte]$VirtualKey, $scan, 2, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 130
}

function Send-Text {
  param([string]$Text, [switch]$NoFocus, [int]$CharDelayMs = 90)
  if (-not $NoFocus) { Focus-Game | Out-Null }
  foreach ($ch in $Text.ToCharArray()) {
    $code = [int][char]$ch
    $vk = $null
    $shift = $false
    if ($code -ge 97 -and $code -le 122) { $vk = $code - 32 }        # a-z (the game upper-cases ids itself)
    elseif ($code -ge 65 -and $code -le 90) { $vk = $code }          # A-Z
    elseif ($code -ge 48 -and $code -le 57) { $vk = $code }          # 0-9
    elseif ($code -eq 32) { $vk = 0x20 }                             # space
    elseif ($code -eq 45) { $vk = 0xBD }                             # -
    elseif ($code -eq 95) { $vk = 0xBD; $shift = $true }             # _ (shift + minus)
    elseif ($code -eq 46) { $vk = 0xBE }                             # .
    elseif ($code -eq 44) { $vk = 0xBC }                             # ,
    elseif ($code -eq 47) { $vk = 0xBF }                             # /
    if ($null -eq $vk) { continue }
    # Typing faster than the game's frame rate makes it drop and reorder characters, which silently
    # turns "card YETANNIA-EMPOWERED_VOLLEY" into garbage. Hold each key for a couple of frames and
    # leave a gap.
    if ($shift) { [GIn]::keybd_event(0x10, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 20 }
    Send-Key -VirtualKey $vk -HoldMs 45 -NoFocus
    if ($shift) { [GIn]::keybd_event(0x10, 0, 2, [UIntPtr]::Zero); Start-Sleep -Milliseconds 20 }
    Start-Sleep -Milliseconds $CharDelayMs
  }
}

# Clears whatever is currently in the dev console's input line (readline Ctrl+U).
function Clear-ConsoleLine {
  [GIn]::keybd_event(0x11, 0, 0, [UIntPtr]::Zero)
  Send-Key -VirtualKey 0x55 -NoFocus      # Ctrl+U
  [GIn]::keybd_event(0x11, 0, 2, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 150
}

function Click-At {
  param([int]$X, [int]$Y, [switch]$DoubleClick)
  Focus-Game | Out-Null
  $h = Get-GameWindow
  $pt = New-Object GIn+POINT
  $pt.X = $X; $pt.Y = $Y
  [GIn]::ClientToScreen($h, [ref]$pt) | Out-Null
  # Godot only starts routing clicks at a control once it has seen the pointer arrive there, so a
  # single teleport-then-click is silently swallowed. Walk the pointer in with real move events.
  for ($i = 1; $i -le 4; $i++) {
    $sx = [int]($pt.X - (5 - $i) * 40)
    $sy = [int]($pt.Y - (5 - $i) * 30)
    [GIn]::SetCursorPos($sx, $sy) | Out-Null
    [GIn]::mouse_event(0x0001, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 90
  }
  [GIn]::SetCursorPos($pt.X, $pt.Y) | Out-Null
  [GIn]::mouse_event(0x0001, 0, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 350
  [GIn]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 150
  [GIn]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
  if ($DoubleClick) {
    Start-Sleep -Milliseconds 90
    [GIn]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 150
    [GIn]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
  }
  Start-Sleep -Milliseconds 350
}

# The developer console toggles on ` ' * ^ or Shift+8 (see NDevConsole._Input).
function Open-Console {
  Send-Key -VirtualKey 0xC0      # VK_OEM_3 = ` ~
  Start-Sleep -Milliseconds 400
}

function Send-ConsoleCommand {
  param([string]$Command, [int]$SettleMs = 600)
  Open-Console
  Send-Text -Text $Command -NoFocus
  Start-Sleep -Milliseconds 200
  Send-Key -VirtualKey 0x0D -NoFocus   # Enter
  Start-Sleep -Milliseconds $SettleMs
}
