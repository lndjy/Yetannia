# Compact grid montage of the rendered icons, for set-level review at a glance.
#   powershell -File .tools/art/grid.ps1 -Group power -Out C:\temp\art\grid.png [-Big]
# ASCII only: Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI.
param(
  [string]$Group = 'power',
  [string]$Out = 'C:\temp\art\grid.png',
  [switch]$Big,
  [int]$Cell = 190,
  [int]$Cols = 6
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$dir = if ($Group -eq 'power') { 'powers_big' } elseif ($Group -eq 'relic') { 'relics_big' } else { 'ui' }
$src = Join-Path $root ('.tools\pckproject\Yetannia\images\' + $dir)
$files = Get-ChildItem $src -Filter *.png | Sort-Object Name
$pad = 6; $lab = 20
$rows = [math]::Ceiling($files.Count / $Cols)
$W = $Cols * ($Cell + $pad) + $pad
$H = $rows * ($Cell + $lab + $pad) + $pad
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::FromArgb(16, 18, 24))
$g.InterpolationMode = 'HighQualityBicubic'
$font = New-Object System.Drawing.Font('Consolas', 11)
for ($i = 0; $i -lt $files.Count; $i++) {
  $c = $i % $Cols; $r = [math]::Floor($i / $Cols)
  $x = $pad + $c * ($Cell + $pad); $y = $pad + $r * ($Cell + $lab + $pad)
  $img = [System.Drawing.Image]::FromFile($files[$i].FullName)
  $g.DrawImage($img, $x, $y, $Cell, $Cell)
  $g.DrawString($files[$i].BaseName, $font, [System.Drawing.Brushes]::White, $x, ($y + $Cell + 2))
  $img.Dispose()
}
$g.Dispose(); $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
Write-Output "$Out  $W x $H  ($($files.Count) icons)"
