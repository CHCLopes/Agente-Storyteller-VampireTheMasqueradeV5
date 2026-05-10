@echo off
setlocal

:: Variaveis de Ambiente Estritas
set API_PORT=8000
set API_HOST=127.0.0.1

:: Inicializacao de Ambiente Virtual Isolado
if not exist ".venv\Scripts\activate" (
    echo [Sistema] Provisionando ambiente virtual isolado (.venv)...
    python -m venv .venv
    call .venv\Scripts\activate
    echo [Sistema] Instalando dependencias base...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

:: Garantir infraestrutura fisica
python setup_infra.py

:: Validação de Porta do LM Studio via cURL (Ping simulado)
curl -s http://localhost:1234/v1/models >nul 2>&1
if %errorlevel% neq 0 (
    echo [31m[Erro] Servidor do LM Studio nao detectado na porta 1234. Siga o Passo 3 do Manual.[0m
    pause
    exit /b 1
)

:: Iniciar API REST
start "" python -m uvicorn api.main:app --host %API_HOST% --port %API_PORT%

:: UX no Terminal
timeout /t 3 /nobreak >nul
cls
echo ===================================================
echo [Sistema] Coterie de Agentes Online e Aguardando.
echo Endpoint REST local ativo em: http://%API_HOST%:%API_PORT%
echo ===================================================

endlocal
