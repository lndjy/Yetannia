# Measures the mod's own delivered icon sets into stats/mine.*.json, so verify-v2.js compares the
# CURRENT renders against the vanilla reference numbers instead of a stale snapshot.
# NOTE: ASCII-only on purpose - Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI, and the
# deliverable path contains non-ASCII characters, so every path is derived from $PSScriptRoot.
$ErrorActionPreference = 'Stop'
$art   = $PSScriptRoot
$root  = Split-Path -Parent (Split-Path -Parent $art)
$stats = Join-Path $art 'stats'
$images = Join-Path $root '.tools\pckproject\Yetannia\images'
New-Item -ItemType Directory -Force -Path $stats | Out-Null

$sets = @(
  @{ name = 'mine.power.64';  dir = Join-Path $images 'powers' },
  @{ name = 'mine.power.256'; dir = Join-Path $images 'powers_big' },
  @{ name = 'mine.relic.64';  dir = Join-Path $images 'relics' },
  @{ name = 'mine.relic.256'; dir = Join-Path $images 'relics_big' },
  @{ name = 'mine.ui';        dir = Join-Path $images 'ui' }
)
foreach ($s in $sets) {
  $out = Join-Path $stats ($s.name + '.json')
  node (Join-Path $art 'measure.js') $s.dir --json $out --quiet | Out-Null
  Write-Output ("measured {0} -> {1}" -f $s.name, $out)
}
