# Full v2 icon render -> refine -> downscale pipeline.
#   .tools/art/artbuild.js   : HTML sheet + manifest from paint.js
#   .tools/icongen/shot.ps1  : Edge headless screenshot (the pipeline the previous round proved)
#   .tools/art/artcrop.ps1   : System.Drawing slice of the 512 cells
#   .tools/art/artrefine.js  : chamfer-based ink band + soft edge pass
#   .tools/art/artresize.ps1 : System.Drawing 512 -> 256 -> 64 into the deliverable folders
# NOTE: ASCII-only on purpose - Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI.
param([switch]$SkipShot)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)

node (Join-Path $here 'artbuild.js') | Out-Null
# sheet size comes from the manifest, so adding icons never silently clips the last row
$man = Get-Content 'C:\temp\art\manifest.json' -Raw -Encoding utf8 | ConvertFrom-Json
if (-not $SkipShot) {
  & (Join-Path $root '.tools\icongen\shot.ps1') -Url 'file:///C:/temp/art/sheet.html' -W $man.width -H $man.height -Out 'C:\temp\art\sheet512.png' 2>$null | Out-Null
}
& (Join-Path $here 'artcrop.ps1')
node (Join-Path $here 'artrefine.js')
& (Join-Path $here 'artresize.ps1')
Write-Output 'art pipeline done'
