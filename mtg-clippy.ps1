# mtg-clippy: Fix and standardize MTG card text in text/.
# Reads each .txt as a card, applies wording/typo fixes, writes back if changed.
# Writes list of changed card names to clippy-changed.txt for improve-everything.
# Run from repo root.

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$TextDir = Join-Path $Root "text"
$ChangedListPath = Join-Path $Root "clippy-changed.txt"

# MTG keywords/abilities to capitalize (word boundaries)
$Keywords = @(
    'First Strike', 'Double Strike', 'Flying', 'Haste', 'Hexproof', 'Reach', 'Trample',
    'Vigilance', 'Lifelink', 'Deathtouch', 'Menace', 'Ward', 'Protection from',
    'Scry', 'Equip', 'Enlist', 'Slow', 'Ascend', 'Ascends'
)

# Common typos and wording fixes (regex pattern -> replacement)
$Fixes = @(
    @{ Pattern = '\btaarget\b'; Replacement = 'target' },
    @{ Pattern = '\bteh\b'; Replacement = 'the' },
    @{ Pattern = '\btaht\b'; Replacement = 'that' },
    @{ Pattern = '\bcreatue\b'; Replacement = 'creature' },
    @{ Pattern = '\bartifact\b'; Replacement = 'artifact' },
    @{ Pattern = '\benchantment\b'; Replacement = 'enchantment' },
    @{ Pattern = '\boponent\b'; Replacement = 'opponent' },
    @{ Pattern = '\boponents\b'; Replacement = "opponent's" },
    @{ Pattern = '\bdraw 1 card\b'; Replacement = 'draw a card' },
    @{ Pattern = '\bdraw one card\b'; Replacement = 'draw a card' },
    @{ Pattern = '\bDeal 1 damage\b'; Replacement = 'Deal 1 damage' },
    @{ Pattern = '(\d), (T):'; Replacement = '$1, T: ' },
    @{ Pattern = 'T:(\S)'; Replacement = 'T: $1' },
    @{ Pattern = '(\w)\s*\.\s*([A-Z])'; Replacement = '$1. $2' }
)

function Get-SafeFileName {
    param([string]$name)
    $bad = [char[]]'\/:*?"<>|'
    foreach ($c in $bad) { $name = $name.Replace($c, '_') }
    return $name.Trim()
}

function Fix-KeywordCapitalization {
    param([string]$text)
    $result = $text
    foreach ($kw in $Keywords) {
        $lower = $kw.ToLower()
        $regex = [regex]::Escape($lower)
        $result = [regex]::Replace($result, "\b$regex\b", $kw)
    }
    return $result
}

function Add-PeriodsToAbilities {
    param([string]$text)
    $lines = $text -split "`n"
    $out = @()
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t -and $t -notmatch '\.$' -and $t -match ':\s*.+') { $t = $t + '.' }
        $out += $t
    }
    return ($out -join "`n")
}

function Invoke-ClippyFixes {
    param([string]$content)
    $result = $content
    foreach ($fix in $Fixes) {
        $result = $result -replace $fix.Pattern, $fix.Replacement
    }
    $result = Fix-KeywordCapitalization $result
    $result = Add-PeriodsToAbilities $result
    # Normalize multiple spaces
    $result = $result -replace '\s+', ' '
    $result = $result -replace ' \.', '.'
    $result = $result.Trim()
    return $result
}

function Get-RulesAndFlavorFromContent {
    param([string]$content)
    $lines = $content -split "`n"
    $rules = @()
    $flavor = @()
    $pastHeader = $false
    $blankAfterHeader = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $t = $lines[$i].Trim()
        if (-not $pastHeader) {
            if ($t -match '^(Cost|Type|P/T):') { continue }
            if ($t -eq '') { $blankAfterHeader = $true; continue }
            if ($blankAfterHeader -and $t -ne '') { $pastHeader = $true }
        }
        if (-not $pastHeader) { continue }
        if ($t -eq '') {
            if ($rules.Count -gt 0) { $blankAfterHeader = $true }; continue
        }
        if ($blankAfterHeader -and $rules.Count -gt 0) { $flavor += $t }
        else { $rules += $t }
    }
    return @{ Rules = ($rules -join "`n"); Flavor = ($flavor -join "`n") }
}

function Get-FullCardContent {
    param([string]$name, [string]$cost, [string]$type, [string]$pt, [string]$rules, [string]$flavor)
    $parts = @($name)
    if ($cost) { $parts += "Cost: $cost" }
    if ($type) { $parts += "Type: $type" }
    if ($pt) { $parts += "P/T: $pt" }
    $parts += ''
    if ($rules) { $parts += $rules }
    if ($flavor) { $parts += ''; $parts += $flavor }
    return $parts -join "`n"
}

# Ensure text dir exists
if (-not (Test-Path $TextDir)) {
    Write-Error "Text directory not found: $TextDir"
    exit 1
}

$changed = @()
$files = Get-ChildItem -Path $TextDir -Filter "*.txt" -File
foreach ($f in $files) {
    $content = Get-Content -Path $f.FullName -Raw
    if (-not $content) { continue }

    $lines = ($content -split "`n") | ForEach-Object { $_.TrimEnd() }
    $name = $lines[0].Trim()
    $cost = ''; $type = ''; $pt = ''
    foreach ($i in 1..([Math]::Min(5, $lines.Count - 1))) {
        if ($lines[$i] -match '^Cost:\s*(.*)$') { $cost = $Matches[1].Trim() }
        if ($lines[$i] -match '^Type:\s*(.*)$') { $type = $Matches[1].Trim() }
        if ($lines[$i] -match '^P/T:\s*(.*)$') { $pt = $Matches[1].Trim() }
    }

    $rf = Get-RulesAndFlavorFromContent $content
    $fixedRules = Invoke-ClippyFixes $rf.Rules
    $fixedFlavor = Invoke-ClippyFixes $rf.Flavor

    $newContent = Get-FullCardContent -name $name -cost $cost -type $type -pt $pt -rules $fixedRules -flavor $fixedFlavor
    $newContent = $newContent.TrimEnd()

    $origNorm = ($content -replace '\r\n', "`n").TrimEnd()
    if ($newContent -ne $origNorm) {
        [System.IO.File]::WriteAllText($f.FullName, $newContent, [System.Text.UTF8Encoding]::new($false))
        $changed += $name
    }
}

# Write list of changed cards (one name per line) for improve-everything
$changed | Set-Content -Path $ChangedListPath -Encoding UTF8
Write-Host "mtg-clippy: Processed $($files.Count) cards. Changed: $($changed.Count). List: $ChangedListPath"
