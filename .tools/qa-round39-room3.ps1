$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\game-input.ps1"
$out = "$PSScriptRoot\out\visual\ingame\select"
Send-Key -VirtualKey 0xC0
Start-Sleep -Milliseconds 700
Clear-ConsoleLine
Send-Text -Text 'room' -NoFocus
Send-Key -VirtualKey 0x20 -HoldMs 90 -NoFocus
Start-Sleep -Milliseconds 300
Send-Text -Text 'RestSite' -NoFocus
Start-Sleep -Milliseconds 500
Save-Shot -Path "$out\06_console_typed.png" | Out-Null
Send-Key -VirtualKey 0x0D -NoFocus
Start-Sleep -Milliseconds 6000
Save-Shot -Path "$out\07_console_after.png" | Out-Null
Write-Host "ok"
