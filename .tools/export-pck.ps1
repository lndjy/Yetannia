# Packs the mod's art into Yetannia\build\Yetannia.pck using a script-free Godot project.
# Re-run this whenever you add or change images under .tools\pckproject\Yetannia\images\.
#
# ASCII only: Windows PowerShell 5.1 reads .ps1 files as ANSI unless they carry a UTF-8 BOM.
$ErrorActionPreference = 'Continue'

$tools  = $PSScriptRoot
$root   = Split-Path $tools -Parent
$godot  = Join-Path $tools 'godot\Godot_v4.5.1-stable_win64_console.exe'
$proj   = Join-Path $tools 'pckproject'
$outDir = Join-Path $root 'Yetannia\build'
$out    = Join-Path $outDir 'Yetannia.pck'

if (-not (Test-Path $godot)) { Write-Host "Godot not found at $godot"; exit 1 }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Remove-Item $out -ErrorAction SilentlyContinue

Write-Host "importing assets..."
& $godot --headless --path $proj --import 2>&1 | Select-String -Pattern 'ERROR|SCRIPT ERROR|reimport \|' | Select-Object -Last 6

Write-Host "exporting pack..."
& $godot --headless --path $proj --export-pack "BasicExport" $out 2>&1 | Select-String -Pattern 'ERROR|SCRIPT ERROR|savepack \|' | Select-Object -Last 6

if (-not (Test-Path $out)) { Write-Host "EXPORT FAILED"; exit 1 }
$size = (Get-Item $out).Length
Write-Host ("packed {0} ({1:N0} bytes)" -f $out, $size)

Write-Host "contents:"
& node (Join-Path $tools 'pck.js') list $out 2>$null | ForEach-Object { "  $_" }
