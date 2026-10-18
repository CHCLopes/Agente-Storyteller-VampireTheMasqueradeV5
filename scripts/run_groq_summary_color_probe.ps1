[CmdletBinding()]
param([Parameter(Mandatory = $true)][System.Security.SecureString] $ApiKey)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_summary_color.py"
$outputRoot = Join-Path $projectRoot "eval-results"
$candidateId = "qwen-3.8-27b-groq-free-synthetic-nonthink"
$caseIds = @("reading-room-a", "reading-room-b")

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
    foreach ($field in @("projection", "projection_valid", "projection_audit", "admitted", "final_schema_valid", "inline_generation_parameters", "support_coverage_review")) {
        if ($Document.PSObject.Properties.Name -contains $field) { throw "Unexpected prior-contract field." }
    }
    foreach ($field in @("full_evaluation", "runtime_promoted", "automated_gates_passed", "diagnostics_executed", "causal_comparison", "full_record_derivation")) {
        if ($Document.$field -isnot [bool] -or $Document.$field -ne $false) { throw "Incoherent probe scope." }
    }
    foreach ($field in @("synthetic_only", "human_review_required", "structural_only", "semantic_not_evaluated")) {
        if ($Document.$field -isnot [bool] -or $Document.$field -ne $true) { throw "Incoherent probe scope." }
    }
    if ($Document.purpose -cne "summary_color_qwen_probe" -or $Document.probe_kind -cne "summary_color_qwen_probe" -or
        $Document.experiment_version -cne "record-summary-color-qwen-observation-v1" -or
        $Document.protocol -cne "record-summary-only-v1" -or $Document.actor_admission -cne "not_applied" -or
        $Document.cap_001_status -cne "not_evaluated" -or $Document.selected_candidate_id -cne $candidateId) { throw "Incoherent probe identity." }
    foreach ($limit in @(@("automatic_retries", 0), @("max_calls", 2), @("repetitions", 1), @("narrative_generation_calls", 0))) {
        $value = $Document.($limit[0])
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -ne $limit[1]) { throw "Incoherent probe limit." }
    }
}

function Assert-Preflight($Document) {
    Assert-FixedScope $Document
    if ($Document.evaluator.file -cne "scripts/evaluate_narrator_summary_color.py" -or
        $Document.evaluator.sha256 -cne (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Evaluator provenance mismatch." }
    $expectedParameters = '{"deadline_seconds":60,"minimum_inter_call_delay_seconds":60,"requested":{"temperature":0.65,"max_output_tokens":768},"transmitted":{"temperature":0.65,"max_output_tokens":768,"reasoning_effort":"none"},"max_total_output_tokens":1536,"user_packet_budget":{"estimated_tokens":2000,"method":"characters_divided_by_4"}}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $Document.summary_generation_parameters $expectedParameters)) { throw "Incoherent generation parameters." }
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
    $corpusFile = "evals/narrator/record_summary_color_cases_v1.json"
    $corpusHash = "2795503b86b084b24c7864f5368f12a5acc9889601a57b24e6e557d977cf710a"
    if ($inputs.PSObject.Properties.Name -contains "case" -or
        $inputs.corpus.file -cne "record_summary_color_cases_v1.json" -or
        $inputs.corpus.sha256 -cne $corpusHash -or
        $inputs.corpus.sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $corpusFile) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Fixed corpus mismatch." }
    if ($inputs.prompt.variant -cne "record-summary-budget-v1" -or
        $inputs.prompt.file -cne "evals/narrator/prompts/record-summary-budget-v1.md" -or
        $inputs.prompt.sha256 -cne "1eca37a720951743b0f989b3ed31b1fd726663345bad71016179966d5548d5ce" -or
        $inputs.prompt.file_sha256 -cne "6a59513d8b99659f00548ed3d5300f3137e402f40a2e3f7fc26d674dbc9964f4" -or
        $inputs.prompt.file_sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $inputs.prompt.file) -Algorithm SHA256).Hash.ToLowerInvariant() -or
        $inputs.response_schema_sha256 -cne "56665f9935721c6e5909de1d3f8b7fb869de6cda7cecd4af0b3591d977a15616" -or
        $inputs.provider_schema_sha256 -cne "56665f9935721c6e5909de1d3f8b7fb869de6cda7cecd4af0b3591d977a15616" -or
        @($inputs.implementation).Count -lt 1 -or @($inputs.cases).Count -ne 2) { throw "Incomplete fixed inputs." }
    $implementationFiles = @()
    foreach ($item in $inputs.implementation) {
        if ([string]::IsNullOrWhiteSpace($item.file) -or $item.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw "Incomplete implementation provenance." }
        $implementationPath = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $item.file))
        $rootPrefix = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
        if (-not $implementationPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
            $item.file -cin $implementationFiles -or
            $item.sha256 -cne (Get-FileHash -LiteralPath $implementationPath -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Implementation provenance mismatch." }
        $implementationFiles += $item.file
        if ($item.file -ceq "scripts/narrator_summary_only.py" -and
            $item.sha256 -cne "ad3324da8bce3213f4e128c78f7f97998e91a0376046c3a09c007e45021e5182") { throw "Summary-only contract mismatch." }
    }
    foreach ($requiredFile in @("scripts/narrator_summary_only.py", "scripts/narrator_record_budget_observer.py",
        "scripts/evaluate_narrator_models.py", "api/llm/adapters/groq.py", "api/llm/adapters/openai_compatible.py", "api/llm/contract.py")) {
        if ($requiredFile -cnotin $implementationFiles) { throw "Missing summary-only implementation provenance." }
    }
    $corpusDocument = Get-Content -Raw -LiteralPath (Join-Path $projectRoot $corpusFile) | ConvertFrom-Json
    $narrativeHashes = @("aa1def53c01ab1ff078e85634aaafe53d29f4531acd85fd537161356ff6b669b", "890dc5a5bed0be1a2e855a73fb424d04aa846a99206d6c94c66248b0dfc99d23")
    $userHashes = @("149c1ffdd529220e034dad6c372da216e51db67637c81484176d22a237068f3d", "ef2b18269066b38df7ef546ae7b292cb8fbb1fd90908b4330ced21759d396eb8")
    $sourceUnitHashes = @("7045a45a0cc35c0780f4eed0e0f66fe259dbfa8fd08f5ae2a0180600c0e15ced", "722e7eaf506e43050f94834beb6c32eb90ca1cf221fb0ab4fd6a81ef4575800b")
    $bodyHashes = @("25be06f95bc681bf84a9cf7c4fd62fedd726c150c508a4a3cd28b7307e339065", "032ce8babd9e14b2c55515c7e502c05c1ca2126ce41c2f49c50ba3edd47a5d3a")
    $estimatedTokens = @(172, 172)
    $expectedRequests = @()
    for ($index = 0; $index -lt 2; $index++) {
        $case = @($inputs.cases)[$index]
        $sourceCase = @($corpusDocument.cases)[$index]
        $expectedSource = @{
            origin="agent_authored_synthetic_case"; synthetic_only=$true; corpus_file=$corpusFile
            corpus_sha256=$corpusHash; case_id=$caseIds[$index]; case_index=$index; field="narrative"
            narrative_sha256=$narrativeHashes[$index]
        } | ConvertTo-Json | ConvertFrom-Json
        $expectedBudget = @{
            scope="user_packet_only"; method="characters_divided_by_4"; limit=2000; estimated_tokens=$estimatedTokens[$index]
        } | ConvertTo-Json | ConvertFrom-Json
        if ($case.case_id -cne $caseIds[$index] -or -not (Test-JsonEqual $case.source $expectedSource) -or
            $case.generation_context.version -cne "record-inline-evidence-v1" -or
            $case.generation_context.user_packet_sha256 -cne $userHashes[$index] -or
            $case.generation_context.source_units_sha256 -cne $sourceUnitHashes[$index] -or
            -not (Test-JsonEqual $case.generation_context.source_units $sourceCase.source_units) -or
            -not (Test-JsonEqual $case.generation_context.budget $expectedBudget)) { throw "Incoherent ordered source case." }
        $expectedRequests += [pscustomobject]@{case_id=$caseIds[$index]; body_sha256=$bodyHashes[$index]; user_packet_sha256=$userHashes[$index]}
    }
    $dossier = $inputs.dossier
    if ($dossier.file -cne "evals/narrator/reports/record-summary-color-dossier-95dd9fd2-2026-09-07.json" -or
        $dossier.sha256 -cne "d998a881504ac935a7a4a5ca248afa33b2a78c966668af3e52a0fcacd1a44915" -or
        $dossier.sha256 -cne (Get-FileHash -LiteralPath (Join-Path $projectRoot $dossier.file) -Algorithm SHA256).Hash.ToLowerInvariant() -or
        -not (Test-JsonEqual $dossier.requests $expectedRequests)) { throw "Incoherent ordered request dossier." }
    $dossierDocument = Get-Content -Raw -LiteralPath (Join-Path $projectRoot $dossier.file) | ConvertFrom-Json
    if (-not (Test-JsonEqual $inputs.stopping_policy $dossierDocument.stopping_policy)) { throw "Incoherent stopping policy." }
    if ($inputs.PSObject.Properties.Name -contains "projection_policy") { throw "Unexpected projection policy." }
    $expectedMeasurement = '{"method":"unicode_words_with_internal_hyphen_or_apostrophe","pattern":"[^\\W_]+(?:[-\u2019''][^\\W_]+)*","max_words":25,"changes_exit_code":false,"semantic_validation":false}' | ConvertFrom-Json
    if (-not (Test-JsonEqual $inputs.measurement_policy $expectedMeasurement)) { throw "Incoherent measurement policy." }
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
Write-Host "Summary color Qwen probe batch: $batchId"
Write-Host "Two authored synthetic cases in fixed A-B order; at most two Qwen summary calls, 768 tokens each and 1536 total, reasoning effort none, temperature 0.65."
Write-Host "Initial and inter-call wait: at least 60 seconds; then a 60-second deadline per call. Stop on operational failure; remaining cases are skipped. No retries or fallback."
Write-Host "Only summary text is requested; word measurement does not evaluate semantic fidelity or change the operational exit code."
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
            Write-Host "Summary color Qwen probe cancelled with partial local evidence; files were preserved but no complete summary could be verified."
            throw "Incomplete cancellation evidence."
        }
        Write-Host "Summary color Qwen probe cancelled; no completed summary was produced."
        exit 130
    }
    if ($newSummaries.Count -ne 1) { throw "Expected exactly one new summary." }
    $summaryPath = $newSummaries[0].FullName
    $document = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
    Assert-FixedScope $document
    if ($document.batch_id -cne $batchId -or
        ($document.process_exit_code -isnot [int] -and $document.process_exit_code -isnot [long]) -or
        $document.process_exit_code -ne $exitCode) { throw "Incoherent invocation provenance." }
    $expectedEvaluationStatus = if ($exitCode -in @(0, 1, 2)) { "completed" }
        elseif ($exitCode -eq 3) { "local_error" }
        else { "cancelled" }
    if ($document.evaluation_status -isnot [string] -or
        $document.evaluation_status -cne $expectedEvaluationStatus) { throw "Incoherent evaluation status." }
    foreach ($field in @("inputs", "evaluator", "summary_generation_parameters", "candidate_policy")) {
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
    foreach ($field in @("semantic_fidelity_review")) {
        if (-not (Test-JsonEqual $summary.$field $expectedReview)) { throw "Incoherent semantic review scope." }
    }
    if (($summary.process_exit_code -isnot [int] -and $summary.process_exit_code -isnot [long]) -or
        $summary.process_exit_code -ne $exitCode) { throw "Incoherent summary exit status." }
    foreach ($field in @("calls_made", "schema_valid", "cases_skipped")) {
        $value = $summary.$field
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt 2) { throw "Incoherent call count." }
    }
    if (($exitCode -in @(1, 2) -and $summary.calls_made -eq 0) -or
        $summary.calls_made + $summary.cases_skipped -ne 2 -or
        $summary.schema_valid -gt $summary.calls_made -or
        $summary.operational_probe_passed -isnot [bool] -or $summary.operational_probe_passed -ne ($exitCode -eq 0)) { throw "Incoherent operational result." }
    if ($summary.provider_observations -isnot [array] -or
        @($summary.provider_observations).Count -ne $summary.calls_made) { throw "Incoherent provider observations." }
    for ($index = 0; $index -lt $summary.calls_made; $index++) {
        $entry = @($summary.provider_observations)[$index]
        if ($entry.observation -isnot [System.Management.Automation.PSCustomObject]) { throw "Incoherent provider observation." }
        $expectedObservation = @{case_id=$caseIds[$index]; observation=$entry.observation} | ConvertTo-Json -Depth 20 | ConvertFrom-Json
        if (-not (Test-JsonEqual $entry $expectedObservation)) { throw "Incoherent observation case order." }
    }
    if ($summary.calls_made -eq 1) {
        $singleObservation = @($summary.provider_observations)[0].observation
        if (-not (Test-JsonEqual $summary.provider_observation $singleObservation)) { throw "Incoherent singular provider observation." }
    }
    elseif ($null -ne $summary.provider_observation) { throw "Incoherent singular provider observation." }
    $route = $summary.route_verification
    foreach ($field in @("calls_made", "verified_calls", "unavailable_calls", "mismatched_calls")) {
        $value = $route.$field
        if (($value -isnot [int] -and $value -isnot [long]) -or $value -lt 0 -or $value -gt 2) { throw "Incoherent route count." }
    }
    if ($route.calls_made -ne $summary.calls_made -or
        $route.verified_calls + $route.unavailable_calls + $route.mismatched_calls -ne $route.calls_made) { throw "Incoherent route evidence." }
    if ($summary.PSObject.Properties.Name -contains "instruction_measurements" -or
        $summary.case_measurements -isnot [array] -or @($summary.case_measurements).Count -ne 2) { throw "Incoherent per-case measurements." }
    $measuredCases = 0
    for ($index = 0; $index -lt 2; $index++) {
        $entry = @($summary.case_measurements)[$index]
        $measurement = $entry.instruction_measurements
        $expectedEntry = @{case_id=$caseIds[$index]; instruction_measurements=$measurement} | ConvertTo-Json -Depth 10 | ConvertFrom-Json
        if (-not (Test-JsonEqual $entry $expectedEntry)) { throw "Incoherent measurement case order." }
        if ($null -ne $measurement) {
            if ($index -ge $summary.calls_made -or
                $measurement -isnot [System.Management.Automation.PSCustomObject] -or
                ($measurement.word_count -isnot [int] -and $measurement.word_count -isnot [long]) -or
                $measurement.word_count -lt 0 -or $measurement.word_count -gt 600) { throw "Incoherent instruction measurement." }
            $expectedMeasurement = @{
                method=$preflight.inputs.measurement_policy.method; pattern=$preflight.inputs.measurement_policy.pattern
                word_count=$measurement.word_count; max_words=25; within_word_limit=($measurement.word_count -le 25)
                semantic_fidelity_evaluated=$false
            } | ConvertTo-Json | ConvertFrom-Json
            if (-not (Test-JsonEqual $measurement $expectedMeasurement)) { throw "Incoherent instruction measurement." }
            $measuredCases++
        }
    }
    if ($measuredCases -gt $summary.schema_valid -or $measuredCases -gt $route.verified_calls -or
        ($summary.calls_made -eq 2 -and $null -eq @($summary.case_measurements)[0].instruction_measurements)) { throw "Incoherent measurement stage." }
    if ($summary.transport_and_schema_passed -isnot [bool] -or
        $summary.transport_and_schema_passed -ne ($exitCode -eq 0)) { throw "Incoherent transport and schema result." }
    if ($exitCode -eq 0 -and $measuredCases -ne 2) { throw "Missing successful instruction measurements." }
    if ($exitCode -eq 0) {
        if ($summary.calls_made -ne 2 -or $summary.schema_valid -ne 2 -or
            $route.status -cne "verified" -or $route.verified_calls -ne 2 -or
            $route.unavailable_calls -ne 0 -or $route.mismatched_calls -ne 0 -or
            $route.identity_consistent -isnot [bool] -or $route.identity_consistent -ne $true) { throw "Incoherent successful observation." }
    }
    Write-Host "Summary: $summaryPath"
}
catch {
    # Never echo child output, exception payloads, credentials or generated prose.
    Write-Host "Summary color Qwen probe stopped because execution or evidence verification failed ($failureStage)."
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
Write-Host "Summary color Qwen probe ended with exit code $exitCode; narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
