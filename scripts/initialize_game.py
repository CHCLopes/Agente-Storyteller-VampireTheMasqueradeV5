#!/usr/bin/env python3
"""
scripts/initialize_game.py
Inicializador automatizado em cascata com feedback visual em tempo real para Agente Storyteller V5.
"""

import os
import sys
import time
import socket
import subprocess
import webbrowser
import asyncio
import argparse
import logging
import httpx


REQUIRED_LLM_SETTINGS = (
    "LLM_TARGET_ID",
    "LLM_PROVIDER_LABEL",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_ADAPTER_KIND",
    "LLM_STRUCTURED_GENERATION",
    "LLM_STREAMING",
)

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('initialize_game.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class GameInitializerWithFeedback:
    def __init__(self, no_browser=False):
        self.backend_port = 8000
        self.frontend_url = f"http://localhost:{self.backend_port}"
        self.no_browser = no_browser
        self.browser_choice = "0"
        self.client = httpx.AsyncClient(timeout=5.0)

    async def close(self):
        await self.client.aclose()

    async def send_log(self, status: str, message: str, phase: int):
        """Envia log para o backend via POST com fallback para print no terminal"""
        timestamp = time.time() * 1000
        payload = {
            "status": status,
            "message": message,
            "phase": phase,
            "timestamp": timestamp
        }
        
        prefix = {
            "success": "[✓]",
            "error": "[✗]",
            "warning": "[⚠]",
            "pending": "[...]"
        }.get(status, "[*]")
        
        log_msg = f"{prefix} {message}"
        if status == "success":
            logger.info(log_msg)
        elif status == "error":
            logger.error(log_msg)
        elif status == "warning":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        try:
            url = f"http://127.0.0.1:{self.backend_port}/api/initialization/logs"
            res = await self.client.post(url, json=payload)
            if res.status_code != 200:
                logger.warning(f"[Fallback] Servidor respondeu com status {res.status_code}")
        except Exception:
            pass

    def select_browser(self):
        """Menu interativo para escolha de navegador"""
        if self.no_browser:
            self.browser_choice = "0"
            return

        print("=" * 60)
        print("  AGENTE STORYTELLER V5 — SELEÇÃO DE NAVEGADOR")
        print("=" * 60)
        print("\n[?] Qual navegador deseja usar?")
        print("  (1) Chrome (padrão)")
        print("  (2) Firefox")
        print("  (3) Edge")
        print("  (0) Auto-detectar")
        print()
        
        try:
            choice = input("Escolha (0-3) [default: 1]: ").strip()
            if not choice:
                choice = "1"
            if choice not in ["0", "1", "2", "3"]:
                print("[⚠] Escolha inválida. Usando auto-detecção.")
                choice = "0"
            self.browser_choice = choice
        except Exception:
            self.browser_choice = "0"

    def open_browser(self):
        """Abre o navegador com base na escolha"""
        if self.no_browser:
            return

        url = self.frontend_url
        choice = self.browser_choice
        if choice == '1':
            try:
                paths = [
                    "C:/Program Files/Google/Chrome/Application/chrome.exe %s",
                    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s",
                    "chrome %s"
                ]
                opened = False
                for p in paths:
                    try:
                        webbrowser.get(p).open(url)
                        opened = True
                        break
                    except Exception:
                        continue
                if not opened:
                    webbrowser.open(url)
            except Exception:
                webbrowser.open(url)
        elif choice == '2':
            try:
                paths = [
                    "C:/Program Files/Mozilla Firefox/firefox.exe %s",
                    "C:/Program Files (x86)/Mozilla Firefox/firefox.exe %s",
                    "firefox %s"
                ]
                opened = False
                for p in paths:
                    try:
                        webbrowser.get(p).open(url)
                        opened = True
                        break
                    except Exception:
                        continue
                if not opened:
                    webbrowser.open(url)
            except Exception:
                webbrowser.open(url)
        elif choice == '3':
            try:
                paths = [
                    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe %s",
                    "C:/Program Files/Microsoft/Edge/Application/msedge.exe %s",
                    "msedge %s"
                ]
                opened = False
                for p in paths:
                    try:
                        webbrowser.get(p).open(url)
                        opened = True
                        break
                    except Exception:
                        continue
                if not opened:
                    webbrowser.open(url)
            except Exception:
                webbrowser.open(url)
        else:
            webbrowser.open(url)

    def is_port_open(self, port: int) -> bool:
        """Verifica se uma porta local está aberta"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    async def wait_for_port(self, port: int, timeout_sec: int = 15) -> bool:
        """Espera até que a porta especificada abra"""
        start = time.time()
        while time.time() - start < timeout_sec:
            if self.is_port_open(port):
                return True
            await asyncio.sleep(1)
        return False

    async def check_llm_connection(self) -> bool:
        """Valida o alvo explícito pelo diagnóstico canônico de prontidão."""
        url = f"http://127.0.0.1:{self.backend_port}/api/llm/test-connection"
        try:
            # The readiness endpoint performs three fail-fast probes under one
            # 60-second server-side budget.  Keep a small transport margin so
            # a healthy but slower remote target is not reported as offline.
            response = await self.client.post(url, timeout=70.0)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            await self.send_log(
                "error",
                f"Falha ao executar o teste de conexão do alvo LLM: {exc}",
                1,
            )
            return False

        if not isinstance(payload, dict):
            await self.send_log(
                "error",
                "O endpoint de teste do alvo LLM retornou uma resposta inválida.",
                1,
            )
            return False

        if payload.get("configured") is not True:
            required = ", ".join(REQUIRED_LLM_SETTINGS)
            detail = payload.get("message")
            detail_suffix = f" Detalhe: {detail}" if isinstance(detail, str) else ""
            await self.send_log(
                "error",
                f"Configuração LLM incompleta. Preencha explicitamente: {required}. "
                "O perfil OpenRouter também exige LLM_ADAPTER_KIND=openrouter, "
                "LLM_OPENROUTER_PROVIDER e LLM_API_KEY; o perfil Gemini exige "
                "LLM_ADAPTER_KIND=gemini, o endpoint oficial, LLM_API_KEY e "
                "LLM_CAMPAIGN_DATA_ALLOWED=true após revisão da política; o "
                "perfil NVIDIA exige LLM_ADAPTER_KIND=nvidia, NVIDIA NIM, o "
                "endpoint e modelo fixos, LLM_API_KEY e o mesmo opt-in explícito "
                "após revisão da política."
                f"{detail_suffix}",
                1,
            )
            return False

        if payload.get("ready") is not True or payload.get("success") is not True:
            await self.send_log(
                "error",
                "O alvo LLM configurado não passou no diagnóstico de prontidão.",
                1,
            )
            return False

        await self.send_log(
            "success",
            "O alvo LLM configurado passou no diagnóstico de prontidão.",
            1,
        )
        return True

    async def run_backend_server(self) -> bool:
        """Inicia o servidor FastAPI em background se ele não estiver rodando"""
        if self.is_port_open(self.backend_port):
            return True
            
        try:
            venv_python = os.path.join('.venv', 'Scripts', 'python.exe') if sys.platform == 'win32' else os.path.join('.venv', 'bin', 'python')
            if not os.path.exists(venv_python):
                venv_python = 'python'
                
            cmd = [
                venv_python, "-m", "uvicorn", "api.main:app", 
                "--host", "127.0.0.1", 
                "--port", str(self.backend_port)
            ]
            
            subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            return await self.wait_for_port(self.backend_port, timeout_sec=10)
        except Exception:
            return False

    async def run(self) -> bool:
        self.select_browser()

        logger.info("[*] Verificando infraestrutura local...")
        backend_ready = await self.run_backend_server()
        if not backend_ready:
            logger.error("[✗] Erro crítico: Não foi possível iniciar o backend na porta 8000.")
            return False

        await self.send_log("success", "[0/3] Backend disponível", 0)
        await self.send_log("pending", "[1/3] Testando o alvo LLM configurado...", 1)
        if not await self.check_llm_connection():
            return False

        await self.send_log("pending", "[2/3] Abrindo navegador...", 2)
        try:
            self.open_browser()
            await asyncio.sleep(1.0)
            await self.send_log("success", "Navegador aberto com sucesso", 2)
        except Exception as e:
            await self.send_log("error", f"Falha ao abrir navegador: {str(e)}", 2)
            return False

        await self.send_log("success", "[3/3] Sistema Pronto! Boa Caçada! 🦇", 3)
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Inicializador do Agente Storyteller V5")
    parser.add_argument("--no-browser", action="store_true", help="Não abre o navegador automaticamente")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    initializer = GameInitializerWithFeedback(no_browser=args.no_browser)
    try:
        success = asyncio.run(initializer.run())
    except KeyboardInterrupt:
        success = False
    finally:
        asyncio.run(initializer.close())
        
    if not success:
        sys.exit(1)
    sys.exit(0)
