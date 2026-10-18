[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [System.Security.SecureString] $ApiKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_continuity.py"
$manifest = Join-Path $projectRoot "evals\narrator\groq_candidates_2026-09-05.json"
$fixture = Join-Path $projectRoot "evals\narrator\experiments\continuity-probe-v1.json"
$prompt = Join-Path $projectRoot "evals\narrator\prompts\scene-focus-v1.md"
foreach ($requiredPath in @($python, $evaluator, $manifest, $fixture, $prompt)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        Write-Host "Required continuity probe file was not found: $requiredPath"
        exit 3
    }
}

$runId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
$summaryPath = Join-Path $projectRoot "eval-results\continuity-probe\$runId\summary.json"
$candidate = "gpt-oss-120b-groq-free-synthetic-low"
$plainTextKey = $null
$groqApiKeyExisted = Test-Path Env:GROQ_API_KEY
$previousGroqApiKey = if ($groqApiKeyExisted) { (Get-Item Env:GROQ_API_KEY).Value } else { $null }
$nativeCommandPreferenceExists = Test-Path Variable:PSNativeCommandUseErrorActionPreference
$previousNativeCommandPreference = $null
if ($nativeCommandPreferenceExists) {
    $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}
$exitCode = 3
$failureStage = "credential validation"
$summaryVerified = $false

Write-Host "Continuity probe: $runId"
Write-Host "Fixed candidate: $candidate; prompt: scene-focus-v1."
Write-Host "Synthetic data only; at most one provider call, no diagnostics, retries or fallback."
Write-Host "Exit 0 verifies transport, schema and admission only; narrative quality and CAP-001 are not approved."

try {
    $plainTextKey = [System.Net.NetworkCredential]::new("", $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) {
        throw "The supplied Groq API key is blank."
    }
    $env:GROQ_API_KEY = $plainTextKey
    $failureStage = "evaluator invocation"
    # Native Python updates the global automatic variable, not a local shadow.
    $global:LASTEXITCODE = $null
    & $python $evaluator --live --run-id $runId
    $invocationSucceeded = $?
    $exitCode = $global:LASTEXITCODE
    if ($null -eq $exitCode -or $exitCode -notin @(0, 1, 2, 3, 130) -or
        ($exitCode -eq 0 -and -not $invocationSucceeded)) {
        throw "Evaluator returned no usable exit status."
    }

    $failureStage = "summary verification"
    if ($exitCode -eq 130 -and -not (Test-Path -LiteralPath $summaryPath -PathType Leaf)) {
        Write-Host "Continuity probe cancelled; no completed summary was produced."
    }
    else {
        # Never scan for a recent report: only this invocation's exact UUID path
        # can substantiate the result, and every scope marker must match.
        $document = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
        $expectedMarkers = @{
            run_id = $runId
            purpose = "continuity_probe"
            mode = "live"
            selected_candidate_id = $candidate
            prompt_variant = "scene-focus-v1"
            cap_001_status = "not_evaluated"
        }
        foreach ($field in $expectedMarkers.Keys) {
            if ($document.$field -isnot [string] -or $document.$field -cne $expectedMarkers[$field]) {
                throw "Summary scope does not match this limited probe."
            }
        }
        foreach ($field in @("full_evaluation", "diagnostics_executed", "fallback", "runtime_promoted")) {
            if ($document.$field -isnot [bool] -or $document.$field) {
                throw "Summary indicates an unsupported evaluation operation."
            }
        }
        $expectedCounts = @{ maximum_provider_calls = 1; automatic_retries = 0 }
        foreach ($field in $expectedCounts.Keys) {
            if (($document.$field -isnot [int] -and $document.$field -isnot [long]) -or
                $document.$field -ne $expectedCounts[$field]) {
                throw "Summary call limits do not match this one-call probe."
            }
        }
        if (($document.calls_started -isnot [int] -and $document.calls_started -isnot [long]) -or
            $document.calls_started -lt 0 -or $document.calls_started -gt 1 -or
            $document.continuation_automated_passed -isnot [bool] -or
            ($document.process_exit_code -isnot [int] -and $document.process_exit_code -isnot [long]) -or
            $document.process_exit_code -ne $exitCode) {
            throw "Summary metadata does not match this limited probe."
        }
        if ($exitCode -eq 0 -and ($document.status -isnot [string] -or
            $document.status -cne "observed" -or $document.calls_started -ne 1 -or
            -not $document.continuation_automated_passed)) {
            throw "Success requires an observed and admitted live continuation."
        }
        $summaryVerified = $true
    }
}
catch {
    # Raw exception payloads can contain provider data or credentials.
    Write-Host "Continuity probe stopped because execution or report verification failed ($failureStage)."
    $exitCode = 3
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

if ($summaryVerified) {
    Write-Host "Verified continuity probe summary: $summaryPath"
}
switch ($exitCode) {
    0 { Write-Host "Limited probe passed transport, schema and admission checks. Human narrative review and full evaluation remain required." }
    1 { Write-Host "Limited probe failed an automated response gate; inspect the verified summary." }
    2 { Write-Host "Provider availability prevented the limited probe; no retry was started." }
    3 { Write-Host "Local execution or evidence verification failed; no result was approved." }
    130 { Write-Host "Limited probe cancelled; no retry was started." }
}
Write-Host "CAP-001 status: not_evaluated. This is not model selection or a complete evaluation."
exit $exitCode
