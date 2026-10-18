[CmdletBinding()]
param([switch] $PreflightOnly, [switch] $UseProcessCredential)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot 'scripts\evaluate_source_player.py'
$batchId = [guid]::NewGuid().ToString('D').ToLowerInvariant()
$evidenceDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('storyteller-source-player-window-' + $batchId)
$preflightPath = Join-Path $evidenceDirectory 'preflight.json'
$lifecyclePath = $null
$stage = 'offline preflight'
$exitCode = 3
$credential = $null
$plainTextKey = $null
$child = $null

function Test-Integer($Value, [long] $Expected) {
    return (($Value -is [int] -or $Value -is [long]) -and $Value -eq $Expected)
}

function Write-Lifecycle([string] $Status, $Code = $null) {
    if ($null -eq $lifecyclePath) { return }
    $record = @{ batch_id=$batchId; status=$Status; updated_at=[DateTime]::UtcNow.ToString('o'); exit_code=$Code }
    [System.IO.File]::WriteAllText($lifecyclePath, ($record | ConvertTo-Json) + "`n", [System.Text.UTF8Encoding]::new($false))
}

function Invoke-IsolatedEvaluator([string[]] $Arguments, [switch] $WithCredential) {
    # No inherited credential/config environment is enumerated or copied.
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $python
    $start.WorkingDirectory = $projectRoot
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $start.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
    $quoted = foreach ($argument in @('-B', $evaluator) + $Arguments) {
        # These arguments are closed flags, UUID/hash or Windows leaf paths.
        if ($argument.Contains('"') -or $argument.Contains("`r") -or $argument.Contains("`n") -or $argument.EndsWith('\')) { throw 'Unsafe local argument.' }
        '"' + $argument + '"'
    }
    $start.Arguments = $quoted -join ' '
    $start.EnvironmentVariables.Clear()
    foreach ($name in @('SYSTEMROOT','WINDIR','TEMP','TMP','PATH','PATHEXT','COMSPEC','USERPROFILE','LOCALAPPDATA','APPDATA')) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($null -ne $value) { $start.EnvironmentVariables[$name] = $value }
    }
    $start.EnvironmentVariables['STORYTELLER_DISABLE_DOTENV'] = '1'
    $start.EnvironmentVariables['PYTHONDONTWRITEBYTECODE'] = '1'
    $start.EnvironmentVariables['PYTHONUTF8'] = '1'
    $start.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $start.EnvironmentVariables['GIT_CONFIG_COUNT'] = '1'
    $start.EnvironmentVariables['GIT_CONFIG_KEY_0'] = 'safe.directory'
    $start.EnvironmentVariables['GIT_CONFIG_VALUE_0'] = $projectRoot
    if ($WithCredential) { $start.EnvironmentVariables['STORYTELLER_SOURCE_PLAYER_GROQ_KEY'] = $env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    $started = $false
    try {
        if (-not $process.Start()) { throw 'Local evaluator could not start.' }
        $started = $true
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        return @{ exit_code=$process.ExitCode; stdout=$stdout.GetAwaiter().GetResult(); stderr=$stderr.GetAwaiter().GetResult() }
    }
    finally {
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_PLAYER_GROQ_KEY')
        if ($started) {
            try {
                if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
            }
            catch { # The owned process may already have exited; never expose exception data.
            }
        }
        $process.Dispose()
    }
}

function Assert-Preflight($Document, [string] $EvaluatorHash) {
    if ($Document.purpose -cne 'source_player_probe' -or
        $Document.probe_kind -cne 'source_player_probe' -or
        $Document.experiment_version -cne 'source-player-observation-v1' -or
        $Document.protocol -cne 'narrative-source-application-v1' -or
        $Document.selected_candidate_id -cne 'qwen-3.8-27b-groq-free-synthetic-nonthink' -or
        -not (Test-Integer $Document.max_calls 2) -or
        $Document.synthetic_only -isnot [bool] -or $Document.synthetic_only -ne $true -or
        $Document.campaign_data_eligible -isnot [bool] -or $Document.campaign_data_eligible -ne $false -or
        $Document.cap_001_approved -isnot [bool] -or $Document.cap_001_approved -ne $false -or
        $Document.runtime_default_eligible -isnot [bool] -or $Document.runtime_default_eligible -ne $false) { throw 'Preflight identity differs.' }
    $ownEntry = @($Document.inputs.implementation | Where-Object { $_.file -ceq 'scripts/evaluate_source_player.py' })
    if ($ownEntry.Count -ne 1 -or $ownEntry[0].sha256 -cne $EvaluatorHash) { throw 'Preflight executable differs.' }
    $parameters = $Document.generation_parameters
    if (-not (Test-Integer $parameters.deadline_seconds 60) -or
        -not (Test-Integer $parameters.minimum_inter_call_delay_seconds 60) -or
        -not (Test-Integer $parameters.initial_quiet_seconds 60) -or
        -not (Test-Integer $parameters.max_total_output_tokens 1536) -or
        -not (Test-Integer $parameters.max_output_tokens 768) -or
        ($parameters.temperature -isnot [double] -and $parameters.temperature -isnot [decimal]) -or
        $parameters.temperature -ne 0.65 -or
        $parameters.reasoning_effort -cne 'none') { throw 'Preflight limits differ.' }
}

function Assert-FrozenPreparation {
    if ((Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash -or
        (Get-FileHash -LiteralPath $preflightPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $preflightHash) { throw 'Frozen preparation changed.' }
}

Write-Host "Source player probe batch: $batchId"
Write-Host 'Two authored synthetic player actions through setup and the actual producer; fixed Qwen/Groq, 768 tokens per call, 1536 total, temperature 0.65, reasoning none.'
Write-Host 'Initial wait, spacing and per-call deadline: 60 seconds. First failure stops the chain; no retry, repair, diagnostics or fallback.'
try {
    Remove-Item Env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $evidenceDirectory) { throw 'Evidence directory already exists.' }
    foreach ($file in @($python, $evaluator)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required local file unavailable.' }
    }
    $runDirectory = Join-Path (Join-Path $projectRoot 'eval-results') ('source-player-' + $batchId)
    $summaryPath = Join-Path $runDirectory 'summary.json'
    if (Test-Path -LiteralPath $runDirectory) { throw 'Run directory already exists.' }
    $evaluatorHash = (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()
    $child = Invoke-IsolatedEvaluator @('--preflight')
    if ($child.exit_code -ne 0 -or -not [string]::IsNullOrWhiteSpace($child.stderr)) { throw 'Offline preflight failed.' }
    $preflight = $child.stdout | ConvertFrom-Json
    Assert-Preflight $preflight $evaluatorHash
    if ((Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash) { throw 'Evaluator changed during preflight.' }
    [System.IO.Directory]::CreateDirectory($evidenceDirectory) | Out-Null
    [System.IO.File]::WriteAllText($preflightPath, $child.stdout.TrimEnd("`r", "`n") + "`n", [System.Text.UTF8Encoding]::new($false))
    $preflightHash = (Get-FileHash -LiteralPath $preflightPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $lifecyclePath = Join-Path $evidenceDirectory 'lifecycle.json'
    $binding = @{ batch_id=$batchId; preflight_sha256=$preflightHash; evaluator_sha256=$evaluatorHash }
    [System.IO.File]::WriteAllText((Join-Path $evidenceDirectory 'binding.json'), ($binding | ConvertTo-Json) + "`n", [System.Text.UTF8Encoding]::new($false))
    $child = $null
    Write-Lifecycle 'preflight_verified'
    if ($PreflightOnly) {
        $exitCode = 0
        Write-Lifecycle 'preflight_only_completed' 0
        Write-Host "Offline preflight verified: $preflightPath"
        Write-Host 'No credential requested and no live invocation made.'
    }
    else {
        $stage = 'protected credential entry'
        Write-Lifecycle 'awaiting_secure_credential'
        if ($UseProcessCredential) {
            # Explicitly use the already prepared environment of THIS PowerShell.
            # Never inspect another process, history, transcript, file or .env.
            if ([string]::IsNullOrWhiteSpace($env:GROQ_API_KEY)) { throw 'Process credential unavailable.' }
            Assert-FrozenPreparation
            $env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY = $env:GROQ_API_KEY
        }
        else {
            $credential = Read-Host 'Cole a chave Groq somente neste prompt protegido e pressione Enter' -AsSecureString
            if ($credential -isnot [System.Security.SecureString]) { throw 'Protected credential required.' }
            Assert-FrozenPreparation
            $plainTextKey = [System.Net.NetworkCredential]::new('', $credential).Password
            if ([string]::IsNullOrWhiteSpace($plainTextKey)) { throw 'Blank protected credential.' }
            $env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY = $plainTextKey
            $plainTextKey = $null
            $credential.Dispose()
            $credential = $null
        }
        if (Test-Path -LiteralPath $runDirectory) { throw 'Run directory already exists.' }
        $stage = 'bounded live invocation'
        Write-Lifecycle 'running'
        Write-Host 'Protected credential accepted. The evaluator performs the initial wait before its first call.'
        $child = Invoke-IsolatedEvaluator @('--live','--allow-synthetic-only','--batch-id',$batchId,'--expected-preflight',$preflightPath,'--expected-preflight-sha256',$preflightHash,'--api-key-env','STORYTELLER_SOURCE_PLAYER_GROQ_KEY') -WithCredential
        $exitCode = $child.exit_code
        $child = $null
        Remove-Item Env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY -ErrorAction SilentlyContinue
        if ($exitCode -notin @(0,1,2,3,130)) { throw 'Invalid evaluator exit code.' }
        $stage = 'offline artifact verification'
        Write-Lifecycle 'verifying_artifacts'
        Assert-FrozenPreparation
        if (-not (Test-Path -LiteralPath $summaryPath -PathType Leaf)) { throw 'Expected artifact absent.' }
        $summaryHash = (Get-FileHash -LiteralPath $summaryPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $child = Invoke-IsolatedEvaluator @('--verify-artifacts',$summaryPath,'--batch-id',$batchId,'--expected-preflight',$preflightPath,'--expected-preflight-sha256',$preflightHash)
        if ($child.exit_code -ne 0 -or -not [string]::IsNullOrWhiteSpace($child.stderr)) { throw 'Artifact verifier failed.' }
        $verified = $child.stdout | ConvertFrom-Json
        if ($verified.verified -isnot [bool] -or $verified.verified -ne $true -or
            $verified.batch_id -cne $batchId -or -not (Test-Integer $verified.process_exit_code $exitCode) -or
            [System.IO.Path]::GetFullPath($verified.summary_path) -cne [System.IO.Path]::GetFullPath($summaryPath) -or
            $summaryHash -cne (Get-FileHash -LiteralPath $summaryPath -Algorithm SHA256).Hash.ToLowerInvariant()) { throw 'Artifact verifier identity differs.' }
        $document = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
        if ($document.batch_id -cne $batchId -or -not (Test-Integer $document.process_exit_code $exitCode)) { throw 'Verified summary identity differs.' }
        Assert-FrozenPreparation
        $child = $null
        Write-Host "Verified summary: $summaryPath"
        Write-Host "Frozen preflight: $preflightPath"
    }
}
catch {
    # All external text and exception details stay out of console/lifecycle.
    $exitCode = 3
    Write-Host "Source player probe stopped during $stage. Any local evidence was preserved."
}
finally {
    Remove-Item Env:STORYTELLER_SOURCE_PLAYER_GROQ_KEY -ErrorAction SilentlyContinue
    if ($null -ne $credential -and $credential -is [System.Security.SecureString]) { $credential.Dispose() }
    $credential = $null
    $plainTextKey = $null
    $child = $null
    $verified = $null
    $preflight = $null
}
try {
    if (-not $PreflightOnly -or $exitCode -ne 0) { Write-Lifecycle 'finished' $exitCode }
}
catch {
    $exitCode = 3
    Write-Host 'Source player probe stopped during lifecycle finalization. Any local evidence was preserved.'
}
Write-Host "Source player probe ended with exit code $exitCode; semantic truth, narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
