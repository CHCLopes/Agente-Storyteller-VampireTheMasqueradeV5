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
from pathlib import Path
import httpx

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
        self.lm_studio_port = 1234
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

    def find_lm_studio(self) -> str | None:
        """Verifica se LM Studio está instalado e retorna o executável"""
        try:
            cmd = 'where' if sys.platform == 'win32' else 'which'
            res = subprocess.run([cmd, 'lm-studio'], capture_output=True, text=True)
            if res.returncode == 0:
                path = res.stdout.strip().split('\n')[0]
                if os.path.exists(path):
                    return path
        except Exception:
            pass

        if sys.platform == 'win32':
            user_profile = os.environ.get('USERPROFILE', '')
            program_files = os.environ.get('ProgramFiles', '')
            local_appdata = os.environ.get('LOCALAPPDATA', '')
            
            common_paths = [
                os.path.join(local_appdata, 'Programs', 'lm-studio', 'LM Studio.exe'),
                os.path.join(program_files, 'LM Studio', 'LM Studio.exe'),
                os.path.join(user_profile, 'AppData', 'Local', 'Programs', 'lm-studio', 'LM Studio.exe'),
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        return None

    def start_lm_studio(self, path: str) -> bool:
        """Tenta iniciar o processo do LM Studio"""
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            else:
                subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def is_port_open(self, port: int) -> bool:
        """Verifica se uma porta local está aberta"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def scan_local_models(self) -> list[str]:
        """Procura modelos .gguf na pasta de cache padrão do LM Studio"""
        models_dir = Path.home() / '.cache' / 'lm-studio' / 'models'
        if not models_dir.exists():
            return []
        
        gguf_files = []
        for root, _, files in os.walk(models_dir):
            for file in files:
                if file.endswith('.gguf'):
                    gguf_files.append(file.lower())
        return gguf_files

    def check_recommended_models(self, installed_files: list[str]) -> tuple[list[str], list[str]]:
        """Verifica se os modelos recomendados estão instalados"""
        recommended = {
            'qwen': 'Qwen (ex: qwen2.5-1.5b-instruct)',
            'deepseek': 'DeepSeek (ex: deepseek-r1-distill-qwen-7b)',
            'llama': 'Llama (ex: llama-3.2-3b-instruct)'
        }
        found = []
        missing = []
        
        for key, name in recommended.items():
            is_present = any(key in f for f in installed_files)
            if is_present:
                found.append(name)
            else:
                missing.append(name)
        return found, missing

    async def wait_for_port(self, port: int, timeout_sec: int = 15) -> bool:
        """Espera até que a porta especificada abra"""
        start = time.time()
        while time.time() - start < timeout_sec:
            if self.is_port_open(port):
                return True
            await asyncio.sleep(1)
        return False

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

        await self.send_log("pending", "[0/5] Abrindo navegador...", 0)
        try:
            self.open_browser()
            await asyncio.sleep(1.0)
            await self.send_log("success", "Navegador aberto com sucesso", 0)
        except Exception as e:
            await self.send_log("error", f"Falha ao abrir navegador: {str(e)}", 0)
            return False

        await self.send_log("pending", "[1/5] Detectando LM Studio...", 1)
        lm_path = self.find_lm_studio()
        if not lm_path:
            await self.send_log("error", "LM Studio não encontrado. Instale em https://lmstudio.ai/", 1)
            return False
        await self.send_log("success", f"LM Studio encontrado em: {lm_path}", 1)

        await self.send_log("pending", "[2/5] Iniciando LM Studio...", 2)
        if self.is_port_open(self.lm_studio_port):
            await self.send_log("success", "LM Studio já está respondendo na porta 1234.", 2)
            await self.send_log("success", "[3/5] Porta 1234 disponível", 3)
        else:
            await self.send_log("pending", "LM Studio offline. Iniciando processo local...", 2)
            if not self.start_lm_studio(lm_path):
                await self.send_log("error", "Não foi possível carregar o executável do LM Studio.", 2)
                return False
            
            await self.send_log("pending", "[3/5] Testando porta 1234 (aguardando servidor)...", 3)
            if await self.wait_for_port(self.lm_studio_port, timeout_sec=20):
                await self.send_log("success", "LM Studio carregado e respondendo na porta 1234.", 2)
                await self.send_log("success", "Porta 1234 ativada com sucesso.", 3)
            else:
                await self.send_log("error", "O servidor do LM Studio não respondeu na porta 1234 (timeout 20s).", 3)
                return False

        await self.send_log("pending", "[4/5] Verificando modelos necessários...", 4)
        installed_files = self.scan_local_models()
        found, missing = self.check_recommended_models(installed_files)
        
        if found:
            await self.send_log("success", f"Modelos encontrados: {', '.join(found)}", 4)
        if missing:
            await self.send_log("warning", f"Aviso: Modelos recomendados em falta: {', '.join(missing)}", 4)

        await self.send_log("success", "[5/5] Sistema Pronto! Boa Caçada! 🦇", 5)
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
