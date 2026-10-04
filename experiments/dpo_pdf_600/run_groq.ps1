param(
    [ValidateSet('smoke','train','development','export','models')]
    [string]$Mode = 'smoke',
    [string]$Python = ''
)
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$ErrorActionPreference = 'Stop'
if ($Mode -in @('smoke','train','development')) {
    throw 'Generazione API in pausa: completare la revisione locale in revisione_locale\LOTTO_5_CONTESTI.md prima di riattivare il lanciatore.'
}
$dpoScript = Join-Path $PSScriptRoot 'build_dataset.py'
$dpoData = Join-Path $PSScriptRoot 'dataset_v5'
if (-not (Test-Path -LiteralPath $Python)) { throw "Python non trovato: $Python" }
if ($Mode -eq 'export') {
    & $Python $dpoScript export --out $dpoData
    if ($LASTEXITCODE -ne 0) { throw 'Export non completato: leggere il messaggio precedente.' }
    return
}
$dpoPreviousKey = $env:ORACLE_API_KEY
$dpoSecureKey = $null
try {
    if ([string]::IsNullOrWhiteSpace($env:ORACLE_API_KEY)) {
        $dpoSecureKey = Read-Host 'Incolla la chiave Groq (input nascosto; non viene salvata su disco)' -AsSecureString
        $dpoPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($dpoSecureKey)
        try { $env:ORACLE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($dpoPointer) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($dpoPointer) }
    }
    if ([string]::IsNullOrWhiteSpace($env:ORACLE_API_KEY)) { throw 'Chiave vuota.' }
    if ($Mode -eq 'models') {
        & $Python (Join-Path $PSScriptRoot 'list_groq_models.py')
        if ($LASTEXITCODE -ne 0) { throw 'Elenco modelli non disponibile: leggere il messaggio precedente.' }
        return
    }
    $dpoArgs = @($dpoScript, 'generate', '--out', $dpoData, '--provider', 'openai',
        '--model', 'openai/gpt-oss-120b', '--url', 'https://api.groq.com/openai/v1', '--allow-cloud')
    if ($Mode -eq 'smoke') { $dpoArgs += @('--max-attempts','12') }
    if ($Mode -eq 'development') { $dpoArgs += @('--split','development') }
    & $Python @dpoArgs
    if ($LASTEXITCODE -ne 0) { throw 'Generazione interrotta. I risultati gia salvati restano disponibili.' }
}
finally {
    $env:ORACLE_API_KEY = $dpoPreviousKey
    if ($null -ne $dpoSecureKey) { $dpoSecureKey.Dispose() }
}
