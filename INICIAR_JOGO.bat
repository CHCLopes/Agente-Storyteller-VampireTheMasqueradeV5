@echo off
setlocal

:: Variaveis de Ambiente Estritas
set OLLAMA_MODELS=.\models
set API_PORT=8000
set API_HOST=127.0.0.1

echo [Agente Storyteller] Inicializando Motor V5...
echo Modelos isolados em: %OLLAMA_MODELS%

:: Garantir infraestrutura fisica
python setup_infra.py

:: Iniciar API REST
echo [Agente Storyteller] Iniciando FastAPI Backend...
python -m uvicorn api.main:app --host %API_HOST% --port %API_PORT% --reload

endlocal
