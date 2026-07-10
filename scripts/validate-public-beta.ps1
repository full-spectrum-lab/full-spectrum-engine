param()

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..
$tempDir = Join-Path $env:TEMP "full-spectrum-engine-public-beta"
New-Item -ItemType Directory -Force $tempDir | Out-Null

Write-Host "[1/4] Running deterministic simulation tests..."
python -m unittest tests.test_simulate_determinism -v

Write-Host "[2/4] Running golden sample regression tests..."
python -m unittest tests.test_golden_samples -v

Write-Host "[3/4] Rebuilding temporary seeded outputs and comparing with committed golden samples..."
$tempRefund = Join-Path $tempDir "golden_refund_seed42.json"
$tempKnowledge = Join-Path $tempDir "golden_knowledge_seed42.json"
$tempLogistics = Join-Path $tempDir "golden_logistics_coldchain_seed42.json"
python simulate.py --config examples/scenario_refund_conflict.json --seed 42 --output $tempRefund | Out-Null
python simulate.py --config examples/scenario_knowledge_conflict.json --seed 42 --output $tempKnowledge | Out-Null
python simulate.py --config examples/scenario_logistics_coldchain.json --seed 42 --output $tempLogistics | Out-Null

$goldenRefund = "test-records/v0.8-public-beta/golden_refund_seed42.json"
$goldenKnowledge = "test-records/v0.8-public-beta/golden_knowledge_seed42.json"
$goldenLogistics = "test-records/v0.8-public-beta/golden_logistics_coldchain_seed42.json"

if ((Get-Content $tempRefund -Raw) -ne (Get-Content $goldenRefund -Raw)) {
    throw "Refund golden sample drift detected."
}

if ((Get-Content $tempKnowledge -Raw) -ne (Get-Content $goldenKnowledge -Raw)) {
    throw "Knowledge golden sample drift detected."
}

if ((Get-Content $tempLogistics -Raw) -ne (Get-Content $goldenLogistics -Raw)) {
    throw "Logistics coldchain golden sample drift detected."
}

Write-Host "[4/4] Running full pytest suite..."
python -m pytest tests -v

Remove-Item $tempRefund, $tempKnowledge, $tempLogistics -ErrorAction SilentlyContinue
Write-Host "Public beta validation completed."
