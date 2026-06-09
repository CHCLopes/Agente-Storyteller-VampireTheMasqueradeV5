# DESIGN.md — Agente Storyteller V5 — Phase 2.5 (Novo Fluxo de Inicialização)

## Arquitetura Geral

```
┌────────────────────────────────────────────────────────┐
│              INICIAR_JOGO.bat                          │
│  └─ Executa: python scripts/initialize_game.py         │
└─────────────────────┬────────────────────────────────┘
                      ↓
         ┌─────────────────────────┐
         │  Menu de Navegador      │
         │  (input terminal)       │
         │  (1) Chrome (2) Firefox │
         │  (3) Edge   (0) Auto    │
         └────────────┬────────────┘
                      ↓
    ┌─────────────────────────────────────┐
    │  Browser window abre                │
    │  http://localhost:8000              │
    └────────┬─────────────────────────────┘
             ↓
    ┌─────────────────────────────────────┐
    │  React App carrega                  │
    │  InitializationPanel renderizado    │
    └────────┬─────────────────────────────┘
             ↓ (estabelece conexão)
    ┌─────────────────────────────────────┐
    │  useInitializationLog hook           │
    │  ↓ WebSocket /ws/initialization     │
    │  Backend (initialization_manager)    │
    └────────┬─────────────────────────────┘
             ↑ (broadcast logs)
    ┌─────────────────────────────────────┐
    │  Script Python (background)         │
    │  ├─ [0/5] Abrindo navegador        │
    │  ├─ [1/5] Detectando LM Studio     │
    │  ├─ [2/5] Iniciando LM Studio      │
    │  ├─ [3/5] Testando porta 1234      │
    │  ├─ [4/5] Verificando modelos      │
    │  └─ [5/5] Sistema Pronto! 🦇      │
    │                                     │
    │  POST /api/initialization/logs      │
    │  (cada log individualmente)         │
    └─────────────────────────────────────┘
```

---

## IMPLEMENTAÇÃO TÉCNICA

### 1. Hook React: `useInitializationLog.ts`

**Arquivo**: `client/src/hooks/useInitializationLog.ts`

```typescript
import { useState, useEffect, useRef, useCallback } from 'react';

export interface InitLog {
  id: string;
  timestamp: number;
  status: 'pending' | 'success' | 'error' | 'warning';
  message: string;
  phase?: number; // [0/5], [1/5], etc
}

interface UseInitializationLogOptions {
  onComplete?: (success: boolean) => void;
  onError?: (error: string) => void;
}

export const useInitializationLog = (options?: UseInitializationLogOptions) => {
  const [logs, setLogs] = useState<InitLog[]>([]);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Adicionar log manualmente (para testes ou logs local)
  const addLog = useCallback((logData: Partial<InitLog>) => {
    const fullLog: InitLog = {
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      status: 'pending',
      message: '',
      ...logData,
    };

    setLogs((prev) => [...prev, fullLog]);
    return fullLog;
  }, []);

  // Conectar ao WebSocket de inicialização
  useEffect(() => {
    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//localhost:8000/ws/initialization`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        addLog({
          status: 'success',
          message: '[✓] Conectado ao servidor de inicialização',
        });
        console.log('[Init] WebSocket conectado');
      };

      ws.onmessage = (event) => {
        try {
          const logData = JSON.parse(event.data) as InitLog;
          
          // Validar log
          if (!logData.message) {
            console.warn('[Init] Log sem mensagem:', logData);
            return;
          }

          // Adicionar ao estado
          setLogs((prev) => [...prev, logData]);

          // Se erro crítico, marcar como falha
          if (logData.status === 'error') {
            setIsInitializing(false);
            setError(logData.message);
            options?.onError?.(logData.message);
          }

          // Se sucesso final, desbloquear
          if (
            logData.status === 'success' &&
            logData.message.includes('Pronto')
          ) {
            setIsInitializing(false);
            setError(null);
            options?.onComplete?.(true);
          }

          console.log('[Init] Log recebido:', logData);
        } catch (e) {
          console.error('[Init] Parse error:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('[Init] WebSocket error:', error);
        addLog({
          status: 'error',
          message: '[✗] Erro de conexão com servidor de inicialização',
        });
        setIsInitializing(false);
        setError('WebSocket connection error');
        options?.onError?.('WebSocket error');
      };

      ws.onclose = () => {
        console.log('[Init] WebSocket fechado');
        // Tentar reconectar após 2s
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [addLog, options]);

  const retry = useCallback(() => {
    // Re-executar script de inicialização
    setLogs([]);
    setError(null);
    setIsInitializing(true);

    // Enviar sinal para backend re-iniciar
    fetch('/api/initialization/retry', { method: 'POST' });
  }, []);

  return { logs, isInitializing, error, addLog, retry };
};
```

---

### 2. Componente React: `InitializationPanel.tsx`

**Arquivo**: `client/src/components/InitializationPanel.tsx`

```typescript
import React, { useEffect, useRef } from 'react';
import { useInitializationLog, type InitLog } from '../hooks/useInitializationLog';

interface InitializationPanelProps {
  onInitializationComplete: (success: boolean) => void;
}

const LogEntry: React.FC<{ log: InitLog }> = ({ log }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-green-500 dark:text-green-400';
      case 'error':
        return 'text-red-500 dark:text-red-400';
      case 'warning':
        return 'text-yellow-500 dark:text-yellow-400';
      case 'pending':
      default:
        return 'text-zinc-400 dark:text-zinc-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return '✓';
      case 'error':
        return '✗';
      case 'warning':
        return '⚠';
      case 'pending':
      default:
        return '...';
    }
  };

  return (
    <div
      className={`animate-fade-in ${getStatusColor(log.status)} text-sm font-mono`}
    >
      <span className="font-bold">[{getStatusIcon(log.status)}]</span> {log.message}
    </div>
  );
};

export const InitializationPanel: React.FC<InitializationPanelProps> = ({
  onInitializationComplete,
}) => {
  const { logs, isInitializing, error, retry } = useInitializationLog({
    onComplete: (success) => {
      if (success) {
        // Pequeno delay antes de mostrar HUD
        setTimeout(() => onInitializationComplete(true), 500);
      }
    },
    onError: (err) => {
      console.error('[Init] Error:', err);
    },
  });

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Scroll automático para o último log
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="w-full h-screen bg-v5-charcoal dark:bg-v5-charcoal light:bg-v5light-parchment flex flex-col p-8 overflow-hidden">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-4xl font-gothic text-v5-crimson dark:text-v5-crimson light:text-v5light-earth tracking-wider">
          Inicializando Sistema
        </h1>
        <p className="text-zinc-400 dark:text-zinc-400 light:text-zinc-600 text-sm mt-2">
          Aguarde enquanto configuramos o ambiente...
        </p>
      </div>

      {/* Logs Container */}
      <div className="flex-1 overflow-y-auto bg-v5-card dark:bg-v5-card light:bg-v5light-parchment/30 border border-v5-border dark:border-v5-border light:border-v5light-border rounded p-6 space-y-2 mb-6">
        {logs.length === 0 && isInitializing ? (
          <div className="text-zinc-500 dark:text-zinc-500 light:text-zinc-600 italic text-sm">
            Aguardando conexão com o servidor...
          </div>
        ) : (
          logs.map((log) => <LogEntry key={log.id} log={log} />)
        )}
        <div ref={logsEndRef} />
      </div>

      {/* Error State */}
      {error && (
        <div className="mb-4 p-4 bg-red-900/30 dark:bg-red-900/30 light:bg-red-100 border border-red-900 dark:border-red-800 light:border-red-300 rounded">
          <div className="text-red-500 dark:text-red-400 light:text-red-700 font-bold mb-2">
            ✗ Erro de Inicialização
          </div>
          <div className="text-red-400 dark:text-red-300 light:text-red-600 text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Success State */}
      {!isInitializing && !error && logs.length > 0 && (
        <div className="mb-4 p-4 bg-green-900/30 dark:bg-green-900/30 light:bg-green-100 border border-green-900 dark:border-green-800 light:border-green-300 rounded">
          <div className="text-green-500 dark:text-green-400 light:text-green-700 font-bold">
            ✓ Sistema Pronto!
          </div>
          <div className="text-green-400 dark:text-green-300 light:text-green-600 text-sm">
            Carregando interface...
          </div>
        </div>
      )}

      {/* Retry Button */}
      {error && !isInitializing && (
        <div className="flex gap-3">
          <button
            onClick={retry}
            className="px-4 py-2 bg-v5-crimson dark:bg-v5-crimson light:bg-v5light-earth hover:bg-red-700 dark:hover:bg-red-700 light:hover:bg-yellow-700 text-white dark:text-white light:text-white rounded font-serif text-sm font-semibold transition-colors active:scale-95"
          >
            Tentar Novamente
          </button>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-zinc-700 dark:bg-zinc-700 light:bg-zinc-400 hover:bg-zinc-600 dark:hover:bg-zinc-600 light:hover:bg-zinc-300 text-white dark:text-white light:text-black rounded font-serif text-sm font-semibold transition-colors active:scale-95"
          >
            Recarregar Página
          </button>
        </div>
      )}
    </div>
  );
};
```

---

### 3. Tailwind CSS Animation

**Adicionar a `client/src/index.css`**:

```css
@layer utilities {
  @keyframes fade-in {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-fade-in {
    animation: fade-in 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
}
```

---

### 4. Modificar App.tsx

**Arquivo**: `client/src/App.tsx`

```typescript
import React, { useState } from 'react';
import { InitializationPanel } from './components/InitializationPanel';
// ... outros imports

export default function App() {
  const [initializationComplete, setInitializationComplete] = useState(false);

  // Se inicialização não completou, mostrar InitializationPanel
  if (!initializationComplete) {
    return (
      <InitializationPanel
        onInitializationComplete={(success) => {
          if (success) {
            setInitializationComplete(true);
          }
          // Se falhar, fica na tela de erro com botões de retry
        }}
      />
    );
  }

  // Resto do app normal
  const { isDark, toggle: toggleDarkMode } = useDarkMode();
  const characterState = useCharacterState();
  const [narrativeMessages, setNarrativeMessages] = React.useState([]);

  const { isConnected, send: sendWebSocket } = useWebSocket({
    url: 'ws://localhost:8000/ws/session/default',
    onMessage: (data) => {
      if (data.type === 'narrative') {
        setNarrativeMessages((prev) => [...prev, data]);
      } else if (data.type === 'state_update') {
        characterState.updateSheet(data.sheet);
      }
    },
  });

  return (
    <div className={isDark ? 'dark' : 'light'}>
      <div className="min-h-screen bg-v5-charcoal dark:bg-v5-charcoal light:bg-v5light-parchment text-v5-parchment dark:text-v5-parchment light:text-v5light-charcoal font-sans overflow-hidden flex flex-col relative select-none">
        {/* ... resto do componente ... */}
      </div>
    </div>
  );
}
```

---

### 5. Backend: Rota POST e WebSocket

**Arquivo**: `api/main.py`

**Adicionar imports:**

```python
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
```

**Adicionar classe de gerenciamento:**

```python
class InitializationManager:
    """Gerencia WebSocket connections para inicialização"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[Init] Client conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[Init] Client desconectado. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Enviar log para todos os clientes WebSocket"""
        print(f"[Init] Broadcasting: {message['message']}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[Init] Erro ao enviar para client: {e}")

# Instanciar gerenciador global
initialization_manager = InitializationManager()
```

**Adicionar rota POST:**

```python
@app.post("/api/initialization/logs")
async def receive_init_log(log_data: dict):
    """
    Receber log do script Python e distribuir para clientes WebSocket
    
    Payload:
    {
        "status": "pending|success|error|warning",
        "message": "[0/5] Abrindo navegador...",
        "phase": 0,
        "timestamp": 1717856400000
    }
    """
    try:
        # Validar estrutura
        required_fields = ["status", "message"]
        if not all(field in log_data for field in required_fields):
            return {"status": "error", "message": "Missing required fields"}

        # Enriquecer log com timestamp se não houver
        if "timestamp" not in log_data:
            log_data["timestamp"] = int(datetime.now().timestamp() * 1000)

        # Gerar ID único
        log_data["id"] = f"log-{log_data['timestamp']}-{hash(log_data['message']) % 10000}"

        # Broadcast para todos os clientes
        await initialization_manager.broadcast(log_data)

        return {"status": "ok", "log_id": log_data["id"]}
    except Exception as e:
        print(f"[Init] Erro ao processar log: {e}")
        return {"status": "error", "message": str(e)}
```

**Adicionar WebSocket:**

```python
@app.websocket("/ws/initialization")
async def websocket_initialization(websocket: WebSocket):
    """
    WebSocket para inicialização
    Clientes se conectam aqui e recebem logs em tempo real
    """
    await initialization_manager.connect(websocket)
    try:
        while True:
            # Aguardar heartbeat (ou qualquer mensagem) do cliente
            data = await websocket.receive_text()
            # Pode ser usado para validar conexão viva
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        initialization_manager.disconnect(websocket)
    except Exception as e:
        print(f"[Init] WebSocket error: {e}")
        initialization_manager.disconnect(websocket)
```

**Adicionar rota de retry (opcional):**

```python
@app.post("/api/initialization/retry")
async def retry_initialization():
    """
    Endpoint para cliente solicitar retry
    Limpa estado anterior e reseta
    """
    print("[Init] Retry solicitado")
    await initialization_manager.broadcast({
        "status": "pending",
        "message": "[0/5] Reiniciando diagnóstico...",
        "phase": 0,
        "timestamp": int(datetime.now().timestamp() * 1000),
    })
    return {"status": "ok"}
```

---

### 6. Script Python Refatorado: `initialize_game.py`

**Arquivo**: `scripts/initialize_game.py`

```python
#!/usr/bin/env python3
"""
Auto-initialization script for Agente Storyteller V5
Envia logs em tempo real via POST → Backend → WebSocket → Frontend
"""

import subprocess
import sys
import time
import os
import json
import webbrowser
import httpx
import asyncio
from pathlib import Path
from typing import Optional

class GameInitializerWithFeedback:
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.lm_studio_port = 1234
        self.max_retries = 3
        self.phase_counter = 0

    async def send_log(
        self,
        status: str,
        message: str,
        phase: Optional[int] = None
    ):
        """Enviar log para backend via POST"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "status": status,
                    "message": message,
                    "phase": phase,
                    "timestamp": int(time.time() * 1000),
                }
                
                response = await client.post(
                    f"{self.backend_url}/api/initialization/logs",
                    json=payload,
                    timeout=5.0,
                )
                
                if response.status_code != 200:
                    print(f"[!] Erro ao enviar log (HTTP {response.status_code})")
                else:
                    print(f"[+] Log enviado: {message}")
        except Exception as e:
            print(f"[!] Erro ao conectar backend: {e}")
            # Fallback: imprimir no console
            print(f"    {message}")

    def select_browser(self) -> str:
        """Menu interativo para escolher navegador (Opção B)"""
        print("\n" + "="*50)
        print("  AGENTE STORYTELLER V5 — SELEÇÃO DE NAVEGADOR")
        print("="*50)
        print("\n[?] Qual navegador deseja usar?\n")
        print("  (1) Chrome (padrão)")
        print("  (2) Firefox")
        print("  (3) Edge")
        print("  (0) Auto-detectar")
        print()

        try:
            choice = input("Escolha (0-3): ").strip()
            
            match choice:
                case "1":
                    return "chrome"
                case "2":
                    return "firefox"
                case "3":
                    return "edge"
                case "0":
                    return "default"
                case _:
                    print("[!] Opção inválida. Usando auto-detectar.")
                    return "default"
        except Exception as e:
            print(f"[!] Erro ao ler input: {e}")
            return "default"

    def check_lm_studio_installed(self) -> bool:
        """Verifica se LM Studio está instalado"""
        try:
            # Procurar em caminhos comuns do Windows
            common_paths = [
                Path.home() / "AppData" / "Local" / "Programs" / "lm-studio" / "LM Studio.exe",
                Path("C:/Program Files/LM Studio/LM Studio.exe"),
                Path("C:/Program Files (x86)/LM Studio/LM Studio.exe"),
            ]
            
            for path in common_paths:
                if path.exists():
                    print(f"[+] LM Studio encontrado em: {path}")
                    return True
            
            # Tentar via PATH
            result = subprocess.run(
                ["where" if sys.platform == "win32" else "which", "lm-studio"],
                capture_output=True,
                timeout=2,
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[!] Erro ao verificar LM Studio: {e}")
            return False

    def start_lm_studio(self) -> bool:
        """Tenta iniciar LM Studio"""
        try:
            if sys.platform == "win32":
                # Windows
                subprocess.Popen(
                    "lm-studio",
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif sys.platform == "darwin":
                # macOS
                subprocess.Popen(
                    ["open", "-a", "LM Studio"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                # Linux
                subprocess.Popen(
                    ["lm-studio"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            
            print("[+] LM Studio iniciado")
            return True
        except Exception as e:
            print(f"[!] Erro ao iniciar LM Studio: {e}")
            return False

    async def test_port_available(self, port: int, timeout: int = 10) -> bool:
        """Testa se a porta está aberta (com retry)"""
        import socket
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                
                if result == 0:
                    print(f"[+] Porta {port} disponível")
                    return True
            except Exception as e:
                print(f"[!] Erro ao testar porta: {e}")
            
            await asyncio.sleep(0.5)
        
        print(f"[!] Porta {port} não respondeu após {timeout}s")
        return False

    def test_models_installed(self) -> dict:
        """Testa quais modelos estão instalados"""
        required_models = [
            "qwen2.5-1.5b-instruct",
            "deepseek-r1-distill-qwen-7b",
            "llama-3.2-3b-instruct"
        ]
        
        models_dir = Path.home() / ".cache" / "lm-studio" / "models"
        installed = {}
        
        for model in required_models:
            model_path = models_dir / model
            installed[model] = model_path.exists()
            status = "✓" if installed[model] else "✗"
            print(f"    {status} {model}")
        
        return installed

    async def run(self):
        """Execução principal em cascata com feedback"""
        
        try:
            # ============================================================
            # FASE 0: Abrindo Navegador
            # ============================================================
            await self.send_log(
                "pending",
                "[0/5] Abrindo navegador...",
                phase=0
            )
            
            browser = self.select_browser()
            
            try:
                webbrowser.get(browser).open("http://localhost:8000")
                await self.send_log(
                    "success",
                    "[✓] Navegador aberto com sucesso",
                    phase=0
                )
            except Exception as e:
                await self.send_log(
                    "error",
                    f"[✗] Erro ao abrir navegador: {e}. Visite http://localhost:8000 manualmente.",
                    phase=0
                )
                return False

            # Aguardar navegador carregar (2s)
            await asyncio.sleep(2)

            # ============================================================
            # FASE 1: Detectando LM Studio
            # ============================================================
            await self.send_log(
                "pending",
                "[1/5] Detectando LM Studio...",
                phase=1
            )
            
            if not self.check_lm_studio_installed():
                await self.send_log(
                    "error",
                    "[✗] LM Studio não encontrado. Instale em https://lmstudio.ai/",
                    phase=1
                )
                return False
            
            await self.send_log(
                "success",
                "[✓] LM Studio encontrado",
                phase=1
            )

            # ============================================================
            # FASE 2: Iniciando LM Studio
            # ============================================================
            await self.send_log(
                "pending",
                "[2/5] Iniciando LM Studio...",
                phase=2
            )
            
            if not self.start_lm_studio():
                await self.send_log(
                    "error",
                    "[✗] Erro ao iniciar LM Studio",
                    phase=2
                )
                return False
            
            await self.send_log(
                "success",
                "[✓] LM Studio iniciado",
                phase=2
            )

            # ============================================================
            # FASE 3: Testando Porta 1234
            # ============================================================
            await self.send_log(
                "pending",
                "[3/5] Testando porta 1234...",
                phase=3
            )
            
            if not await self.test_port_available(self.lm_studio_port):
                await self.send_log(
                    "error",
                    f"[✗] Porta {self.lm_studio_port} não disponível. LM Studio pode estar bloqueado.",
                    phase=3
                )
                return False
            
            await self.send_log(
                "success",
                "[✓] Porta 1234 disponível",
                phase=3
            )

            # ============================================================
            # FASE 4: Verificando Modelos
            # ============================================================
            await self.send_log(
                "pending",
                "[4/5] Verificando modelos necessários...",
                phase=4
            )
            
            models = self.test_models_installed()
            missing = [m for m, installed in models.items() if not installed]
            
            if missing:
                await self.send_log(
                    "warning",
                    f"[⚠] Modelos faltando: {', '.join(missing[:2])}... "
                    f"Baixe em LM Studio → Model Search",
                    phase=4
                )
            else:
                await self.send_log(
                    "success",
                    "[✓] Todos os modelos encontrados",
                    phase=4
                )

            # ============================================================
            # FASE 5: Sucesso! Sistema Pronto
            # ============================================================
            await self.send_log(
                "success",
                "[✓] [5/5] Sistema Pronto! Boa Caçada 🦇",
                phase=5
            )

            print("\n" + "="*50)
            print("  ✓ INICIALIZAÇÃO COMPLETA")
            print("="*50)
            print("\nAcesse: http://localhost:8000")
            print("Navegador deve estar aberto em poucos segundos...\n")

            return True

        except Exception as e:
            await self.send_log(
                "error",
                f"[✗] Erro inesperado: {e}",
                phase=None
            )
            return False

async def main():
    init = GameInitializerWithFeedback()
    success = await init.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 7. Atualizar INICIAR_JOGO.bat

**Arquivo**: `INICIAR_JOGO.bat`

```batch
@echo off
REM INICIAR_JOGO.bat — Agente Storyteller V5
REM Executa o script de inicialização Python

cd /d "%~dp0"

echo [*] Iniciando Agente Storyteller V5...
echo.

REM Ativar virtual environment
call .venv\Scripts\activate.bat

REM Rodar script de inicialização
python scripts/initialize_game.py

REM Manter janela aberta se houver erro
if errorlevel 1 (
    echo.
    echo [!] Erro durante inicialização
    pause
)

exit /b %errorlevel%
```

---

## FLUXO VISUAL COMPLETO

```
┌─────────────────────────────────────────────────────────┐
│ DUPLO-CLIQUE: INICIAR_JOGO.lnk                          │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ Terminal (Script Python)                                │
│                                                         │
│ [?] Qual navegador deseja usar?                        │
│   (1) Chrome   (2) Firefox   (3) Edge   (0) Auto       │
│ Escolha: 1                                              │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ Browser abre: http://localhost:8000                    │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ React App carrega                                       │
│                                                         │
│ ═══════════════════════════════════════════════════════ │
│  Inicializando Sistema                                 │
│ ═══════════════════════════════════════════════════════ │
│                                                         │
│  Aguardando conexão com o servidor...                 │
│                                                         │
└────────────────┬────────────────────────────────────────┘
                 ↓
                (WebSocket conecta)
                 ↓
┌─────────────────────────────────────────────────────────┐
│ InitializationPanel                                     │
│                                                         │
│ ═══════════════════════════════════════════════════════ │
│  Inicializando Sistema                                 │
│ ═══════════════════════════════════════════════════════ │
│                                                         │
│  [✓] Conectado ao servidor de inicialização           │
│  [...] [0/5] Abrindo navegador...                     │
│  [✓] Navegador aberto com sucesso                     │
│  [...] [1/5] Detectando LM Studio...                  │
│  [✓] LM Studio encontrado                             │
│  [...] [2/5] Iniciando LM Studio...                   │
│  [✓] LM Studio iniciado                               │
│  [...] [3/5] Testando porta 1234...                   │
│  [✓] Porta 1234 disponível                            │
│  [...] [4/5] Verificando modelos necessários...       │
│  [✓] Todos os modelos encontrados                     │
│  [✓] [5/5] Sistema Pronto! Boa Caçada 🦇            │
│                                                         │
│  ✓ Sistema Pronto!                                     │
│  Carregando interface...                               │
│                                                         │
└────────────────┬────────────────────────────────────────┘
                 ↓ (fade-out 0.5s)
┌─────────────────────────────────────────────────────────┐
│ HUD Renderizado (Ficha do PC)                          │
│                                                         │
│  ┌─────────────┐         ┌──────────────────────────┐ │
│  │ Atributos   │         │ Log Narrativo            │ │
│  │ Força: 3    │         │                          │ │
│  │ Destreza: 2 │         │ [Sistema] Pronto!       │ │
│  │ ...         │         │                          │ │
│  └─────────────┘         └──────────────────────────┘ │
│                                                         │
│  Chat Ativo ✓                                           │
│  WebSocket Conectado ✓                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
                 ↓
            🦇 JOGO COMEÇAR 🦇
```

---

## Tratamento de Erros

### Erro: LM Studio não encontrado
```
[✗] LM Studio não encontrado. Instale em https://lmstudio.ai/

[Tentar Novamente] [Recarregar Página]
```

### Erro: Porta 1234 bloqueada
```
[✗] Porta 1234 não disponível. LM Studio pode estar bloqueado.

[Tentar Novamente] [Recarregar Página]
```

### Erro: WebSocket não conecta
```
[✗] Erro de conexão com servidor de inicialização

[Tentar Novamente] [Recarregar Página]
```

---

## Validação de Requisitos

- [ ] Init.1: Script abre navegador automaticamente
- [ ] Init.2: Menu interativo (Chrome/Firefox/Edge/Auto)
- [ ] Init.3: InitializationPanel renderiza no client
- [ ] Init.4: Script envia logs via POST → WebSocket
- [ ] Init.5: Logs em cascata (fade-in, cores, scroll)
- [ ] Init.6: Fim com sucesso (HUD) ou erro (retry)

---

**Status**: Pronto para implementação. Aguardando execução no Antigravity.
