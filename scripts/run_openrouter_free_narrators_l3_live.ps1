[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialName = 'STORYTELLER_OPENROUTER_FREE_KEY'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'scripts\evaluate_openrouter_free_narrators_l3_live.py'
$preflightDirectory = Join-Path $projectRoot 'eval-results\preflights'
$finalExit = 3

try {
    New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null
    $batchId = [guid]::NewGuid().ToString()
    $preflightPath = Join-Path $preflightDirectory "openrouter-free-narrators-l3-$batchId.json"
    $summaryPath = Join-Path $projectRoot "eval-results\openrouter-free-narrators-l3-$batchId\summary.json"
    $preflightLines = & $pythonPath $runnerPath --preflight
    if ($LASTEXITCODE -ne 0) { throw 'preflight_failed' }
    Set-Content -LiteralPath $preflightPath -Value $preflightLines -Encoding utf8NoBOM
    $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
    if (
        $preflight.hypothesis_id -ne 'HYP-005-OPENROUTER-FREE-L3-STRICT-OVERLOAD-RETRY' -or
        $preflight.execution_window -ne 'new_free_daily_window_only' -or
        $preflight.provider_calls -ne 0 -or
        $preflight.credential_inspected -ne $false -or
        $preflight.schedule.Count -ne 24 -or
        $preflight.max_calls -ne 48 -or
        $preflight.single_changed_variable.name -ne 'overload_retry_policy' -or
        $preflight.retry_policy.max_attempts_per_slot -ne 2 -or
        $preflight.retry_policy.category -ne 'provider_unavailable' -or
        $preflight.retry_policy.code -ne 'openrouter_provider_overloaded' -or
        $preflight.retry_policy.retryable_must_be_true -ne $true -or
        $preflight.retry_policy.same_request_body -ne $true -or
        $preflight.retry_policy.same_target -ne $true -or
        $preflight.retry_policy.all_other_errors_retried -ne $false -or
        $preflight.generation_parameters.max_output_tokens -ne 2048 -or
        $preflight.generation_parameters.max_total_output_tokens -ne 98304 -or
        $preflight.automatic_retries -ne 1 -or
        $preflight.repair -ne $false -or
        $preflight.model_fallback -ne $false -or
        $preflight.provider_fallback -ne $false -or
        $preflight.paid_spend_authorized -ne $false -or
        $preflight.zero_cost_must_be_reported_per_response -ne $true -or
        $preflight.synthetic_only -ne $true
    ) { throw 'preflight_contract_invalid' }

    Write-Host 'Execute somente em uma nova janela diaria gratuita do OpenRouter.' -ForegroundColor Yellow
    Write-Host 'Confirme no catalogo que os tres slugs :free permanecem com entrada e saida a USD 0.' -ForegroundColor Yellow
    Write-Host 'L3-B permite uma unica repeticao da mesma requisicao apenas para sobrecarga exata do provedor.' -ForegroundColor Yellow
    Write-Host 'A bateria usa somente fixtures sinteticas; nao ha reparo, fallback ou troca de alvo.' -ForegroundColor Yellow
    Write-Host 'Qualquer custo diferente de zero ou qualquer outro erro encerra o lote sem retry.' -ForegroundColor Yellow
    $secureTierConfirmation = Read-Host 'Digite FREE para confirmar nova janela diaria e custo zero' -AsSecureString
    $tierConfirmation = [System.Net.NetworkCredential]::new('', $secureTierConfirmation).Password
    Remove-Variable secureTierConfirmation -ErrorAction SilentlyContinue
    if ($tierConfirmation -cne 'FREE') { throw 'free_tier_not_confirmed' }

    $secureKey = Read-Host 'OpenRouter API key' -AsSecureString
    $plainKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
    [Environment]::SetEnvironmentVariable($credentialName, $plainKey, 'Process')
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($credentialName, 'Process'))) {
        throw 'credential_missing'
    }

    $preflightHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $preflightPath).Hash.ToLowerInvariant()
    Write-Host "LIVE_BATCH_ID=$batchId" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_SHA256=$preflightHash" -ForegroundColor Cyan
    Write-Host 'Iniciando HYP-005 L3-B: 24 slots, no maximo 48 chamadas gratuitas.' -ForegroundColor Green
    & $pythonPath $runnerPath --live --allow-synthetic-only --batch-id $batchId `
        --expected-preflight $preflightPath --expected-preflight-sha256 $preflightHash
    $liveExit = $LASTEXITCODE

    if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
        & $pythonPath $runnerPath --verify-artifacts $summaryPath --batch-id $batchId `
            --expected-preflight $preflightPath --expected-preflight-sha256 $preflightHash
        $verifyExit = $LASTEXITCODE
    } else {
        $verifyExit = 3
        Write-Error 'O lote nao produziu summary.json.' -ErrorAction Continue
    }
    Write-Host "LIVE_EXIT=$liveExit" -ForegroundColor Cyan
    Write-Host "VERIFY_EXIT=$verifyExit" -ForegroundColor Cyan
    Write-Host "SUMMARY_PATH=$summaryPath" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_PATH=$preflightPath" -ForegroundColor Cyan
    $finalExit = if ($verifyExit -ne 0) { 3 } else { $liveExit }
}
catch {
    Write-Error 'O HYP-005 L3-B foi interrompido por falha local segura.' -ErrorAction Continue
    $finalExit = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable tierConfirmation -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
}
exit $finalExit
