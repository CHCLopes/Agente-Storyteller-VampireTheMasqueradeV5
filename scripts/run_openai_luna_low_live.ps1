[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialName = 'STORYTELLER_OPENAI_LUNA_KEY'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'scripts\evaluate_openai_luna_low_live.py'
$gatePath = Join-Path $projectRoot 'evals\narrator\reports\openai-luna-low-live-gate-2026-09-26.json'
$preflightDirectory = Join-Path $projectRoot 'eval-results\preflights'
$finalExit = 3
$costRunDirectory = $null
$costDispatchPossible = $false
$verifyExit = 3

try {
    $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
    if ($gate.live_inference_authorized -ne $true -or $gate.paid_spend_authorized -ne $true) {
        throw 'paid_live_authorization_missing'
    }
    if ($gate.required_future_authorization.account_spend_limit_required_usd -ne 0.05) {
        throw 'paid_spend_ceiling_drifted'
    }
    New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null
    $batchId = [guid]::NewGuid().ToString()
    $preflightPath = Join-Path $preflightDirectory "openai-luna-low-$batchId.json"
    $summaryPath = Join-Path $projectRoot "eval-results\openai-luna-low-$batchId\summary.json"
    $costRunDirectory = Split-Path -Parent $summaryPath
    $preflightLines = & $pythonPath $runnerPath --preflight
    if ($LASTEXITCODE -ne 0) { throw 'preflight_failed' }
    Set-Content -LiteralPath $preflightPath -Value $preflightLines -Encoding utf8NoBOM
    $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
    if (
        $preflight.hypothesis_id -ne 'HYP-006-OPENAI-LUNA-LOW-L1' -or
        $preflight.live_inference_authorized -ne $true -or
        $preflight.paid_spend_authorized -ne $true -or
        $preflight.max_calls -ne 8 -or
        $preflight.generation_parameters.reasoning_effort -ne 'low' -or
        $preflight.automatic_retries -ne 0 -or
        $preflight.repair -ne $false -or
        $preflight.fallback -ne $false
    ) { throw 'preflight_contract_invalid' }

    $secureConfirmation = Read-Host 'Digite PAID-USD-0.05 para confirmar o teto aprovado' -AsSecureString
    $confirmation = [System.Net.NetworkCredential]::new('', $secureConfirmation).Password
    Remove-Variable secureConfirmation -ErrorAction SilentlyContinue
    if ($confirmation -cne 'PAID-USD-0.05') { throw 'paid_ceiling_not_confirmed' }
    $secureKey = Read-Host 'OpenAI API key' -AsSecureString
    $plainKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
    [Environment]::SetEnvironmentVariable($credentialName, $plainKey, 'Process')
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($credentialName, 'Process'))) {
        throw 'credential_missing'
    }
    $preflightHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $preflightPath).Hash.ToLowerInvariant()
    Write-Host "LIVE_BATCH_ID=$batchId" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_SHA256=$preflightHash" -ForegroundColor Cyan
    $costDispatchPossible = $true
    & $pythonPath $runnerPath --live --allow-synthetic-only --batch-id $batchId `
        --expected-preflight $preflightPath --expected-preflight-sha256 $preflightHash
    $liveExit = $LASTEXITCODE
    if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
        & $pythonPath $runnerPath --verify-artifacts $summaryPath --batch-id $batchId `
            --expected-preflight $preflightPath --expected-preflight-sha256 $preflightHash
        $verifyExit = $LASTEXITCODE
    } else { $verifyExit = 3 }
    Write-Host "LIVE_EXIT=$liveExit" -ForegroundColor Cyan
    Write-Host "VERIFY_EXIT=$verifyExit" -ForegroundColor Cyan
    Write-Host "SUMMARY_PATH=$summaryPath" -ForegroundColor Cyan
    $finalExit = if ($verifyExit -ne 0) { 3 } else { $liveExit }
}
catch {
    Write-Error 'O HYP-006 Luna foi interrompido antes de gasto não autorizado.' -ErrorAction Continue
    $finalExit = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable confirmation -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
    try {
        $costArgs = @()
        if ($null -ne $costRunDirectory) { $costArgs += @('--run-directory', $costRunDirectory) }
        if (-not $costDispatchPossible) { $costArgs += '--no-dispatch' }
        elseif ($verifyExit -eq 0) { $costArgs += '--settled' }
        & $pythonPath (Join-Path $projectRoot 'scripts\report_luna_test_cost.py') @costArgs
        if ($LASTEXITCODE -ne 0) { Write-Host 'CUSTO FINAL LUNA: indisponivel; relatorio nao concluido.' }
    } catch { Write-Host 'CUSTO FINAL LUNA: indisponivel; relatorio nao concluido.' }
}
exit $finalExit
