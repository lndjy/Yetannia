$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\game-input.ps1"
$out = "$PSScriptRoot\out\visual\ingame\select"
Send-ConsoleCommand 'room RestSite' -SettleMs 6000
Save-Shot -Path "$out\04_restsite.png" | Out-Null
Write-Host "ok"
