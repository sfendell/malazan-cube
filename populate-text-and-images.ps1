# Create art/ with card artwork only (one image per card, named by card name).
# Art comes from the MSE set's embedded images (image1.png, image2.png, ...).
# Full generated cards remain in exported_cards. Run from repo root.
# Requires mse-extract/ (extract .mse-set as .zip first).

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$SetPath = Join-Path $Root "mse-extract\set"
$MseExtractDir = Join-Path $Root "mse-extract"
$ArtDir = Join-Path $Root "art"

if (-not (Test-Path $SetPath)) {
    Write-Error "Set file not found. Extract Malazan Cube of the Fallen.mse-set as .zip to mse-extract first."
    exit 1
}

# Sanitize filename for Windows (no \ / : * ? " < > |)
function Get-SafeFileName {
    param([string]$name)
    $bad = [char[]]'\/:*?"<>|'
    foreach ($c in $bad) { $name = $name.Replace($c, '_') }
    return $name.Trim()
}

# Parse set file into card blocks and copy art
$content = Get-Content -Path $SetPath -Raw
$blocks = $content -split '(?m)^card:\r?\n'
$artCount = 0

foreach ($block in $blocks) {
    if (-not $block.Trim()) { continue }
    if ($block -notmatch '\tname:\s*') { continue }

    $lines = $block -split '\r?\n'
    $key = $null
    $value = $null
    $card = @{}

    foreach ($line in $lines) {
        if ($line -match '^\t(\t*)([a-z_0-9]+):\s*(.*)$') {
            if ($key) { $card[$key] = $value.Trim() }
            $key = $Matches[2]
            $value = $Matches[3]
        } elseif ($key -and ($line -match '^\t\t')) {
            $value += "`n" + $line.TrimStart()
        } elseif ($line -match '^\t([a-z_0-9]+):\s*$') {
            if ($key) { $card[$key] = $value.Trim() }
            $key = $Matches[1]
            $value = ''
        }
    }
    if ($key) { $card[$key] = $value.Trim() }

    $name = $card['name']
    $imageFile = $card['image']
    if (-not $name -or -not $imageFile) { continue }

    $srcPath = Join-Path $MseExtractDir $imageFile
    if (-not (Test-Path $srcPath)) { continue }

    $safeName = Get-SafeFileName $name
    $destPath = Join-Path $ArtDir "$safeName.png"
    New-Item -ItemType Directory -Force -Path $ArtDir | Out-Null
    Copy-Item -Path $srcPath -Destination $destPath -Force
    $artCount++
}

Write-Host "Created $artCount card art files in $ArtDir"
