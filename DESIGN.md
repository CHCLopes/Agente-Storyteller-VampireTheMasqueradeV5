# DESIGN.md — Agente Storyteller V5

## Arquitetura Alto Nível
┌─────────────────────────────────────────────────┐
│               Cliente (React 19 + TS)           │
│         /client (Vite + React + TS)             │
└────────────────────┬────────────────────────────┘
│ WebSocket (/ws/session/{id})
↓
┌─────────────────────────────────────────────────┐
│            Backend (FastAPI + Python 3.11)      │
├─────────────────────────────────────────────────┤
│  Camada de Orquestração (main.py)               │
│  ├─ Middleware: Validação de status (TORPOR)   │
│  ├─ Rotas: /roll, /action, /narrative          │
│  └─ WebSocket Manager: Broadcasts             │
├─────────────────────────────────────────────────┤
│  Serviços Especializados                        │
│  ├─ orchestrator_service.py  (Fluxo de turnos) │
│  ├─ state_service.py (Persistência + Locks)    │
│  ├─ parser_service.py (Parsing de ações)       │
│  ├─ rules_service.py (Regras VTM v5)           │
│  └─ config.py (Pydantic-settings)              │
├─────────────────────────────────────────────────┤
│  Persistência (JSON + asyncio.Lock)             │
│  └─ sessions/{session_id}/state.json           │
└─────────────────────────────────────────────────┘
│
↓
┌─────────────────────────────────────────────────┐
│        LM Studio (LLMs Locais)                  │
│  ├─ qwen2.5-1.5b (Árbitro)                     │
│  ├─ deepseek-r1-7b (Memória)                   │
│  └─ llama-3.2-3b (Narrador)                    │
└─────────────────────────────────────────────────┘

## Stack & Rationale

| Componente | Choice | Por Quê |
|---|---|---|
| **Backend** | FastAPI (Python 3.11+) | Async nativa, WebSocket, tipo-seguro, zero boilerplate |
| **WebSocket** | FastAPI WebSockets | Real-time, nativa, sem dependências extras |
| **Persistência** | JSON + aiofiles | Simples, local, offline. Sem overhead de DB |
| **Concorrência** | asyncio.Lock + aiofiles | Previne race conditions em leitura/escrita simultânea |
| **Validação** | Pydantic v2 | Tipo-seguro, validação automática de schemas |
| **Config** | pydantic-settings | Variáveis de ambiente, type-safe |
| **LLMs** | LM Studio local | Offline, controle total, nenhuma API key necessária |
| **Frontend** | React 19 + TypeScript | Interface interativa modularizada com Tailwind CSS v4 e logs estruturados em cascata no HUD |

## Padrões de Código

### Estrutura de Pastas
AgenteStoryteller/
├── api/
│   ├── main.py                  (Orquestração + WebSocket)
│   ├── core/
│   │   ├── init.py
│   │   └── config.py            (Pydantic-settings)
│   ├── orchestrator_service.py  (Fluxo de turnos)
│   ├── state_service.py         (Persistência)
│   ├── rules_service.py         (Regras VTM v5)
│   └── parser_service.py        (Parsing de ações)
├── client/
│   ├── index.html               (Vite Entrypoint)
│   ├── src/                     (React Application)
│   │   ├── App.tsx              (Main Component)
│   │   ├── main.tsx
│   │   ├── components/          (HUD & Actions)
│   │   └── hooks/               (State & WebSockets)
├── client_legacy/               (Legado - Nao utilizar para novos desenvolvimentos)
├── tests/
│   ├── test_concurrency.py
│   ├── test_websocket_flows.py
│   └── test_remorse.py
├── sessions/                    (Diretório de persistência)
├── requirements.txt
├── .env.example
└── pyrightconfig.json           (Type checking)

### Convenções de Naming
- Serviços: `*_service.py` (state_service, rules_service)
- Schemas Pydantic: `*Model` (PlayerSheetModel, StateUpdateEvent)
- Métodos assíncronos: `async def` sempre com `await` explícito
- Locks: `async with <lock>:` para seção crítica

## Padrões Técnicos

### 1. Estado do Personagem (Schemas)
```python
# rules_service.py
class PlayerSheetModel(BaseModel):
    humanidade: int  # 0-10, regra crítica
    fome: int        # 0-5, quando >= 5 → FRENZY_CHECK
    saude: int       # Pontos de vida
    # ... outros atributos
```

### 2. Persistência Concorrente
```python
# state_service.py
async def save_session_state(session_id: str, state: dict):
    async with lock_manager.get_lock(session_id):
        async with aiofiles.open(path, mode='w') as f:
            await f.write(json.dumps(state))
```
**Por quê**: Evita corrupção se 2 requisições tentam gravar ao mesmo tempo.

### 3. WebSocket com Middleware
```python
# main.py
@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    state = await load_session_state(session_id)
    
    # Middleware: Valida TORPOR
    if state['status'] == 'TORPOR':
        await websocket.send_json({"error": "Personagem em torpor"})
        await websocket.close()
        return
    
    # ... resto da lógica
```
**Por quê**: Garante que regras críticas são validadas antes de processar ações.

## Testing Strategy

### Cobertura Esperada
- **Unit**: Schemas Pydantic (validação de dados)
- **Integration**: Fluxo completo (carregar → validar → persistir)
- **Concurrency**: 10+ requisições simultâneas → verificar sync de estado
- **E2E**: WebSocket real-time (conectar → enviar ação → receber narrativa)

### Testes Implementados
- ✅ `test_concurrency.py`: 10 corrotinas gravando ao mesmo tempo → sem corrupção
- ✅ `test_websocket_flows.py`: Fluxo de WebSocket (connect → disconnect)
- ✅ `test_remorse.py`: Validação de Remorso (atributo VTM v5)

## Performance Targets

| Métrica | Target | Crítico? |
|---|---|---|
| Latência WebSocket (roundtrip) | < 100ms (local) | Sim (interação real-time) |
| Tempo de resposta LLM | < 2s (local, 3B model) | Não (aceitável narrativa) |
| Persistência JSON | < 50ms | Sim (não bloquear ação) |
| Memória (backend) | < 200MB | Não (máquina local) |

## Security Constraints

### Dados Sensíveis
- Nenhum dado de usuário (projeto local, 1 jogador)
- Estado do personagem em JSON (sem encriptação necessária)

### Isolamento
- `client/` é SEALED (Foundation V1) — mudanças estruturais requerem decisão explícita
- LLM executa localmente (sem API keys expostas)
- WebSocket usa session_id (sem autenticação, pois é local)

### Compliance
- Nenhum requisito GDPR/CCPA (projeto pessoal, offline)
