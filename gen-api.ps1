# gen-api.ps1 — Run from konkurs/ root: ./gen-api.ps1
# Step 1: Generate openapi.json from FastAPI app
Write-Host "→ Generating openapi.json from FastAPI..."
python backend/scripts/gen_openapi.py
if ($LASTEXITCODE -ne 0) { Write-Error "gen_openapi.py failed"; exit 1 }

# Step 2: Generate TypeScript client from openapi.json
Write-Host "→ Generating TypeScript client..."
Push-Location frontend
npx openapi-ts
$exit = $LASTEXITCODE
Pop-Location
if ($exit -ne 0) { Write-Error "openapi-ts failed"; exit 1 }

Write-Host "✓ API client ready at frontend/src/api/generated/"
