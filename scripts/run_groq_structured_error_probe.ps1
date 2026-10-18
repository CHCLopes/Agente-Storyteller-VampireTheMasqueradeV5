[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [System.Security.SecureString] $ApiKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_models.py"
$manifest = Join-Path $projectRoot "evals\narrator\groq_candidates_2026-09-05.json"
$corpus = Join-Path $projectRoot "evals\narrator\corpus_v1.json"
$prompt = Join-Path $projectRoot "evals\narrator\prompts\scene-faithful-v1.md"
$adapter = Join-Path $projectRoot "api\llm\adapters\groq.py"
$outputRoot = Join-Path $projectRoot "eval-results"
$candidateId = "gpt-oss-120b-groq-free-synthetic-low"
$variant = "scene-faithful-v1"
$promptHash = "76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2"
foreach ($requiredPath in @($python, $evaluator, $manifest, $corpus, $prompt, $adapter)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        Write-Host "Required structured probe file was not found: $requiredPath"
        exit 3
    }
}
$adapterHash = (Get-FileHash -LiteralPath $adapter -Algorithm SHA256).Hash.ToLowerInvariant()
$evaluatorHash = (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()
$manifestHash = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
$corpusHash = (Get-FileHash -LiteralPath $corpus -Algorithm SHA256).Hash.ToLowerInvariant()
$batchId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
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
$failed = $false
$failureStage = "credential validation"
Write-Host "Structured error probe batch: $batchId"
Write-Host "One fixed synthetic faithful opening for $candidateId; 768 tokens, temperature 0.65, deadline 60 seconds."
Write-Host "No text/streaming diagnostics, retries, fallback, baseline or other turn."
Write-Host "This operational error observation never approves narrative quality, runtime or CAP-001."
try {
    $plainTextKey = [System.Net.NetworkCredential]::new("", $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) { throw "Blank credential." }
    $env:GROQ_API_KEY = $plainTextKey
    $failureStage = "child invocation"
    $previousSummaryPaths = @(
        Get-ChildItem -LiteralPath $outputRoot -Filter "summary.json" -File -Recurse -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName }
    )
    $global:LASTEXITCODE = $null
    & $python $evaluator `
        --live `
        --structured-error-probe `
        --manifest $manifest `
        --corpus $corpus `
        --candidate $candidateId `
        --prompt-variant $variant `
        --batch-id $batchId `
        --api-key-env GROQ_API_KEY `
        --allow-synthetic-only `
        --repetitions 1 `
        --deadline-seconds 60 `
        --temperature 0.65 `
        --max-output-tokens 768
    $invocationSucceeded = $?
    $exitCode = $global:LASTEXITCODE
    if ($null -eq $exitCode -or $exitCode -notin @(0, 1, 2, 3, 130) -or
        ($exitCode -eq 0 -and -not $invocationSucceeded)) {
        throw "No usable child exit status."
    }
    $failureStage = "summary verification"
    $availableSummaries = @(
        Get-ChildItem -LiteralPath $outputRoot -Filter "summary.json" -File -Recurse -ErrorAction SilentlyContinue
    )
    $matchingSummaries = @(
        $availableSummaries | Where-Object {
            try {
                $document = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json
                $document.batch_id -eq $batchId -and $document.selected_candidate_id -eq $candidateId
            }
            catch { $false }
        }
    )
    $newSummaries = @($availableSummaries | Where-Object { $_.FullName -notin $previousSummaryPaths })
    if ($exitCode -eq 130 -and $matchingSummaries.Count -eq 0 -and $newSummaries.Count -eq 0) {
        Write-Host "Structured error probe cancelled; no completed summary was produced."
        # PowerShell still runs finally, restoring the credential and native preference.
        exit 130
    }
    if ($matchingSummaries.Count -ne 1) { throw "Expected exactly one matching summary." }
    $matchingSummary = $matchingSummaries[0]
    $document = Get-Content -Raw -LiteralPath $matchingSummary.FullName | ConvertFrom-Json
    if ($document.process_exit_code -ne $exitCode -or
        $document.purpose -ne "operational_probe" -or $document.probe_kind -ne "structured_error_probe" -or
        $document.full_evaluation -isnot [bool] -or $document.full_evaluation -ne $false -or
        $document.runtime_promoted -isnot [bool] -or $document.runtime_promoted -ne $false -or
        $document.human_review_required -isnot [bool] -or $document.human_review_required -ne $true -or
        $document.synthetic_only -isnot [bool] -or $document.synthetic_only -ne $true -or
        $document.cap_001_status -ne "not_evaluated" -or $document.repetitions -ne 1 -or
        $document.diagnostics_executed -isnot [bool] -or $document.diagnostics_executed -ne $false -or
        $document.automatic_retries -ne 0 -or
        $document.inputs.prompt.variant -ne $variant -or
        $document.inputs.prompt.file -ne "evals/narrator/prompts/$variant.md" -or
        $document.inputs.prompt.sha256 -ne $promptHash -or
        $document.inputs.manifest.file -ne "groq_candidates_2026-09-05.json" -or
        $document.inputs.manifest.sha256 -ne $manifestHash -or
        $document.inputs.corpus.file -ne "corpus_v1.json" -or
        $document.inputs.corpus.sha256 -ne $corpusHash -or
        $document.inputs.structured_error_probe_adapter.file -ne "api/llm/adapters/groq.py" -or
        $document.inputs.structured_error_probe_adapter.sha256 -ne $adapterHash -or
        $document.evaluator.file -ne "scripts/evaluate_narrator_models.py" -or
        $document.evaluator.sha256 -ne $evaluatorHash) {
        throw "Incoherent operational scope or provenance."
    }
    $experiment = $document.inputs.scene_focus_experiment
    if ($experiment.version -ne $variant -or
        $experiment.context_contract_version -ne "scene-focus-v1" -or
        $experiment.baseline_prompt_variant -ne "scene-attributed-v1" -or
        @($experiment.interventions).Count -ne 1 -or @($experiment.interventions)[0] -ne "system_prompt" -or
        $experiment.causal_comparison -isnot [bool] -or $experiment.causal_comparison -ne $false -or
        $experiment.complete_ab_experiment -isnot [bool] -or $experiment.complete_ab_experiment -ne $false -or
        $experiment.runtime_promoted -isnot [bool] -or $experiment.runtime_promoted -ne $false -or
        $experiment.human_review_required -isnot [bool] -or $experiment.human_review_required -ne $true -or
        $experiment.response_schema_sha256 -ne "bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2") {
        throw "Incoherent focused contract metadata."
    }
    $parameters = $document.narrative_generation_parameters
    foreach ($kind in @("requested", "transmitted")) {
        if ($parameters.$kind.max_output_tokens -ne 768 -or $parameters.$kind.temperature -ne 0.65) {
            throw "Incoherent generation parameters."
        }
    }
    $retry = $document.evaluation_pacing.diagnostic_rate_limit_retry
    if ($parameters.deadline_seconds -ne 60 -or
        $retry.enabled -isnot [bool] -or $retry.enabled -ne $false -or $retry.maximum_attempts_per_probe -ne 0) {
        throw "Incoherent probe limits."
    }
    if ($exitCode -in @(0, 1, 2)) {
        $summary = $document.summary
        if ($summary.purpose -ne "operational_probe" -or $summary.probe_kind -ne "structured_error_probe" -or
            $summary.evaluation_stage -ne "structured_error_probe" -or $summary.narrative_calls -ne 1 -or
            $summary.automated_gates_passed -isnot [bool] -or $summary.automated_gates_passed -ne $false -or
            $summary.operational_probe_passed -isnot [bool] -or
            $summary.operational_probe_passed -ne ($exitCode -eq 0)) {
            throw "Incoherent operational result."
        }
    }
    Write-Host "Summary: $($matchingSummary.FullName)"
}
catch {
    # Never echo credentials, child exception payloads or generated prose.
    Write-Host "Structured error probe stopped because execution or evidence verification failed ($failureStage)."
    $failed = $true
}
finally {
    if ($groqApiKeyExisted) { $env:GROQ_API_KEY = $previousGroqApiKey }
    else { Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue }
    $plainTextKey = $null
    $previousGroqApiKey = $null
    if ($nativeCommandPreferenceExists) { $PSNativeCommandUseErrorActionPreference = $previousNativeCommandPreference }
}
if ($failed) { exit 3 }
Write-Host "Structured error probe ended with exit code $exitCode; narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
