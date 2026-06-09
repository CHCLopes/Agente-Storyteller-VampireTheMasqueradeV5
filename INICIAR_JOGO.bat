@echo off
setlocal enabledelayedexpansion

:: Garante o diretorio do script como CWD
cd /d "%~dp0"

echo ═════════════════════════════════════════════════════════════
echo  AGENTE STORYTELLER V5 — INICIALIZAÇÃO
echo ═════════════════════════════════════════════════════════════
echo.

:: Passo 0: Build frontend se necessário
echo [0/4] Verificando build do frontend...
if not exist "client\dist\index.html" (
    echo [CRIANDO] Build do frontend...
    cd client
    call npm run build
    if errorlevel 1 (
        echo [ERRO] npm build falhou
        pause
        exit /b 1
    )
    cd ..
    echo [OK] Frontend compilado
) else (
    echo [OK] Frontend ja compilado
)
echo.

:: Passo 1: Verificar Python
echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH
    echo.
    echo Solucao:
    echo   1. Instale Python de https://www.python.org/
    echo   2. Marque "Add Python to PATH" durante instalacao
    echo   3. Reinicie o computador
    echo.
    pause
    exit /b 1
)
echo [OK] Python encontrado
echo.

:: Passo 2: Criar/ativar venv
echo [2/4] Configurando ambiente virtual...
if not exist ".venv\Scripts\activate.bat" (
    echo [CRIANDO] Ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Nao foi possivel criar .venv
        pause
        exit /b 1
    )
)
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERRO] Nao foi possivel ativar .venv
    pause
    exit /b 1
)
echo [OK] Ambiente virtual ativado
echo.

:: Passo 3: Instalar dependências
echo [3/4] Instalando dependencias...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Nao foi possivel instalar dependencias
    echo.
    echo Tente manualmente:
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas
echo.

:: Passo 4: Executar script de inicialização
echo [4/4] Inicializando jogo...
echo.
python scripts\initialize_game.py

:: Capturar erro
set SCRIPT_ERROR=%errorlevel%

echo.
echo ═════════════════════════════════════════════════════════════

if %SCRIPT_ERROR% equ 0 (
    echo [SUCESSO] Inicializacao concluida!
    echo.
    echo Se o navegador nao abriu, acesse manualmente:
    echo   http://localhost:8000
    echo.
) else (
    echo [ERRO] Inicializacao falhou com codigo: %SCRIPT_ERROR%
    echo.
    echo Verifique a saida acima para mensagens de erro.
    echo Se o terminal fechou sem mensagem, verifique:
    echo   1. Python esta em PATH? (python --version)
    echo   2. requirements.txt foi instalado? (pip list)
    echo   3. Backend esta rodando? (python api/main.py)
    echo.
)

pause
endlocal
