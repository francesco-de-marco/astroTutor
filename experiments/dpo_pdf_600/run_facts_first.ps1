param(
    [ValidateSet('smoke','summary')]
    [string]$Mode = 'smoke',
    [string]$Python = ''
)
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$ErrorActionPreference = 'Stop'
$dpoScript = Join-Path $PSScriptRoot 'facts_first\pipeline_facts.py'
if (-not (Test-Path -LiteralPath $Python)) { throw "Python non trovato: $Python" }
if ($Mode -eq 'summary') {
    & $Python $dpoScript summary
    if ($LASTEXITCODE -ne 0) { throw 'Riepilogo non disponibile: leggere il messaggio precedente.' }
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
    $dpoArgs = @($dpoScript, 'run')
    & $Python @dpoArgs
    if ($LASTEXITCODE -ne 0) { throw 'Generazione interrotta. I risultati gia salvati restano disponibili.' }
}
finally {
    $env:ORACLE_API_KEY = $dpoPreviousKey
    if ($null -ne $dpoSecureKey) { $dpoSecureKey.Dispose() }
}
