[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialName = 'STORYTELLER_GROUNDED_PROGRESSION_GROQ_KEY'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runnerPath = Join-Path $projectRoot 'scripts\evaluate_grounded_progression_live.py'

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    Write-Error 'Python do projeto não encontrado.' -ErrorAction Continue
    exit 3
}

$credentialAvailable = -not [string]::IsNullOrWhiteSpace(
    [Environment]::GetEnvironmentVariable($credentialName, 'Process')
)
if (-not $credentialAvailable) {
    Write-Error `
        'Credencial protegida ausente nesta sessão do terminal.' `
        -ErrorAction Continue
    exit 3
}

$batchId = [guid]::NewGuid().ToString()
$preflightDirectory = Join-Path $projectRoot 'eval-results\preflights'
$preflightPath = Join-Path $preflightDirectory "grounded-progression-$batchId.json"
$summaryPath = Join-Path `
    $projectRoot `
    "eval-results\grounded-progression-$batchId\summary.json"
$finalExit = 3

try {
    New-Item -ItemType Directory -Path $preflightDirectory -Force | Out-Null

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
        $preflight.schedule.Count -ne 16
    ) {
        throw 'preflight_contract_invalid'
    }

    $preflightHash = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $preflightPath
    ).Hash.ToLowerInvariant()

    Write-Host "LIVE_BATCH_ID=$batchId" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_SHA256=$preflightHash" -ForegroundColor Cyan
    Write-Host 'Iniciando o lote L1 autorizado.' -ForegroundColor Green

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
        Write-Error 'O lote não produziu summary.json.'
    }

    Write-Host "LIVE_EXIT=$liveExit" -ForegroundColor Cyan
    Write-Host "VERIFY_EXIT=$verifyExit" -ForegroundColor Cyan
    Write-Host "SUMMARY_PATH=$summaryPath" -ForegroundColor Cyan
    Write-Host "PREFLIGHT_PATH=$preflightPath" -ForegroundColor Cyan

    $finalExit = if ($verifyExit -ne 0) { 3 } else { $liveExit }
}
catch {
    Write-Error 'A execução L1 foi interrompida por falha local segura.'
    $finalExit = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
}

exit $finalExit
