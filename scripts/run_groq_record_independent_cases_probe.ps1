[CmdletBinding()]
param([Parameter(Mandatory = $true)][System.Security.SecureString] $ApiKey)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_record_independent_cases.py"
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
    if ($Document.purpose -cne "record_evidence_independent_cases_probe" -or $Document.probe_kind -cne "record_evidence_independent_cases_probe" -or
        $Document.experiment_version -cne "record-evidence-independent-cases-v1" -or
        $Document.cap_001_status -cne "not_evaluated" -or $Document.selected_candidate_id -cne $candidateId) { throw "Incoherent probe identity." }
    foreach ($limit in @(@("automatic_retries", 0), @("max_calls", 2), @("repetitions", 1), @("narrative_generation_calls", 0))) {
        $value = $Document.($limit[0])
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -ne $limit[1]) { throw "Incoherent probe limit." }
    }
}

function Assert-Preflight($Document) {
    Assert-FixedScope $Document
    if ($Document.evaluator.file -cne "scripts/evaluate_narrator_record_independent_cases.py" -or
        $Document.evaluator.sha256 -cne (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Evaluator provenance mismatch." }
    $expectedParameters = '{"deadline_seconds":60,"minimum_inter_call_delay_seconds":60,"requested":{"temperature":0.65,"max_output_tokens":3072},"transmitted":{"temperature":0.65,"max_output_tokens":3072,"reasoning_effort":"low"},"max_total_output_tokens":6144,"user_packet_budget":{"estimated_tokens":2000,"method":"characters_divided_by_4"}}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $Document.evidence_generation_parameters $expectedParameters)) { throw "Incoherent generation parameters." }
    $inputs = $Document.inputs
    foreach ($pair in @(@("manifest", "groq_candidates_2026-09-05.json"), @("corpus", "record_independent_cases_v1.json"))) {
        $item = $inputs.($pair[0])
        $path = Join-Path $projectRoot ("evals\narrator\" + $pair[1])
        if ($item.file -cne $pair[1] -or $item.sha256 -cne (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Fixed input provenance mismatch." }
    }
    if ($inputs.prompt.variant -cne "record-evidence-claim-check-v1" -or
        $inputs.prompt.file -cne "evals/narrator/prompts/record-evidence-claim-check-v1.md" -or
        $inputs.prompt.sha256 -cne "dc338d3ff2f1cf3fa04222e717b5e3f060541fbf41cf4abd5a9cf7af66a74839" -or
        $inputs.response_schema_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $inputs.provider_schema_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $inputs.final_schema_sha256 -cne 'bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2' -or
        @($inputs.implementation).Count -lt 1 -or @($inputs.cases).Count -ne 2) { throw "Incomplete fixed inputs." }
    foreach ($item in $inputs.implementation) {
        if ([string]::IsNullOrWhiteSpace($item.file) -or $item.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw "Incomplete implementation provenance." }
    }
    if ($inputs.corpus.sha256 -cne "fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353") { throw "Independent corpus fingerprint differs." }
    $expectedCases = '[{"case_id":"uncertain-signal","episode_id":"independent-uncertainty","turn_id":"derive-uncertainty","source":{"case_binding":"record-independent-cases-v1","origin":"agent_authored_synthetic_cases","synthetic_only":true,"corpus_id":"storyteller-record-independent-cases-v1","corpus_file":"evals/narrator/record_independent_cases_v1.json","corpus_sha256":"fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353","case_path":"/cases/0","case_id":"uncertain-signal","episode_id":"independent-uncertainty","turn_id":"derive-uncertainty","field":"narrative","narrative_sha256":"0fab6e6c72d44d20f2c8512650ba99861b069e381d6354bdc37c140b96dc865a","context_origin":"original_synthetic_corpus","protected_secrets_count":0},"user_packet_sha256":"8406c7783c645b9f8df1ca1d1d856c19f48f4f3fd6b178010a811d8613710602"},{"case_id":"sensory-evidence","episode_id":"independent-sensory","turn_id":"derive-sensory","source":{"case_binding":"record-independent-cases-v1","origin":"agent_authored_synthetic_cases","synthetic_only":true,"corpus_id":"storyteller-record-independent-cases-v1","corpus_file":"evals/narrator/record_independent_cases_v1.json","corpus_sha256":"fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353","case_path":"/cases/1","case_id":"sensory-evidence","episode_id":"independent-sensory","turn_id":"derive-sensory","field":"narrative","narrative_sha256":"5db12d31eb1f50451261f84dbc5e4ca493728ecb3ef0b49bee7d02847608f79e","context_origin":"original_synthetic_corpus","protected_secrets_count":0},"user_packet_sha256":"67686acf1d0bbbf56575a8987ff18dd21019083e1bed740e06c1d6054efb3b96"}]' | ConvertFrom-Json
    for ($index = 0; $index -lt 2; $index++) {
        $case = @($inputs.cases)[$index]
        $expectedCase = @($expectedCases)[$index]
        if ($case.case_id -cne $expectedCase.case_id -or $case.episode_id -cne $expectedCase.episode_id -or
            $case.turn_id -cne $expectedCase.turn_id -or
            -not (Test-JsonEqual $case.source $expectedCase.source) -or
            -not (Test-JsonEqual $case.generation_context.source $expectedCase.source) -or
            $case.generation_context.version -cne "record-evidence-v1" -or
            $case.generation_context.user_packet_sha256 -cne $expectedCase.user_packet_sha256) { throw "Incoherent independent source case." }
    }
    $helperFile = "scripts/narrator_record_independent_cases.py"
    $helperHash = "ba4cb5ca28d89e0439b1d3992da03ec190b2bf1be8ba02403037fffa87a1dada"
    $helper = @($inputs.implementation | Where-Object { $_.file -ceq $helperFile })
    if ($helper.Count -ne 1 -or $helper[0].sha256 -cne $helperHash -or
        $helperHash -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $helperFile) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Incoherent independent loader provenance." }
    $dossier = $inputs.dossier
    $expectedDossier = '{"file":"evals/narrator/reports/record-evidence-independent-cases-dossier-84ea2c0c-2026-09-07.json","sha256":"24a3b302938e27481f131c9ecf1826fd9571c1fdf68e2ae3238fa0a94a3cdd36","original_body_sha256":"0ef02b6c4987318c829e7193e6cdbba67dcc58d6937e966fdcf3809c64cbd209","changed_payload_fields":["messages[1].content"],"requests":[{"case_id":"uncertain-signal","body_sha256":"dfeab91b18a02b969f887ff06877e576c6f6dc3fd1b55fcb652a1ec6ab5c4840"},{"case_id":"sensory-evidence","body_sha256":"2a762328afd75a5951071f9d39cffeee329e3184cfeaec2cc86dc13333f1b40b"}]}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $dossier $expectedDossier) -or
        $dossier.sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $expectedDossier.file) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Incoherent independent request dossier." }
    $expectedSupportPolicy = '{"method":"unique_exact_target_quote","quote_protocol":"record-evidence-target-quotes-v1","matching":"literal_unicode_code_points","ambiguous_quote":"reject","missing_quote":"reject","records_rewritten":false,"offsets_purpose":"audit_only","coverage_validation":false,"entailment_validation":false}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $inputs.support_resolution_policy $expectedSupportPolicy)) { throw "Incoherent quote protocol policy." }
    $expectedObservation = '{"max_error_body_bytes":65536,"raw_error_retained":false,"raw_reasoning_retained":false}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $inputs.observation_policy $expectedObservation)) { throw "Incoherent observation policy." }
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
Write-Host "Record evidence independent cases probe batch: $batchId"
Write-Host "Two independently authored synthetic cases; at most two calls, 3072 tokens each and 6144 total including supports and provider-accounted reasoning, temperature 0.65."
Write-Host "Initial local wait and minimum call-start gap: 60 seconds; each call has a 60-second deadline. Any failed call stops the remaining cases; no retries, diagnostics or fallback."
Write-Host "Frozen exact-quote protocol, SYSTEM, schemas and per-call budget; only USER content changes for the two independent inputs. No opening or Mara replay."
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
            Write-Host "Record evidence independent cases probe cancelled with partial local evidence; files were preserved but no complete summary could be verified."
            throw "Incomplete cancellation evidence."
        }
        Write-Host "Record evidence independent cases probe cancelled; no completed summary was produced."
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
    foreach ($field in @("calls_made", "cases_skipped", "schema_valid", "envelope_valid", "final_schema_valid", "admitted")) {
        $value = $summary.$field
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt 2) { throw "Incoherent call count." }
    }
    if ($summary.calls_made + $summary.cases_skipped -ne 2) { throw "Incoherent completed case accounting." }
    if (($exitCode -in @(1, 2) -and $summary.calls_made -eq 0) -or
        $summary.admitted -gt $summary.final_schema_valid -or $summary.final_schema_valid -gt $summary.envelope_valid -or
        $summary.envelope_valid -gt $summary.schema_valid -or $summary.schema_valid -gt $summary.calls_made -or
        $summary.operational_probe_passed -isnot [bool] -or $summary.operational_probe_passed -ne ($exitCode -eq 0)) { throw "Incoherent operational result." }
    $observations = @($summary.provider_observations)
    if ($summary.provider_observations -isnot [array] -or $observations.Count -ne $summary.calls_made) { throw "Incoherent provider observation count." }
    $orderedCaseIds = @("uncertain-signal", "sensory-evidence")
    for ($index = 0; $index -lt $observations.Count; $index++) {
        if ($observations[$index].case_id -cne $orderedCaseIds[$index] -or
            $null -eq $observations[$index].observation) { throw "Incoherent provider observation identity." }
    }
    if ($summary.calls_made -eq 1) {
        if (-not (Test-JsonEqual $summary.provider_observation $observations[0].observation)) { throw "Incoherent single-call observation." }
    }
    elseif ($null -ne $summary.provider_observation) { throw "Unexpected single-call observation." }
    if ($exitCode -eq 0) {
        $route = $summary.route_verification
        foreach ($field in @("calls_made", "verified_calls", "unavailable_calls", "mismatched_calls")) {
            $value = $route.$field
            if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt 2) { throw "Incoherent route count." }
        }
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
    Write-Host "Record evidence independent cases probe stopped because execution or evidence verification failed ($failureStage)."
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
Write-Host "Record evidence independent cases probe ended with exit code $exitCode; narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
