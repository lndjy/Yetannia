# QA sheet for a targeted icon redraw: for each name it lays out
#   [ previous 256 (from the backup) | new 256 | new 64 blown up 4x nearest ]
# so a redraw can be judged at the authoring size and at the in-game size in one look.
#
#   powershell -File .tools/art/qa-montage.ps1 -Names prophet_tally,nirvana -Out C:\temp\art\qa.png
# ASCII only: Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI.
param(
  [Parameter(Mandatory=$true)][string[]]$Names,
  [string]$Group = 'power',
  [string]$Out = 'C:\temp\art\qa.png',
  [string]$Backup = 'C:\temp\art\images-backup-v2-pre-redraw'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$bigDir = if ($Group -eq 'power') { 'powers_big' } elseif ($Group -eq 'relic') { 'relics_big' } else { 'ui' }
$smlDir = if ($Group -eq 'power') { 'powers' } elseif ($Group -eq 'relic') { 'relics' } else { 'ui' }
$big = Join-Path $root ('.tools\pckproject\Yetannia\images\' + $bigDir)
$sml = Join-Path $root ('.tools\pckproject\Yetannia\images\' + $smlDir)

$cell = 256; $pad = 8; $lab = 20; $gap = 14
$W = $pad + $cell + $gap + $cell + $gap + $cell + $pad
$H = $pad + $Names.Count * ($cell + $lab + $pad)

$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(16, 18, 24))
$g.InterpolationMode = 'HighQualityBicubic'
$g.PixelOffsetMode = 'Half'
$font = New-Object System.Drawing.Font('Consolas', 12)
$small = New-Object System.Drawing.Font('Consolas', 10)
$br = [System.Drawing.Brushes]::White
$brDim = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(150, 160, 175))

for ($i = 0; $i -lt $Names.Count; $i++) {
  $n = $Names[$i]
  $y = $pad + $i * ($cell + $lab + $pad)
  $x0 = $pad
  $x1 = $pad + $cell + $gap
  $x2 = $pad + 2 * ($cell + $gap)

  $old = Join-Path (Join-Path $Backup $bigDir) ($n + '.png')
  if (Test-Path $old) {
    $img = [System.Drawing.Image]::FromFile($old)
    $g.DrawImage($img, $x0, $y, $cell, $cell); $img.Dispose()
    $g.DrawString('before', $small, $brDim, $x0, ($y + $cell + 2))
  } else {
    $g.DrawString('(no backup)', $small, $brDim, $x0, ($y + $cell + 2))
  }
  $f = Join-Path $big ($n + '.png')
  if (Test-Path $f) {
    $img = [System.Drawing.Image]::FromFile($f)
    $g.DrawImage($img, $x1, $y, $cell, $cell); $img.Dispose()
  }
  $g.DrawString(('after 256  ' + $n), $font, $br, $x1, ($y + $cell + 2))
  $f2 = Join-Path $sml ($n + '.png')
  if (Test-Path $f2) {
    $img = [System.Drawing.Image]::FromFile($f2)
    $g.InterpolationMode = 'NearestNeighbor'
    $g.DrawImage($img, $x2, $y, $cell, $cell)
    $g.InterpolationMode = 'HighQualityBicubic'
    $img.Dispose()
  }
  $g.DrawString('after 64 (4x nearest)', $small, $brDim, $x2, ($y + $cell + 2))
}
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("$Out  $W x $H  ($($Names.Count) icons)")
