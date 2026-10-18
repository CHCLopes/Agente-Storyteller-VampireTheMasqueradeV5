[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialName = 'STORYTELLER_SILICONFLOW_FREE_KEY'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'scripts\evaluate_siliconflow_free_chinese_live.py'
$preflightDirectory = Join-Path $projectRoot 'eval-results\preflights'
$finalExit = 3

try {
    New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null
    $batchId = [guid]::NewGuid().ToString()
    $preflightPath = Join-Path $preflightDirectory "siliconflow-free-chinese-$batchId.json"
    $summaryPath = Join-Path $projectRoot "eval-results\siliconflow-free-chinese-$batchId\summary.json"
    $preflightLines = & $pythonPath $runnerPath --preflight
    if ($LASTEXITCODE -ne 0) { throw 'preflight_failed' }
    Set-Content -LiteralPath $preflightPath -Value $preflightLines -Encoding utf8NoBOM
    $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
    if (
        $preflight.hypothesis_id -ne 'HYP-005-SILICONFLOW-FREE-CHINESE-L1' -or
        $preflight.provider_calls -ne 0 -or
        $preflight.credential_inspected -ne $false -or
        $preflight.schedule.Count -ne 24 -or
        $preflight.max_calls -ne 24 -or
        $preflight.automatic_retries -ne 0 -or
        $preflight.repair -ne $false -or
        $preflight.fallback -ne $false -or
        $preflight.paid_spend_authorized -ne $false -or
        $preflight.synthetic_only -ne $true
    ) { throw 'preflight_contract_invalid' }

    Write-Host 'Confirme no painel SiliconFlow que os três modelos permanecem gratuitos.' -ForegroundColor Yellow
    Write-Host 'A bateria contém apenas fixtures sintéticas e não altera o narrador padrão.' -ForegroundColor Yellow
    $secureTierConfirmation = Read-Host 'Digite FREE para confirmar custo zero' -AsSecureString
    $tierConfirmation = [System.Net.NetworkCredential]::new('', $secureTierConfirmation).Password
    Remove-Variable secureTierConfirmation -ErrorAction SilentlyContinue
    if ($tierConfirmation -cne 'FREE') { throw 'free_tier_not_confirmed' }

    $secureKey = Read-Host 'SiliconFlow API key' -AsSecureString
    $plainKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
    [Environment]::SetEnvironmentVariable($credentialName, $plainKey, 'Process')
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($credentialName, 'Process'))) {
        throw 'credential_missing'
    }

    $preflightHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $preflightPath).Hash.ToLowerInvariant()
    Write-Host "LIVE_BATCH_ID=$batchId" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_SHA256=$preflightHash" -ForegroundColor Cyan
    Write-Host 'Iniciando HYP-005 SiliconFlow gratuito: no máximo 24 chamadas.' -ForegroundColor Green
    & $pythonPath $runnerPath --live --allow-synthetic-only --batch-id $batchId `
        --expected-preflight $preflightPath --expected-preflight-sha256 $preflightHash
    $liveExit = $LASTEXITCODE

    if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
        & $pythonPath $runnerPath --verify-artifacts $summaryPath --batch-id $batchId `
            --expected-preflight $preflightPath --expected-preflight-sha256 $preflightHash
        $verifyExit = $LASTEXITCODE
    } else {
        $verifyExit = 3
        Write-Error 'O lote não produziu summary.json.' -ErrorAction Continue
    }
    Write-Host "LIVE_EXIT=$liveExit" -ForegroundColor Cyan
    Write-Host "VERIFY_EXIT=$verifyExit" -ForegroundColor Cyan
    Write-Host "SUMMARY_PATH=$summaryPath" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_PATH=$preflightPath" -ForegroundColor Cyan
    $finalExit = if ($verifyExit -ne 0) { 3 } else { $liveExit }
}
catch {
    Write-Error 'O HYP-005 foi interrompido por falha local segura.' -ErrorAction Continue
    $finalExit = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable tierConfirmation -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
}
exit $finalExit

