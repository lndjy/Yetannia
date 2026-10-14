$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\game-input.ps1"
$out = "$PSScriptRoot\out\visual\ingame\select"
Click-At -X 1790 -Y 749
Start-Sleep -Seconds 9
Save-Shot -Path "$out\03_after_confirm.png" | Out-Null
Write-Host "ok"
