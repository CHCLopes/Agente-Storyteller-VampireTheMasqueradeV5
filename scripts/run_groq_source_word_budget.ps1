[CmdletBinding()]
param([switch] $PreflightOnly, [AllowNull()][System.Security.SecureString] $Credential)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot 'scripts\evaluate_source_word_budget.py'
$launcher = $PSCommandPath
$batchId = [guid]::NewGuid().ToString('D').ToLowerInvariant()
$evidenceDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('storyteller-source-word-budget-window-' + $batchId)
$preflightPath = Join-Path $evidenceDirectory 'preflight.json'
$lifecyclePath = $null
$stage = 'offline preflight'
$exitCode = 3
$credentialProvided = $PSBoundParameters.ContainsKey('Credential')
$secureCredentialCopy = $null
$promptCredential = $null
$child = $null

function Test-Integer($Value, [long] $Expected) {
    return (($Value -is [int] -or $Value -is [long]) -and $Value -eq $Expected)
}

function Write-Lifecycle([string] $Status, $Code = $null) {
    if ($null -eq $lifecyclePath) { return }
    $record = @{ batch_id=$batchId; status=$Status; updated_at=[DateTime]::UtcNow.ToString('o'); exit_code=$Code }
    [System.IO.File]::WriteAllText($lifecyclePath, ($record | ConvertTo-Json) + "`n", [System.Text.UTF8Encoding]::new($false))
}

function Invoke-IsolatedEvaluator([string[]] $Arguments, [System.Security.SecureString] $ChildCredential = $null) {
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
    foreach ($argument in @('-B', $evaluator) + $Arguments) {
        $start.ArgumentList.Add($argument)
    }
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
    $childKey = $null
    if ($null -ne $ChildCredential) {
        $childKey = [System.Net.NetworkCredential]::new('', $ChildCredential).Password
        if ([string]::IsNullOrWhiteSpace($childKey)) { throw 'Blank protected credential.' }
        $start.EnvironmentVariables['STORYTELLER_SOURCE_WORD_BUDGET_GROQ_KEY'] = $childKey
        $childKey = $null
    }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    $started = $false
    try {
        if (-not $process.Start()) { throw 'Local evaluator could not start.' }
        $started = $true
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_WORD_BUDGET_GROQ_KEY')
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        return @{ exit_code=$process.ExitCode; stdout=$stdout.GetAwaiter().GetResult(); stderr=$stderr.GetAwaiter().GetResult() }
    }
    finally {
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_WORD_BUDGET_GROQ_KEY')
        $childKey = $null
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
    foreach ($prompt in @($Document.inputs.prompts.A, $Document.inputs.prompts.B)) { $entries += @{ file=$prompt.file; sha256=$prompt.file_sha256 } }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $entries) {
        # Only declared project source files are hashed. No environment files,
        # absolute paths, traversal, or inherited shell values are inspected.
        if ($entry.file -isnot [string] -or $entry.sha256 -isnot [string] -or
            $entry.file -cnotmatch '^(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(py|ps1|json|md)$' -or
            $entry.file.StartsWith('/') -or $entry.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
            -not $seen.Add($entry.file)) { throw 'Invalid frozen input.' }
        $path = Join-Path $projectRoot $entry.file
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.sha256) { throw 'Frozen input changed.' }
    }
}

function Assert-Preflight($Document, [string] $EvaluatorHash) {
    if ($Document.purpose -cne 'source_word_budget_probe' -or
        $Document.probe_kind -cne 'source_word_budget_probe' -or
        $Document.experiment_version -cne 'source-word-budget-v1' -or
        $Document.protocol -cne 'narrative-source-application-v1' -or
        $Document.selected_candidate_id -cne 'qwen-3.8-27b-groq-free-synthetic-nonthink' -or
        -not (Test-Integer $Document.max_calls 4) -or
        $Document.synthetic_only -isnot [bool] -or $Document.synthetic_only -ne $true -or
        $Document.campaign_data_eligible -isnot [bool] -or $Document.campaign_data_eligible -ne $false -or
        $Document.cap_001_approved -isnot [bool] -or $Document.cap_001_approved -ne $false -or
        $Document.runtime_default_eligible -isnot [bool] -or $Document.runtime_default_eligible -ne $false) { throw 'Preflight identity differs.' }
    if ($Document.target.profile -cne 'source-word-budget-qwen-3.8-27b-groq-free-synthetic-nonthink' -or
        $Document.target.model -cne 'qwen/qwen3.8-27b' -or $Document.target.provider -cne 'Groq') { throw 'Candidate configuration differs.' }
    if (@($Document.slots).Count -ne 4) { throw 'Slot count differs.' }
    for ($index = 0; $index -lt 4; $index++) {
        $slot = $Document.slots[$index]
        if ($slot.slot_id -cne ('slot-' + ($index + 1)) -or
            $slot.context_id -cne @('C1','C1','C2','C2')[$index] -or
            $slot.arm_id -cne @('A','B','B','A')[$index]) { throw 'Slot order differs.' }
    }
    if ($Document.inputs.corpus.file -cne 'evals/narrator/source_word_budget_v1.json' -or
        $Document.inputs.protocol.file -cne 'evals/narrator/source_word_budget_protocol_v1.md') { throw 'Authored diagnostic differs.' }
    $promptFiles = @('evals/narrator/prompts/narrative-source-progress-v1.md', 'evals/narrator/prompts/narrative-source-word-budget-v1.md')
    if (@($Document.inputs.prompts.PSObject.Properties).Count -ne 2) { throw 'Prompt count differs.' }
    for ($index = 0; $index -lt 2; $index++) {
        $prompt = $Document.inputs.prompts.(@('A','B')[$index])
        if ($prompt.file -cne $promptFiles[$index] -or
            $prompt.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Prompt identity differs.' }
    }
    Assert-InputFiles $Document
    $ownEntry = @($Document.inputs.implementation | Where-Object { $_.file -ceq 'scripts/evaluate_source_word_budget.py' })
    if ($ownEntry.Count -ne 1 -or $ownEntry[0].sha256 -cne $EvaluatorHash) { throw 'Preflight executable differs.' }
    $parameters = $Document.generation_parameters
    if (-not (Test-Integer $parameters.deadline_seconds 60) -or
        -not (Test-Integer $parameters.minimum_inter_call_delay_seconds 60) -or
        -not (Test-Integer $parameters.initial_quiet_seconds 60) -or
        -not (Test-Integer $parameters.max_total_output_tokens 3072) -or
        -not (Test-Integer $parameters.max_output_tokens 768) -or
        ($parameters.temperature -isnot [double] -and $parameters.temperature -isnot [decimal]) -or
        $parameters.temperature -ne 0.65 -or $parameters.reasoning_effort -cne 'none') { throw 'Preflight limits differ.' }
}

function Assert-FrozenPreparation {
    Assert-InputFiles $preflight
    if ((Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash.ToLowerInvariant() -cne $launcherHash -or
        (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash -or
        (Get-FileHash -LiteralPath $preflightPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $preflightHash) { throw 'Frozen preparation changed.' }
}

Write-Host "Source word budget diagnostic batch: $batchId"
Write-Host 'Two new authored synthetic contexts; fixed slots A/C1, B/C1, B/C2, A/C2. Qwen/Groq, reasoning none.'
Write-Host 'At most 4 calls, 768 tokens per call, 3072 total, temperature 0.65. Original admission gates remain unchanged.'
Write-Host 'Initial wait, global spacing and per-call deadline: 60 seconds. No retry, repair, diagnostics or fallback.'
Write-Host 'No SQLite, campaign, commit, UI or default change. This bounded observation does not approve a narrator.'

try {
    if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 required.' }
    if (Test-Path -LiteralPath $evidenceDirectory) { throw 'Evidence directory already exists.' }
    foreach ($file in @($python, $evaluator)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required local file unavailable.' }
    }
    $runDirectory = Join-Path (Join-Path $projectRoot 'eval-results') ('source-word-budget-' + $batchId)
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
        if ($credentialProvided) {
            if ($null -eq $Credential) { throw 'Protected credential required.' }
            # This object belongs to the caller's current PowerShell session.
            # Only our copy may be disposed; never inspect another process.
            $secureCredentialCopy = $Credential.Copy()
        }
        else {
            $promptCredential = Read-Host 'Cole a chave Groq somente neste prompt protegido e pressione Enter' -AsSecureString
            if ($promptCredential -isnot [System.Security.SecureString]) { throw 'Protected credential required.' }
            $secureCredentialCopy = $promptCredential.Copy()
            $promptCredential.Dispose()
            $promptCredential = $null
        }
        Assert-FrozenPreparation
        if (Test-Path -LiteralPath $runDirectory) { throw 'Run directory already exists.' }
        $stage = 'bounded live invocation'
        Write-Lifecycle 'running'
        Write-Host 'Protected credential accepted. The evaluator performs the initial wait before its first call.'
        $child = Invoke-IsolatedEvaluator @('--live','--allow-synthetic-only','--batch-id',$batchId,'--expected-preflight',$preflightPath,'--expected-preflight-sha256',$preflightHash,'--api-key-env','STORYTELLER_SOURCE_WORD_BUDGET_GROQ_KEY') -ChildCredential $secureCredentialCopy
        $exitCode = $child.exit_code
        $secureCredentialCopy.Dispose()
        $secureCredentialCopy = $null
        $child = $null
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
    Write-Host "Source word budget diagnostic stopped during $stage. Any local evidence was preserved."
}
finally {
    if ($null -ne $secureCredentialCopy) { $secureCredentialCopy.Dispose() }
    if ($null -ne $promptCredential) { $promptCredential.Dispose() }
    $secureCredentialCopy = $null
    $promptCredential = $null
    $child = $null
    $verified = $null
    $preflight = $null
}

try {
    if (-not $PreflightOnly -or $exitCode -ne 0) { Write-Lifecycle 'finished' $exitCode }
}
catch {
    $exitCode = 3
    Write-Host 'Source word budget diagnostic stopped during lifecycle finalization. Any local evidence was preserved.'
}
Write-Host "Source word budget diagnostic ended with exit code $exitCode; semantic truth, narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
