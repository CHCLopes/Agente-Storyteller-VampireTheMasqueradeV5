[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialName = 'STORYTELLER_GROUNDED_PROGRESSION_GROQ_KEY'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'scripts\evaluate_closed_world_render_replication_live.py'
$preflightDirectory = Join-Path $projectRoot 'eval-results\preflights'
$finalExit = 3

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    Write-Error 'Python do projeto não encontrado.' -ErrorAction Continue
    exit 3
}

try {
    New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null
    $batchId = [guid]::NewGuid().ToString()
    $preflightPath = Join-Path $preflightDirectory "closed-world-render-replication-$batchId.json"
    $summaryPath = Join-Path `
        $projectRoot `
        "eval-results\closed-world-render-replication-$batchId\summary.json"

    $preflightLines = & $pythonPath $runnerPath --preflight
    if ($LASTEXITCODE -ne 0) {
        throw 'preflight_failed'
    }
    Set-Content `
        -LiteralPath $preflightPath `
        -Value $preflightLines `
        -Encoding utf8NoBOM

    $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
    if (
        $preflight.hypothesis_id -ne 'HYP-004-QWEN-GPT-OSS-REPLICATION-L1' -or
        $preflight.provider_calls -ne 0 -or
        $preflight.credential_inspected -ne $false -or
        $preflight.schedule.Count -ne 16 -or
        $preflight.max_calls -ne 16 -or
        $preflight.automatic_retries -ne 0 -or
        $preflight.repair -ne $false -or
        $preflight.fallback -ne $false -or
        $preflight.paid_spend_authorized -ne $false -or
        $preflight.synthetic_only -ne $true -or
        $preflight.replication.aggregate_for_admission -ne $false -or
        $preflight.replication.best_of_selection -ne $false
    ) {
        throw 'preflight_contract_invalid'
    }

    Write-Host 'Confirme que a chave Groq usada pertence ao acesso gratuito e que nenhum saldo pago será utilizado.' -ForegroundColor Yellow
    Write-Host 'A bateria contém somente fixtures sintéticas e não altera o narrador padrão.' -ForegroundColor Yellow
    $secureTierConfirmation = Read-Host `
        'Digite FREE para confirmar execução sem gasto pago' `
        -AsSecureString
    $tierConfirmation = [System.Net.NetworkCredential]::new(
        '', $secureTierConfirmation
    ).Password
    Remove-Variable secureTierConfirmation -ErrorAction SilentlyContinue
    if ($tierConfirmation -cne 'FREE') {
        throw 'free_tier_not_confirmed'
    }

    $secureKey = Read-Host 'Groq API key' -AsSecureString
    $plainKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
    [Environment]::SetEnvironmentVariable($credentialName, $plainKey, 'Process')
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace(
        [Environment]::GetEnvironmentVariable($credentialName, 'Process')
    )) {
        throw 'credential_missing'
    }

    $preflightHash = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $preflightPath
    ).Hash.ToLowerInvariant()
    Write-Host "LIVE_BATCH_ID=$batchId" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_SHA256=$preflightHash" -ForegroundColor Cyan
    Write-Host 'Iniciando HYP-004: replicação Qwen/GPT-OSS, 16 chamadas máximas.' -ForegroundColor Green

    $liveArguments = @(
        $runnerPath
        '--live'
        '--allow-synthetic-only'
        '--batch-id'
        $batchId
        '--expected-preflight'
        $preflightPath
        '--expected-preflight-sha256'
        $preflightHash
    )
    & $pythonPath @liveArguments
    $liveExit = $LASTEXITCODE

    if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
        $verifyArguments = @(
            $runnerPath
            '--verify-artifacts'
            $summaryPath
            '--batch-id'
            $batchId
            '--expected-preflight'
            $preflightPath
            '--expected-preflight-sha256'
            $preflightHash
        )
        & $pythonPath @verifyArguments
        $verifyExit = $LASTEXITCODE
    }
    else {
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
    Write-Error 'A replicação Qwen/GPT-OSS foi interrompida por falha local segura.' -ErrorAction Continue
    $finalExit = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable tierConfirmation -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
}

exit $finalExit
