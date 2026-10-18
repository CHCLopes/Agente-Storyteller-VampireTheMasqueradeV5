[CmdletBinding()]
param([Parameter(Mandatory = $true)][System.Security.SecureString] $ApiKey)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_record_evidence.py"
$outputRoot = Join-Path $projectRoot "eval-results"
$candidateId = "gpt-oss-120b-groq-free-synthetic-low"

function Test-JsonEqual($Left, $Right) {
    if ($null -eq $Left -or $null -eq $Right) { return ($null -eq $Left -and $null -eq $Right) }
    if ($Left -is [System.Management.Automation.PSCustomObject]) {
        if ($Right -isnot [System.Management.Automation.PSCustomObject]) { return $false }
        $leftNames = @($Left.PSObject.Properties.Name | Sort-Object)
        $rightNames = @($Right.PSObject.Properties.Name | Sort-Object)
        if ($leftNames.Count -ne $rightNames.Count) { return $false }
        for ($index = 0; $index -lt $leftNames.Count; $index++) {
            if ($leftNames[$index] -cne $rightNames[$index] -or
                -not (Test-JsonEqual $Left.($leftNames[$index]) $Right.($rightNames[$index]))) { return $false }
        }
        return $true
    }
    if ($Left -is [array]) {
        if ($Right -isnot [array] -or $Left.Count -ne $Right.Count) { return $false }
        for ($index = 0; $index -lt $Left.Count; $index++) {
            if (-not (Test-JsonEqual $Left[$index] $Right[$index])) { return $false }
        }
        return $true
    }
    if ($Left -is [bool]) { return ($Right -is [bool] -and $Left -eq $Right) }
    if ($Left -is [string]) { return ($Right -is [string] -and $Left -ceq $Right) }
    if ($Left -is [ValueType] -and $Right -is [ValueType] -and $Right -isnot [bool]) { return ($Left -eq $Right) }
    return $false
}

function Assert-FixedScope($Document) {
    foreach ($field in @("full_evaluation", "runtime_promoted", "automated_gates_passed", "diagnostics_executed", "causal_comparison")) {
        if ($Document.$field -isnot [bool] -or $Document.$field -ne $false) { throw "Incoherent probe scope." }
    }
    foreach ($field in @("synthetic_only", "human_review_required")) {
        if ($Document.$field -isnot [bool] -or $Document.$field -ne $true) { throw "Incoherent probe scope." }
    }
    if ($Document.purpose -cne "record_evidence_probe" -or $Document.probe_kind -cne "record_evidence_probe" -or
        $Document.cap_001_status -cne "not_evaluated" -or $Document.selected_candidate_id -cne $candidateId) { throw "Incoherent probe identity." }
    foreach ($limit in @(@("automatic_retries", 0), @("max_calls", 2), @("repetitions", 1), @("narrative_generation_calls", 0))) {
        $value = $Document.($limit[0])
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -ne $limit[1]) { throw "Incoherent probe limit." }
    }
}

function Assert-Preflight($Document) {
    Assert-FixedScope $Document
    if ($Document.evaluator.file -cne "scripts/evaluate_narrator_record_evidence.py" -or
        $Document.evaluator.sha256 -cne (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Evaluator provenance mismatch." }
    $expectedParameters = '{"deadline_seconds":60,"minimum_inter_call_delay_seconds":60,"requested":{"temperature":0.65,"max_output_tokens":768},"transmitted":{"temperature":0.65,"max_output_tokens":768,"reasoning_effort":"low"},"max_total_output_tokens":1536,"user_packet_budget":{"estimated_tokens":2000,"method":"characters_divided_by_4"}}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $Document.evidence_generation_parameters $expectedParameters)) { throw "Incoherent generation parameters." }
    $inputs = $Document.inputs
    foreach ($pair in @(@("manifest", "groq_candidates_2026-09-05.json"), @("corpus", "corpus_v1.json"))) {
        $item = $inputs.($pair[0])
        $path = Join-Path $projectRoot ("evals\narrator\" + $pair[1])
        if ($item.file -cne $pair[1] -or $item.sha256 -cne (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Fixed input provenance mismatch." }
    }
    if ($inputs.prompt.variant -cne "record-evidence-v1" -or
        $inputs.prompt.file -cne "evals/narrator/prompts/record-evidence-v1.md" -or
        $inputs.prompt.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $inputs.response_schema_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $inputs.provider_schema_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $inputs.final_schema_sha256 -cne 'bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2' -or
        @($inputs.implementation).Count -lt 1 -or @($inputs.cases).Count -ne 2) { throw "Incomplete fixed inputs." }
    foreach ($item in $inputs.implementation) {
        if ([string]::IsNullOrWhiteSpace($item.file) -or $item.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw "Incomplete implementation provenance." }
    }
    $cases = @($inputs.cases)
    $expectedTurns = @(@("opening", "establish-scene"), @("player-agency", "world-reacts-player-remains-free"))
    for ($index = 0; $index -lt 2; $index++) {
        $case = $cases[$index]
        if ([string]::IsNullOrWhiteSpace($case.case_id) -or
            $case.episode_id -cne $expectedTurns[$index][0] -or $case.turn_id -cne $expectedTurns[$index][1] -or
            $null -eq $case.source -or $null -eq $case.generation_context) { throw "Incoherent fixed cases." }
    }
    if ($cases[0].case_id -ceq $cases[1].case_id) { throw "Duplicate fixed case." }
}

$batchId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
$plainTextKey = $null
$groqApiKeyExisted = Test-Path Env:GROQ_API_KEY
$previousGroqApiKey = if ($groqApiKeyExisted) { (Get-Item Env:GROQ_API_KEY).Value } else { $null }
$nativePreferenceExists = Test-Path Variable:PSNativeCommandUseErrorActionPreference
$previousNativePreference = $null
if ($nativePreferenceExists) {
    $previousNativePreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}
$exitCode = 3
$failed = $false
$failureStage = "offline preflight"
Write-Host "Record evidence probe batch: $batchId"
Write-Host "Two fixed synthetic narratives; at most two evidence derivation calls, 768 tokens each including supports, temperature 0.65."
Write-Host "Local pacing and per-call deadline: 60 seconds. No narrative generation, diagnostics, retries or fallback."
Write-Host "This probe never approves narrative quality, runtime or CAP-001."
try {
    foreach ($path in @($python, $evaluator)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required probe file unavailable." }
    }
    # Preflight receives neither the supplied key nor an older environment key.
    Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
    $global:LASTEXITCODE = $null
    $preflightOutput = @(& $python $evaluator --preflight 2>&1)
    $preflightSucceeded = $?
    if (-not $preflightSucceeded -or $global:LASTEXITCODE -ne 0) { throw "Offline preflight failed." }
    $preflight = ($preflightOutput -join "`n") | ConvertFrom-Json
    Assert-Preflight $preflight
    $preflightOutput = $null
    $failureStage = "credential validation"
    $plainTextKey = [System.Net.NetworkCredential]::new("", $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) { throw "Blank credential." }
    $env:GROQ_API_KEY = $plainTextKey
    $failureStage = "child invocation"
    $previousArtifactPaths = @(
        Get-ChildItem -LiteralPath $outputRoot -Recurse -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName }
    )
    $global:LASTEXITCODE = $null
    $childOutput = @(& $python $evaluator --live --allow-synthetic-only --batch-id $batchId --api-key-env GROQ_API_KEY 2>&1)
    $invocationSucceeded = $?
    $exitCode = $global:LASTEXITCODE
    $childOutput = $null
    if ($null -eq $exitCode -or $exitCode -notin @(0, 1, 2, 3, 130) -or
        ($exitCode -eq 0 -and -not $invocationSucceeded)) { throw "No usable child exit status." }
    $failureStage = "summary verification"
    $newArtifacts = @(
        Get-ChildItem -LiteralPath $outputRoot -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notin $previousArtifactPaths }
    )
    $newSummaries = @($newArtifacts | Where-Object { -not $_.PSIsContainer -and $_.Name -eq "summary.json" })
    if ($exitCode -eq 130 -and $newSummaries.Count -eq 0) {
        if ($newArtifacts.Count -ne 0) {
            Write-Host "Record evidence probe cancelled with partial local evidence; files were preserved but no complete summary could be verified."
            throw "Incomplete cancellation evidence."
        }
        Write-Host "Record evidence probe cancelled; no completed summary was produced."
        exit 130
    }
    if ($newSummaries.Count -ne 1) { throw "Expected exactly one new summary." }
    $summaryPath = $newSummaries[0].FullName
    $document = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
    Assert-FixedScope $document
    if ($document.batch_id -cne $batchId -or
        ($document.process_exit_code -isnot [int] -and $document.process_exit_code -isnot [long]) -or
        $document.process_exit_code -ne $exitCode) { throw "Incoherent invocation provenance." }
    foreach ($field in @("inputs", "evaluator", "evidence_generation_parameters")) {
        if (-not (Test-JsonEqual $document.$field $preflight.$field)) { throw "Preflight provenance changed." }
    }
    $summary = $document.summary
    $summaryScope = $summary | Select-Object *
    if ($summaryScope.PSObject.Properties.Name -contains "selected_candidate_id") {
        if ($summaryScope.selected_candidate_id -cne $candidateId) { throw "Incoherent summary candidate." }
    }
    else { $summaryScope | Add-Member -NotePropertyName "selected_candidate_id" -NotePropertyValue $candidateId }
    Assert-FixedScope $summaryScope
    if (($summary.process_exit_code -isnot [int] -and $summary.process_exit_code -isnot [long]) -or
        $summary.process_exit_code -ne $exitCode) { throw "Incoherent summary exit status." }
    foreach ($field in @("calls_made", "schema_valid", "envelope_valid", "final_schema_valid", "admitted")) {
        $value = $summary.$field
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt 2) { throw "Incoherent call count." }
    }
    if (($exitCode -in @(1, 2) -and $summary.calls_made -eq 0) -or
        $summary.admitted -gt $summary.final_schema_valid -or $summary.final_schema_valid -gt $summary.envelope_valid -or
        $summary.envelope_valid -gt $summary.schema_valid -or $summary.schema_valid -gt $summary.calls_made -or
        $summary.operational_probe_passed -isnot [bool] -or $summary.operational_probe_passed -ne ($exitCode -eq 0)) { throw "Incoherent operational result." }
    if ($exitCode -eq 0) {
        $route = $summary.route_verification
        if ($summary.calls_made -ne 2 -or $summary.schema_valid -ne 2 -or $summary.envelope_valid -ne 2 -or
            $summary.final_schema_valid -ne 2 -or $summary.admitted -ne 2 -or
            $route.status -cne "verified" -or $route.calls_made -ne 2 -or $route.verified_calls -ne 2 -or
            $route.unavailable_calls -ne 0 -or $route.mismatched_calls -ne 0 -or
            $route.identity_consistent -isnot [bool] -or $route.identity_consistent -ne $true) { throw "Incoherent successful observation." }
    }
    Write-Host "Summary: $summaryPath"
}
catch {
    # Never echo child output, exception payloads, credentials or generated prose.
    Write-Host "Record evidence probe stopped because execution or evidence verification failed ($failureStage)."
    $failed = $true
}
finally {
    if ($groqApiKeyExisted) { $env:GROQ_API_KEY = $previousGroqApiKey }
    else { Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue }
    $plainTextKey = $null
    $previousGroqApiKey = $null
    $preflightOutput = $null
    $childOutput = $null
    if ($nativePreferenceExists) { $PSNativeCommandUseErrorActionPreference = $previousNativePreference }
}
if ($failed) { exit 3 }
Write-Host "Record evidence probe ended with exit code $exitCode; narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
