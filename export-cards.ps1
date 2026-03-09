# Export all cards from "Malazan Cube of the Fallen.mse-set" as PNG images.
# Each file is named after the card name (e.g. "Anomander Rake.png").
# Run from this folder or anywhere: .\export-cards.ps1

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Get-Location }

$MseExe = Join-Path $ScriptDir "..\M15-Magic-Pack-main\mse.exe"
$SetFile = Join-Path $ScriptDir "Malazan Cube of the Fallen.mse-set"
$OutDir = Join-Path $ScriptDir "exported_cards"

# Image path template: MSE replaces {card.name} with each card's name
$ImageTemplate = Join-Path $OutDir "{card.name}.png"

if (-not (Test-Path $MseExe)) {
    Write-Error "MSE not found at: $MseExe"
    exit 1
}
if (-not (Test-Path $SetFile)) {
    Write-Error "Set file not found: $SetFile"
    exit 1
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
# Remove previous export so only card-named files remain
Get-ChildItem -Path $OutDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "Exporting cards to: $OutDir"
Write-Host "Filenames: card name (e.g. My Card Name.png)"
Write-Host ""

& $MseExe --export-images $SetFile $ImageTemplate

if ($LASTEXITCODE -eq 0) {
    $count = (Get-ChildItem -Path $OutDir -Filter "*.png" -File -ErrorAction SilentlyContinue).Count
    Write-Host ""
    Write-Host "Done. Exported $count card image(s) to $OutDir"
} else {
    Write-Host "MSE exited with code $LASTEXITCODE (dictionary warnings are usually harmless)."
}
