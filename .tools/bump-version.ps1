# Bumps the mod version everywhere it is recorded, then refreshes the generated card table.
#
# The version lives in two places:
#   1. Yetannia/Yetannia.json          - the manifest the game and the card table read
#   2. .tools/mod-readme.txt           - the tester-facing readme shipped inside the zip
# Yetannia-卡牌表.xlsx is generated and reads the version out of the manifest, so it is simply
# regenerated rather than edited.
#
# Usage:
#   & .tools\bump-version.ps1 v0.6.0
#   & .tools\bump-version.ps1 v0.6.0 -SkipTable
#
# ASCII-only source on purpose, for two reasons:
#   * Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI, which would mangle any non-ASCII literal
#     in here (that silently broke an earlier version of this script's readme regex);
#   * and the files it writes must stay BOM-less: a UTF-8 BOM in Yetannia.json makes the manifest
#     unparseable for both the game and the card-table generator.
# So: no non-ASCII literals, and write through UTF8Encoding($false).

param(
    [Parameter(Mandatory = $true)][string]$Version,
    [switch]$SkipTable
)

$ErrorActionPreference = "Stop"

$root     = Split-Path -Parent $PSScriptRoot
$manifest = Join-Path $root "Yetannia\Yetannia.json"
$readme   = Join-Path $PSScriptRoot "mod-readme.txt"

if ($Version -notmatch '^v\d+\.\d+\.\d+$') {
    throw "version must look like v1.2.3 (got '$Version')"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# ---------------------------------------------------------------- manifest

$text = [System.IO.File]::ReadAllText($manifest)
$new  = [regex]::Replace($text, '"version"\s*:\s*"[^"]*"', '"version": "' + $Version + '"')
if ($new -eq $text -and $text -notmatch [regex]::Escape($Version)) {
    throw "could not find a version field in $manifest"
}
[System.IO.File]::WriteAllText($manifest, $new, $utf8NoBom)
Write-Host "manifest : $Version"

# ------------------------------------------------------------ tester readme

# Only the first line carries the version ("... v0.5.9"), and it is the only 'v<digits>' on that line.
# Matching by pattern instead of by surrounding words keeps this file free of non-ASCII literals.
if (Test-Path $readme) {
    $lines = [System.IO.File]::ReadAllLines($readme)
    if ($lines.Count -gt 0 -and $lines[0] -match 'v\d+(\.\d+)+') {
        $lines[0] = [regex]::Replace($lines[0], 'v\d+(\.\d+)+', $Version)
        [System.IO.File]::WriteAllLines($readme, $lines, $utf8NoBom)
        Write-Host "readme   : $Version"
    } else {
        Write-Warning "no 'vX.Y.Z' on the first line of mod-readme.txt; update it by hand"
    }
}

# --------------------------------------------------------------- card table

if ($SkipTable) {
    Write-Host "card table: skipped"
} else {
    & node (Join-Path $PSScriptRoot "cards-xlsx.js") | ForEach-Object { "  $_" }
}

Write-Host ""
Write-Host "next: & .tools\package-mod.ps1   (builds and re-packages; refreshes the table again)"
