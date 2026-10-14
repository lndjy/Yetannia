# Launches Slay the Spire 2 via Steam, then watches the game log, printing progress, until the
# Yetannia self-check appears (or the timeout expires). Finally closes the game.
#
# ASCII only: Windows PowerShell 5.1 reads .ps1 files as ANSI unless they carry a UTF-8 BOM.
param(
    [int]$TimeoutSeconds = 600,
    [int]$PollSeconds = 15
)

$ErrorActionPreference = 'Continue'
$logDir = "$env:APPDATA\SlayTheSpire2\logs"

if (-not (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue)) {
    Write-Host "launching game..."
    Start-Process 'steam://rungameid/2868840' | Out-Null
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue) { break }
    }
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$done = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds $PollSeconds
    $newest = Get-ChildItem $logDir -File -Filter 'godot*.log' -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($newest) {
        $tail = (Get-Content $newest.FullName -Tail 1 -ErrorAction SilentlyContinue)
        $hit = Select-String -Path $newest.FullName -Pattern 'self-check relic pool' -Encoding utf8 -ErrorAction SilentlyContinue
        Write-Host ("[{0}] {1,7:N0}KB  {2}" -f (Get-Date -Format 'HH:mm:ss'), ($newest.Length / 1KB), $tail)
        if ($hit) { $done = $true; break }
    }
    if (-not (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue)) { Write-Host "game exited"; break }
}
Write-Host "selfCheckSeen=$done"

if (Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue) {
    Write-Host "closing game..."
    Get-Process SlayTheSpire2 | ForEach-Object { $_.CloseMainWindow() | Out-Null }
    Start-Sleep -Seconds 8
    Get-CimInstance Win32_Process -Filter "Name='SlayTheSpire2.exe'" -ErrorAction SilentlyContinue |
        ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
    Start-Sleep -Seconds 5
}
