# fix-and-render: Run wording fix (mtg-clippy) then regenerate all rendered cards (render-all-cards).
# Run from repo root. Requires OPENAI_API_KEY for step 1; mse-extract/, export-cards.ps1, MSE for step 2.
#
# Usage:
#   .\fix-and-render.ps1
#
# Or run the two steps separately:
#   .\mtg-clippy.ps1      # 1) Fix wording in text/*.txt
#   .\render-all-cards.ps1 # 2) Sync text -> MSE set and export all cards

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot

Write-Host "=== Step 1: Fix wording (mtg-clippy) ==="
& (Join-Path $Root "mtg-clippy.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Step 2: Render all cards ==="
& (Join-Path $Root "render-all-cards.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "fix-and-render complete."
