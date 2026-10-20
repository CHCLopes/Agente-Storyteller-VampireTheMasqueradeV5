[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$runner = Join-Path $root 'scripts\evaluate_hybrid_campaign_luna_l61_live.py'
$costReporter = Join-Path $root 'scripts\report_luna_test_cost.py'
$gatePath = Join-Path $root 'evals\narrator\reports\hybrid-campaign-luna-l61-live-gate-2026-10-20.json'
$credentialName = 'STORYTELLER_OPENAI_HYP007_L61_KEY'
$batchId = $null
$runDirectory = $null
$dispatched = $false
$exitCode = 3

try {
    $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
    if ($gate.hypothesis_id -cne 'HYP-007' -or
        $gate.lot_id -cne 'HYP-007-L61' -or
        $gate.target_model -cne 'gpt-5.6-luna' -or
        $gate.reasoning_effort -cne 'low' -or
        $gate.content_version -cne 'record-at-risk.v2' -or
        $gate.policy_version -cne 'campaign-progression.v2' -or
        $gate.max_calls -ne 17 -or
        $gate.max_estimated_usd -cne '0.15' -or
        $gate.paid_ceiling_authorized -ne $true -or
        $gate.live_inference_authorized -ne $true -or
        $gate.admission_automatic -ne $false) {
        throw 'paid_authorization_missing_or_drifted'
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'python_unavailable' }
    $env:STORYTELLER_DISABLE_DOTENV = '1'
    $env:PYTHONPATH = $root
    $preflightLines = @(& $python $runner --preflight)
    if ($LASTEXITCODE -ne 0 -or $preflightLines.Count -lt 1) { throw 'keyless_preflight_failed' }
    $preflight = $preflightLines[0] | ConvertFrom-Json
    if ($preflight.hypothesis_id -cne 'HYP-007' -or
        $preflight.lot_id -cne 'HYP-007-L61' -or
        $preflight.content_version -cne 'record-at-risk.v2' -or
        $preflight.provider_calls -ne 0 -or
        $preflight.calls_planned -ne 17 -or
        $preflight.max_request_bytes_observed -gt 20000 -or
        $preflight.prompt_sha256 -cne $gate.prompt_sha256) {
        throw 'keyless_preflight_drifted'
    }
    Write-Host 'Preflight HYP-007 aprovado: 17 turnos sintéticos, zero chamadas.' -ForegroundColor Cyan
    Write-Host 'Teto estimado adicional USD 0,15 ja aprovado; lote unico HYP-007-L61.' -ForegroundColor Cyan
    $readyDirectory = Join-Path $root 'eval-results\preflights'
    [IO.Directory]::CreateDirectory($readyDirectory) | Out-Null
    $readyPath = Join-Path $readyDirectory 'hybrid-campaign-luna-l61-ready.json'
    [pscustomobject]@{
        lot_id = 'HYP-007-L61'
        process_id = $PID
        ready_at_utc = [DateTime]::UtcNow.ToString('o')
        phase = 'awaiting_secure_credential'
        provider_calls = 0
        prompt_sha256 = $preflight.prompt_sha256
        max_request_bytes = $preflight.max_request_bytes_observed
    } | ConvertTo-Json | Set-Content -LiteralPath $readyPath -Encoding UTF8
    $secureKey = Read-Host 'OpenAI API key para HYP-007-L61' -AsSecureString
    $plainKey = [Net.NetworkCredential]::new('', $secureKey).Password
    if ([string]::IsNullOrWhiteSpace($plainKey)) { throw 'credential_missing' }
    [Environment]::SetEnvironmentVariable($credentialName, $plainKey, 'Process')
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue

    $batchId = [guid]::NewGuid().ToString('D').ToLowerInvariant()
    $runDirectory = Join-Path $root ('eval-results\hybrid-campaign-luna-l61-' + $batchId)
    Write-Host "LIVE_BATCH_ID=$batchId" -ForegroundColor Cyan
    Write-Host 'Iniciando HYP-007-L61; no máximo 17 chamadas, sem retry ou fallback.' -ForegroundColor Cyan
    $dispatched = $true
    & $python $runner --live --batch-id $batchId
    $exitCode = $LASTEXITCODE
    Write-Host "LIVE_EXIT=$exitCode" -ForegroundColor Cyan
    Write-Host "SUMMARY_PATH=$(Join-Path $runDirectory 'summary.json')" -ForegroundColor Cyan
}
catch {
    Write-Host 'HYP-007 interrompido antes de autorizar gasto ou por falha local.' -ForegroundColor Yellow
    $exitCode = 3
}
finally {
    Remove-Item "Env:\$credentialName" -ErrorAction SilentlyContinue
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
    Write-Host 'Credencial removida do ambiente deste terminal.' -ForegroundColor Green
    try {
        if (-not $dispatched) {
            & $python $costReporter --no-dispatch
        } elseif ($null -ne $runDirectory -and (Test-Path -LiteralPath (Join-Path $runDirectory 'records.jsonl') -PathType Leaf)) {
            $summaryPath = Join-Path $runDirectory 'summary.json'
            $settled = $false
            if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
                $summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
                $recordsHash = (Get-FileHash -LiteralPath (Join-Path $runDirectory 'records.jsonl') -Algorithm SHA256).Hash.ToLowerInvariant()
                $settled = $summary.records_sha256 -ceq $recordsHash
            }
            if ($settled) { & $python $costReporter --run-directory $runDirectory --settled }
            else { & $python $costReporter --run-directory $runDirectory }
        } else {
            Write-Host 'CUSTO FINAL LUNA: indisponível; execução iniciada sem artefato de chamadas verificável.' -ForegroundColor Yellow
        }
    } catch {
        Write-Host 'CUSTO FINAL LUNA: indisponível; relatório não concluído.' -ForegroundColor Yellow
    }
}
exit $exitCode
