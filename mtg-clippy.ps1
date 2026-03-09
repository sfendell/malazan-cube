# mtg-clippy: Fix and standardize MTG card ABILITY TEXT only in text/ using an LLM.
# Does not change name, cost, type, or P/T—only the rules/flavor wording.
# Writes list of changed card names to clippy-changed.txt for improve-everything.
# Requires: OPENAI_API_KEY environment variable set.
# Run from repo root.

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$TextDir = Join-Path $Root "text"
$ChangedListPath = Join-Path $Root "clippy-changed.txt"

$SystemPrompt = @"
You fix only the wording of Magic the Gathering card ability text (rules and flavor). Do not change card name, cost, type, or P/T.

Rules:
- Fix wording to standard Magic the Gathering card syntax.
- "Slow" is a valid keyword for activated abilities (use it as-is).
- Ignore incorrect usage of the mechanic "ascends" if it appears.
- Use "cook" instead of "create a food token".
- Use "bleed" instead of "create a blood token".
- Treat Malazan, Pure, Child, and Alien as valid MTG types.

You will receive only the ability text (rules and optional flavor). Return ONLY the fixed ability text—nothing else. No card name, no Cost/Type/P/T lines, no explanation, no markdown.
"@

function Get-AbilityTextOnly {
    param([string]$content)
    $lines = ($content -replace "`r", "") -split "`n"
    $pastHeader = $false
    $blankAfterHeader = $false
    $abilityLines = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $t = $lines[$i]
        if (-not $pastHeader) {
            if ($t -match '^(Cost|Type|P/T):') { continue }
            if ($t -match '^\s*$') { $blankAfterHeader = $true; continue }
            if ($blankAfterHeader) { $pastHeader = $true }
        }
        if (-not $pastHeader) { continue }
        $abilityLines += $t
    }
    return ($abilityLines -join "`n").Trim()
}

function Get-HeaderAndAbility {
    param([string]$content)
    $lines = ($content -replace "`r", "") -split "`n"
    $headerEnd = -1
    $blankAfterHeader = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $t = $lines[$i]
        if ($t -match '^(Cost|Type|P/T):') { continue }
        if ($t -match '^\s*$') { $blankAfterHeader = $true; continue }
        if ($blankAfterHeader) { $headerEnd = $i; break }
    }
    if ($headerEnd -lt 0) { $headerEnd = $lines.Count }
    $header = $lines[0..($headerEnd - 1)] | Where-Object { $_.Length -gt 0 -or $_ -match '^\s*$' }
    $headerLines = @()
    $i = 0
    while ($i -lt $headerEnd) {
        $headerLines += $lines[$i]
        $i++
    }
    $abilityStart = $headerEnd
    $abilityLines = @()
    for ($j = $abilityStart; $j -lt $lines.Count; $j++) { $abilityLines += $lines[$j] }
    return @{
        HeaderLines = $headerLines
        AbilityText = ($abilityLines -join "`n").Trim()
    }
}

function Get-FullCardContent {
    param([string[]]$headerLines, [string]$abilityText)
    $out = @()
    foreach ($line in $headerLines) {
        $out += $line.TrimEnd()
    }
    $abilityLines = $abilityText -split "`n"
    foreach ($line in $abilityLines) {
        $out += $line.TrimEnd()
    }
    return ($out -join "`n").TrimEnd()
}

function Escape-JsonString {
    param([string]$s)
    if (-not $s) { return '""' }
    $s = $s -replace '\\', '\\\\'
    $s = $s -replace '"', '\"'
    $s = $s -replace "`r`n", '\n'
    $s = $s -replace "`n", '\n'
    $s = $s -replace "`r", '\n'
    $s = $s -replace "`t", '\t'
    return '"' + $s + '"'
}

function Get-ClippyFromLLM {
    param([string]$abilityText)
    $apiKey = $env:OPENAI_API_KEY
    if (-not $apiKey) {
        Write-Error "OPENAI_API_KEY environment variable is not set."
        exit 1
    }
    $systemEsc = Escape-JsonString $SystemPrompt
    $userEsc = Escape-JsonString $abilityText
    $body = '{"model":"gpt-4o-mini","messages":[{"role":"system","content":' + $systemEsc + '},{"role":"user","content":' + $userEsc + '}],"temperature":0.2}'
    $headers = @{
        "Authorization" = "Bearer $apiKey"
        "Content-Type"  = "application/json; charset=utf-8"
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    try {
        $response = Invoke-RestMethod -Uri "https://api.openai.com/v1/chat/completions" -Method Post -Headers $headers -Body $bytes
        $fixed = $response.choices[0].message.content
        return $fixed.Trim()
    } catch {
        Write-Error "LLM request failed: $_"
        throw
    }
}

# Ensure text dir exists
if (-not (Test-Path $TextDir)) {
    Write-Error "Text directory not found: $TextDir"
    exit 1
}

$changed = @()
$files = Get-ChildItem -Path $TextDir -Filter "*.txt" -File
$total = $files.Count
$n = 0
foreach ($f in $files) {
    $n++
    $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.UTF8Encoding]::new($false))
    $content = ($content -replace "`r\n", "`n").TrimEnd()
    if (-not $content) { continue }

    $parsed = Get-HeaderAndAbility $content
    $abilityOnly = $parsed.AbilityText
    if (-not $abilityOnly) {
        Write-Host "[$n/$total] $($f.Name) (no ability text, skip)"
        continue
    }

    Write-Host "[$n/$total] $($f.Name)..."
    $fixedAbility = Get-ClippyFromLLM -abilityText $abilityOnly
    if (-not $fixedAbility) { continue }

    $newContent = Get-FullCardContent -headerLines $parsed.HeaderLines -abilityText $fixedAbility
    $origNorm = ($content -replace '\r\n', "`n").TrimEnd()
    if ($newContent -ne $origNorm) {
        [System.IO.File]::WriteAllText($f.FullName, $newContent + "`n", [System.Text.UTF8Encoding]::new($false))
        $name = ($content -split "`n")[0].Trim()
        $changed += $name
    }
    Start-Sleep -Milliseconds 300
}

$changed | Set-Content -Path $ChangedListPath -Encoding UTF8
Write-Host "mtg-clippy: Processed $total cards. Changed: $($changed.Count). List: $ChangedListPath"
