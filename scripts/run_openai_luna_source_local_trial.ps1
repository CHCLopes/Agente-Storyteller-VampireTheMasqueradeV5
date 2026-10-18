[CmdletBinding()]
param([switch] $PreflightOnly, [AllowNull()][System.Security.SecureString] $Credential)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$backend = Join-Path $projectRoot 'scripts\run_source_local_luna_trial.py'
$launcher = $PSCommandPath
$gatePath = Join-Path $projectRoot 'evals\narrator\reports\openai-luna-manual-trial-gate-2026-09-28.json'
$clientRoot = Join-Path $projectRoot 'client'
$vite = Join-Path $clientRoot 'node_modules\vite\bin\vite.js'
$viteEntry = Join-Path $clientRoot 'node_modules\vite\dist\node\index.js'
$viteConfig = Join-Path $clientRoot 'vite.source-player-trial.config.ts'
$node = $null
$runId = [guid]::NewGuid().ToString('D').ToLowerInvariant()
$sessionId = 'source-luna-trial.' + $runId
$runDirectory = Join-Path $projectRoot ('eval-results\source-local-luna-trial-' + $runId)
$statusDirectory = Join-Path ([IO.Path]::GetTempPath()) ('storyteller-source-local-luna-trial-' + $runId)
$statusPath = Join-Path $statusDirectory 'status.json'
$evidenceDirectory = Join-Path ([IO.Path]::GetTempPath()) ('storyteller-source-local-trial-window-' + $runId)
$preflightPath = Join-Path $evidenceDirectory 'preflight.json'
$lifecyclePath = $null
$stage = 'offline preflight'
$exitCode = 3
$finalStatus = 'failed'
$credentialProvided = $PSBoundParameters.ContainsKey('Credential')
$secureCredentialCopy = $null
$promptCredential = $null
$server = $null
$frontend = $null
$preflight = $null
$frozen = @{}
$forcedShutdown = $false
$failureObserved = $false
$interactiveStarted = $false
$costDispatchPossible = $false
$backendIdentity = @{ pid=$null }
$frontendProgram = @'
import { createServer } from 'vite';
import { createInterface } from 'node:readline';
let server;
let input;
let stopping = false;
async function stop(failed = false) {
  if (stopping) return;
  stopping = true;
  try { if (server) await server.close(); }
  catch { failed = true; }
  process.exitCode = failed ? 3 : 0;
  if (input) input.close();
  process.stdin.destroy();
}
try {
  server = await createServer({ configFile: process.argv[1], clearScreen: false,
    logLevel: 'silent', server: { host: '127.0.0.1', port: 5178, strictPort: true } });
  await server.listen();
  input = createInterface({ input: process.stdin, terminal: false });
  input.on('line', line => { void stop(line !== 'stop'); });
  input.on('close', () => { void stop(); });
} catch { await stop(true); }
'@

function Test-Integer($Value, [long] $Expected) {
    return (($Value -is [int] -or $Value -is [long]) -and $Value -eq $Expected)
}

function Write-Lifecycle([string] $Status, $Code = $null) {
    if ($null -eq $lifecyclePath) { return }
    $record = @{ run_id=$runId; session_id=$sessionId; status=$Status; exit_code=$Code;
        updated_at=[DateTime]::UtcNow.ToString('o'); forced_shutdown=$forcedShutdown }
    [IO.File]::WriteAllText($lifecyclePath, ($record | ConvertTo-Json) + "`n", [Text.UTF8Encoding]::new($false))
}

function Assert-RegularFile([string] $Path) {
    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Invalid local file.' }
    $parent = $item.Directory
    while ($null -ne $parent) {
        if ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked local path refused.' }
        $parent = $parent.Parent
    }
}

function Remember-File([string] $Path, [AllowNull()][string] $Expected = $null) {
    Assert-RegularFile $Path
    $hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Expected -and $hash -cne $Expected) { throw 'Frozen source differs.' }
    if ($frozen.ContainsKey($Path) -and $frozen[$Path] -cne $hash) { throw 'Frozen source changed.' }
    $frozen[$Path] = $hash
}

function Assert-FrozenPreparation {
    foreach ($path in $frozen.Keys) {
        Assert-RegularFile $path
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $frozen[$path]) { throw 'Frozen preparation changed.' }
    }
}

function New-IsolatedChild([string] $Executable, [string] $WorkingDirectory, [string[]] $Arguments,
        [System.Security.SecureString] $ChildCredential = $null, [switch] $CapturePreflight) {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.WorkingDirectory = $WorkingDirectory
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $start.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
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
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        if ($null -ne $ChildCredential) {
            $childKey = [Net.NetworkCredential]::new('', $ChildCredential).Password
            if ([string]::IsNullOrWhiteSpace($childKey)) { throw 'Blank protected credential.' }
            $start.EnvironmentVariables['STORYTELLER_SOURCE_LOCAL_TRIAL_LUNA_KEY'] = $childKey
            $childKey = $null
        }
        if (-not $process.Start()) { throw 'Child start failed.' }
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_LOCAL_TRIAL_LUNA_KEY')
        if ($CapturePreflight) {
            $stdout = $process.StandardOutput.ReadToEndAsync()
            $stderr = $process.StandardError.ReadToEndAsync()
        } else {
            # Live output is not copied to console, files or an in-memory log.
            $stdout = $process.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
            $stderr = $process.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        }
        return @{ process=$process; stdout=$stdout; stderr=$stderr; forced=$false }
    }
    catch {
        try { if ($process.Id -gt 0 -and -not $process.HasExited) { $process.Kill($true); $process.WaitForExit(2000) | Out-Null } } catch { }
        $process.Dispose()
        throw 'Owned child could not start.'
    }
    finally {
        $start.EnvironmentVariables.Remove('STORYTELLER_SOURCE_LOCAL_TRIAL_LUNA_KEY')
        $childKey = $null
    }
}

function Stop-OwnedChild($Child, [string] $Command, [int] $WaitMilliseconds = 10000) {
    if ($WaitMilliseconds -lt 1 -or $WaitMilliseconds -gt 75000) { throw 'Invalid owned shutdown deadline.' }
    if ($null -eq $Child) { return }
    $process = $Child.process
    if (-not $process.HasExited) {
        try {
            # Only a literal shutdown command travels to our own child's stdin.
            # It is not a credential broker or a channel to another shell.
            $process.StandardInput.WriteLine($Command)
            $process.StandardInput.Flush()
            $process.StandardInput.Close()
        } catch { }
        if (-not $process.WaitForExit($WaitMilliseconds)) {
            $Child.forced = $true
            $process.Kill($true)
            if (-not $process.WaitForExit(5000)) { throw 'Owned child did not terminate.' }
        }
    }
}

function Assert-Preflight($Document) {
    if ($Document.status -cne 'preflight_passed' -or $Document.purpose -cne 'source_local_luna_trial' -or
        $Document.protocol -cne 'source-local-luna-trial-v2' -or $Document.profile -cne 'narrative-source-application-v1' -or
        $Document.run_id -cne $runId -or $Document.session_id -cne $sessionId -or
        $Document.synthetic_only -isnot [bool] -or $Document.synthetic_only -ne $true -or
        $Document.cap_001_approved -isnot [bool] -or $Document.cap_001_approved -ne $false -or
        $Document.runtime_default_eligible -isnot [bool] -or $Document.runtime_default_eligible -ne $false) { throw 'Invalid preflight identity.' }
    if ($Document.target.profile -cne 'source-local-luna-trial-gpt-5.6-luna-low-synthetic' -or
        $Document.target.provider -cne 'OpenAI' -or $Document.target.model -cne 'gpt-5.6-luna' -or
        -not (Test-Integer $Document.backend_port 8018) -or -not (Test-Integer $Document.origin_port 5178) -or
        $Document.expected_origin -cne 'http://127.0.0.1:5178' -or $Document.expected_host -cne '127.0.0.1:8018') { throw 'Invalid trial configuration.' }
    $parameters = $Document.generation_parameters
    $budget = $Document.budget
    if (-not (Test-Integer $parameters.max_output_tokens 768) -or $parameters.reasoning_effort -cne 'low' -or
        ($parameters.temperature -isnot [double] -and $parameters.temperature -isnot [decimal]) -or $parameters.temperature -ne 0.65 -or
        -not (Test-Integer $budget.max_calls 4) -or -not (Test-Integer $budget.max_total_output_tokens 3072) -or
        -not (Test-Integer $budget.initial_quiet_seconds 0) -or -not (Test-Integer $budget.minimum_inter_call_delay_seconds 0) -or
        -not (Test-Integer $budget.deadline_seconds 60)) { throw 'Invalid trial limits.' }
    $expectedPaths = @{ run_directory=$runDirectory; database=(Join-Path $runDirectory 'storyteller.sqlite3'); status_directory=$statusDirectory; status_file=$statusPath }
    foreach ($name in $expectedPaths.Keys) {
        if ($Document.paths.$name -isnot [string] -or [IO.Path]::GetFullPath($Document.paths.$name) -cne [IO.Path]::GetFullPath($expectedPaths[$name])) { throw 'Invalid trial path.' }
    }
    if ($Document.paths.frontend_url -cne ('http://127.0.0.1:5178/source-player-trial.html?backendPort=8018&session=' + $sessionId) -or
        $Document.paths.websocket_url -cne ('ws://127.0.0.1:8018/ws/source-local/' + $sessionId)) { throw 'Invalid trial URL.' }
    if ($Document.prompt.file -cne 'evals/narrator/prompts/narrative-source-progress-v1.md' -or
        $Document.prompt.version -cne 'narrative-source-progress-v1' -or
        $Document.prompt.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $Document.prompt.file_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid trial prompt.' }
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in @($Document.inputs)) {
        if ($entry.file -isnot [string] -or $entry.sha256 -isnot [string] -or
            $entry.file -cnotmatch '^(api|scripts|client|evals|tests)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.(py|ps1|json|md|ts|tsx|html|css)$' -or
            $entry.sha256 -cnotmatch '^[a-f0-9]{64}$' -or -not $seen.Add($entry.file)) { throw 'Invalid frozen input.' }
        Remember-File (Join-Path $projectRoot $entry.file) $entry.sha256
    }
    if (-not $seen.Contains('scripts/run_source_local_luna_trial.py') -or -not $seen.Contains('client/vite.source-player-trial.config.ts') -or
        -not $seen.Contains('client/source-player-trial.html')) { throw 'Missing frozen component.' }
    Remember-File (Join-Path $projectRoot $Document.prompt.file) $Document.prompt.file_sha256
}

function Assert-FreeTrialPorts {
    foreach ($port in @(8018,5178)) {
        $listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
        if ($listeners.Count -gt 0) { throw 'Trial port already occupied.' }
    }
}

function Test-OwnedListener($Child, [int] $Port) {
    if ($null -eq $Child -or $Child.process.HasExited) { return $false }
    foreach ($listener in @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
        if ($listener.LocalAddress -cne '127.0.0.1') { continue }
        if ($listener.OwningProcess -eq $Child.process.Id) { return $true }
        # A Windows venv executable can retain one directly owned Python worker.
        if ($Port -eq 8018) {
            $owned = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $listener.OwningProcess + ' AND ParentProcessId = ' + $Child.process.Id) -Property ProcessId,ParentProcessId,Name -ErrorAction SilentlyContinue
            if ($null -ne $owned -and $owned.Name -ieq 'python.exe' -and $owned.ParentProcessId -eq $Child.process.Id) { return $true }
        }
    }
    return $false
}

function Read-BackendStatus {
    $document = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
    if ($document.run_id -cne $runId -or $document.session_id -cne $sessionId -or
        $document.protocol -cne 'source-local-luna-trial-v2' -or $document.purpose -cne 'source_local_luna_trial' -or
        $document.status -cnotin @('preparing','prepared','running','stopped','failed') -or
        ($document.pid -isnot [int] -and $document.pid -isnot [long]) -or $document.pid -le 0) { throw 'Invalid backend lifecycle.' }
    if ([IO.Path]::GetFullPath($document.paths.database) -cne [IO.Path]::GetFullPath((Join-Path $runDirectory 'storyteller.sqlite3')) -or
        [IO.Path]::GetFullPath($document.paths.status_file) -cne [IO.Path]::GetFullPath($statusPath)) { throw 'Backend lifecycle path differs.' }
    if ($null -ne $backendIdentity.pid -and $document.pid -ne $backendIdentity.pid) { throw 'Backend lifecycle owner changed.' }
    if ($null -ne $server -and $null -eq $backendIdentity.pid -and $document.pid -ne $server.process.Id) {
        $owned = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $document.pid + ' AND ParentProcessId = ' + $server.process.Id) -Property ProcessId,ParentProcessId,Name -ErrorAction SilentlyContinue
        if ($null -eq $owned -or $owned.Name -ine 'python.exe' -or $owned.ParentProcessId -ne $server.process.Id) { throw 'Backend lifecycle owner differs.' }
    }
    $backendIdentity.pid = $document.pid
    return $document
}

try {
    if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 required.' }
    $node = @(Get-Command node.exe -CommandType Application -ErrorAction Stop)[0].Source
    if (Test-Path -LiteralPath $evidenceDirectory) { throw 'Evidence directory already exists.' }
    if ((Test-Path -LiteralPath $runDirectory) -or (Test-Path -LiteralPath $statusDirectory)) { throw 'Trial identity already used.' }
    foreach ($path in @($python,$backend,$launcher,$gatePath,$node,$vite,$viteEntry,$viteConfig)) { Remember-File $path }
    $child = New-IsolatedChild $python $projectRoot @('-B',$backend,'--preflight-only','--run-id',$runId,'--port','8018','--origin-port','5178') -CapturePreflight
    try {
        $child.process.StandardInput.Close()
        if (-not $child.process.WaitForExit(30000)) { throw 'Preflight timeout.' }
        $text = $child.stdout.GetAwaiter().GetResult()
        $errorText = $child.stderr.GetAwaiter().GetResult()
        if ($child.process.ExitCode -ne 0 -or -not [string]::IsNullOrWhiteSpace($errorText)) { throw 'Preflight failed.' }
        $preflight = $text | ConvertFrom-Json
        Assert-Preflight $preflight
        Assert-FrozenPreparation
        [IO.Directory]::CreateDirectory($evidenceDirectory) | Out-Null
        [IO.File]::WriteAllText($preflightPath,$text.TrimEnd("`r","`n") + "`n",[Text.UTF8Encoding]::new($false))
    } finally {
        Stop-OwnedChild $child 'stop'
        $child.process.Dispose()
        $child = $null
        $text = $null
        $errorText = $null
    }
    Remember-File $preflightPath
    $lifecyclePath = Join-Path $evidenceDirectory 'lifecycle.json'
    $binding = @{ run_id=$runId; session_id=$sessionId; preflight_sha256=$frozen[$preflightPath]; backend_sha256=$frozen[$backend]; launcher_sha256=$frozen[$launcher]; node_sha256=$frozen[$node]; vite_sha256=$frozen[$vite]; inputs=$frozen }
    [IO.File]::WriteAllText((Join-Path $evidenceDirectory 'binding.json'),($binding | ConvertTo-Json -Depth 6)+"`n",[Text.UTF8Encoding]::new($false))
    Write-Lifecycle 'preflight_verified'
    if ($PreflightOnly) {
        $exitCode = 0
        $finalStatus = 'preflight_only_completed'
        Write-Host ('Preflight local verificado: ' + $preflightPath)
        Write-Host 'Nenhuma chave solicitada, banco, listener ou inferencia iniciados.'
    } else {
        $stage = 'protected credential entry'
        $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
        if ($gate.status -cne 'single_manual_trial_authorized' -or
            $gate.live_inference_authorized -ne $true -or
            $gate.paid_spend_authorized -ne $true -or
            $gate.model -cne 'gpt-5.6-luna' -or
            $gate.reasoning_effort -cne 'low' -or
            $gate.constraints.max_calls -ne 4 -or
            $gate.constraints.max_output_tokens_total -ne 3072 -or
            $gate.constraints.account_hard_spend_limit_usd -ne 0.05) {
            throw 'Manual paid gate invalid.'
        }
        $secureConfirmation = Read-Host 'Digite MANUAL-LUNA-USD-0.05 para confirmar este ensaio limitado' -AsSecureString
        $confirmation = [Net.NetworkCredential]::new('', $secureConfirmation).Password
        $secureConfirmation.Dispose()
        $secureConfirmation = $null
        if ($confirmation -cne 'MANUAL-LUNA-USD-0.05') { throw 'Manual paid ceiling not confirmed.' }
        $confirmation = $null
        Assert-FreeTrialPorts
        Write-Lifecycle 'awaiting_secure_credential'
        if ($credentialProvided) {
            if ($null -eq $Credential) { throw 'Protected credential required.' }
            $secureCredentialCopy = $Credential.Copy()
        } else {
            $promptCredential = Read-Host 'Cole a chave OpenAI somente neste prompt protegido e pressione Enter' -AsSecureString
            if ($promptCredential -isnot [Security.SecureString]) { throw 'Protected credential required.' }
            $secureCredentialCopy = $promptCredential.Copy()
            $promptCredential.Dispose()
            $promptCredential = $null
        }
        Assert-FrozenPreparation
        Assert-FreeTrialPorts
        if ((Test-Path -LiteralPath $runDirectory) -or (Test-Path -LiteralPath $statusDirectory)) { throw 'Trial identity already used.' }
        $stage = 'starting owned local services'
        Write-Lifecycle 'starting'
        $costDispatchPossible = $true
        $server = New-IsolatedChild $python $projectRoot @('-B',$backend,'--live','--allow-synthetic-only','--run-id',$runId,'--port','8018','--origin-port','5178','--expected-preflight',$preflightPath,'--expected-preflight-sha256',$frozen[$preflightPath],'--api-key-env','STORYTELLER_SOURCE_LOCAL_TRIAL_LUNA_KEY','--managed-stdin-stop') -ChildCredential $secureCredentialCopy
        $secureCredentialCopy.Dispose()
        $secureCredentialCopy = $null
        $frontend = New-IsolatedChild $node $clientRoot @('--input-type=module','--eval',$frontendProgram,'--',$viteConfig)
        $ready = $false
        for ($index=0; $index -lt 80; $index++) {
            if ($server.process.HasExited -or $frontend.process.HasExited) { throw 'Owned service exited before readiness.' }
            if (Test-Path -LiteralPath $statusPath -PathType Leaf) {
                $state = Read-BackendStatus
                if ($state.status -eq 'failed') { throw 'Backend start failed.' }
                if ($state.status -eq 'running' -and (Test-OwnedListener $server 8018) -and (Test-OwnedListener $frontend 5178)) { $ready=$true; break }
            }
            Start-Sleep -Milliseconds 250
        }
        if (-not $ready) { throw 'Owned services not ready.' }
        Assert-FrozenPreparation
        $stage = 'interactive local trial'
        $interactiveStarted = $true
        Write-Lifecycle 'running'
        Write-Host ('Ensaio OpenAI/Luna experimental: ' + $preflight.paths.frontend_url)
        Write-Host 'Somente dialogo e espera. Ate 4 chamadas, 768 tokens/chamada; sem espera artificial, retry ou fallback. Prazo maximo por acao: 60 s.'
        $stage = 'opening external browser'
        try {
            Start-Process -FilePath $preflight.paths.frontend_url | Out-Null
        } catch {
            throw 'Default external browser could not be opened.'
        }
        $stage = 'interactive local trial'
        Write-Host 'A pagina foi aberta no navegador externo padrao. Use apenas essa aba durante o ensaio.'
        Write-Host 'Mantenha esta janela aberta. Enter ou Ctrl+C encerra somente os servicos deste lancador.'
        while (-not $server.process.WaitForExit(250)) {
            if ($frontend.process.HasExited) { throw 'Frontend ended during trial.' }
            if (-not [Console]::IsInputRedirected -and [Console]::KeyAvailable) {
                if ([Console]::ReadKey($true).Key -eq [ConsoleKey]::Enter) { break }
            }
        }
        $stage = 'owned service shutdown'
        Stop-OwnedChild $server 'stop' 75000
        if ($server.forced) { $forcedShutdown=$true; throw 'Backend needed forced stop.' }
        $state = Read-BackendStatus
        if ($state.status -cne 'stopped' -or $server.process.ExitCode -ne 0) { throw 'Backend did not settle cleanly.' }
        Assert-FrozenPreparation
        $exitCode=0
        $finalStatus='stopped'
    }
} catch {
    $failureObserved=$true
    $exitCode=3
    $finalStatus='failed'
    if ($PreflightOnly -and $stage -eq 'offline preflight') {
        Write-Host ('Preflight local recusado: ' + $_.Exception.Message)
    }
    Write-Host ('Ensaio local interrompido durante ' + $stage + '. Evidencias locais preservadas.')
} finally {
    if ($null -ne $secureCredentialCopy) { $secureCredentialCopy.Dispose() }
    if ($null -ne $promptCredential) { $promptCredential.Dispose() }
    $secureCredentialCopy=$null
    $promptCredential=$null
    try {
        Stop-OwnedChild $server 'stop' 75000
        Stop-OwnedChild $frontend 'stop'
        if (($null -ne $server -and $server.forced) -or ($null -ne $frontend -and $frontend.forced)) {
            $forcedShutdown=$true
            $exitCode=3
            $finalStatus='failed'
        }
        if ($null -ne $frontend -and $frontend.process.ExitCode -ne 0) { throw 'Frontend shutdown failed.' }
        if ($interactiveStarted -and -not $failureObserved -and -not $forcedShutdown) {
            $state = Read-BackendStatus
            if ($state.status -cne 'stopped' -or $server.process.ExitCode -ne 0) { throw 'Backend shutdown incomplete.' }
            Assert-FrozenPreparation
            $exitCode=0
            $finalStatus='stopped'
        }
    } catch {
        $exitCode=3
        $finalStatus='failed'
    }
    try { Write-Lifecycle $finalStatus $exitCode } catch { $exitCode=3 }
    foreach ($ownedChild in @($server,$frontend)) {
        if ($null -ne $ownedChild) { $ownedChild.process.Dispose() }
    }
    try {
        $costArgs = @('--run-directory', $runDirectory)
        if (-not $costDispatchPossible) { $costArgs += '--no-dispatch' }
        elseif ($finalStatus -eq 'stopped' -and -not $forcedShutdown) { $costArgs += '--settled' }
        & $python (Join-Path $projectRoot 'scripts\report_luna_test_cost.py') @costArgs
        if ($LASTEXITCODE -ne 0) { Write-Host 'CUSTO FINAL LUNA: indisponivel; relatorio nao concluido.' }
    } catch { Write-Host 'CUSTO FINAL LUNA: indisponivel; relatorio nao concluido.' }
    $preflight=$null
}
Write-Host ('Lancador local encerrado com codigo ' + $exitCode + '. Default, campanha completa e admissao do narrador permanecem sem aprovacao.')
exit $exitCode

