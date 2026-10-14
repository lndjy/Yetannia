# Stages the built mod and packs it into a zip that can be extracted straight into the game's
# mods folder: the archive's top level is exactly the `Yetannia/` folder, so
#   extract <zip> into  ...\Slay the Spire 2\mods\
# produces ...\mods\Yetannia\Yetannia.dll and friends.
#
# ASCII-only source on purpose: Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI, so non-ASCII
# here would be mangled. The Chinese readme lives in .tools/mod-readme.txt (UTF-8) instead.
#
# Usage:
#   & .tools\package-mod.ps1                       # build Release, stage, zip
#   & .tools\package-mod.ps1 -SkipBuild            # reuse the last build
#   & .tools\package-mod.ps1 -Out D:\somewhere.zip

param(
    [string]$Out = "",
    [switch]$SkipBuild,
    # Default OFF: a shipped .pdb carries every source file's absolute path (verified: the release
    # .pdb contained "D:\<...>\sts2mod\Yetannia\Code\..."), which leaks the builder's local layout.
    # Release builds no longer emit symbols at all (see Yetannia.csproj), so this also stops a stale
    # .pdb left over from an earlier build from being packaged by accident.
    [switch]$IncludePdb = $false
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$root    = Split-Path -Parent $PSScriptRoot
$project = Join-Path $root "Yetannia"
$stage   = Join-Path $PSScriptRoot "package"
$modName = "Yetannia"

# ---------------------------------------------------------------- build

if (-not $SkipBuild) {
    $env:DOTNET_CLI_HOME          = Join-Path $PSScriptRoot "clihome"
    $env:NUGET_PACKAGES           = Join-Path $PSScriptRoot "nuget"
    $env:NUGET_HTTP_CACHE_PATH    = Join-Path $PSScriptRoot "nuget-http"
    $env:NUGET_PLUGINS_CACHE_PATH = Join-Path $PSScriptRoot "nuget-plugins"
    $env:DOTNET_ROOT              = Join-Path $PSScriptRoot "dotnet"
    $env:DOTNET_CLI_UI_LANGUAGE   = "en"
    $env:DOTNET_NOLOGO            = "1"

    Write-Host "building Release..."
    Push-Location $project
    try {
        & (Join-Path $PSScriptRoot "dotnet\dotnet.exe") build -c Release -v minimal |
            Select-String -Pattern "error|Build succeeded" | ForEach-Object { $_.Line.Trim() }
    } finally {
        Pop-Location
    }
}

# ------------------------------------------------------- card table refresh

# Yetannia-卡牌表.xlsx carries the mod version, read from Yetannia.json. Regenerating it here means a
# version bump cannot leave a stale card table behind: every release goes through this script, so the
# table is refreshed (and re-stamped with the new version) as part of packaging.
# ASCII output only - see the note at the top of this file about PowerShell 5.1 and encodings.
Write-Host "regenerating card table..."
try {
    & node (Join-Path $PSScriptRoot "cards-xlsx.js") | ForEach-Object { "  $_" }
} catch {
    Write-Warning "card table regeneration failed: $_"
}

# ---------------------------------------------------------------- stage

$dll  = Join-Path $project "bin\Release\Yetannia.dll"
$pdb  = Join-Path $project "bin\Release\Yetannia.pdb"
$json = Join-Path $project "Yetannia.json"
$pck  = Join-Path $project "build\Yetannia.pck"
$help = Join-Path $PSScriptRoot "mod-readme.txt"

foreach ($f in @($dll, $json, $pck)) {
    if (-not (Test-Path $f)) { throw "missing build artifact: $f" }
}

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
$modStage = Join-Path $stage $modName
New-Item -ItemType Directory -Path $modStage -Force | Out-Null

Copy-Item $dll  -Destination $modStage
Copy-Item $json -Destination $modStage
Copy-Item $pck  -Destination $modStage
if ($IncludePdb -and (Test-Path $pdb)) { Copy-Item $pdb -Destination $modStage }

# The readme ships inside the mod folder so the archive has exactly one top-level entry and can be
# extracted straight into mods\ without leaving stray files next to the other mods.
if (Test-Path $help) {
    Copy-Item $help -Destination (Join-Path $modStage "README.txt")
}

$manifest = Get-Content $json -Raw | ConvertFrom-Json
$version = $manifest.version

# ---------------------------------------------------------------- zip

# -Out was always honoured (the guard below), but a RELATIVE -Out used to resolve against the
# caller's CWD instead of the repo root, so the same command wrote to different places depending on
# where it was run from. Relative now resolves against $root. (An earlier attempt at this fix nested
# a second if/elseif INSIDE the whitespace guard, which made the branch unreachable -- exactly the
# kind of silently-inert code this project keeps tripping over. QA caught it; this is the real fix.)
if ([string]::IsNullOrWhiteSpace($Out)) {
    $Out = Join-Path $root ("Yetannia-{0}-test.zip" -f $version)
} elseif (-not [System.IO.Path]::IsPathRooted($Out)) {
    $Out = Join-Path $root $Out
}
if (Test-Path $Out) { Remove-Item $Out -Force }

# Built by hand rather than with Compress-Archive / ZipFile.CreateFromDirectory so entry names are
# guaranteed to use forward slashes and no directory entries are written - some extractors mishandle
# both, and a mod folder that unzips wrong simply will not load.
$zipStream = [System.IO.File]::Open($Out, [System.IO.FileMode]::CreateNew)
try {
    $archive = New-Object System.IO.Compression.ZipArchive($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        $prefix = "$modName/"
        # [Content_Types] style ordering does not matter here; a stable, readable order does.
        $order = @("Yetannia.json", "Yetannia.dll", "Yetannia.pdb", "Yetannia.pck", "README.txt")
        $files = Get-ChildItem $modStage -File | Sort-Object {
            $i = $order.IndexOf($_.Name); if ($i -lt 0) { 999 } else { $i }
        }
        foreach ($file in $files) {
            $entry = $archive.CreateEntry($prefix + $file.Name, [System.IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $file.LastWriteTime
            # NOTE: do not name this stream $out - PowerShell variable names are case-insensitive and
            # $out would collide with the $Out script parameter.
            $entryStream = $entry.Open()
            $in = [System.IO.File]::OpenRead($file.FullName)
            try {
                $in.CopyTo($entryStream)
            } finally {
                $in.Dispose()
                $entryStream.Dispose()
            }
            Write-Host ("  + {0,-16} {1,9:N0} bytes" -f $file.Name, $file.Length)
        }
    } finally { $archive.Dispose() }
} finally { $zipStream.Dispose() }

$zipInfo = Get-Item $Out
Write-Host ""
Write-Host ("wrote {0}" -f $zipInfo.FullName)
Write-Host ("size  {0:N0} bytes" -f $zipInfo.Length)
Write-Host ("  -> extract into <Slay the Spire 2>\mods\ to get mods\{0}\" -f $modName)
