# Starts Steam, launches Slay the Spire 2 through Steam (direct exe launch fails SteamAPI_Init),
# waits for Yetannia's mod initialization to appear in the game log, then shuts everything down.
#
# Needs full filesystem access: the game and Steam write outside the workspace.
$ErrorActionPreference = 'Continue'

$game      = "D:\SteamLibrary\steamapps\common\Slay the Spire 2"
$logDir    = "$env:APPDATA\SlayTheSpire2\logs"
$steamExe  = 'C:\Program Files (x86)\Steam\steam.exe'
$appId     = '2868840'

$steamWasRunning = [bool](Get-Process steam -ErrorAction SilentlyContinue | Select-Object -First 1)

if (-not $steamWasRunning) {
    Write-Host "starting Steam..."
    Start-Process -FilePath $steamExe -ArgumentList '-silent','-no-browser' | Out-Null
    $deadline = (Get-Date).AddSeconds(180)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        $activeUser = (Get-ItemProperty 'HKCU:\Software\Valve\Steam\ActiveProcess' -ErrorAction SilentlyContinue).ActiveUser
        if ($activeUser -ne $null -and $activeUser -ne 0) { break }
    }
    Write-Host "steam logged in (activeUser=$activeUser); letting it settle..."
    Start-Sleep -Seconds 45
} else {
    Write-Host "Steam already running"
}

$start = Get-Date
Write-Host "launching app $appId through Steam..."
Start-Process "steam://rungameid/$appId" | Out-Null

# Wait for the game process to appear.
$proc = $null
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    $proc = Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($proc) { break }
}
if (-not $proc) { Write-Host "game process never appeared"; }
else { Write-Host "game running pid=$($proc.Id)" }

# Poll the game log until Yetannia shows up (or we time out).
$found = $null
$deadline = (Get-Date).AddSeconds(300)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $newLogs = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
               Where-Object { $_.LastWriteTime -gt $start }
    foreach ($f in $newLogs) {
        $m = Select-String -Path $f.FullName -Pattern "Finished mod initialization for 'Yetannia'|Exception thrown while loading mod Yetannia|MOD_ERROR" -Encoding utf8 -ErrorAction SilentlyContinue
        if ($m) { $found = $f; break }
    }
    if ($found) { break }
    $proc = Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $proc) { Write-Host "game exited"; break }
}
Write-Host "yetanniaInitSeen=$([bool]$found)"
if ($found) { Write-Host "logFile=$($found.FullName)" }

Start-Sleep -Seconds 15
Write-Host "closing game..."
Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object {
    $_.CloseMainWindow() | Out-Null
}
Start-Sleep -Seconds 10
Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==================== log files from this run ===================="
Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $start } |
    ForEach-Object { "  $($_.LastWriteTime.ToString('s'))  $([math]::Round($_.Length/1KB,1))KB  $($_.Name)" }

Write-Host ""
Write-Host "==================== Yetannia-related log lines ===================="
$fresh = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
         Where-Object { $_.LastWriteTime -gt $start } | Select-Object -ExpandProperty FullName
if ($fresh) {
    Select-String -Path $fresh -Pattern "Yetannia|YETANNIA|Prophet|TestAttack|TestSkill|mods\\Yetannia" -Encoding utf8 -ErrorAction SilentlyContinue |
        Select-Object -First 80 | ForEach-Object { $_.Line.Trim() }
}

Write-Host ""
Write-Host "==================== mod load summary ===================="
if ($fresh) {
    Select-String -Path $fresh -Pattern "RUNNING MODDED|Loaded \d+ mods|Finished mod initialization for 'BaseLib'|Setting up mods|duplicate|Disabling" -Encoding utf8 -ErrorAction SilentlyContinue |
        Select-Object -First 30 | ForEach-Object { $_.Line.Trim() }
}

Write-Host ""
Write-Host "==================== mod errors ===================="
if ($fresh) {
    Select-String -Path $fresh -Pattern "MOD_ERROR|Exception thrown while loading mod|Failed to load|Tried to load mod|assembly, but no assembly|no assembly at path" -Encoding utf8 -ErrorAction SilentlyContinue |
        Select-Object -First 40 | ForEach-Object { $_.Line.Trim() }
}

if (-not $steamWasRunning) {
    Write-Host ""
    Write-Host "shutting Steam down again (it was not running before this test)"
    Start-Process -FilePath $steamExe -ArgumentList '-shutdown' | Out-Null
}
