# qa-round39-quick.ps1 -- launch once with no flags, wait for the main menu so ModSelfCheck has run,
# then dump the Yetannia self-check lines and close. Used to confirm Harmony attachments landed
# (get the game to the main menu only, so it is a ~1 minute check instead of a full run).
#
# ASCII only (PowerShell 5.1 reads BOM-less .ps1 as ANSI).
param([int]$WaitSeconds = 150, [string]$Pattern = 'self-check')
$ErrorActionPreference = 'Continue'
$game = 'D:\SteamLibrary\steamapps\common\Slay the Spire 2'
$logDir = "$env:APPDATA\SlayTheSpire2\logs"
$start = Get-Date

Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 4
Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
  ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
Start-Sleep -Seconds 3

$proc = Start-Process -FilePath (Join-Path $game 'SlayTheSpire2.exe') -WorkingDirectory $game -PassThru
Write-Host "launched pid=$($proc.Id)"

$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 5
  if ($proc.HasExited) { Write-Host "GAME EXITED code=$($proc.ExitCode)"; break }
  $hit = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
         Where-Object { $_.LastWriteTime -gt $start } |
         ForEach-Object { Select-String -Path $_.FullName -Pattern 'self-check merchant' -Encoding utf8 -ErrorAction SilentlyContinue }
  if ($hit) { break }
}

Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 8
Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
  ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
Start-Sleep -Seconds 3

Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -gt $start } | ForEach-Object {
    Write-Host "--- $($_.Name) ---"
    Select-String -Path $_.FullName -Pattern $Pattern -Encoding utf8 | ForEach-Object { $_.Line.Trim() }
  }
