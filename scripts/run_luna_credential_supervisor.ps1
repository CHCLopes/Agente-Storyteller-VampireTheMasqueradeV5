[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ExpiresAt)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$env:STORYTELLER_DISABLE_DOTENV = '1'
Set-Location -LiteralPath $root
& $python -m scripts.luna_credential_supervisor --expires-at $ExpiresAt
exit $LASTEXITCODE
