# Generate cards.json for GitHub Pages: card list with colors, type, and text for filtering.
# Reads text/*.txt for metadata and matches exported_cards/*.png. Run from repo root.

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$TextDir = Join-Path $Root "text"
$ExportDir = Join-Path $Root "exported_cards"
$OutPath = Join-Path $Root "cards.json"

$WUBRG = @('W','U','B','R','G')

function Get-ColorsFromCost {
    param([string]$cost)
    if (-not $cost) { return @() }
    $chars = $cost.ToUpperInvariant().ToCharArray() | Where-Object { $WUBRG -contains $_ }
    $colors = $chars | Sort-Object -Unique
    return @($colors)
}

function Get-PrimaryType {
    param([string]$typeLine)
    if (-not $typeLine) { return 'Other' }
    $t = $typeLine.Trim()
    if ($t -match 'Land') { return 'Land' }
    if ($t -match 'Instant') { return 'Instant' }
    if ($t -match 'Sorcery') { return 'Sorcery' }
    if ($t -match 'Creature') { return 'Creature' }
    if ($t -match 'Artifact') { return 'Artifact' }
    if ($t -match 'Enchantment') { return 'Enchantment' }
    if ($t -match 'Planeswalker') { return 'Planeswalker' }
    if ($t -match 'Battle') { return 'Battle' }
    return 'Other'
}

# Build metadata from text/
$meta = @{}
if (Test-Path $TextDir) {
    Get-ChildItem -Path $TextDir -Filter "*.txt" -File | ForEach-Object {
        $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.UTF8Encoding]::new($false))
        $lines = ($content -replace "`r", "").TrimEnd() -split "`n"
        $name = $lines[0].Trim()
        $cost = $null
        $typeLine = $null
        $textLines = @()
        $pastBlank = $false
        for ($i = 1; $i -lt $lines.Count; $i++) {
            $line = $lines[$i]
            if ($line -match '^Cost:\s*(.*)') { $cost = $Matches[1].Trim(); continue }
            if ($line -match '^Type:\s*(.*)') { $typeLine = $Matches[1].Trim(); continue }
            if ($line -match '^P/T:') { continue }
            if ($line -match '^\s*$') { $pastBlank = $true; continue }
            if ($pastBlank) { $textLines += $line.Trim() }
        }
        $colors = Get-ColorsFromCost $cost
        $colorKey = ($colors | Sort-Object { $WUBRG.IndexOf($_) }) -join ''
        $meta[$name] = @{
            colors = $colorKey
            type   = Get-PrimaryType $typeLine
            text   = ($textLines -join " ").Trim()
        }
    }
}

# Build list from exported_cards, merge metadata
$cards = @()
Get-ChildItem -Path $ExportDir -Filter "*.png" -File -ErrorAction SilentlyContinue | ForEach-Object {
    $imgName = $_.Name
    $name = $imgName -replace '\.png$', ''
    $m = $meta[$name]
    $colors = if ($m) { $m.colors } else { '' }
    $type = if ($m) { $m.type } else { 'Other' }
    $text = if ($m) { $m.text } else { '' }
    $cards += [PSCustomObject]@{ name = $name; img = $imgName; colors = $colors; type = $type; text = $text }
}
$cards = $cards | Sort-Object { $_.name }

$json = $cards | ConvertTo-Json -Compress
[System.IO.File]::WriteAllText($OutPath, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($cards.Count) cards to $OutPath"
