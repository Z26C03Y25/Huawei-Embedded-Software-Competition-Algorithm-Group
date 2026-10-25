$ErrorActionPreference = "Stop"
$taskVenvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskVenvPython)) {
    throw 'Run .\online_judge\setup.ps1 first.'
}
& $taskVenvPython (Join-Path $PSScriptRoot 'judge.py') @args
exit $LASTEXITCODE
