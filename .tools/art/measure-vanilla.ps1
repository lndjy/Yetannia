# Measures every vanilla reference set we extracted, into one JSON per set.
# NOTE: ASCII-only on purpose - Windows PowerShell 5.1 reads BOM-less .ps1 files as ANSI, so a
# non-ASCII path literal here would be mangled. All paths are derived from $PSScriptRoot instead.
$ErrorActionPreference = 'Stop'
$art   = $PSScriptRoot
$root  = Split-Path -Parent (Split-Path -Parent $art)
$stats = Join-Path $art 'stats'
New-Item -ItemType Directory -Force -Path $stats | Out-Null

$sets = @(
  @{ name = 'vanilla.power.64';  dir = Join-Path $art 'ref64\powers' },
  @{ name = 'vanilla.relic.64';  dir = Join-Path $art 'ref64\relics' },
  @{ name = 'vanilla.power.256'; dir = Join-Path $art 'ref\powers' },
  @{ name = 'vanilla.relic.256'; dir = Join-Path $art 'ref\relics' }
)
foreach ($s in $sets) {
  $out = Join-Path $stats ($s.name + '.json')
  node (Join-Path $art 'measure.js') $s.dir --json $out --quiet | Out-Null
  Write-Output ("measured {0} -> {1}" -f $s.name, $out)
}
