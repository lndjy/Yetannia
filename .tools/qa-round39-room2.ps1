$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\game-input.ps1"
$out = "$PSScriptRoot\out\visual\ingame\select"
# close whatever state the console is in
Send-Key -VirtualKey 0x1B          # Escape
Start-Sleep -Milliseconds 500
Send-Key -VirtualKey 0xC0          # open console
Start-Sleep -Milliseconds 600
Send-Text -Text 'room' -NoFocus
Send-Key -VirtualKey 0x20 -HoldMs 90 -NoFocus      # the space is dropped if typed too fast
Start-Sleep -Milliseconds 300
Send-Text -Text 'RestSite' -NoFocus
Start-Sleep -Milliseconds 400
Send-Key -VirtualKey 0x0D -NoFocus
Start-Sleep -Milliseconds 7000
Send-Key -VirtualKey 0x1B
Start-Sleep -Milliseconds 800
Save-Shot -Path "$out\05_restsite.png" | Out-Null
Write-Host "ok"
