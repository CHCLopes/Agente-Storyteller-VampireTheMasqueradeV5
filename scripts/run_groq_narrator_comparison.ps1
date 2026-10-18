[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [System.Security.SecureString] $ApiKey,

    [ValidateRange(0, 300)]
    [double] $InterCallDelaySeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_models.py"
$manifest = Join-Path $projectRoot "evals\narrator\groq_candidates_2026-09-05.json"
$outputRoot = Join-Path $projectRoot "eval-results"
$candidates = @(
    "qwen-3.8-27b-groq-free-synthetic-nonthink",
    "gpt-oss-120b-groq-free-synthetic-low"
)

foreach ($requiredPath in @($python, $evaluator, $manifest)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required evaluation file was not found: $requiredPath"
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
$exitCodes = [ordered] @{}
$summaryPaths = [ordered] @{}
$batchId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
$nativeCommandPreferenceExists = Test-Path Variable:PSNativeCommandUseErrorActionPreference
$previousNativeCommandPreference = $null
if ($nativeCommandPreferenceExists) {
    $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}

Write-Host "Evaluation batch: $batchId"
Write-Host "Narrative output ceiling: 768 tokens per call (same budget for both candidates)."
try {
    $plainTextKey = [System.Net.NetworkCredential]::new("", $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) {
        throw "The supplied Groq API key is blank."
    }
    $env:GROQ_API_KEY = $plainTextKey

    for ($index = 0; $index -lt $candidates.Count; $index++) {
        $candidate = $candidates[$index]
        Write-Host "Starting live screening: $candidate"
        & $python $evaluator `
            --live `
            --manifest $manifest `
            --candidate $candidate `
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
        $exitCode = $LASTEXITCODE
        $exitCodes[$candidate] = $exitCode

        $matchingSummary = Get-ChildItem -LiteralPath $outputRoot `
            -Filter "summary.json" -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTimeUtc -Descending |
            Where-Object {
                try {
                    $document = Get-Content -Raw -LiteralPath $_.FullName |
                        ConvertFrom-Json
                    $document.batch_id -eq $batchId -and
                        $document.selected_candidate_id -eq $candidate
                }
                catch {
                    $false
                }
            } |
            Select-Object -First 1
        if ($null -eq $matchingSummary) {
            throw "Evaluator returned without a matching summary for $candidate."
        }
        $summaryPaths[$candidate] = $matchingSummary.FullName

        Write-Host "Finished $candidate with evaluator exit code $exitCode"
        Write-Host "Summary: $($matchingSummary.FullName)"
        if ($exitCode -eq 130) {
            Write-Host "Batch cancelled by user."
            break
        }
        if ($null -eq $exitCode -or $exitCode -notin @(0, 1, 2, 3, 130)) {
            Write-Host "Batch stopped: evaluator returned an unexpected exit code."
            break
        }
        if ($exitCode -in @(2, 3)) {
            Write-Host "Batch stopped to avoid contaminating the next candidate."
            break
        }
        if ($index -lt ($candidates.Count - 1)) {
            $candidateCooldownSeconds = [Math]::Max(
                $InterCallDelaySeconds,
                60.0
            )
            Write-Host (
                "Provider cooldown: waiting {0:N1}s before the next candidate" -f `
                    $candidateCooldownSeconds
            )
            Start-Sleep -Seconds ([int][Math]::Ceiling($candidateCooldownSeconds))
        }
    }
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

$summaryTable = $exitCodes.GetEnumerator() | Format-Table -AutoSize | Out-String
Write-Host $summaryTable.TrimEnd()
foreach ($candidate in $summaryPaths.Keys) {
    Write-Host "$candidate -> $($summaryPaths[$candidate])"
}

$unexpectedExitCodes = @(
    $exitCodes.Values | Where-Object {
        $null -eq $_ -or $_ -notin @(0, 1, 2, 3, 130)
    }
)
if ($unexpectedExitCodes.Count -gt 0) {
    Write-Host "Screening stopped: evaluator returned an unexpected exit code."
    exit 3
}
if ($exitCodes.Values -contains 130) {
    exit 130
}
if ($exitCodes.Values -contains 2) {
    Write-Host "Screening stopped before completion during diagnostics or narratives. Inspect the summary path above for the failure stage and cause."
    exit 2
}
if ($exitCodes.Values -contains 3) {
    Write-Host "Screening stopped: evaluator failed internally. Inspect the summary path above."
    exit 3
}
if ($exitCodes.Values -contains 1) {
    Write-Host "Screening completed, but at least one candidate failed automated gates."
    exit 1
}

Write-Host "All screened candidates passed the automated screening gates."
exit 0
