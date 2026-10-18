[CmdletBinding()]
param([switch] $PreflightOnly, [AllowNull()][System.Security.SecureString] $Credential)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluator = Join-Path $projectRoot 'scripts\evaluate_source_dialogue_continuity.py'
$launcher = $PSCommandPath
$batchId = [guid]::NewGuid().ToString('D').ToLowerInvariant()
$evidenceDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('storyteller-source-dialogue-continuity-window-' + $batchId)
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
        $start.EnvironmentVariables['STORYTELLER_SOURCE_DIALOGUE_CONTINUITY_GROQ_KEY'] = $childKey
        $childKey = $null
    }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $start
    $started = $false
    try {
        if (-not $process.Start()) { throw 'Local evaluator could not start.' }
        $started = $true
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_DIALOGUE_CONTINUITY_GROQ_KEY')
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        return @{ exit_code=$process.ExitCode; stdout=$stdout.GetAwaiter().GetResult(); stderr=$stderr.GetAwaiter().GetResult() }
    }
    finally {
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_DIALOGUE_CONTINUITY_GROQ_KEY')
        $childKey = $null
        if ($started) {
            try {
                if (-not $process.HasExited) { $process.Kill($true); $process.WaitForExit() }
            }
            catch { # The owned process may already have exited; never expose exception data.
            }
        }
        $process.Dispose()
    }
}

function Get-TextHash([string] $Text) {
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [System.Convert]::ToHexString($hasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Text))).ToLowerInvariant()
    }
    finally { $hasher.Dispose() }
}

function Assert-InputFiles($Document) {
    $entries = @($Document.inputs.implementation) + @($Document.inputs.corpus, $Document.inputs.protocol, $Document.inputs.manifest)
    $entries += @{ file=$Document.inputs.prompt.file; sha256=$Document.inputs.prompt.file_sha256 }
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

function Assert-Parameters($Parameters) {
    if (-not (Test-Integer $Parameters.shared_turn_deadline_seconds 60) -or
        -not (Test-Integer $Parameters.minimum_inter_call_delay_seconds 60) -or
        -not (Test-Integer $Parameters.initial_quiet_seconds 60) -or
        -not (Test-Integer $Parameters.max_total_output_tokens 1536) -or
        -not (Test-Integer $Parameters.max_calls 2) -or
        -not (Test-Integer $Parameters.max_output_tokens 768) -or
        ($Parameters.temperature -isnot [double] -and $Parameters.temperature -isnot [decimal]) -or
        $Parameters.temperature -ne 0.65 -or $Parameters.reasoning_effort -cne 'none') { throw 'Preflight limits differ.' }
}

function Assert-Preflight($Document, [string] $EvaluatorHash) {
    if ($Document.purpose -cne 'source_dialogue_continuity_probe' -or
        $Document.probe_kind -cne 'source_dialogue_continuity_probe' -or
        $Document.experiment_version -cne 'source-dialogue-continuity-v1' -or
        $Document.protocol -cne 'narrative-source-application-v1' -or
        $Document.selected_candidate_id -cne 'qwen-3.8-27b-groq-free-synthetic-nonthink' -or
        -not (Test-Integer $Document.max_calls 2) -or
        $Document.synthetic_only -isnot [bool] -or $Document.synthetic_only -ne $true -or
        $Document.campaign_data_eligible -isnot [bool] -or $Document.campaign_data_eligible -ne $false -or
        $Document.cap_001_approved -isnot [bool] -or $Document.cap_001_approved -ne $false -or
        $Document.runtime_default_eligible -isnot [bool] -or $Document.runtime_default_eligible -ne $false) { throw 'Preflight identity differs.' }
    if ($Document.target.profile -cne 'source-dialogue-continuity-qwen-3.8-27b-groq-free-synthetic-nonthink' -or
        $Document.target.model -cne 'qwen/qwen3.8-27b' -or $Document.target.provider -cne 'Groq') { throw 'Candidate configuration differs.' }
    if (@($Document.turns).Count -ne 2 -or 'frozen_requests' -in @($Document.PSObject.Properties.Name)) { throw 'Retained turn recipe differs.' }
    $fixedActions = @('Digo a Mara: "Mara, o que é este lugar?"', 'Digo a Mara: "Mara, explique melhor sua resposta."')
    for ($index = 0; $index -lt 2; $index++) {
        if ($Document.turns[$index].turn_slot -cne ('turn-' + ($index + 1)) -or
            $Document.turns[$index].player_input -cne $fixedActions[$index]) { throw 'Fixed dialogue actions differ.' }
    }
    $sourcePolicy = $Document.source_policy
    if ($sourcePolicy.source_field -cne 'n' -or $sourcePolicy.source_origin -cne 'runtime_committed_generated_narrative' -or
        $sourcePolicy.contexts_independent -isnot [bool] -or $sourcePolicy.contexts_independent -ne $false -or
        $sourcePolicy.question_is_source -isnot [bool] -or $sourcePolicy.question_is_source -ne $false -or
        $sourcePolicy.briefing_is_source -isnot [bool] -or $sourcePolicy.briefing_is_source -ne $false -or
        @($sourcePolicy.npc_aliases).Count -ne 1 -or $sourcePolicy.npc_aliases[0] -cne 'Mara' -or
        $sourcePolicy.second_user -cne 'previous_committed_complete_source') { throw 'Committed source policy differs.' }
    $template = $Document.first_request_template
    if ($template.is_live_request -isnot [bool] -or $template.is_live_request -ne $false -or
        $template.requires_retained_capsule -isnot [bool] -or $template.requires_retained_capsule -ne $true -or
        $null -ne $template.body_sha256 -or $template.player_input -cne $fixedActions[0] -or
        $template.setup.protocol -cne 'narrative-source-setup-request-v1' -or $template.setup.location -cne 'Galeria' -or
        @($template.setup.npcs_present).Count -ne 1 -or $template.setup.npcs_present[0] -cne 'Mara' -or
        $template.provider_static.model -cne 'qwen/qwen3.8-27b' -or
        (Get-TextHash $template.provider_static.system_prompt) -cne $Document.inputs.prompt.sha256) { throw 'Prospective request template differs.' }
    Assert-Parameters $template.provider_static.generation_parameters
    if ($Document.inputs.corpus.file -cne 'evals/narrator/source_dialogue_continuity_v1.json' -or
        $Document.inputs.protocol.file -cne 'evals/narrator/source_dialogue_continuity_protocol_v1.md' -or
        $Document.inputs.prompt.file -cne 'evals/narrator/prompts/narrative-source-dialogue-v1.md' -or
        $Document.inputs.prompt.version -cne 'narrative-source-dialogue-v1' -or
        $Document.inputs.prompt.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $Document.inputs.response_schema_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $Document.inputs.provider_schema_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Authored diagnostic differs.' }
    Assert-InputFiles $Document
    $ownEntry = @($Document.inputs.implementation | Where-Object { $_.file -ceq 'scripts/evaluate_source_dialogue_continuity.py' })
    if ($ownEntry.Count -ne 1 -or $ownEntry[0].sha256 -cne $EvaluatorHash) { throw 'Preflight executable differs.' }
    Assert-Parameters $Document.generation_parameters
}

function Assert-FrozenPreparation {
    Assert-InputFiles $preflight
    if ((Get-FileHash -LiteralPath $launcher -Algorithm SHA256).Hash.ToLowerInvariant() -cne $launcherHash -or
        (Get-FileHash -LiteralPath $evaluator -Algorithm SHA256).Hash.ToLowerInvariant() -cne $evaluatorHash -or
        (Get-FileHash -LiteralPath $preflightPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $preflightHash) { throw 'Frozen preparation changed.' }
}

Write-Host "Source dialogue continuity diagnostic batch: $batchId"
Write-Host 'Two fixed consecutive dialogue turns using an actually committed source. Qwen/Groq, reasoning none.'
Write-Host 'At most 2 calls, 768 tokens per call, 1536 total, temperature 0.65. Original admission gates remain unchanged.'
Write-Host 'Initial wait and global spacing: 60 seconds. Preparation and narrative share one 60-second deadline per turn. No retry, repair, diagnostics or fallback.'
Write-Host 'The evaluator sends two fixed speech actions automatically; turn 2 is composed only after the actual turn 1 commit.'
Write-Host 'New isolated synthetic SQLite session; no existing campaign, UI or default change. This bounded observation does not approve a narrator.'

try {
    if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 required.' }
    if (Test-Path -LiteralPath $evidenceDirectory) { throw 'Evidence directory already exists.' }
    foreach ($file in @($python, $evaluator)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Required local file unavailable.' }
    }
    $runDirectory = Join-Path (Join-Path $projectRoot 'eval-results') ('source-dialogue-continuity-' + $batchId)
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
        $child = Invoke-IsolatedEvaluator @('--live','--allow-synthetic-only','--batch-id',$batchId,'--expected-preflight',$preflightPath,'--expected-preflight-sha256',$preflightHash,'--api-key-env','STORYTELLER_SOURCE_DIALOGUE_CONTINUITY_GROQ_KEY') -ChildCredential $secureCredentialCopy
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
    Write-Host "Source dialogue continuity diagnostic stopped during $stage. Any local evidence was preserved."
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
    Write-Host 'Source dialogue continuity diagnostic stopped during lifecycle finalization. Any local evidence was preserved.'
}
Write-Host "Source dialogue continuity diagnostic ended with exit code $exitCode; semantic truth, narrative quality, runtime and CAP-001 remain unapproved."
exit $exitCode
