[CmdletBinding()]
param([Parameter(Mandatory = $true)][System.Security.SecureString] $ApiKey)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_inline_evidence_qwen.py"
$outputRoot = Join-Path $projectRoot "eval-results"
$candidateId = "qwen-3.8-27b-groq-free-synthetic-nonthink"

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
    foreach ($field in @("full_evaluation", "runtime_promoted", "automated_gates_passed", "diagnostics_executed", "causal_comparison", "full_record_derivation")) {
        if ($Document.$field -isnot [bool] -or $Document.$field -ne $false) { throw "Incoherent probe scope." }
    }
    foreach ($field in @("synthetic_only", "human_review_required", "structural_only", "semantic_not_evaluated")) {
        if ($Document.$field -isnot [bool] -or $Document.$field -ne $true) { throw "Incoherent probe scope." }
    }
    if ($Document.purpose -cne "inline_evidence_qwen_probe" -or $Document.probe_kind -cne "inline_evidence_qwen_probe" -or
        $Document.experiment_version -cne "record-inline-evidence-qwen-observation-v1" -or
        $Document.protocol -cne "record-inline-evidence-v1" -or $Document.actor_admission -cne "not_applied" -or
        $Document.cap_001_status -cne "not_evaluated" -or $Document.selected_candidate_id -cne $candidateId) { throw "Incoherent probe identity." }
    foreach ($limit in @(@("automatic_retries", 0), @("max_calls", 1), @("repetitions", 1), @("narrative_generation_calls", 0))) {
        $value = $Document.($limit[0])
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -ne $limit[1]) { throw "Incoherent probe limit." }
    }
}

function Assert-Preflight($Document) {
    Assert-FixedScope $Document
    if ($Document.evaluator.file -cne "scripts/evaluate_narrator_inline_evidence_qwen.py" -or
        $Document.evaluator.sha256 -cne (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Evaluator provenance mismatch." }
    $expectedParameters = '{"deadline_seconds":60,"minimum_inter_call_delay_seconds":60,"requested":{"temperature":0.65,"max_output_tokens":3072},"transmitted":{"temperature":0.65,"max_output_tokens":3072,"reasoning_effort":"none"},"max_total_output_tokens":3072,"user_packet_budget":{"estimated_tokens":2000,"method":"characters_divided_by_4"}}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $Document.inline_generation_parameters $expectedParameters)) { throw "Incoherent generation parameters." }
    $policy = $Document.candidate_policy
    if ($policy.adapter_kind -cne "groq" -or $policy.provider_label -cne "Groq" -or
        $policy.effective_provider -cne "Groq" -or $null -ne $policy.upstream_provider -or
        $policy.structured_mode -cne "native" -or $policy.reasoning_effort -cne "none" -or
        $policy.campaign_data_eligible -isnot [bool] -or $policy.campaign_data_eligible -ne $false) { throw "Incoherent candidate policy." }
    $inputs = $Document.inputs
    $manifest = $inputs.manifest
    if ($manifest.file -cne "groq_candidates_2026-09-05.json" -or
        $manifest.sha256 -cne "de31691d9562e7cc8abe2b13d004098967976cda321c975d2f3ed7a147a15de6" -or
        $manifest.sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot ("evals/narrator/" + $manifest.file)) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Fixed manifest mismatch." }
    $caseFile = "evals/narrator/record_inline_case_v1.json"
    $caseHash = "5b812d5f4f20ef592e20268a08c2e7fd837cb5d1e6d0d96a175a4033b0383cd7"
    if ($inputs.case.file -cne $caseFile -or $inputs.case.case_id -cne "archive-vibration" -or
        $inputs.case.sha256 -cne $caseHash -or
        $inputs.case.sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $caseFile) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Fixed case mismatch." }
    if ($inputs.prompt.variant -cne "record-inline-evidence-v1" -or
        $inputs.prompt.file -cne "evals/narrator/prompts/record-inline-evidence-v1.md" -or
        $inputs.prompt.sha256 -cne "0ca6e7b9ebb2210bce3830119b324d121cfc92bd4b548b29639fb4029812cf87" -or
        $inputs.prompt.file_sha256 -cne "e895df2097c875c8b16f2504c96c5f403bde62f92cbc2ec1c1d69ee94a468c8f" -or
        $inputs.prompt.file_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $inputs.prompt.file) -Algorithm SHA256).Hash.ToLowerInvariant() -or
        $inputs.response_schema_sha256 -cne "f83bc66cab29a079598f074db3ee4838a94882ef65f254866d0505aa29b37d9a" -or
        $inputs.provider_schema_sha256 -cne "f83bc66cab29a079598f074db3ee4838a94882ef65f254866d0505aa29b37d9a" -or
        @($inputs.implementation).Count -lt 1 -or @($inputs.cases).Count -ne 1) { throw "Incomplete fixed inputs." }
    $implementationFiles = @()
    foreach ($item in $inputs.implementation) {
        if ([string]::IsNullOrWhiteSpace($item.file) -or $item.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw "Incomplete implementation provenance." }
        $implementationPath = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $item.file))
        $rootPrefix = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
        if (-not $implementationPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
            $item.file -cin $implementationFiles -or
            $item.sha256 -cne (Get-FileHash -LiteralPath $implementationPath -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Implementation provenance mismatch." }
        $implementationFiles += $item.file
        if ($item.file -ceq "scripts/narrator_inline_evidence.py" -and
            $item.sha256 -cne "e92f769047baff1b8171d2ca98b12ba225b5c990df178b8fbe1e0c9322524419") { throw "Inline contract mismatch." }
    }
    foreach ($requiredFile in @("scripts/narrator_inline_evidence.py", "scripts/narrator_record_budget_observer.py",
        "scripts/evaluate_narrator_models.py", "api/llm/adapters/groq.py", "api/llm/adapters/openai_compatible.py", "api/llm/contract.py")) {
        if ($requiredFile -cnotin $implementationFiles) { throw "Missing inline implementation provenance." }
    }
    $case = @($inputs.cases)[0]
    $expectedSource = @{ origin="agent_authored_synthetic_case"; synthetic_only=$true; case_file=$caseFile; case_sha256=$caseHash; field="narrative"; narrative_sha256="70adab37989c455858052582a4dba8e2edfa3fbce0d1d2ca8257a18aa37e8685" } | ConvertTo-Json | ConvertFrom-Json
    $sourceDocument = Get-Content -Raw -LiteralPath (Join-Path $projectRoot $caseFile) | ConvertFrom-Json
    $expectedBudget = '{"scope":"user_packet_only","method":"characters_divided_by_4","limit":2000,"estimated_tokens":168}' | ConvertFrom-Json
    if ($case.case_id -cne "archive-vibration" -or -not (Test-JsonEqual $case.source $expectedSource) -or
        $case.generation_context.version -cne "record-inline-evidence-v1" -or
        $case.generation_context.user_packet_sha256 -cne "b7706e060b634d25235955eb43dd3720051916947b7ef508afb02fa75badc7bc" -or
        $case.generation_context.source_units_sha256 -cne "b327fdb6be496eb5028dd640fd7ee9fa5e97e2d98e2288b612948146f9a4ec2b" -or
        -not (Test-JsonEqual $case.generation_context.source_units $sourceDocument.source_units) -or
        -not (Test-JsonEqual $case.generation_context.budget $expectedBudget)) { throw "Incoherent inline source case." }
    $dossier = $inputs.dossier
    if ($dossier.file -cne "evals/narrator/reports/record-inline-evidence-qwen-dossier-6876955e-2026-09-07.json" -or
        $dossier.sha256 -cne "ce551e0d33659cb600af00a861d4af85a00d98acc2db270bf66f9ce470eb5e30" -or
        $dossier.sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $dossier.file) -Algorithm SHA256).Hash.ToLowerInvariant() -or
        $dossier.body_sha256 -cne "bd7219cf1cd27f2ce1d80879370064b6ef7ac3d2b64f4be7a0d32da5db0326f7") { throw "Incoherent request dossier." }
    $expectedProjection = '{"concatenation":"literal_no_separator","offset_unit":"unicode_code_points","interval":"[start,end)","semantic_validation":false}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $inputs.projection_policy $expectedProjection)) { throw "Incoherent projection policy." }
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
Write-Host "Inline evidence Qwen probe batch: $batchId"
Write-Host "One authored synthetic case; at most one Qwen inline evidence call, 3072 output tokens, reasoning effort none, temperature 0.65."
Write-Host "Initial local wait: 60 seconds; then a 60-second deadline for the single call. No narrative generation, diagnostics, retries or fallback."
Write-Host "Only summary and open questions are projected by literal concatenation; structural validation does not evaluate semantic fidelity."
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
            Write-Host "Inline evidence Qwen probe cancelled with partial local evidence; files were preserved but no complete summary could be verified."
            throw "Incomplete cancellation evidence."
        }
        Write-Host "Inline evidence Qwen probe cancelled; no completed summary was produced."
        exit 130
    }
    if ($newSummaries.Count -ne 1) { throw "Expected exactly one new summary." }
    $summaryPath = $newSummaries[0].FullName
    $document = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
    Assert-FixedScope $document
    if ($document.batch_id -cne $batchId -or
        ($document.process_exit_code -isnot [int] -and $document.process_exit_code -isnot [long]) -or
        $document.process_exit_code -ne $exitCode) { throw "Incoherent invocation provenance." }
    foreach ($field in @("inputs", "evaluator", "inline_generation_parameters", "candidate_policy")) {
        if (-not (Test-JsonEqual $document.$field $preflight.$field)) { throw "Preflight provenance changed." }
    }
    $summary = $document.summary
    $summaryScope = $summary | Select-Object *
    if ($summaryScope.PSObject.Properties.Name -contains "selected_candidate_id") {
        if ($summaryScope.selected_candidate_id -cne $candidateId) { throw "Incoherent summary candidate." }
    }
    else { $summaryScope | Add-Member -NotePropertyName "selected_candidate_id" -NotePropertyValue $candidateId }
    Assert-FixedScope $summaryScope
    $expectedReview = '{"status":"not_performed","approval":null}' | ConvertFrom-Json
    foreach ($field in @("semantic_fidelity_review", "support_coverage_review")) {
        if (-not (Test-JsonEqual $summary.$field $expectedReview)) { throw "Incoherent semantic review scope." }
    }
    if (($summary.process_exit_code -isnot [int] -and $summary.process_exit_code -isnot [long]) -or
        $summary.process_exit_code -ne $exitCode) { throw "Incoherent summary exit status." }
    foreach ($field in @("calls_made", "schema_valid", "projection_valid", "cases_skipped")) {
        $value = $summary.$field
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt 1) { throw "Incoherent call count." }
    }
    if (($exitCode -in @(1, 2) -and $summary.calls_made -eq 0) -or
        $summary.calls_made + $summary.cases_skipped -ne 1 -or
        $summary.projection_valid -gt $summary.schema_valid -or $summary.schema_valid -gt $summary.calls_made -or
        $summary.operational_probe_passed -isnot [bool] -or $summary.operational_probe_passed -ne ($exitCode -eq 0)) { throw "Incoherent operational result." }
    if (($summary.calls_made -eq 1 -and $summary.provider_observation -isnot [System.Management.Automation.PSCustomObject]) -or
        ($summary.calls_made -eq 0 -and $null -ne $summary.provider_observation)) { throw "Incoherent provider observation." }
    $route = $summary.route_verification
    foreach ($field in @("calls_made", "verified_calls", "unavailable_calls", "mismatched_calls")) {
        $value = $route.$field
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt 1) { throw "Incoherent route count." }
    }
    if ($route.calls_made -ne $summary.calls_made -or
        $route.verified_calls + $route.unavailable_calls + $route.mismatched_calls -ne $route.calls_made) { throw "Incoherent route evidence." }
    if ($exitCode -eq 0) {
        if ($summary.calls_made -ne 1 -or $summary.schema_valid -ne 1 -or $summary.projection_valid -ne 1 -or
            $route.status -cne "verified" -or $route.verified_calls -ne 1 -or
            $route.unavailable_calls -ne 0 -or $route.mismatched_calls -ne 0 -or
            $route.identity_consistent -isnot [bool] -or $route.identity_consistent -ne $true) { throw "Incoherent successful observation." }
    }
    Write-Host "Summary: $summaryPath"
}
catch {
    # Never echo child output, exception payloads, credentials or generated prose.
    Write-Host "Inline evidence Qwen probe stopped because execution or evidence verification failed ($failureStage)."
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
Write-Host "Inline evidence Qwen probe ended with exit code $exitCode; narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
