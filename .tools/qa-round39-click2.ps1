$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\game-input.ps1"
$out = "$PSScriptRoot\out\visual\ingame\select"
Click-At -X 565 -Y 470
Start-Sleep -Seconds 7
Save-Shot -Path "$out\02_charselect.png" | Out-Null
Write-Host "ok"
