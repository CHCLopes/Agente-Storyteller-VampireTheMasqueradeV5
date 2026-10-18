[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialName = 'STORYTELLER_OPENROUTER_FREE_KEY'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'scripts\evaluate_openrouter_free_narrators_l2_live.py'
$preflightDirectory = Join-Path $projectRoot 'eval-results\preflights'
$finalExit = 3

try {
    New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null
    $batchId = [guid]::NewGuid().ToString()
    $preflightPath = Join-Path $preflightDirectory "openrouter-free-narrators-l2-$batchId.json"
    $summaryPath = Join-Path $projectRoot "eval-results\openrouter-free-narrators-l2-$batchId\summary.json"
    $preflightLines = & $pythonPath $runnerPath --preflight
    if ($LASTEXITCODE -ne 0) { throw 'preflight_failed' }
    Set-Content -LiteralPath $preflightPath -Value $preflightLines -Encoding utf8NoBOM
    $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
    if (
        $preflight.hypothesis_id -ne 'HYP-005-OPENROUTER-FREE-L2-OUTPUT-BUDGET' -or
        $preflight.provider_calls -ne 0 -or
        $preflight.credential_inspected -ne $false -or
        $preflight.schedule.Count -ne 24 -or
        $preflight.max_calls -ne 24 -or
        $preflight.single_changed_variable.name -ne 'max_output_tokens' -or
        $preflight.single_changed_variable.from -ne 768 -or
        $preflight.single_changed_variable.to -ne 2048 -or
        $preflight.generation_parameters.max_output_tokens -ne 2048 -or
        $preflight.generation_parameters.max_total_output_tokens -ne 49152 -or
        $preflight.automatic_retries -ne 0 -or
        $preflight.repair -ne $false -or
        $preflight.model_fallback -ne $false -or
        $preflight.provider_fallback -ne $false -or
        $preflight.paid_spend_authorized -ne $false -or
        $preflight.zero_cost_must_be_reported_per_response -ne $true -or
        $preflight.synthetic_only -ne $true
    ) { throw 'preflight_contract_invalid' }

    Write-Host 'Confirme no catalogo OpenRouter que os tres slugs :free permanecem com entrada e saida a USD 0.' -ForegroundColor Yellow
    Write-Host 'L2-B altera somente max_output_tokens: 768 para 2048; todos os demais gates permanecem.' -ForegroundColor Yellow
    Write-Host 'A bateria usa apenas fixtures sinteticas, sem dados pessoais, campanha ou lore privado.' -ForegroundColor Yellow
    Write-Host 'Qualquer custo diferente de zero interrompe o lote; nao ha retry nem fallback.' -ForegroundColor Yellow
    $secureTierConfirmation = Read-Host 'Digite FREE para confirmar custo zero' -AsSecureString
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
    Write-Host 'Iniciando HYP-005 L2-B OpenRouter gratuito: no maximo 24 chamadas.' -ForegroundColor Green
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
    Write-Error 'O HYP-005 L2-B OpenRouter foi interrompido por falha local segura.' -ErrorAction Continue
    $finalExit = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable tierConfirmation -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
}
exit $finalExit

