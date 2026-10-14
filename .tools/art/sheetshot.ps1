# Screenshots the v2 contact sheet into .tools/shots/icon-sheet-v2.png.
# Window size comes from C:\temp\art\sheet\sheet-size.json so it always matches the layout.
# NOTE: ASCII-only on purpose - Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$size = Get-Content 'C:\temp\art\sheet\sheet-size.json' -Raw -Encoding utf8 | ConvertFrom-Json
$out = Join-Path $root '.tools\shots\icon-sheet-v2.png'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null
& (Join-Path $root '.tools\icongen\shot.ps1') -Url 'file:///C:/temp/art/sheet/sheet.html' `
  -W $size.width -H $size.height -Out $out 2>$null | Out-Null
Write-Output ("contact sheet -> {0}  ({1}x{2})" -f $out, $size.width, $size.height)
