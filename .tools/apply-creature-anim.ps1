# Copies the generated Yetannia creature animation + character icon into the mod's pck project.
#
# This is the WHOLE integration: the animated visual is a drop-in replacement for the old static
# Sprite2D scene plus one new texture, and the character icon is a drop-in replacement for the old
# square illustration. No C# change is needed -- YetanniaCharacter.CustomVisualPath already points at
# "creature_visuals/yetannia" and CustomIconTexturePath at "images/charui/character_icon_yetannia.png"
# (Yetannia/Code/Character/YetanniaCharacter.cs:88 and :74).
#
# The atlas .import travels WITH the png on purpose: it is what puts the atlas on VRAM Compressed
# (BC7) instead of Godot's lossless default. See the IMPORT_TEMPLATE comment in
# build-creature-anim.py and .tools/out/visual/vram-import.ps1 for the measurements.
#
# ASCII only (Windows PowerShell 5.1 reads .ps1 files as ANSI without a BOM).
param(
  # where build-creature-anim.py staged its output
  [string]$Src = ''
)
$ErrorActionPreference = 'Stop'
$tools = $PSScriptRoot
if (-not $Src) { $Src = Join-Path $tools 'out\visual\build' }
$proj  = Join-Path $tools 'pckproject\Yetannia'

$scene  = Join-Path $Src 'creature_visuals\yetannia.tscn'
$atlas  = Join-Path $Src 'frames\yetannia_atlas_0.png'
$import = Join-Path $Src 'frames\yetannia_atlas_0.png.import'
$icon   = Join-Path $Src 'icon\character_icon_yetannia.png'
$dstS   = Join-Path $proj 'scenes\creature_visuals\yetannia.tscn'
$dstD   = Join-Path $proj 'images\creature'
$dstI   = Join-Path $proj 'images\charui\character_icon_yetannia.png'
$dstO   = Join-Path $proj 'images\charui\character_icon_yetannia_outline.png'

foreach ($f in @($scene, $atlas, $import, $icon)) {
    if (-not (Test-Path $f)) { Write-Host "missing generated asset: $f"; exit 1 }
}
New-Item -ItemType Directory -Force -Path $dstD | Out-Null
Copy-Item $scene $dstS -Force
Copy-Item $atlas (Join-Path $dstD 'yetannia_atlas_0.png') -Force
Copy-Item $import (Join-Path $dstD 'yetannia_atlas_0.png.import') -Force
Copy-Item $icon $dstI -Force

# The outline layer is derived from the icon's own alpha silhouette, so it MUST be regenerated
# whenever the icon changes -- otherwise it is still the dilation of the previous artwork.
python (Join-Path $tools 'icon-outline.py') make $dstI $dstO

Write-Host "applied:"
foreach ($f in @($dstS, (Join-Path $dstD 'yetannia_atlas_0.png'),
                 (Join-Path $dstD 'yetannia_atlas_0.png.import'), $dstI, $dstO)) {
    Write-Host ("  {0}  ({1:N0} bytes)" -f $f, (Get-Item $f).Length)
}
Write-Host "next: .tools/export-pck.ps1   (mandatory - package-mod.ps1 does NOT re-export)"
