# qa-round39-verify.ps1 -- run a seeded autoslay run and capture a dense sequence of client-area shots,
# so the campfire (rest site) and shop (merchant) figures can be inspected in the real game.
#
# Same mechanism as out/visual/verify-run.ps1: the retail build gates --autoslay behind !IsReleaseGame()
# and the YetanniaQA scaffold's ReleaseGamePatch opens that gate, so the scaffold is enabled for the
# duration and disabled again afterwards.
#
# ASCII only (PowerShell 5.1 reads BOM-less .ps1 as ANSI).
param(
  [string]$OutDir = '',
  [int]$Shots = 40,
  [int]$IntervalSeconds = 5,
  [string]$ExtraFlags = '--autoslay --qagym --qarelic --qaprobe --qawin --seed=qa7'
)
$ErrorActionPreference = 'Continue'
$tools = $PSScriptRoot
$root = Split-Path $tools -Parent
$game = 'D:\SteamLibrary\steamapps\common\Slay the Spire 2'
$logDir = "$env:APPDATA\SlayTheSpire2\logs"
# The SteamID64 folder used to be hard-coded here. It is derived from the active account at run time
# instead, because this file is tracked in a public repository and a hard-coded id publishes the account.
$sid = 76561197960265728 + (Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess' -Name ActiveUser).ActiveUser
$save = "$env:APPDATA\SlayTheSpire2\steam\$sid\settings.save"
if (-not $OutDir) { $OutDir = Join-Path $tools 'out\qa39' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

. (Join-Path $tools 'game-input.ps1')
Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 4
Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
  ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
Start-Sleep -Seconds 3

if (-not (Test-Path $save)) { Write-Host "settings.save not found"; exit 1 }
node (Join-Path $tools 'set-mod-enabled.js') $save YetanniaQA true

$start = Get-Date
$exe = Join-Path $game 'SlayTheSpire2.exe'
$proc = Start-Process -FilePath $exe -ArgumentList $ExtraFlags -WorkingDirectory $game -PassThru
Write-Host "launched pid=$($proc.Id) flags='$ExtraFlags'"

# wait for the main menu so the window exists, then start shooting
$deadline = (Get-Date).AddSeconds(200)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 5
  if ($proc.HasExited) { Write-Host "GAME EXITED EARLY code=$($proc.ExitCode)"; break }
  $hit = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
         Where-Object { $_.LastWriteTime -gt $start } |
         ForEach-Object { Select-String -Path $_.FullName -Pattern 'main menu loaded' -Encoding utf8 -ErrorAction SilentlyContinue }
  if ($hit) { break }
}
Start-Sleep -Seconds 10

for ($i = 1; $i -le $Shots; $i++) {
  if ($proc.HasExited) { Write-Host "game gone before shot $i"; break }
  $shot = Join-Path $OutDir ("r{0:d02}.png" -f $i)
  try { Save-Shot -Path $shot | Out-Null } catch { Write-Host "shot $i failed: $_" }
  Start-Sleep -Seconds $IntervalSeconds
}

if (-not $proc.HasExited) {
  Write-Host 'closing game...'
  Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
  Start-Sleep -Seconds 8
  Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
    ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
  Start-Sleep -Seconds 4
}
node (Join-Path $tools 'set-mod-enabled.js') $save YetanniaQA false
Remove-Item ($save + '.bak') -ErrorAction SilentlyContinue
Write-Host 'restored settings.save'
Get-ChildItem $OutDir -Filter 'r*.png' | Measure-Object | ForEach-Object { Write-Host "shots: $($_.Count)" }
