# Slices the rendered 512x512 icon sheet into one PNG per icon.
# Native System.Drawing cropping: fast, and it keeps the per-icon refinement pass in Node working
# on small (512x512) images instead of one 2048x3584 decode.
# NOTE: ASCII-only on purpose - Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$here = $PSScriptRoot
$work = 'C:\temp\art'
$man  = Get-Content (Join-Path $work 'manifest.json') -Raw -Encoding utf8 | ConvertFrom-Json
$out  = Join-Path $work 'w512'
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force -Path $out | Out-Null

$sheet = [System.Drawing.Image]::FromFile((Join-Path $work 'sheet512.png'))
if ($sheet.Width -ne $man.width -or $sheet.Height -ne $man.height) {
  throw ("sheet is {0}x{1}, manifest says {2}x{3}" -f $sheet.Width, $sheet.Height, $man.width, $man.height)
}

$report = @()
foreach ($icon in $man.icons) {
  $bmp = New-Object System.Drawing.Bitmap $icon.size, $icon.size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
  $dst = New-Object System.Drawing.Rectangle 0, 0, $icon.size, $icon.size
  $g.DrawImage($sheet, $dst, $icon.x, $icon.y, $icon.size, $icon.size, [System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose()
  $file = Join-Path $out ("{0}_{1}.png" -f $icon.index, $icon.name)
  $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  $report += [pscustomobject]@{ index = $icon.index; name = $icon.name; group = $icon.group; cat = $icon.cat; file = $file }
}
$sheet.Dispose()
# no BOM: Set-Content -Encoding UTF8 in PS 5.1 writes one and JSON.parse chokes on it
$json = $report | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText((Join-Path $work 'cells.json'), $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("cropped {0} cells -> {1}" -f $report.Count, $out)
