param([int]$Port=8501,[string]$Python='')
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$ErrorActionPreference='Stop'
$appRoot=Join-Path (Split-Path -Parent $PSScriptRoot) 'demo'
$appPreviousPath=$env:PYTHONPATH
try {
    $appPackages=Join-Path $appRoot '.packages'
    if (Test-Path $appPackages) { $env:PYTHONPATH=$appPackages+[IO.Path]::PathSeparator+$appPreviousPath }
    & $Python -B -c "import streamlit"
    if ($LASTEXITCODE -ne 0) { throw 'Streamlit non installato. Installare requirements.txt dalla radice del repository.' }
    & $Python -B -m streamlit run (Join-Path $appRoot 'app.py') --global.developmentMode false --server.address 127.0.0.1 --server.port $Port --browser.gatherUsageStats false --server.fileWatcherType none
} finally { $env:PYTHONPATH=$appPreviousPath }
