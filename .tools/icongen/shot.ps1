param(
  [Parameter(Mandatory=$true)][string]$Url,
  [Parameter(Mandatory=$true)][int]$W,
  [Parameter(Mandatory=$true)][int]$H,
  [Parameter(Mandatory=$true)][string]$Out
)
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if (Test-Path $Out) { Remove-Item $Out -Force }
$args = @(
  '--headless=old','--disable-gpu','--force-device-scale-factor=1','--hide-scrollbars',
  '--default-background-color=00000000','--virtual-time-budget=4000',
  "--window-size=$W,$H", "--screenshot=$Out", $Url
)
$p = Start-Process -FilePath $edge -ArgumentList $args -Wait -PassThru -NoNewWindow
# Edge sometimes writes the file a moment after exiting
for ($i = 0; $i -lt 40; $i++) {
  if (Test-Path $Out) { break }
  Start-Sleep -Milliseconds 250
}
if (-not (Test-Path $Out)) { Write-Error "screenshot not produced: $Out"; exit 1 }
Write-Output ("{0} bytes -> {1}" -f (Get-Item $Out).Length, $Out)
