param(
    [ValidateSet('all','smoke','train','test')]
    [string]$Mode = 'all',
    [string]$Python = ''
)
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$ErrorActionPreference = 'Stop'
$dpoModel = 'mistralai/Mistral-7B-Instruct-v0.3'
$dpoTrainer = Join-Path $PSScriptRoot 'train_mistral_600.py'
$dpoTest = Join-Path $PSScriptRoot 'compare_test_mistral_600.py'
$dpoTrainOut = Join-Path $PSScriptRoot 'runs\mistralai__Mistral-7B-Instruct-v0.3_train_v1'
$dpoSmokeOut = Join-Path $PSScriptRoot 'runs\mistralai__Mistral-7B-Instruct-v0.3_smoke_v1'
$dpoTestOut = Join-Path $PSScriptRoot 'evaluation\mistral_test_v1'
if (-not (Test-Path -LiteralPath $Python)) { throw "Python non trovato: $Python" }

function Test-CompletedRun([string]$RunPath) {
    $dpoResultPath = Join-Path $RunPath 'result.json'
    if (-not (Test-Path -LiteralPath $dpoResultPath)) { return $false }
    $dpoResult = Get-Content -LiteralPath $dpoResultPath -Raw | ConvertFrom-Json
    $dpoManifest = Get-Content -LiteralPath (Join-Path $RunPath 'run_manifest.json') -Raw | ConvertFrom-Json
    if ($dpoManifest.model -ne $dpoModel) { throw 'Modello inatteso nella cartella del run.' }
    if ($dpoResult.status -eq 'completed') {
        if (-not (Test-Path -LiteralPath (Join-Path $RunPath 'adapter\adapter_config.json'))) {
            throw 'Run completato ma adapter assente.'
        }
        return $true
    }
    return $false
}

if ($Mode -in @('all','smoke')) {
    if (Test-CompletedRun $dpoSmokeOut) { Write-Host 'Smoke gia completato.' }
    else {
        & $Python $dpoTrainer smoke --model $dpoModel --output-dir $dpoSmokeOut
        if ($LASTEXITCODE -ne 0) { throw 'Smoke non completato. Il training non viene avviato.' }
    }
}
if ($Mode -in @('all','train')) {
    if (-not (Test-CompletedRun $dpoSmokeOut)) { throw 'Prima eseguire lo smoke con -Mode smoke.' }
    if (Test-CompletedRun $dpoTrainOut) { Write-Host 'Training gia completato.' }
    else {
        & $Python $dpoTrainer train --model $dpoModel --output-dir $dpoTrainOut
        if ($LASTEXITCODE -ne 0) { throw 'Training non completato. Il test non viene avviato.' }
    }
}
if ($Mode -in @('all','test')) {
    if (-not (Test-CompletedRun $dpoTrainOut)) { throw 'Training non completato.' }
    & $Python $dpoTest --training-dir $dpoTrainOut --output-dir $dpoTestOut
    if ($LASTEXITCODE -ne 0) { throw 'Test interrotto: rilanciare con -Mode test per riprendere le risposte mancanti.' }
}
Write-Host "FASE COMPLETATA: $Mode"
if ($Mode -in @('all','test')) { Write-Host "Confronto: $(Join-Path $dpoTestOut 'comparison.md')" }
