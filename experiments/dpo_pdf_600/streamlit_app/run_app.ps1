param([int]$Port=8501,[string]$Python='')
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
$ErrorActionPreference='Stop'
$appPreviousPath=$env:PYTHONPATH
try {
    $appPackages=Join-Path $PSScriptRoot '.packages'
    if (Test-Path $appPackages) { $env:PYTHONPATH=$appPackages+[IO.Path]::PathSeparator+$appPreviousPath }
    & $Python -B -c "import streamlit"
    if ($LASTEXITCODE -ne 0) { throw 'Streamlit non installato. Leggere README.md nella cartella streamlit_app.' }
    & $Python -B -m streamlit run (Join-Path $PSScriptRoot 'app.py') --global.developmentMode false --server.address 127.0.0.1 --server.port $Port --browser.gatherUsageStats false --server.fileWatcherType none
} finally { $env:PYTHONPATH=$appPreviousPath }
