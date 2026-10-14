$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\game-input.ps1"
$out = "$PSScriptRoot\out\visual\ingame\select"
Click-At -X 721 -Y 663
Start-Sleep -Seconds 6
Save-Shot -Path "$out\01_after_singleplayer.png" | Out-Null
Write-Host "ok"
