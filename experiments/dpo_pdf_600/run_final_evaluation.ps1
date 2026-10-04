param(
    [ValidateSet('check','smoke','all','summary')]
    [string]$Mode = 'all',
    [string]$Python = ''
)
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$ErrorActionPreference = 'Stop'
$judgeScript = Join-Path $PSScriptRoot 'evaluate_final_local.py'
if (-not (Test-Path -LiteralPath $Python)) { throw "Python non trovato: $Python" }
if ($Mode -in @('check','summary')) {
    $judgeMode = if ($Mode -eq 'check') { 'prepare' } else { 'summary' }
    & $Python $judgeScript $judgeMode --provider groq
    if ($LASTEXITCODE -ne 0) { throw 'Controllo o riepilogo non completato.' }
    return
}
Write-Host 'Giudice: openai/gpt-oss-120b su Groq. Vengono inviati contesti e risposte, senza nomi dei modelli.'
Write-Host 'Usa le quote API del tuo account; non scarica altri pesi e non rifà i training.'
$judgePreviousKey = $env:ORACLE_API_KEY
$judgeSecureKey = $null
try {
    if ([string]::IsNullOrWhiteSpace($env:ORACLE_API_KEY)) {
        $judgeSecureKey = Read-Host 'Incolla la chiave Groq (input nascosto, non salvata su disco)' -AsSecureString
        $judgePointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($judgeSecureKey)
        try { $env:ORACLE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($judgePointer) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($judgePointer) }
    }
    if ([string]::IsNullOrWhiteSpace($env:ORACLE_API_KEY)) { throw 'Chiave vuota.' }
    $judgeArgs = @($judgeScript, 'score', '--provider', 'groq')
    if ($Mode -eq 'smoke') { $judgeArgs += @('--max-batches','3') }
    & $Python @judgeArgs
    if ($LASTEXITCODE -ne 0) { throw 'Valutazione interrotta. I giudizi validi sono salvati; leggere il motivo prima di rilanciare.' }
}
finally {
    $env:ORACLE_API_KEY = $judgePreviousKey
    if ($null -ne $judgeSecureKey) { $judgeSecureKey.Dispose() }
}
