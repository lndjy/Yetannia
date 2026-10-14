param([switch]$SkipShot)
# NOTE: kept ASCII-only on purpose - Windows PowerShell 5.1 reads .ps1 files without a
# BOM as ANSI, so non-ASCII literals in a script get mangled. Paths are derived instead.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot

node "$here\build-sheet.js" | Out-Null
if (-not $SkipShot) {
  & "$here\shot.ps1" -Url 'file:///C:/temp/icogen/sheet256.html' -W 1536 -H 1280 -Out 'C:\temp\icogen\sheet256.png' 2>$null | Out-Null
}
node "$here\crop.js"
& "$here\resize.ps1"
Write-Output 'pipeline done'
