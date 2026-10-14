# Build -> deploy into the game -> launch via Steam -> collect Yetannia's self-check lines.
# Run with full filesystem access (writes into the game folder and %APPDATA%).
#
# NOTE: this file must stay ASCII-only. Windows PowerShell 5.1 reads .ps1 files as ANSI unless
# they carry a UTF-8 BOM, so non-ASCII literals (like the workspace path) would be mangled.
$ErrorActionPreference = 'Continue'

$tools    = $PSScriptRoot
$root     = Split-Path $tools -Parent
$game     = "D:\SteamLibrary\steamapps\common\Slay the Spire 2"
$logDir   = "$env:APPDATA\SlayTheSpire2\logs"
$steamExe = 'C:\Program Files (x86)\Steam\steam.exe'

# ---------- make sure the game is not holding the deployed dll ----------
Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "closing running game pid=$($_.Id)"
    $_.CloseMainWindow() | Out-Null
}
Start-Sleep -Seconds 5
Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# ---------- build + deploy ----------
$env:DOTNET_CLI_HOME = "$root\.tools\clihome"
$env:NUGET_PACKAGES = "$root\.tools\nuget"
$env:NUGET_HTTP_CACHE_PATH = "$root\.tools\nuget-http"
$env:NUGET_PLUGINS_CACHE_PATH = "$root\.tools\nuget-plugins"
$env:DOTNET_ROOT = "$root\.tools\dotnet"
$env:DOTNET_CLI_UI_LANGUAGE = 'en'
$env:DOTNET_NOLOGO = '1'

Push-Location "$root\Yetannia"
& "$root\.tools\dotnet\dotnet.exe" build -c Release -p:DeployToGame=true -v minimal 2>&1 | Select-Object -Last 25
$buildOk = $LASTEXITCODE -eq 0
Pop-Location
Write-Host "buildOk=$buildOk"
if (-not $buildOk) { exit 1 }

# ---------- steam ----------
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
    Write-Host "steam logged in (activeUser=$activeUser), settling..."
    Start-Sleep -Seconds 45
}

# ---------- run the game ----------
$start = Get-Date
Start-Process "steam://rungameid/2868840" | Out-Null
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    if (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue) { break }
}

$deadline = (Get-Date).AddSeconds(300)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $hit = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
           Where-Object { $_.LastWriteTime -gt $start } |
           ForEach-Object { Select-String -Path $_.FullName -Pattern 'self-check relic pool' -Encoding utf8 -ErrorAction SilentlyContinue }
    if ($hit) { break }
    if (-not (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue)) { Write-Host "game exited early"; break }
}

Start-Sleep -Seconds 10
Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 10
# Steam launches the game with a token this shell cannot Stop-Process, so go through WMI.
Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
    ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
Start-Sleep -Seconds 5

$fresh = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Select-Object -ExpandProperty FullName

Write-Host ""
Write-Host "==================== Yetannia self-check ===================="
if ($fresh) { Select-String -Path $fresh -Pattern "self-check|\[Yetannia\]|Finished mod initialization for 'Yetannia'" -Encoding utf8 | Select-Object -First 60 | ForEach-Object { $_.Line.Trim() } }
else { Write-Host "no fresh log found" }

Write-Host ""
Write-Host "==================== errors ===================="
if ($fresh) { Select-String -Path $fresh -Pattern "MOD_ERROR|Exception thrown while loading mod|self-check failed|not found in table|LocException" -Encoding utf8 | Select-Object -First 30 | ForEach-Object { $_.Line.Trim() } }

if (-not $steamWasRunning) {
    Write-Host ""
    Write-Host "shutting Steam down again"
    Start-Process -FilePath $steamExe -ArgumentList '-shutdown' | Out-Null
}
