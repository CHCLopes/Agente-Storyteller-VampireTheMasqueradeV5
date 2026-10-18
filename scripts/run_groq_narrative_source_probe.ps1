[CmdletBinding()]
param(
    [System.Security.SecureString] $ApiKey,
    [ValidateSet("courtyard-observe-wait")]
    [string] $CaseId = "courtyard-observe-wait"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_source.py"
$outputRoot = Join-Path $projectRoot "eval-results"
$batchId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
$plainTextKey = $null
$previousKeyExists = Test-Path Env:GROQ_API_KEY
$previousKey = if ($previousKeyExists) { (Get-Item Env:GROQ_API_KEY).Value } else { $null }
$previousDotenv = $env:STORYTELLER_DISABLE_DOTENV
$previousBytecode = $env:PYTHONDONTWRITEBYTECODE
$nativePreferenceExists = Test-Path Variable:PSNativeCommandUseErrorActionPreference
$previousNativePreference = if ($nativePreferenceExists) { $PSNativeCommandUseErrorActionPreference } else { $null }
$stage = "offline preflight"
$failed = $false
$exitCode = 3
$preflightOutput = $null
$childOutput = $null
$verificationOutput = $null
$lifecyclePath = $null

function Write-Lifecycle([string] $Status, $Code = $null) {
    if ($null -eq $lifecyclePath) { return }
    $record = @{ batch_id=$batchId; status=$Status; updated_at=[DateTime]::UtcNow.ToString('o'); exit_code=$Code }
    [System.IO.File]::WriteAllText($lifecyclePath, ($record | ConvertTo-Json) + "`n", [System.Text.UTF8Encoding]::new($false))
}

Write-Host "Narrative source probe batch: $batchId"
Write-Host "Fixed synthetic case $CaseId; at most two dependent n/q calls to the fixed free Qwen/Groq target."
Write-Host "768 tokens per call (1536 total), temperature 0.65, reasoning none; initial wait, call spacing and per-call deadline: 60 seconds."
Write-Host "The second call receives the complete first narrative as an attributed source. First operational or policy failure stops the chain. No diagnostics, retries, repair or fallback."
Write-Host "Source identity does not approve semantic truth, narrative quality, runtime or CAP-001."
try {
    if ($nativePreferenceExists) { $PSNativeCommandUseErrorActionPreference = $false }
    $env:STORYTELLER_DISABLE_DOTENV = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
    foreach ($file in @($python, $evaluator)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required source probe file unavailable.' }
    }
    $global:LASTEXITCODE = $null
    $preflightOutput = @(& $python -B $evaluator --preflight --case-id $CaseId 2>&1)
    $preflightSucceeded = $?
    if (-not $preflightSucceeded -or $global:LASTEXITCODE -ne 0) { throw 'Offline preflight failed.' }
    $preflightText = $preflightOutput -join "`n"
    $preflight = $preflightText | ConvertFrom-Json
    if ($preflight.purpose -cne 'narrative_source_probe' -or
        $preflight.probe_kind -cne 'narrative_source_probe' -or
        $preflight.experiment_version -cne 'narrative-source-observation-v1' -or
        $preflight.protocol -cne 'narrative-source-profile-v1' -or
        ($preflight.max_calls -isnot [int] -and $preflight.max_calls -isnot [long]) -or
        ($preflight.automatic_retries -isnot [int] -and $preflight.automatic_retries -isnot [long]) -or
        $preflight.max_calls -ne 2 -or $preflight.automatic_retries -ne 0 -or
        $preflight.synthetic_only -isnot [bool] -or $preflight.synthetic_only -ne $true -or
        $preflight.runtime_promoted -isnot [bool] -or $preflight.runtime_promoted -ne $false -or
        $preflight.cap_001_status -cne 'not_evaluated' -or
        $preflight.selected_candidate_id -cne 'qwen-3.8-27b-groq-free-synthetic-nonthink' -or
        $preflight.inputs.case.case_id -cne $CaseId -or
        $preflight.evaluator.file -cne 'scripts/evaluate_narrator_source.py' -or
        $preflight.evaluator.sha256 -cne (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()) {
        throw 'Source preflight identity differs.'
    }
    $evaluatorHash = $preflight.evaluator.sha256
    $evidenceDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("storyteller-narrative-source-window-" + $batchId)
    [System.IO.Directory]::CreateDirectory($evidenceDirectory) | Out-Null
    $preflightPath = Join-Path $evidenceDirectory 'preflight.json'
    [System.IO.File]::WriteAllText($preflightPath, $preflightText + "`n", [System.Text.UTF8Encoding]::new($false))
    $lifecyclePath = Join-Path $evidenceDirectory 'lifecycle.json'
    Write-Lifecycle 'preflight_verified'
    $preflightOutput = $null
    $preflightText = $null
    $stage = "protected credential entry"
    if ($null -eq $ApiKey) {
        Write-Lifecycle 'awaiting_secure_credential'
        $ApiKey = Read-Host 'Cole a chave Groq somente neste prompt protegido e pressione Enter' -AsSecureString
    }
    $plainTextKey = [System.Net.NetworkCredential]::new('', $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) { throw 'Blank credential.' }
    if ((Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash) { throw 'Evaluator changed after preflight.' }
    $env:GROQ_API_KEY = $plainTextKey
    $plainTextKey = $null
    $stage = 'bounded live invocation'
    Write-Lifecycle 'running'
    $previousSummaries = @(Get-ChildItem -LiteralPath $outputRoot -Recurse -Filter summary.json -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    Write-Host 'Protected credential accepted. The bounded observation is running; the initial wait occurs before the first call.'
    $global:LASTEXITCODE = $null
    $childOutput = @(& $python -B $evaluator --live --case-id $CaseId --allow-synthetic-only --batch-id $batchId --expected-preflight $preflightPath --api-key-env GROQ_API_KEY 2>&1)
    $childSucceeded = $?
    $exitCode = $global:LASTEXITCODE
    $childOutput = $null
    Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
    $ApiKey.Dispose()
    $ApiKey = $null
    if ($null -eq $exitCode -or $exitCode -notin @(0, 1, 2, 3, 130) -or ($exitCode -eq 0 -and -not $childSucceeded)) { throw 'No usable child exit status.' }
    $stage = 'offline evidence verification'
    Write-Lifecycle 'verifying_artifacts'
    $summaries = @(Get-ChildItem -LiteralPath $outputRoot -Recurse -Filter summary.json -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notin $previousSummaries })
    if ($summaries.Count -ne 1) { throw 'Expected exactly one new summary; any partial evidence was preserved.' }
    $summaryPath = $summaries[0].FullName
    if ((Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash) { throw 'Evaluator changed during observation.' }
    $global:LASTEXITCODE = $null
    $verificationOutput = @(& $python -B $evaluator --verify-artifacts $summaryPath --case-id $CaseId --expected-preflight $preflightPath --batch-id $batchId 2>&1)
    $verificationSucceeded = $?
    if (-not $verificationSucceeded -or $global:LASTEXITCODE -ne 0) { throw 'Artifact verification failed.' }
    $document = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
    if ($document.batch_id -cne $batchId -or
        ($document.process_exit_code -isnot [int] -and $document.process_exit_code -isnot [long]) -or
        $document.process_exit_code -ne $exitCode) { throw 'Child status and verified evidence differ.' }
    Write-Host "Summary: $summaryPath"
    Write-Host "Preflight evidence: $preflightPath"
}
catch {
    # Provider output and exception payloads may contain secrets; never echo them.
    Write-Host "Narrative source probe stopped during $stage. Any local evidence was preserved."
    $failed = $true
}
finally {
    if ($null -ne $ApiKey) { $ApiKey.Dispose() }
    if ($previousKeyExists) { $env:GROQ_API_KEY = $previousKey }
    else { Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue }
    $env:STORYTELLER_DISABLE_DOTENV = $previousDotenv
    $env:PYTHONDONTWRITEBYTECODE = $previousBytecode
    if ($nativePreferenceExists) { $PSNativeCommandUseErrorActionPreference = $previousNativePreference }
    $plainTextKey = $null
    $previousKey = $null
    $preflightOutput = $null
    $childOutput = $null
    $verificationOutput = $null
}
if ($failed) { $exitCode = 3 }
Write-Lifecycle 'finished' $exitCode
if ($failed) { exit 3 }
Write-Host "Narrative source probe ended with exit code $exitCode; narrative quality, semantic truth, runtime and CAP-001 remain unapproved."
exit $exitCode
