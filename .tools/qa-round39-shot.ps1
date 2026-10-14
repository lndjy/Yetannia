$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\game-input.ps1"
$out = "$PSScriptRoot\out\visual\ingame\select"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Get-Process SlayTheSpire2 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 3
Start-Game
Start-Sleep -Seconds 8
Save-Shot -Path "$out\00_menu.png"
Write-Host "shot written"
