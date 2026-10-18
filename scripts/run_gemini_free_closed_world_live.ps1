[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialName = 'STORYTELLER_HYP003_GEMINI_KEY'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'scripts\evaluate_gemini_free_closed_world_live.py'
$preflightDirectory = Join-Path $projectRoot 'eval-results\preflights'
$finalExit = 3

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    Write-Error 'Python do projeto não encontrado.' -ErrorAction Continue
    exit 3
}

try {
    New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null
    $batchId = [guid]::NewGuid().ToString()
    $preflightPath = Join-Path $preflightDirectory "gemini-free-closed-world-$batchId.json"
    $summaryPath = Join-Path `
        $projectRoot `
        "eval-results\gemini-free-closed-world-$batchId\summary.json"

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
        $preflight.provider_calls -ne 0 -or
        $preflight.credential_inspected -ne $false -or
        $preflight.schedule.Count -ne 8 -or
        $preflight.max_provider_attempts -ne 16 -or
        $preflight.transport_retry_policy.max_retries_per_case -ne 2 -or
        $preflight.transport_retry_policy.only_without_response -ne $true -or
        $preflight.paid_spend_authorized -ne $false -or
        $preflight.synthetic_only -ne $true
    ) {
        throw 'preflight_contract_invalid'
    }

    Write-Host 'Confirme no Google AI Studio que o projeto da chave está no Free Tier.' -ForegroundColor Yellow
    Write-Host 'O nível gratuito pode usar entradas e respostas para melhorar produtos; este lote contém somente fixtures sintéticas.' -ForegroundColor Yellow
    $secureTierConfirmation = Read-Host `
        'Digite FREE para confirmar o projeto sem billing habilitado' `
        -AsSecureString
    $tierConfirmation = [System.Net.NetworkCredential]::new(
        '', $secureTierConfirmation
    ).Password
    Remove-Variable secureTierConfirmation -ErrorAction SilentlyContinue
    if ($tierConfirmation -cne 'FREE') {
        throw 'free_tier_not_confirmed'
    }

    $secureKey = Read-Host 'Gemini API key' -AsSecureString
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
    Write-Host 'Iniciando HYP-003-L4 integral Gemini Flash gratuito: oito casos, no máximo 16 tentativas.' -ForegroundColor Green

    $liveArguments = @(
        $runnerPath
        '--live'
        '--allow-synthetic-only'
        '--confirm-free-tier-project'
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
    Write-Error 'A execução Gemini gratuita foi interrompida por falha local segura.' -ErrorAction Continue
    $finalExit = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
    Remove-Variable secureTierConfirmation -ErrorAction SilentlyContinue
    Remove-Variable tierConfirmation -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
}

exit $finalExit
