@echo off
setlocal

:: Garante o diretorio do script como CWD
cd /d "%~dp0"

:: Inicializacao de Ambiente Virtual Isolado
if not exist ".venv\Scripts\activate" (
    echo [Sistema] Provisionando ambiente virtual isolado (.venv)...
    python -m venv .venv
    call .venv\Scripts\activate
    echo [Sistema] Instalando dependencias base...
    pip install -r requirements.txt
    pip install Pillow httpx
) else (
    call .venv\Scripts\activate
)

:: Executa a cascata de testes inteligente em Python
python scripts/initialize_game.py

if %errorlevel% neq 0 (
    echo [Sistema] A inicializacao foi interrompida devido a erros.
    pause
    exit /b 1
)

endlocal
