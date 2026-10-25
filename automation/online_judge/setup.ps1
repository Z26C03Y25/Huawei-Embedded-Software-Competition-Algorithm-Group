param([string]$Python = "python")
$ErrorActionPreference = "Stop"
& $Python (Join-Path $PSScriptRoot 'setup_environment.py')
if ($LASTEXITCODE -ne 0) { throw 'Online judge setup or diagnostics failed.' }
