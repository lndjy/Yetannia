# r44 verify: deploy the freshly built mod into the game, launch it, collect the runtime self-check
# lines, and photograph the character-select screen (which is where the new blurb shows).
#
# ASCII only: Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI.
#
# Usage: & .tools\r44-verify.ps1 [-Language zhs|eng] [-SkipUi]
#   -Language  sets settings.save's language before launching (so the English path can be checked);
#              the caller restores it. Default: leave the save exactly as found.
#   -SkipUi    skip the main-menu -> character-select navigation (the click coordinates are for the
#              Chinese menu; the log is collected either way).
# Restores: closes the game it launched. Reloads settings.save only when -Language was used.
param(
  [string]$Language = '',
  [switch]$SkipUi
)
$ErrorActionPreference = 'Continue'
$tools  = $PSScriptRoot
$root   = Split-Path $tools -Parent
$game   = 'D:\SteamLibrary\steamapps\common\Slay the Spire 2'
$modDir = Join-Path $game 'mods\Yetannia'
$logDir = "$env:APPDATA\SlayTheSpire2\logs"
# The SteamID64 folder used to be hard-coded here. It is derived from the active account at run time
# instead, because this file is tracked in a public repository and a hard-coded id publishes the account.
$sid    = 76561197960265728 + (Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess' -Name ActiveUser).ActiveUser
$save   = "$env:APPDATA\SlayTheSpire2\steam\$sid\settings.save"
$outDir = Join-Path $tools ("out\r44" + $(if ($Language) { "-$Language" } else { '' }))
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# ---------------------------------------------------------------- close anything running
if (Get-Process -Name 'SlayTheSpire2' -ErrorAction SilentlyContinue) {
  Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
  Start-Sleep -Seconds 8
  Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
    ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
  Start-Sleep -Seconds 4
}

# ---------------------------------------------------------------- optional language switch
if ($Language) {
  $json = Get-Content $save -Raw -Encoding utf8 | ConvertFrom-Json
  Write-Host ("language: {0} -> {1}" -f $json.language, $Language)
  $json.language = $Language
  # No BOM: the game reads this file as UTF-8 and a BOM has bitten this workspace before.
  [System.IO.File]::WriteAllText($save, (ConvertTo-Json $json -Compress -Depth 12), (New-Object System.Text.UTF8Encoding($false)))
}

# ---------------------------------------------------------------- deploy
$artifacts = @(
  @{ src = Join-Path $root 'Yetannia\bin\Release\Yetannia.dll'; dst = 'Yetannia.dll' },
  @{ src = Join-Path $root 'Yetannia\bin\Release\Yetannia.pdb'; dst = 'Yetannia.pdb' },
  @{ src = Join-Path $root 'Yetannia\Yetannia.json';           dst = 'Yetannia.json' },
  @{ src = Join-Path $root 'Yetannia\build\Yetannia.pck';       dst = 'Yetannia.pck' }
)
Write-Host '--- deployed ---'
foreach ($a in $artifacts) {
  if (-not (Test-Path $a.src)) { throw "missing artifact $($a.src)" }
  Copy-Item $a.src (Join-Path $modDir $a.dst) -Force
  $h = (Get-FileHash $a.src -Algorithm SHA256).Hash.Substring(0, 16)
  Write-Host ("  {0,-14} {1,10:N0} bytes  sha256:{2}" -f $a.dst, (Get-Item $a.src).Length, $h)
}
$before = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host ("newest log before launch: {0} ({1:N0} bytes)" -f $before.Name, $before.Length)

# ---------------------------------------------------------------- launch and wait for the main menu
$start = Get-Date
$proc = Start-Process -FilePath (Join-Path $game 'SlayTheSpire2.exe') -WorkingDirectory $game -PassThru
Write-Host "launched pid=$($proc.Id)"
$deadline = (Get-Date).AddSeconds(300)
$log = $null
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 5
  if ($proc.HasExited) { Write-Host "GAME EXITED code=$($proc.ExitCode)"; break }
  $cand = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
          Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($cand -and (Select-String -Path $cand.FullName -Pattern 'main menu loaded' -Encoding utf8 -Quiet -ErrorAction SilentlyContinue)) {
    $log = $cand; break
  }
  if ($cand) { $log = $cand }
}
Write-Host "main menu reached=$([bool]$log)  log=$($log.FullName)"
Start-Sleep -Seconds 8

# ---------------------------------------------------------------- photograph the select screen
. (Join-Path $tools 'game-input.ps1')
function Shot([string]$name) {
  $p = Join-Path $outDir $name
  try { Save-Shot -Path $p | Out-Null } catch { Write-Host "  shot $name FAILED: $_" }
  Write-Host "  shot $name"
}
function Resize-To([int]$w, [int]$h) {
  $hw = Get-GameWindow
  if ($hw -eq [IntPtr]::Zero) { return }
  [GIn]::MoveWindow($hw, 0, 0, $w, $h, $true) | Out-Null
  Start-Sleep -Seconds 4
  Focus-Game | Out-Null
  Start-Sleep -Seconds 1
  [GIn]::SetCursorPos(1500, 1000) | Out-Null
  Start-Sleep -Seconds 2
}

if (-not $SkipUi) {
  Resize-To 1920 1080
  Shot '00_menu.png'
  Write-Host 'clicking 单人模式'
  Click-At -X 784 -Y 658
  Start-Sleep -Seconds 5
  Shot '01_modes.png'
  Write-Host 'clicking 标准模式'
  Click-At -X 519 -Y 368
  Start-Sleep -Seconds 7
  Shot '02_select_asopened.png'

  # Round 43 measured every tile's x at this window geometry; y=903 is the tile row. x=1170 is
  # Yetannia's tile (the neighbouring x=1250 is 随机 / random).
  foreach ($x in @(622, 733, 842, 954, 1059, 1170, 1250)) {
    Write-Host "clicking tile x=$x"
    Click-At -X $x -Y 903
    Start-Sleep -Seconds 3
    [GIn]::SetCursorPos(1500, 1000) | Out-Null
    Start-Sleep -Seconds 1
    Shot ("tile_x{0}.png" -f $x)
  }
}

# ---------------------------------------------------------------- close
if (-not $proc.HasExited) {
  Write-Host 'closing game...'
  Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
  Start-Sleep -Seconds 8
  Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
    ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
  Start-Sleep -Seconds 4
}

$fresh = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
         Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($fresh) {
  Copy-Item $fresh.FullName (Join-Path $outDir 'godot-r44.log') -Force
  Write-Host "log copied: $($fresh.FullName)"
}

Write-Host ''
Write-Host '==================== self-check (new lines) ===================='
if ($fresh) {
  Select-String -Path $fresh.FullName -Pattern 'self-check (talk|relic name|relic flavor|char blurb|relic loc|starting relic)' -Encoding utf8 |
    ForEach-Object { $_.Line.Trim() }
}
Write-Host ''
Write-Host '==================== relic icon loads ===================='
if ($fresh) {
  Select-String -Path $fresh.FullName -Pattern 'self-check relic (icon|desc)' -Encoding utf8 |
    ForEach-Object { $_.Line.Trim() }
}
Write-Host ''
Write-Host '==================== mod errors / loc errors ===================='
if ($fresh) {
  Select-String -Path $fresh.FullName -Pattern 'MOD_ERROR|Exception thrown while loading mod|self-check failed|not found in table|LocException|\[Yetannia\].*ERROR' -Encoding utf8 |
    Select-Object -First 25 | ForEach-Object { $_.Line.Trim() }
}
Write-Host ''
Write-Host "game still running: $([bool](Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue))"
