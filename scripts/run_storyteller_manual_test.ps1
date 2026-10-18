[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][guid] $TestId,
    [switch] $PreflightOnly,
    [switch] $BootstrapCheck,
    [guid] $ResumeFromTestId = [guid]::Empty,
    [System.Security.SecureString] $ApiKey
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$runDir = Join-Path ([System.IO.Path]::GetTempPath()) ('storyteller-manual-game-' + $TestId.ToString('D'))
$sessionId = 'local.' + $TestId.ToString('D')
$url = 'http://127.0.0.1:8000/play/' + $sessionId
$statusPath = Join-Path $runDir 'status.json'
$server = $null
$stdoutTask = $null
$stderrTask = $null
$childEnvironment = @{}
$finished = $false
$database = Join-Path $runDir 'storyteller.sqlite3'
# Resume only an explicitly selected isolated manual test, with fresh lifecycle logs.
# Credentials are never read from the earlier process or its artifacts.
if ($ResumeFromTestId -ne [guid]::Empty) {
    if ($BootstrapCheck -or $ResumeFromTestId -eq $TestId) {
        Write-Host 'Retomada exige um TestId novo e nao permite BootstrapCheck.'
        exit 2
    }
    $sourceDir=Join-Path ([IO.Path]::GetTempPath()) ('storyteller-manual-game-' + $ResumeFromTestId.ToString('D'))
    $sourceStatusPath=Join-Path $sourceDir 'status.json'
    $sourceDatabase=Join-Path $sourceDir 'storyteller.sqlite3'
    if (-not (Test-Path -LiteralPath $sourceStatusPath -PathType Leaf) -or -not (Test-Path -LiteralPath $sourceDatabase -PathType Leaf)) {
        Write-Host 'O teste de origem e seu banco isolado precisam existir.'
        exit 2
    }
    $sourceState=Get-Content -LiteralPath $sourceStatusPath -Raw | ConvertFrom-Json
    $sourceSession='local.' + $ResumeFromTestId.ToString('D')
    if ($sourceState.test_id -cne $ResumeFromTestId.ToString('D') -or $sourceState.session_id -cne $sourceSession -or $sourceState.database -ine $sourceDatabase) {
        Write-Host 'A identidade do teste de origem nao confere; nenhum estado foi alterado.'
        exit 2
    }
    $sessionId=$sourceSession
    $url='http://127.0.0.1:8000/play/' + $sessionId
}

# Refuse a duplicate live window or any pre-existing test database before writing state.
if ((Test-Path -LiteralPath $database) -or (Test-Path -LiteralPath ($database + '-wal')) -or (Test-Path -LiteralPath ($database + '-shm'))) {
    Write-Host 'Identificador ja utilizado: banco existente preservado. Use um TestId novo.'
    exit 2
}
if (Test-Path -LiteralPath $statusPath) {
    $existingState = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
    if ($ResumeFromTestId -ne [guid]::Empty) {
        # An offline preflight may become one launch; finished/failed launches
        # must get a new ID even though their database lives in the source run.
        $priorArtifacts=@('readiness.json','backend.stdout.log','backend.stderr.log') |
            Where-Object { Test-Path -LiteralPath (Join-Path $runDir $_) }
        if ($existingState.status -cne 'preflight_passed' -or $null -ne $existingState.server_pid -or @($priorArtifacts).Count -gt 0) {
            Write-Host 'Identificador de retomada ja utilizado; seus logs foram preservados. Use um TestId novo.'
            exit 2
        }
    }
    if ($existingState.status -in @('awaiting_secure_credential','starting','checking_narrator','ready')) {
        Write-Host 'Uma janela deste teste ja esta ativa; nao sera duplicada.'
        exit 2
    }
}

if ($ResumeFromTestId -ne [guid]::Empty) { $database=$sourceDatabase }

function Write-State([string]$Status, [string]$Code = '') {
    $record = @{ test_id=$TestId.ToString('D'); status=$Status; code=$Code;
        updated_at=[DateTime]::UtcNow.ToString('o'); url=$url; session_id=$sessionId;
        database=$database; server_pid=$null; resumed_from_test_id=$ResumeFromTestId.ToString('D') }
    if ($null -ne $server) { $record.server_pid=$server.Id }
    [IO.File]::WriteAllText($statusPath, ($record | ConvertTo-Json) + "`n", [Text.UTF8Encoding]::new($false))
}
function New-PythonProcess([string[]]$Arguments, [hashtable]$Environment) {
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName=$python; $info.WorkingDirectory=$projectRoot
    $info.UseShellExecute=$false; $info.CreateNoWindow=$true
    $info.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
    $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
    $info.Environment.Clear()
    foreach ($entry in $Environment.GetEnumerator()) { $info.Environment[$entry.Key]=[string]$entry.Value }
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    return [Diagnostics.Process]::Start($info)
}
function Test-OwnedListener {
    if ($null -eq $server -or $server.HasExited) { return $false }
    $listeners=@(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
    foreach ($item in $listeners) {
        if ($item.LocalAddress -cne '127.0.0.1') { continue }
        if ($item.OwningProcess -eq $server.Id) { return $true }
        # Windows venv/python.exe can be a launcher retaining one Python child.
        $child=Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $item.OwningProcess) -ErrorAction SilentlyContinue
        if ($null -ne $child -and $child.ParentProcessId -eq $server.Id -and $child.Name -ieq 'python.exe') { return $true }
    }
    return $false
}
function Send-InitLog([string]$Status, [string]$Message, [int]$Phase) {
    if (-not (Test-OwnedListener)) { throw 'server_ownership_lost' }
    $body = @{status=$Status; message=$Message; phase=$Phase;
        timestamp=([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0)} | ConvertTo-Json
    Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/initialization/logs' -Method Post `
        -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 5 | Out-Null
}

try {
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'python_missing' }
    [IO.Directory]::CreateDirectory($runDir) | Out-Null
    # This process supplies an allowlisted environment; no existing credential is read.
    foreach ($name in @('SYSTEMROOT','WINDIR','TEMP','TMP','PATH','PATHEXT','COMSPEC','USERPROFILE','LOCALAPPDATA','APPDATA')) {
        $value=[Environment]::GetEnvironmentVariable($name, 'Process')
        if ($null -ne $value) { $childEnvironment[$name]=$value }
    }
    $childEnvironment['STORYTELLER_DISABLE_DOTENV']='1'
    $childEnvironment['PYTHONDONTWRITEBYTECODE']='1'
    $childEnvironment['PYTHONIOENCODING']='utf-8'
    $childEnvironment['PYTHONUTF8']='1'
    $childEnvironment['STORYTELLER_DB_PATH']=$database
    if ($ResumeFromTestId -ne [guid]::Empty) { $childEnvironment['STORYTELLER_MANUAL_RESUME_SESSION']=$sessionId }
    $childEnvironment['LLM_TARGET_ID']='manual-game-groq-qwen-' + $TestId.ToString('D')
    $childEnvironment['LLM_PROVIDER_LABEL']='Groq'
    $childEnvironment['LLM_MODEL']='qwen/qwen3.8-27b'
    $childEnvironment['LLM_BASE_URL']='https://api.groq.com/openai/v1'
    $childEnvironment['LLM_ADAPTER_KIND']='groq'
    $childEnvironment['LLM_STRUCTURED_GENERATION']='native'
    $childEnvironment['LLM_STREAMING']='native'
    $childEnvironment['LLM_REASONING_EFFORT']='none'
    $childEnvironment['LLM_TIMEOUT_SECONDS']='60'
    $childEnvironment['LLM_SCENE_DIRECTOR_MAX_OUTPUT_TOKENS']='768'
    $childEnvironment['LLM_SCENE_DIRECTOR_TEMPERATURE']='0.65'
    $childEnvironment['NARRATOR_CONTEXT_TOKEN_BUDGET']='768'
    $childEnvironment['LLM_H0_ENABLED']='false'
    $childEnvironment['LLM_H1_ENABLED']='false'
    $childEnvironment['LLM_H4_ACTION_ENRICHMENT_ENABLED']='false'
    $childEnvironment['LLM_API_KEY']='synthetic-offline-preflight-placeholder'
    Write-State 'preflight'
    $check=New-PythonProcess @('-B',(Join-Path $PSScriptRoot 'manual_game_preflight.py')) $childEnvironment
    $checkOut=$check.StandardOutput.ReadToEndAsync(); $checkErr=$check.StandardError.ReadToEndAsync()
    if (-not $check.WaitForExit(30000)) { $check.Kill(); throw 'preflight_timeout' }
    $preflightText=$checkOut.GetAwaiter().GetResult()
    $null=$checkErr.GetAwaiter().GetResult()
    if ($check.ExitCode -ne 0) { throw 'preflight_failed' }
    $checked=$preflightText | ConvertFrom-Json
    if ($checked.status -cne 'passed' -or $checked.provider_calls -ne 0 -or $checked.adapter -cne 'GroqAdapter') { throw 'preflight_identity' }
    [IO.File]::WriteAllText((Join-Path $runDir 'preflight.json'),$preflightText,[Text.UTF8Encoding]::new($false))
    $childEnvironment.Remove('LLM_API_KEY')
    if ($PreflightOnly) {
        Write-State 'preflight_passed'
        Write-Output $preflightText
        $finished=$true
        return
    }
    # PreflightOnly is offline and may inspect preparation while another test runs.
    # A real launch still refuses an occupied port before and after credentials.
    $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,8000)
    try { $listener.Start() } finally { $listener.Stop() }
    Write-Host 'Agente Storyteller - uso teste do jogo completo atual'
    if ($ResumeFromTestId -ne [guid]::Empty) {
        Write-Host 'Retomando a mesma sessao de teste e seu banco. Logs desta abertura separados.'
    } else { Write-Host 'Sessao inventada, banco separado.' }
    Write-Host 'O fluxo B nao esta ativado.'
    Write-Host 'Groq/Qwen explicito; tres diagnosticos de prontidao e depois somente suas acoes.'
    Write-Host ('Interface: ' + $url)
    if ($BootstrapCheck) { $ApiKey=ConvertTo-SecureString 'synthetic-bootstrap-placeholder' -AsPlainText -Force }
    Write-State 'awaiting_secure_credential'
    if ($null -eq $ApiKey) { $ApiKey=Read-Host 'Cole a chave Groq neste prompt protegido e pressione Enter' -AsSecureString }
    if ($ApiKey.Length -eq 0) { throw 'blank_credential' }
    $childEnvironment['LLM_API_KEY']=[Net.NetworkCredential]::new('', $ApiKey).Password
    # The protected prompt may take time; verify the port again before launch.
    $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,8000)
    try { $listener.Start() } finally { $listener.Stop() }
    Write-State 'starting'
    $server=New-PythonProcess @('-B','-m','uvicorn','api.main:app','--host','127.0.0.1','--port','8000','--log-level','warning','--no-access-log') $childEnvironment
    $stdoutTask=$server.StandardOutput.ReadToEndAsync(); $stderrTask=$server.StandardError.ReadToEndAsync()
    $childEnvironment.Remove('LLM_API_KEY')
    [void]$server.StartInfo.Environment.Remove('LLM_API_KEY')
    $ApiKey.Dispose(); $ApiKey=$null
    $ready=$false
    for ($i=0; $i -lt 40; $i++) {
        if ($server.HasExited) { throw 'server_exited' }
        try {
            if (-not (Test-OwnedListener)) { Start-Sleep -Milliseconds 250; continue }
            $health=Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 1
            if ($health.status -ceq 'ok') { $ready=$true; break }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw 'server_not_ready' }
    Send-InitLog 'success' 'Servidor local e sessao de teste disponiveis.' 0
    if ($BootstrapCheck) {
        $capabilities=Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/llm/capabilities' -TimeoutSec 5
        if ($capabilities.configured -ne $true -or $capabilities.target.provider -cne 'Groq') { throw 'bootstrap_capabilities_failed' }
        $page=Invoke-WebRequest -Uri $url -TimeoutSec 5
        if ($page.StatusCode -ne 200 -or $page.Content -notmatch '<div id="root"></div>') { throw 'bootstrap_frontend_failed' }
        Write-Host 'Bootstrap local verificado: servidor proprio, frontend e capabilities; zero diagnostico remoto.'
        $finished=$true
        return
    }
    Send-InitLog 'pending' 'Verificando o narrador Groq: texto, JSON e streaming.' 1
    Write-State 'checking_narrator'
    if (-not (Test-OwnedListener)) { throw 'server_ownership_lost' }
    $diagnostic=Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/llm/test-connection' -Method Post -TimeoutSec 70
    [IO.File]::WriteAllText((Join-Path $runDir 'readiness.json'), ($diagnostic | ConvertTo-Json -Depth 30)+"`n", [Text.UTF8Encoding]::new($false))
    if ($diagnostic.configured -ne $true -or $diagnostic.ready -ne $true -or $diagnostic.success -ne $true) {
        Send-InitLog 'error' 'O narrador nao passou na verificacao. O resultado do teste foi preservado.' 1
        throw 'narrator_not_ready'
    }
    Send-InitLog 'success' 'Jogo pronto para uso teste. Boa cacada!' 3
    Write-State 'ready'
    Write-Host ('Jogo pronto: ' + $url)
    Write-Host ('Dados desta sessao: ' + $runDir)
    $null=Read-Host 'Mantenha esta janela aberta enquanto joga. Pressione Enter para encerrar o servidor'
    $finished=$true
} catch {
    # Never echo a credential, native command environment or exception payload.
    Write-State 'failed' 'manual_game_start_failed'
    Write-Host ('Nao foi possivel concluir a abertura. Diagnostico local: ' + $runDir)
} finally {
    $childEnvironment.Remove('LLM_API_KEY')
    if ($null -ne $ApiKey) { $ApiKey.Dispose() }
    if ($null -ne $server) {
        if (-not $server.HasExited) { $server.Kill($true); $server.WaitForExit() }
        if ($null -ne $stdoutTask) { [IO.File]::WriteAllText((Join-Path $runDir 'backend.stdout.log'),$stdoutTask.GetAwaiter().GetResult()) }
        if ($null -ne $stderrTask) { [IO.File]::WriteAllText((Join-Path $runDir 'backend.stderr.log'),$stderrTask.GetAwaiter().GetResult()) }
        if ($finished) { if ($BootstrapCheck) { Write-State 'bootstrap_passed' } else { Write-State 'stopped' } }
    }
}
if (-not $finished) { exit 1 }
