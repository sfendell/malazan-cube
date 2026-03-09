# improve-everything: Run mtg-clippy on text/, update MSE set for changed cards, then regenerate exported_cards.
# Run from repo root. Requires mse-extract/, export-cards.ps1, and MSE (mse.exe) for final export.

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$SetPath = Join-Path $Root "mse-extract\set"
$TextDir = Join-Path $Root "text"
$ChangedListPath = Join-Path $Root "clippy-changed.txt"
$MseSetPath = Join-Path $Root "Malazan Cube of the Fallen.mse-set"

function Get-SafeFileName {
    param([string]$name)
    $bad = [char[]]'\/:*?"<>|'
    foreach ($c in $bad) { $name = $name.Replace($c, '_') }
    return $name.Trim()
}

# 1) Run mtg-clippy
Write-Host "Running mtg-clippy..."
& (Join-Path $Root "mtg-clippy.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 2) Read list of changed cards
if (-not (Test-Path $ChangedListPath)) {
    Write-Host "No clippy-changed.txt; nothing to update."
    exit 0
}
$changedNames = @(Get-Content -Path $ChangedListPath -Encoding UTF8 | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($changedNames.Count -eq 0) {
    Write-Host "No cards were changed by clippy. Skipping MSE update and export."
    exit 0
}
Write-Host "Updating MSE set for $($changedNames.Count) changed card(s)..."

# 3) Load rules/flavor from each changed card's text file
$cardText = @{}
foreach ($name in $changedNames) {
    $safe = Get-SafeFileName $name
    $txtPath = Join-Path $TextDir "$safe.txt"
    if (-not (Test-Path $txtPath)) { continue }
    $content = Get-Content -Path $txtPath -Raw
    $lines = $content -split "`n"
    $rules = @()
    $flavor = @()
    $pastHeader = $false
    $blank = $false
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t -match '^(Cost|Type|P/T):') { continue }
        if ($t -eq '') { $blank = $true; continue }
        if ($blank -and -not $pastHeader) { $pastHeader = $true }
        if (-not $pastHeader) { continue }
        if ($t -eq '') { $blank = $true; continue }
        if ($blank -and $rules.Count -gt 0) { $flavor += $t } else { $rules += $t }
    }
    $cardText[$name] = @{ Rules = ($rules -join "`n"); Flavor = ($flavor -join " ") }
}

# 4) Update set file: replace rule_text and flavor_text for each changed card
$setContent = Get-Content -Path $SetPath -Raw
$blocks = $setContent -split '(?m)^card:\r?\n'
$newBlocks = @()

foreach ($block in $blocks) {
    if ($block -notmatch '(?m)\tname:\s*(.+)\r?$') {
        $newBlocks += $block
        continue
    }
    $cardName = $Matches[1].Trim()
    if (-not $cardText.ContainsKey($cardName)) {
        $newBlocks += $block
        continue
    }
    $data = $cardText[$cardName]
    $lines = $block -split '\r?\n'
    $ruleStart = -1
    $flavorLine = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^\trule_text:') { $ruleStart = $i }
        if ($lines[$i] -match '^\tflavor_text:') { $flavorLine = $i; break }
    }
    if ($ruleStart -lt 0 -or $flavorLine -lt 0) {
        $newBlocks += $block
        continue
    }
    $ruleLines = $data.Rules -split "`n" | ForEach-Object { "`t`t" + $_.Trim() }
    $flavorEsc = $data.Flavor -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;'
    $newMiddle = @("`trule_text:") + $ruleLines + @("`tflavor_text: <i-flavor>$flavorEsc</i-flavor>")
    $before = $lines[0..($ruleStart - 1)] -join "`n"
    $after = $lines[($flavorLine + 1)..($lines.Count - 1)] -join "`n"
    $block = $before + "`n" + ($newMiddle -join "`n") + "`n" + $after
    $newBlocks += $block
}

$newSetContent = $newBlocks -join "card:`n"
if ($newSetContent -match '^card:\n') { $newSetContent = $newSetContent -replace '^card:\n', '' }
[System.IO.File]::WriteAllText($SetPath, $newSetContent, [System.Text.UTF8Encoding]::new($false))

# 5) Repack mse-extract into .mse-set (zip)
$zipPath = $Root + "\mse-set-repack.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
$mseExtract = Join-Path $Root "mse-extract"
Compress-Archive -Path (Join-Path $mseExtract "*") -DestinationPath $zipPath -Force
# Copy zip contents into root of zip (Compress-Archive puts mse-extract\* so we get image1.png, set, etc. at root)
# Check: Compress-Archive -Path "$mseExtract\*" puts files at root. Good.
Move-Item -Path $zipPath -Destination $MseSetPath -Force
Write-Host "Repacked MSE set to $MseSetPath"

# 6) Run export-cards to regenerate all exported_cards
Write-Host "Regenerating exported_cards..."
& (Join-Path $Root "export-cards.ps1")
Write-Host "improve-everything done."
