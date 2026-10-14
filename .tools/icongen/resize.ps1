# High quality 256 -> 64 downscale with System.Drawing.
# Reads the RGB-dilated 256px copies (so bicubic never samples black-transparent pixels)
# and writes the 64x64 deliverables listed in crop-report.json.
# NOTE: ASCII-only on purpose (Windows PowerShell 5.1 reads BOM-less .ps1 as ANSI).
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$prep   = 'C:\temp\icogen\prep'
$report = Get-Content 'C:\temp\icogen\crop-report.json' -Raw -Encoding utf8 | ConvertFrom-Json

$done = 0
foreach ($item in $report) {
  $src = Join-Path $prep ("{0}_{1}.png" -f $item.index, $item.name)
  if (-not (Test-Path $src)) { throw "missing prep file $src" }

  $img = [System.Drawing.Image]::FromFile($src)
  $bmp = New-Object System.Drawing.Bitmap 64, 64, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g   = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CompositingMode    = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
  $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
  $g.InterpolationMode  = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode    = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.SmoothingMode      = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality

  $ia = New-Object System.Drawing.Imaging.ImageAttributes
  $ia.SetWrapMode([System.Drawing.Drawing2D.WrapMode]::TileFlipXY)

  $destRect = New-Object System.Drawing.Rectangle 0, 0, 64, 64
  $g.DrawImage($img, $destRect, 0, 0, $img.Width, $img.Height,
               [System.Drawing.GraphicsUnit]::Pixel, $ia)
  $g.Dispose()

  $dir = Split-Path -Parent $item.small
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  if (Test-Path $item.small) { Remove-Item $item.small -Force }
  $bmp.Save($item.small, [System.Drawing.Imaging.ImageFormat]::Png)

  $bmp.Dispose(); $img.Dispose(); $ia.Dispose()
  $done++
}
Write-Output ("resized {0} files to 64x64" -f $done)
