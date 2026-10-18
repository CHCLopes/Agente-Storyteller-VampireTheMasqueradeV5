[CmdletBinding()]
param([switch] $PreflightOnly, [switch] $UseProcessCredential)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot 'scripts\evaluate_source_comparison.py'
$launcher = $PSCommandPath
$batchId = [guid]::NewGuid().ToString('D').ToLowerInvariant()
$evidenceDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('storyteller-source-comparison-window-' + $batchId)
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
    if ($WithCredential) { $start.EnvironmentVariables['STORYTELLER_SOURCE_COMPARISON_GROQ_KEY'] = $env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY }
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
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_COMPARISON_GROQ_KEY')
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

function Assert-InputFiles($Document) {
    $entries = @($Document.inputs.implementation) + @($Document.inputs.corpus, $Document.inputs.protocol, $Document.inputs.manifest)
    $entries += @{ file=$Document.inputs.prompt.file; sha256=$Document.inputs.prompt.file_sha256 }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $entries) {
        # Only declared project source files are hashed. No environment files,
        # absolute paths, traversal, or inherited shell values are inspected.
        if ($entry.file -isnot [string] -or $entry.sha256 -isnot [string] -or
            $entry.file -cnotmatch '^[A-Za-z0-9_/-]+\.(py|ps1|json|md)$' -or
            $entry.file.StartsWith('/') -or $entry.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
            -not $seen.Add($entry.file)) { throw 'Invalid frozen input.' }
        $path = Join-Path $projectRoot $entry.file
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.sha256) { throw 'Frozen input changed.' }
    }
}

function Assert-Preflight($Document, [string] $EvaluatorHash) {
    if ($Document.purpose -cne 'source_model_comparison' -or
        $Document.probe_kind -cne 'source_model_comparison' -or
        $Document.experiment_version -cne 'source-comparison-v1' -or
        $Document.protocol -cne 'narrative-source-application-v1' -or
        -not (Test-Integer $Document.max_calls 12) -or
        $Document.synthetic_only -isnot [bool] -or $Document.synthetic_only -ne $true -or
        $Document.campaign_data_eligible -isnot [bool] -or $Document.campaign_data_eligible -ne $false -or
        $Document.cap_001_approved -isnot [bool] -or $Document.cap_001_approved -ne $false -or
        $Document.runtime_default_eligible -isnot [bool] -or $Document.runtime_default_eligible -ne $false) { throw 'Preflight identity differs.' }
    $candidateIds = @('qwen-3.8-27b-groq-free-synthetic-nonthink','gpt-oss-120b-groq-free-synthetic-low')
    $models = @('qwen/qwen3.8-27b','openai/gpt-oss-120b')
    $reasoning = @('none','low')
    if (@($Document.selected_candidate_ids).Count -ne 2 -or @($Document.inputs.candidates).Count -ne 2) { throw 'Candidate count differs.' }
    for ($index = 0; $index -lt 2; $index++) {
        $candidate = $Document.inputs.candidates[$index]
        if ($Document.selected_candidate_ids[$index] -cne $candidateIds[$index] -or
            $candidate.candidate_id -cne $candidateIds[$index] -or
            $candidate.model -cne $models[$index] -or $candidate.provider -cne 'Groq' -or
            $candidate.reasoning_effort -cne $reasoning[$index]) { throw 'Candidate configuration differs.' }
    }
    if ($Document.inputs.corpus.file -cne 'evals/narrator/source_comparison_v1.json' -or
        $Document.inputs.corpus.sha256 -cne 'b755b921be4a77b2c1af030a0eed65fc4e9d9e81d5c4393eaf99507fc6e7d9e5' -or
        $Document.inputs.protocol.file -cne 'evals/narrator/source_comparison_protocol_v1.md' -or
        $Document.inputs.protocol.sha256 -cne 'ea2257537c8d913872dd65dadf0f3ff42a01162f9584c970c5665bc777be741d') { throw 'Authored comparison differs.' }
    Assert-InputFiles $Document
    $ownEntry = @($Document.inputs.implementation | Where-Object { $_.file -ceq 'scripts/evaluate_source_comparison.py' })
    if ($ownEntry.Count -ne 1 -or $ownEntry[0].sha256 -cne $EvaluatorHash) { throw 'Preflight executable differs.' }
    $parameters = $Document.generation_parameters
    if (-not (Test-Integer $parameters.deadline_seconds 60) -or
        -not (Test-Integer $parameters.minimum_inter_call_delay_seconds 60) -or
        -not (Test-Integer $parameters.initial_quiet_seconds 60) -or
        -not (Test-Integer $parameters.max_total_output_tokens 9216) -or
        -not (Test-Integer $parameters.max_output_tokens 768) -or
        ($parameters.temperature -isnot [double] -and $parameters.temperature -isnot [decimal]) -or
        $parameters.temperature -ne 0.65) { throw 'Preflight limits differ.' }
}

function Assert-FrozenPreparation {
    Assert-InputFiles $preflight
    if ((Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash.ToLowerInvariant() -cne $launcherHash -or
        (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash -or
        (Get-FileHash -LiteralPath $preflightPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $preflightHash) { throw 'Frozen preparation changed.' }
}

Write-Host "Source model comparison batch: $batchId"
Write-Host 'Two new authored synthetic scenes, three turns each, four blocks: Qwen/Oficina, GPT-OSS/Oficina, GPT-OSS/Arquivo, Qwen/Arquivo.'
Write-Host 'At most 12 calls, 768 tokens per call, 9216 total, temperature 0.65; Qwen reasoning none and GPT-OSS reasoning low.'
Write-Host 'Initial wait, global spacing and per-call deadline: 60 seconds. Failures stop the chain or entire batch according to the frozen protocol; no retry, repair, diagnostics or fallback.'
try {
    Remove-Item Env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $evidenceDirectory) { throw 'Evidence directory already exists.' }
    foreach ($file in @($python, $evaluator)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required local file unavailable.' }
    }
    $runDirectory = Join-Path (Join-Path $projectRoot 'eval-results') ('source-comparison-' + $batchId)
    $summaryPath = Join-Path $runDirectory 'summary.json'
    if (Test-Path -LiteralPath $runDirectory) { throw 'Run directory already exists.' }
    $launcherHash = (Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash.ToLowerInvariant()
    $evaluatorHash = (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant()
    $child = Invoke-IsolatedEvaluator @('--preflight')
    if ($child.exit_code -ne 0 -or -not [string]::IsNullOrWhiteSpace($child.stderr)) { throw 'Offline preflight failed.' }
    $preflight = $child.stdout | ConvertFrom-Json
    Assert-Preflight $preflight $evaluatorHash
    if ((Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash -or
        (Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash.ToLowerInvariant() -cne $launcherHash) { throw 'Executable changed during preflight.' }
    [System.IO.Directory]::CreateDirectory($evidenceDirectory) | Out-Null
    [System.IO.File]::WriteAllText($preflightPath, $child.stdout.TrimEnd("`r", "`n") + "`n", [System.Text.UTF8Encoding]::new($false))
    $preflightHash = (Get-FileHash -LiteralPath $preflightPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $lifecyclePath = Join-Path $evidenceDirectory 'lifecycle.json'
    $binding = @{ batch_id=$batchId; preflight_sha256=$preflightHash; evaluator_sha256=$evaluatorHash; launcher_sha256=$launcherHash }
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
            $env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY = $env:GROQ_API_KEY
        }
        else {
            $credential = Read-Host 'Cole a chave Groq somente neste prompt protegido e pressione Enter' -AsSecureString
            if ($credential -isnot [System.Security.SecureString]) { throw 'Protected credential required.' }
            Assert-FrozenPreparation
            $plainTextKey = [System.Net.NetworkCredential]::new('', $credential).Password
            if ([string]::IsNullOrWhiteSpace($plainTextKey)) { throw 'Blank protected credential.' }
            $env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY = $plainTextKey
            $plainTextKey = $null
            $credential.Dispose()
            $credential = $null
        }
        if (Test-Path -LiteralPath $runDirectory) { throw 'Run directory already exists.' }
        $stage = 'bounded live invocation'
        Write-Lifecycle 'running'
        Write-Host 'Protected credential accepted. The evaluator performs the initial wait before its first call.'
        $child = Invoke-IsolatedEvaluator @('--live','--allow-synthetic-only','--batch-id',$batchId,'--expected-preflight',$preflightPath,'--expected-preflight-sha256',$preflightHash,'--api-key-env','STORYTELLER_SOURCE_COMPARISON_GROQ_KEY') -WithCredential
        $exitCode = $child.exit_code
        $child = $null
        Remove-Item Env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY -ErrorAction SilentlyContinue
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
    Write-Host "Source model comparison stopped during $stage. Any local evidence was preserved."
}
finally {
    Remove-Item Env:STORYTELLER_SOURCE_COMPARISON_GROQ_KEY -ErrorAction SilentlyContinue
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
    Write-Host 'Source model comparison stopped during lifecycle finalization. Any local evidence was preserved.'
}
Write-Host "Source model comparison ended with exit code $exitCode; semantic truth, narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
