[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [System.Security.SecureString] $ApiKey,

    [ValidateRange(0, 300)]
    [double] $InterCallDelaySeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot "scripts\evaluate_narrator_models.py"
$manifest = Join-Path $projectRoot "evals\narrator\openrouter_chinese_candidates_2026-09-04.json"
$candidates = @(
    "deepseek-v4-flash-0731-deepinfra-zdr-nonthink",
    "glm-5.2-free-decarts-zdr-nonthink"
)

foreach ($requiredPath in @($python, $evaluator, $manifest)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required evaluation file was not found: $requiredPath"
    }
}

$plainTextKey = $null
$exitCodes = [ordered] @{}
$batchId = [guid]::NewGuid().ToString("D").ToLowerInvariant()
$nativeCommandPreferenceExists = Test-Path Variable:PSNativeCommandUseErrorActionPreference
$previousNativeCommandPreference = $null
if ($nativeCommandPreferenceExists) {
    $previousNativeCommandPreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}
Write-Host "Evaluation batch: $batchId"
try {
    $plainTextKey = [System.Net.NetworkCredential]::new("", $ApiKey).Password
    if ([string]::IsNullOrWhiteSpace($plainTextKey)) {
        throw "The supplied OpenRouter API key is blank."
    }
    $env:OPENROUTER_API_KEY = $plainTextKey

    for ($index = 0; $index -lt $candidates.Count; $index++) {
        $candidate = $candidates[$index]
        Write-Host "Starting live screening: $candidate"
        & $python $evaluator `
            --live `
            --manifest $manifest `
            --candidate $candidate `
            --batch-id $batchId `
            --api-key-env OPENROUTER_API_KEY `
            --repetitions 1 `
            --deadline-seconds 60 `
            --inter-call-delay-seconds $InterCallDelaySeconds `
            --diagnostic-rate-limit-retry-delay-seconds 15 `
            --diagnostic-rate-limit-retry-cap-seconds 30 `
            --temperature 0.65 `
            --max-output-tokens 2048
        $exitCode = $LASTEXITCODE
        $exitCodes[$candidate] = $exitCode
        Write-Host "Finished $candidate with evaluator exit code $exitCode"
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
            $candidateCooldownSeconds = [Math]::Max($InterCallDelaySeconds, 30.0)
            Write-Host (
                "Provider cooldown: waiting {0:N1}s before the next candidate" -f `
                    $candidateCooldownSeconds
            )
            Start-Sleep -Seconds ([int][Math]::Ceiling($candidateCooldownSeconds))
        }
    }
}
finally {
    Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
    $plainTextKey = $null
    if ($nativeCommandPreferenceExists) {
        $PSNativeCommandUseErrorActionPreference = $previousNativeCommandPreference
    }
}

$summaryTable = $exitCodes.GetEnumerator() | Format-Table -AutoSize | Out-String
Write-Host $summaryTable.TrimEnd()
$unexpectedExitCodes = @(
    $exitCodes.Values | Where-Object {
        $null -eq $_ -or $_ -notin @(0, 1, 2, 3, 130)
    }
)
if ($unexpectedExitCodes.Count -gt 0) {
    Write-Host "Screening stopped: evaluator returned an unexpected exit code."
    exit 3
}
if ($exitCodes.Values -contains 3) {
    Write-Host "Screening stopped: evaluator internal error. Inspect the summary path above."
    exit 3
}
if ($exitCodes.Values -contains 130) {
    Write-Host "Screening cancelled by user; no later candidate was started."
    exit 130
}
if ($exitCodes.Values -contains 2) {
    Write-Host "Screening stopped: provider availability prevented a complete run. Inspect the summary path above."
    exit 2
}
if ($exitCodes.Values -contains 1) {
    Write-Host "Screening completed with failed gates. Inspect the summary path above."
    exit 1
}

Write-Host "Both live screenings passed automated gates; human review remains."
