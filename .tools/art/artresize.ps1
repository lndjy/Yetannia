# Downscales the refined 512x512 icons into the deliverable sizes with System.Drawing.
#   512 (RGB-dilated) -> 256  -> <group>_big/<name>.png
#                     -> 64   -> <group>/<name>.png        (chained in memory from the 256 bitmap)
# The 512 copies are already RGB-dilated by artrefine.js, so the in-memory 256 still carries a
# dilation margin and the 256 -> 64 bicubic never samples black-transparent pixels.
# NOTE: ASCII-only on purpose - Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$work = 'C:\temp\art'
$src  = Join-Path $work 'w512d'
$dest = Join-Path $root '.tools\pckproject\Yetannia\images'

$cells = Get-Content (Join-Path $work 'cells.json') -Raw -Encoding utf8 | ConvertFrom-Json

function New-Graphics([System.Drawing.Bitmap]$bmp) {
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CompositingMode    = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
  $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
  $g.InterpolationMode  = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode    = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.SmoothingMode      = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
  return $g
}
function New-Attrs {
  $ia = New-Object System.Drawing.Imaging.ImageAttributes
  $ia.SetWrapMode([System.Drawing.Drawing2D.WrapMode]::TileFlipXY)
  return $ia
}

$count = 0
foreach ($cell in $cells) {
  $file = Join-Path $src ("{0}_{1}.png" -f $cell.index, $cell.name)
  if (-not (Test-Path $file)) { throw "missing refined cell $file" }
  $img = [System.Drawing.Image]::FromFile($file)

  # ---- 256
  $b256 = New-Object System.Drawing.Bitmap 256, 256, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = New-Graphics $b256
  $ia = New-Attrs
  $r = New-Object System.Drawing.Rectangle 0, 0, 256, 256
  $g.DrawImage($img, $r, 0, 0, $img.Width, $img.Height, [System.Drawing.GraphicsUnit]::Pixel, $ia)
  $g.Dispose(); $ia.Dispose()

  # ---- 64, chained in memory from the 256 so the dilation margin is still there
  $b64 = New-Object System.Drawing.Bitmap 64, 64, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g2 = New-Graphics $b64
  $ia2 = New-Attrs
  $r2 = New-Object System.Drawing.Rectangle 0, 0, 64, 64
  $g2.DrawImage($b256, $r2, 0, 0, 256, 256, [System.Drawing.GraphicsUnit]::Pixel, $ia2)
  $g2.Dispose(); $ia2.Dispose()

  # Group -> which files this cell produces.
  #   power     : <name>.png at 256 (powers_big) and 64 (powers)
  #   relic     : <name>.png at 256 (relics_big) and 64 (relics)
  #   orb       : ui/energy_yetannia.png at 256 only  (BigEnergyIconPath)
  #   texticon  : ui/energy_yetannia_small.png at 24  (TextEnergyIconPath). Godot draws the inline
  #               [img] at the texture's own size and every vanilla <color>_energy_icon.png in
  #               images/packed/sprite_fonts is 24x24, so this one is emitted at 24 - 64 was 2.67x
  #               too big. It has its own paint model authored for 24 px, it is not a downscale of
  #               the orb.
  #   marker    : ui/map_marker_yetannia.png at 49x64 (CustomMapMarkerPath). All five vanilla markers
  #               are 49x64, so a square downscale would stretch the emblem. The 512 cell is cropped
  #               to the CENTRAL 392x512 - exactly 49:64 - and scaled to 49x64. The paint model is
  #               authored so its bbox is 182x254 design units inside the 256x256 design box, which
  #               lands at ~44x62 px within that crop: the measured vanilla marker footprint.
  $b24 = $null
  $bMk = $null
  $targets = @()
  if ($cell.group -eq 'power') {
    $targets += ,@('powers_big', ($cell.name + '.png'), $b256)
    $targets += ,@('powers', ($cell.name + '.png'), $b64)
  } elseif ($cell.group -eq 'relic') {
    $targets += ,@('relics_big', ($cell.name + '.png'), $b256)
    $targets += ,@('relics', ($cell.name + '.png'), $b64)
  } elseif ($cell.group -eq 'orb') {
    $targets += ,@('ui', 'energy_yetannia.png', $b256)
  } elseif ($cell.group -eq 'texticon') {
    $b24 = New-Object System.Drawing.Bitmap 24, 24, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g3 = New-Graphics $b24
    $ia3 = New-Attrs
    $r3 = New-Object System.Drawing.Rectangle 0, 0, 24, 24
    $g3.DrawImage($img, $r3, 0, 0, $img.Width, $img.Height, [System.Drawing.GraphicsUnit]::Pixel, $ia3)
    $g3.Dispose(); $ia3.Dispose()
    $targets += ,@('ui', 'energy_yetannia_small.png', $b24)
  } elseif ($cell.group -eq 'marker') {
    $bMk = New-Object System.Drawing.Bitmap 49, 64, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g4 = New-Graphics $bMk
    $ia4 = New-Attrs
    $dstMk = New-Object System.Drawing.Rectangle 0, 0, 49, 64
    # NOTE: the (dstRect, srcRect, unit, attrs) overload does not resolve under PowerShell - it picks
    # the Point[]-based one and throws. Use the explicit srcX/srcY/srcW/srcH form, like the 24 px
    # branch above.
    $g4.DrawImage($img, $dstMk, 60, 0, 392, 512, [System.Drawing.GraphicsUnit]::Pixel, $ia4)
    $g4.Dispose(); $ia4.Dispose()
    $targets += ,@('ui', 'map_marker_yetannia.png', $bMk)
  }

  foreach ($pair in $targets) {
    # Guard added after a "does not contain a method named 'Save'" failure that named [System.String]
    # as the receiver: that means $targets got flattened and $pair is a bare string, so $pair[2] is its
    # third CHARACTER. Naming the offending cell turns a confusing type error into a located one.
    if ($pair -is [string]) {
      throw ("cell {0} '{1}' group={2}: target group was flattened to a string '{3}'" -f $cell.index, $cell.name, $cell.group, $pair)
    }
    if ($pair[2] -isnot [System.Drawing.Bitmap]) {
      throw ("cell {0} '{1}' group={2}: target bitmap is {3}" -f $cell.index, $cell.name, $cell.group, $pair[2].GetType().FullName)
    }
    $dir = Join-Path $dest $pair[0]
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $out = Join-Path $dir $pair[1]
    if (Test-Path $out) { Remove-Item $out -Force }
    $pair[2].Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
  }

  if ($b24) { $b24.Dispose() }
  if ($bMk) { $bMk.Dispose() }
  $b256.Dispose(); $b64.Dispose(); $img.Dispose()
  $count++
}
Write-Output ("downscaled {0} icons -> {1}" -f $count, $dest)
