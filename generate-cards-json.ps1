# Generate cards.json for GitHub Pages: list of PNG filenames in exported_cards/.
# Run from repo root. Used by index.html to show the full-width card gallery.

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$ExportDir = Join-Path $Root "exported_cards"
$OutPath = Join-Path $Root "cards.json"

if (-not (Test-Path $ExportDir)) {
    Write-Warning "exported_cards not found. Run render-all-cards.ps1 first."
    exit 1
}

$names = @(Get-ChildItem -Path $ExportDir -Filter "*.png" -File | ForEach-Object { $_.Name } | Sort-Object)
$json = $names | ConvertTo-Json
[System.IO.File]::WriteAllText($OutPath, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($names.Count) cards to $OutPath"
