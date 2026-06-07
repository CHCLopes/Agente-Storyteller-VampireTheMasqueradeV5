---
PROJECT: Agente Storyteller | Motor Narrativo V5 🦇
STACK: Python (FastAPI), WebSocket, Ollama, Vanilla JS (Frontend)
LAST_SESSION: 2026-06-07
SESSION_COUNT: 10

## DECISIONS_LOCKED
- **Engine Split:** Isolamento total do Motor Mecânico V5 em relação à camada de inferência de linguagem do LLM.
- **Protocol:** Comunicação de tempo real baseada estritamente em canais WebSocket assíncronos.

## CONSTRAINTS
- **Simplicidade Cirúrgica:** Proibido o uso de frameworks ORM pesados ou abstrações corporativas complexas. O backend deve ser enxuto.
- **Isolamento de I/O:** Os arquivos em `client/` estão selados e marcados como FOUNDATION V1. Escrita proibida sem ordem de refatoração de interface.

## FILE_STATUS
| Arquivo | Status | Sessão |
|---|---|---|
| client/index.html | SEALED - Foundation V1 | 1 |
| client/style.css | SEALED - Foundation V1 | 1 |
| client/app.js | SEALED - Foundation V1 | 1 |
| DESIGN.md | COMPLETED | 7 |
| DESIGN_SYSTEM.md | COMPLETED | 8 |
| PRODUTO.md | COMPLETED | 6 |
| pyrightconfig.json | COMPLETED | 9 |
| requirements.txt | COMPLETED | 5 |
| api/core/__init__.py | DONE | 5 |
| api/core/config.py | DONE | 5 |
| .env.example | DONE | 5 |
| api/orchestrator_service.py | DONE | 5 |
| api/parser_service.py | DONE | 5 |
| api/state_service.py | DONE | 5 |
| api/rules_service.py | DONE | 5 |
| tests/test_concurrency.py | COMPLETED | 3 |
| tests/test_websocket_flows.py | COMPLETED | 3 |
| tests/test_remorse.py | COMPLETED | 5 |

## COMPLETED
- [Sessão 10] Criação do commit inicial (root-commit) do repositório contendo fontes, testes e especificações atualizadas, omitindo arquivos temporários.
- [Sessão 9] Correção de desvios de contrato de infraestrutura: criação de pyrightconfig.json e ajuste de stack do frontend no log para Vanilla JS.
- [Sessão 8] Unificação de design system em DESIGN_SYSTEM.md contemplando paletas, componentes, App-Shell e acessibilidade WCAG AA.
- [Sessão 7] Unificação da especificação técnica em DESIGN.md contemplando diagramas ASCII, padrões de código e targets de performance.
- [Sessão 6] Unificação de escopo, restrições e novos Acceptance Criteria (AC 1 a AC 9) em PRODUTO.md com Decision Log arquitetural.
- [Sessão 5] Módulo D: config centralizada via `pydantic-settings`. Módulo C: schema de Humanidade e Remorso com testes aprovados.
- [Sessão 4] Correção de anotação de tipo de `status_override`, e warnings do Pyright com inclusão de `types-aiofiles` e `aiofiles` nas dependências.
- [Sessão 4] Refatoração de `save_session_state` e movimentação de `sync_event_from_context` para `state_service.py` para corrigir assinaturas.
- [Sessão 3] Schemas de estado sob JSON alvo, persistência com asyncio.Lock contra condições de corrida e testes concorrentes de I/O.
- [Sessão 3] Middleware Interceptor em api/main.py contra TORPOR, gatilho de Fome crítica e teste de Frenesi por WebSocket.

## IN_PROGRESS
Bloqueio: NENHUM

## NEXT_STEP
1. Iniciar Módulo A (Evolução e XP) ou Módulo B (Frenesi e Torpor) conforme prioridade definida no plano arquitetural.

## ERROS_ENCONTRADOS_E_RESOLUCOES_IMPLEMENTADAS
- **ValidationError ao instanciar TrackersModel em testes unitários:** O script de validação obrigatório de humanidade e máculas resultava em falha de inicialização por ausência de `health` e `willpower` no payload.
  *Resolução:* Os atributos `health` e `willpower` foram reconfigurados como `Optional[TrackerDetail] = None` em `api/state_service.py` para permitir inicializações e validações parciais no motor e nos testes unitários.
- **Instabilidade no teste test_pipeline_willpower_reroll:** O arquivo residual de teste em disco `test_wp.json` persistia em execuções consecutivas do `pytest`, causando acúmulo indesejado de dano superficial no tracker.
  *Resolução:* Remoção do arquivo residual antes das execuções e limpeza na fixture do teste.
- **TypeError em save_session_state:** A alteração do schema de estado na Sessão 3 gerou exceções nas chamadas que enviavam 4 argumentos posicionais.
  *Resolução:* A assinatura de `save_session_state` foi ajustada para aceitar polimorficamente `StateUpdateEvent` ou `dict`.
- **Erro de Atribuição de Tipos (status_override):** O parâmetro `status_override` estava anotado com o tipo estrito `str` mas possuía valor padrão `None`.
  *Resolução:* A anotação do parâmetro foi alterada de `str` para `Optional[str] = None`.

## BLOCKERS
- NENHUM
