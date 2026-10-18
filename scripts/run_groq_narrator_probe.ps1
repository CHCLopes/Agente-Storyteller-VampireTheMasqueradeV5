[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [System.Security.SecureString] $ApiKey,

    [ValidateSet(
        "qwen-3.8-27b-groq-free-synthetic-nonthink",
        "gpt-oss-120b-groq-free-synthetic-low"
    )]
    [string] $CandidateId = "qwen-3.8-27b-groq-free-synthetic-nonthink"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_models.py"
$manifest = Join-Path $projectRoot "evals\narrator\groq_candidates_2026-09-05.json"
$outputRoot = Join-Path $projectRoot "eval-results"
foreach ($requiredPath in @($python, $evaluator, $manifest)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required probe file was not found: $requiredPath"
    }
}

$batchId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
$plainTextKey = $null
$groqApiKeyExisted = Test-Path Env:GROQ_API_KEY
$previousGroqApiKey = if ($groqApiKeyExisted) {
    (Get-Item Env:GROQ_API_KEY).Value
}
else {
    $null
}
$nativeCommandPreferenceExists = Test-Path Variable:PSNativeCommandUseErrorActionPreference
$previousNativeCommandPreference = $null
if ($nativeCommandPreferenceExists) {
    $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}

Write-Host "Operational probe: $batchId"
Write-Host "One synthetic opening for $CandidateId; no diagnostics, retries or CAP-001 approval."
Write-Host "Narrative output ceiling: 768 tokens (account-aware synthetic test budget)."
try {
    $plainTextKey = [System.Net.NetworkCredential]::new("", $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) {
        throw "The supplied Groq API key is blank."
    }
    $env:GROQ_API_KEY = $plainTextKey
    & $python $evaluator `
        --live `
        --opening-probe `
        --manifest $manifest `
        --candidate $CandidateId `
        --batch-id $batchId `
        --api-key-env GROQ_API_KEY `
        --allow-synthetic-only `
        --repetitions 1 `
        --deadline-seconds 60 `
        --temperature 0.65 `
        --max-output-tokens 768
    $exitCode = $LASTEXITCODE
    $matchingSummary = Get-ChildItem -LiteralPath $outputRoot `
        -Filter "summary.json" -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object {
            try {
                $document = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json
                $document.batch_id -eq $batchId -and
                    $document.selected_candidate_id -eq $CandidateId -and
                    $document.purpose -eq "operational_probe" -and
                    $document.full_evaluation -eq $false -and
                    $document.process_exit_code -eq $exitCode
            }
            catch {
                $false
            }
        } |
        Select-Object -First 1
    if ($null -eq $matchingSummary) {
        throw "Probe returned without a matching summary for $CandidateId."
    }
    Write-Host "Summary: $($matchingSummary.FullName)"
}
finally {
    if ($groqApiKeyExisted) {
        $env:GROQ_API_KEY = $previousGroqApiKey
    }
    else {
        Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
    }
    $plainTextKey = $null
    $previousGroqApiKey = $null
    if ($nativeCommandPreferenceExists) {
        $PSNativeCommandUseErrorActionPreference = $previousNativeCommandPreference
    }
}

if ($null -eq $exitCode -or $exitCode -notin @(0, 1, 2, 3, 130)) {
    Write-Host "Operational probe returned an unexpected exit code."
    exit 3
}
Write-Host "Operational probe ended with exit code $exitCode. Full evaluation and human review remain required."
exit $exitCode
