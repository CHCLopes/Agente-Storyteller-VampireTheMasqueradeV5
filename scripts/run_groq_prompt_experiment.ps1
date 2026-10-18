[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [System.Security.SecureString] $ApiKey,

    [ValidateSet(
        "qwen-3.8-27b-groq-free-synthetic-nonthink",
        "gpt-oss-120b-groq-free-synthetic-low"
    )]
    [string] $Candidate = "gpt-oss-120b-groq-free-synthetic-low",

    [ValidateSet("ControlFirst", "VariantFirst")]
    [string] $Order = "ControlFirst",

    [switch] $VariantOnly,

    [switch] $FocusOnly,

    [switch] $GroundedOnly,

    [switch] $AttributedOnly,

    [switch] $FaithfulOnly,

    [ValidateRange(60, 300)]
    [double] $InterCallDelaySeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($FaithfulOnly -and ($AttributedOnly -or $GroundedOnly -or $FocusOnly -or $VariantOnly)) {
    Write-Host "FaithfulOnly, AttributedOnly, GroundedOnly, FocusOnly and VariantOnly are mutually exclusive. No evaluation was started."
    exit 3
}
if ($FaithfulOnly -and $Candidate -ne "gpt-oss-120b-groq-free-synthetic-low") {
    Write-Host "FaithfulOnly requires gpt-oss-120b-groq-free-synthetic-low. No evaluation was started."
    exit 3
}
if ($AttributedOnly -and ($GroundedOnly -or $FocusOnly -or $VariantOnly)) {
    Write-Host "AttributedOnly, GroundedOnly, FocusOnly and VariantOnly are mutually exclusive. No evaluation was started."
    exit 3
}
if ($AttributedOnly -and $Candidate -ne "gpt-oss-120b-groq-free-synthetic-low") {
    Write-Host "AttributedOnly requires gpt-oss-120b-groq-free-synthetic-low. No evaluation was started."
    exit 3
}
if (($VariantOnly -and $FocusOnly) -or ($GroundedOnly -and ($VariantOnly -or $FocusOnly))) {
    Write-Host "GroundedOnly, FocusOnly and VariantOnly are mutually exclusive. No evaluation was started."
    exit 3
}
if ($GroundedOnly -and $Candidate -ne "gpt-oss-120b-groq-free-synthetic-low") {
    Write-Host "GroundedOnly requires gpt-oss-120b-groq-free-synthetic-low. No evaluation was started."
    exit 3
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_models.py"
$manifest = Join-Path $projectRoot "evals\narrator\groq_candidates_2026-09-05.json"
$outputRoot = Join-Path $projectRoot "eval-results"
$variants = @("h6-control-v1", "scene-beat-v1")
if ($FaithfulOnly) {
    $variants = @("scene-faithful-v1")
}
elseif ($AttributedOnly) {
    $variants = @("scene-attributed-v1")
}
elseif ($GroundedOnly) {
    $variants = @("scene-grounded-v1")
}
elseif ($FocusOnly) {
    $variants = @("scene-focus-v1")
}
elseif ($VariantOnly) {
    # A separate observation, not an automatic resume or a completed A/B batch.
    # Earlier control reports remain untouched and must be compared explicitly.
    $variants = @("scene-beat-v1")
}
elseif ($Order -eq "VariantFirst") {
    [array]::Reverse($variants)
}

$promptPaths = if ($FaithfulOnly) {
    @(Join-Path $projectRoot "evals\narrator\prompts\scene-faithful-v1.md")
}
elseif ($AttributedOnly) {
    @(Join-Path $projectRoot "evals\narrator\prompts\scene-attributed-v1.md")
}
elseif ($GroundedOnly) {
    @(Join-Path $projectRoot "evals\narrator\prompts\scene-grounded-v1.md")
}
elseif ($FocusOnly) {
    @(Join-Path $projectRoot "evals\narrator\prompts\scene-focus-v1.md")
}
else {
    @(
        Join-Path $projectRoot "evals\narrator\prompts\h6-control-v1.md"
        Join-Path $projectRoot "evals\narrator\prompts\scene-beat-v1.md"
    )
}
foreach ($requiredPath in (@($python, $evaluator, $manifest) + $promptPaths)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        Write-Host "Required evaluation file was not found: $requiredPath"
        exit 3
    }
}

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
$exitCodes = [ordered] @{}
$summaryPaths = [ordered] @{}
$batchId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
$executionFailed = $false
$failureStage = "credential validation"

Write-Host "Prompt experiment batch: $batchId"
if ($FaithfulOnly) {
    Write-Host "SYSTEM-only observation: scene-faithful-v1 relative to scene-attributed-v1; candidate: $Candidate."
    Write-Host "Same scene-focus-v1 USER packet and actor contract/schema, validators, corpus and parameters; only the SYSTEM prompt changes."
    Write-Host "New batch; no baseline or other arm is run or imported. This is not a complete A/B experiment or a causal A/B conclusion."
    Write-Host "Synthetic data only; at most 9 normal calls plus 2 bounded diagnostic retries."
}
elseif ($AttributedOnly) {
    Write-Host "SYSTEM-only observation: scene-attributed-v1 relative to scene-grounded-v1; candidate: $Candidate."
    Write-Host "Same scene-focus-v1 USER packet and actor contract/schema, validators, corpus and parameters; only the SYSTEM prompt changes."
    Write-Host "New batch; no baseline or other arm is run or imported. This is not a complete A/B experiment or a causal A/B conclusion."
    Write-Host "Synthetic data only; at most 9 normal calls plus 2 bounded diagnostic retries."
}
elseif ($GroundedOnly) {
    Write-Host "SYSTEM-only observation: scene-grounded-v1 relative to scene-focus-v1; candidate: $Candidate."
    Write-Host "Same scene-focus-v1 context organization and actor contract/schema; only the SYSTEM prompt changes."
    Write-Host "New batch; no control is run or imported. This is not a complete A/B experiment or a causal A/B conclusion."
    Write-Host "Synthetic data only; at most 9 normal calls plus 2 bounded diagnostic retries."
}
elseif ($FocusOnly) {
    Write-Host "Joint context+actor-contract observation: scene-focus-v1; candidate: $Candidate."
    Write-Host "New batch; no control is run or imported. This is not a complete A/B experiment."
    Write-Host "Context organization and actor contract change together; their effects are not isolated."
    Write-Host "Synthetic data only; at most 9 normal calls plus 2 bounded diagnostic retries."
}
elseif ($VariantOnly) {
    Write-Host "Variant-only observation: scene-beat-v1; candidate: $Candidate."
    Write-Host "New batch; no control is run or imported. This is not a complete A/B experiment."
    Write-Host "Synthetic data only; at most 9 normal calls plus 2 bounded diagnostic retries."
}
else {
    Write-Host "Same candidate in both arms: $Candidate; order: $Order."
    Write-Host "Synthetic data only; at most 18 normal calls plus 4 bounded diagnostic retries."
}
Write-Host "Narrative output: 768 tokens; diagnostics: 128 tokens; temperature: 0.65."
Write-Host "Calls and arms are separated by at least $InterCallDelaySeconds seconds."
Write-Host "No narrative retries or fallback. This experiment does not approve CAP-001."

try {
    $plainTextKey = [System.Net.NetworkCredential]::new("", $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) {
        throw "The supplied Groq API key is blank."
    }
    $env:GROQ_API_KEY = $plainTextKey

    for ($index = 0; $index -lt $variants.Count; $index++) {
        $variant = $variants[$index]
        $failureStage = "invocation for $variant"
        Write-Host "Starting prompt arm: $variant"
        # Native processes update the global automatic variable. A local reset
        # would shadow that value and make a real Python exit look like null.
        # Clear and read the same scope so stale terminal state cannot be used.
        $global:LASTEXITCODE = $null
        & $python $evaluator `
            --live `
            --manifest $manifest `
            --candidate $Candidate `
            --prompt-variant $variant `
            --batch-id $batchId `
            --api-key-env GROQ_API_KEY `
            --allow-synthetic-only `
            --repetitions 1 `
            --deadline-seconds 60 `
            --inter-call-delay-seconds $InterCallDelaySeconds `
            --diagnostic-rate-limit-retry-delay-seconds 15 `
            --diagnostic-rate-limit-retry-cap-seconds 30 `
            --temperature 0.65 `
            --max-output-tokens 768
        $invocationSucceeded = $?
        $exitCode = $global:LASTEXITCODE
        $exitCodes[$variant] = $exitCode
        if ($null -eq $exitCode -or $exitCode -notin @(0, 1, 2, 3, 130) -or
            ($exitCode -eq 0 -and -not $invocationSucceeded)) {
            throw "Evaluator returned no usable exit status."
        }

        $failureStage = "summary verification for $variant"
        $matchingSummaries = @(
            Get-ChildItem -LiteralPath $outputRoot `
                -Filter "summary.json" -File -Recurse -ErrorAction SilentlyContinue |
                Where-Object {
                    try {
                        $document = Get-Content -Raw -LiteralPath $_.FullName |
                            ConvertFrom-Json
                        $document.batch_id -eq $batchId -and
                            $document.selected_candidate_id -eq $Candidate -and
                            $document.inputs.prompt.variant -eq $variant
                    }
                    catch {
                        $false
                    }
                }
        )
        if ($matchingSummaries.Count -eq 0 -and $exitCode -eq 130) {
            Write-Host "Prompt experiment cancelled; no completed summary for this arm."
            break
        }
        if ($matchingSummaries.Count -ne 1) {
            throw "Evaluator did not produce exactly one matching summary."
        }
        $matchingSummary = $matchingSummaries[0]
        $document = Get-Content -Raw -LiteralPath $matchingSummary.FullName | ConvertFrom-Json
        if ($document.process_exit_code -ne $exitCode) {
            throw "The summary exit status does not match the child process."
        }
        if ($document.inputs.prompt.file -ne "evals/narrator/prompts/$variant.md" -or
            $document.inputs.prompt.sha256 -notmatch '^[a-fA-F0-9]{64}$') {
            throw "The summary is missing prompt provenance."
        }
        if ($FaithfulOnly -or $AttributedOnly) {
            $expectedBaseline = if ($FaithfulOnly) { "scene-attributed-v1" } else { "scene-grounded-v1" }
            $experiment = $document.inputs.scene_focus_experiment
            if ($experiment.version -ne $variant -or
                $experiment.baseline_prompt_variant -ne $expectedBaseline -or
                $experiment.context_contract_version -ne "scene-focus-v1" -or
                @($experiment.interventions).Count -ne 1 -or
                @($experiment.interventions)[0] -ne "system_prompt" -or
                $experiment.causal_comparison -isnot [bool] -or $experiment.causal_comparison -ne $false -or
                $experiment.complete_ab_experiment -isnot [bool] -or $experiment.complete_ab_experiment -ne $false -or
                $experiment.runtime_promoted -isnot [bool] -or $experiment.runtime_promoted -ne $false -or
                $experiment.human_review_required -isnot [bool] -or $experiment.human_review_required -ne $true) {
                if ($FaithfulOnly) {
                    throw "The summary is missing coherent SYSTEM-only fidelity metadata."
                }
                throw "The summary is missing coherent SYSTEM-only attribution metadata."
            }
        }
        $summaryPaths[$variant] = $matchingSummary.FullName
        Write-Host "Finished $variant with evaluator exit code $exitCode"
        Write-Host "Summary: $($matchingSummary.FullName)"
        if ($exitCode -in @(2, 3, 130)) {
            Write-Host "Prompt experiment stopped; the remaining arm was not started."
            break
        }
        # A quality-gate rejection (1) is evidence for the comparison, not a
        # transport failure; the other arm still runs with the same settings.
        if ($index -lt ($variants.Count - 1)) {
            $failureStage = "provider cooldown"
            Write-Host "Provider cooldown: waiting $InterCallDelaySeconds seconds before the next arm."
            Start-Sleep -Seconds ([int][Math]::Ceiling($InterCallDelaySeconds))
        }
    }
}
catch {
    # Do not print raw exception payloads from a child process or credentials.
    Write-Host "Prompt experiment stopped because execution or report verification failed ($failureStage)."
    $executionFailed = $true
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

foreach ($variant in $exitCodes.Keys) {
    Write-Host "$variant -> evaluator exit code $($exitCodes[$variant])"
    if ($summaryPaths.Contains($variant)) {
        Write-Host "Summary: $($summaryPaths[$variant])"
    }
}
if ($executionFailed) {
    exit 3
}
if ($exitCodes.Values -contains 130) {
    exit 130
}
if ($exitCodes.Values -contains 3) {
    exit 3
}
if ($exitCodes.Values -contains 2) {
    exit 2
}
if ($exitCodes.Values -contains 1) {
    if ($FaithfulOnly) {
        Write-Host "Faithful-only SYSTEM observation failed automated gates. Baseline was not run; human review remains required."
    }
    elseif ($AttributedOnly) {
        Write-Host "Attributed-only SYSTEM observation failed automated gates. Baseline was not run; human review remains required."
    }
    elseif ($GroundedOnly) {
        Write-Host "Grounded-only SYSTEM observation failed automated gates. Control was not run; human review remains required."
    }
    elseif ($FocusOnly) {
        Write-Host "Focus-only joint context+actor-contract observation failed automated gates. Control was not run; human review remains required."
    }
    elseif ($VariantOnly) {
        Write-Host "Variant-only observation failed automated gates. Control was not run; human review remains required."
    }
    else {
        Write-Host "Both prompt arms were attempted; at least one failed automated gates. Human review remains required."
    }
    exit 1
}
if ($FaithfulOnly) {
    Write-Host "Faithful-only SYSTEM observation passed automated gates. This is not a causal A/B conclusion, narrative-quality approval, model selection or CAP-001 approval; human review remains required."
}
elseif ($AttributedOnly) {
    Write-Host "Attributed-only SYSTEM observation passed automated gates. This is not a causal A/B conclusion, narrative-quality approval, model selection or CAP-001 approval; human review remains required."
}
elseif ($GroundedOnly) {
    Write-Host "Grounded-only SYSTEM observation passed automated gates. This is not a causal A/B conclusion, narrative-quality approval, model selection or CAP-001 approval; human review remains required."
}
elseif ($FocusOnly) {
    Write-Host "Focus-only joint context+actor-contract observation passed automated gates. This is not a complete A/B experiment, model selection or CAP-001 approval; human review remains required."
}
elseif ($VariantOnly) {
    Write-Host "Variant-only observation passed automated gates. This is not a complete A/B experiment, model selection or CAP-001 approval; human review remains required."
}
else {
    Write-Host "Both prompt arms passed automated gates. This is not model selection or CAP-001 approval; human review remains required."
}
exit 0
