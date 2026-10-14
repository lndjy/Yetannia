# Launches Slay the Spire 2, waits for Yetannia's mod initialization to appear in the log,
# reports what happened, then closes the game again.
#
# Must run with full filesystem access: the game writes its user data (logs, saves) under
# %APPDATA%\SlayTheSpire2, which the workspace sandbox denies.
$ErrorActionPreference = 'Continue'

$game   = "D:\SteamLibrary\steamapps\common\Slay the Spire 2"
$logDir = "$env:APPDATA\SlayTheSpire2\logs"

# A BaseLib copy is already installed through Steam Workshop; keeping a second copy in the local
# mods folder makes the game pick one of them arbitrarily, so drop ours.
if (Test-Path "$game\mods\BaseLib") {
    Remove-Item -Recurse -Force "$game\mods\BaseLib"
    Write-Host "removed duplicate local BaseLib (workshop copy is used instead)"
}

$start = Get-Date
$out = Join-Path $env:TEMP 'sts2_stdout.txt'
$err = Join-Path $env:TEMP 'sts2_stderr.txt'
$proc = Start-Process -FilePath (Join-Path $game 'SlayTheSpire2.exe') -WorkingDirectory $game `
    -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Write-Host "launched pid=$($proc.Id) at $($start.ToString('s'))"

$deadline = (Get-Date).AddSeconds(180)
$found = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 4
    if ($proc.HasExited) { Write-Host "GAME EXITED EARLY code=$($proc.ExitCode)"; break }

    $newLogs = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
               Where-Object { $_.LastWriteTime -gt $start }
    foreach ($f in $newLogs) {
        $m = Select-String -Path $f.FullName -Pattern "Finished mod initialization for 'Yetannia'|Exception thrown while loading mod Yetannia|MOD_ERROR" -Encoding utf8 -ErrorAction SilentlyContinue
        if ($m) { $found = $f; break }
    }
    if ($found) { break }
}
Write-Host "yetanniaInitSeen=$([bool]$found)"
if ($found) { Write-Host "logFile=$($found.FullName)" }

# Give the game a moment to reach the main menu, then shut it down.
Start-Sleep -Seconds 10
if (-not $proc.HasExited) {
    $proc.CloseMainWindow() | Out-Null
    Start-Sleep -Seconds 10
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    Write-Host "game closed"
}

Write-Host ""
Write-Host "==================== log files touched by this run ===================="
Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $start } |
    ForEach-Object { "  $($_.LastWriteTime.ToString('s'))  $([math]::Round($_.Length/1KB,1))KB  $($_.Name)" }

Write-Host ""
Write-Host "==================== Yetannia / local mod lines ===================="
Select-String -Path (Join-Path $logDir 'godot*.log') -Pattern "Yetannia|mods\\BaseLib|SlaytheSpire2.unlockAll" -Encoding utf8 -ErrorAction SilentlyContinue |
    Select-Object -First 60 | ForEach-Object { $_.Line.Trim() }

Write-Host ""
Write-Host "==================== errors / warnings about mods ===================="
Select-String -Path (Join-Path $logDir 'godot*.log') -Pattern "MOD_ERROR|Exception thrown while loading mod|Failed to load|Tried to load mod|does not look like a mod manifest|is missing the 'id' field|assembly, but no assembly" -Encoding utf8 -ErrorAction SilentlyContinue |
    Select-Object -First 40 | ForEach-Object { $_.Line.Trim() }

Write-Host ""
Write-Host "==================== stdout (last 20) ===================="
if (Test-Path $out) { Get-Content $out -Tail 20 }
Write-Host "==================== stderr (last 20) ===================="
if (Test-Path $err) { Get-Content $err -Tail 20 }
