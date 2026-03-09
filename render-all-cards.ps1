# render-all-cards: Sync ALL text/*.txt into mse-extract/set, repack .mse-set, then export every card to exported_cards.
# Run from repo root. Requires mse-extract/, export-cards.ps1, and MSE (mse.exe) for final export.
# Use after fixing wording (e.g. mtg-clippy.ps1) to regenerate all rendered card images.

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$SetPath = Join-Path $Root "mse-extract\set"
$TextDir = Join-Path $Root "text"
$MseSetPath = Join-Path $Root "Malazan Cube of the Fallen.mse-set"

function Normalize-Encoding {
    param([string]$s)
    if (-not $s) { return $s }
    # Fix common UTF-8 mojibake so apostrophes match set and render correctly
    $s = $s -replace [char]0x2019, "'"  # Unicode right single quote -> ASCII
    $s = $s -replace 'â€™', "'"         # UTF-8 misinterpreted as Windows-1252
    $s = $s -replace 'â€"', "-"         # em dash
    $s = $s -replace 'â€œ', '"'         # left double quote
    $s = $s -replace 'â€\u009d', '"'    # right double quote (various)
    return $s
}

# 1) Load rules/flavor from every text file (card name = first line)
$cardText = @{}
$files = Get-ChildItem -Path $TextDir -Filter "*.txt" -File -ErrorAction SilentlyContinue
foreach ($f in $files) {
    $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.UTF8Encoding]::new($false))
    $content = ($content -replace "`r\n", "`n").TrimEnd()
    $content = Normalize-Encoding $content
    if (-not $content) { continue }
    $lines = $content -split "`n"
    $name = $lines[0].Trim()
    $name = Normalize-Encoding $name
    if (-not $name) { continue }

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
    $cardText[$name] = @{ Rules = (Normalize-Encoding ($rules -join "`n")); Flavor = (Normalize-Encoding ($flavor -join " ")) }
}

Write-Host "Loaded text for $($cardText.Count) cards from $TextDir"

if (-not (Test-Path $SetPath)) {
    Write-Error "Set file not found: $SetPath. Extract Malazan Cube of the Fallen.mse-set as .zip to mse-extract first."
    exit 1
}

# 2) Update set file: replace rule_text and flavor_text for each card that has text
$setContent = [System.IO.File]::ReadAllText($SetPath, [System.Text.UTF8Encoding]::new($false))
$blocks = $setContent -split '(?m)^card:\r?\n'
$newBlocks = @()
$updated = 0

foreach ($block in $blocks) {
    if ($block -notmatch '(?m)\tname:\s*(.+)\r?$') {
        $newBlocks += $block
        continue
    }
    $cardName = $Matches[1].Trim()
    $cardName = Normalize-Encoding $cardName
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
    $ruleLines = $data.Rules -split "`n" | ForEach-Object { "`t`t" + ($_.Trim()) }
    $flavorEsc = $data.Flavor -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;'
    $newMiddle = @("`trule_text:") + $ruleLines + @("`tflavor_text: <i-flavor>$flavorEsc</i-flavor>")
    $before = $lines[0..($ruleStart - 1)] -join "`n"
    $after = $lines[($flavorLine + 1)..($lines.Count - 1)] -join "`n"
    $block = $before + "`n" + ($newMiddle -join "`n") + "`n" + $after
    $newBlocks += $block
    $updated++
}

$newSetContent = $newBlocks -join "card:`n"
if ($newSetContent -match '^card:\n') { $newSetContent = $newSetContent -replace '^card:\n', '' }
[System.IO.File]::WriteAllText($SetPath, $newSetContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "Updated MSE set: $updated card(s) synced from text."

# 3) Repack mse-extract into .mse-set (zip)
$zipPath = $Root + "\mse-set-repack.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
$mseExtract = Join-Path $Root "mse-extract"
Compress-Archive -Path (Join-Path $mseExtract "*") -DestinationPath $zipPath -Force
Move-Item -Path $zipPath -Destination $MseSetPath -Force
Write-Host "Repacked MSE set to $MseSetPath"

# 4) Export all cards to exported_cards
Write-Host "Exporting all cards..."
& (Join-Path $Root "export-cards.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "render-all-cards done."
