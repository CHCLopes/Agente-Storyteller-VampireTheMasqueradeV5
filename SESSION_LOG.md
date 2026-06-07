---
PROJECT: Agente Storyteller | Motor Narrativo V5 🦇
STACK: Python (FastAPI), WebSocket, Ollama, Vanilla JS (Frontend)
LAST_SESSION: 2026-06-07
SESSION_COUNT: 9

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
- [Sessão 9] Correção de desvios de contrato de infraestrutura: criação do arquivo de tipagem pyrightconfig.json e ajuste de especificação da stack de frontend no log para Vanilla JS.
- [Sessão 8] Unificação das especificações de design system em DESIGN_SYSTEM.md contemplando paletas de cores, tipografia, componentes base, layout em ASCII (App-Shell), espaçamento, tokens equivalentes, ícones e diretrizes de acessibilidade WCAG AA.
- [Sessão 7] Unificação da especificação técnica em DESIGN.md contemplando diagrama arquitetural ASCII detalhado, padrões de código/naming, implementações de referência e metas de performance.
- [Sessão 6] Unificação do escopo, restrições e novos Acceptance Criteria (AC 1 a AC 9) em PRODUTO.md, integrando o Decision Log arquitetural histórico.
- [Sessão 5] Módulo D: config centralizada via `pydantic-settings`. Módulo C: schema de Humanidade e Remorso implementado com teste unitário aprovado.
- [Sessão 4] Correção de anotação de tipo estrito para `status_override` (`Optional[str]`) mitigando erros de atribuição no analisador estático (Pyright).
- [Sessão 4] Resolução de warnings do Pyright através da inclusão e instalação de `types-aiofiles` e `aiofiles` nas dependências.
- [Sessão 4] Refatoração da assinatura de `save_session_state` e movimentação de `sync_event_from_context` para `state_service.py` para suportar polimorfismo de payloads e corrigir erros de assinatura (`TypeError`).
- [Sessão 3] Implementação dos schemas Pydantic de estado sob o contrato JSON alvo, persistência assíncrona protegida por asyncio.Lock contra condições de corrida, e escrita de testes concorrentes de estresse I/O.
- [Sessão 3] Codificação do Middleware Interceptor em api/main.py barrando ações quando o personagem está em TORPOR.
- [Sessão 3] Acoplamento do gatilho de Fome crítica (Fome >= 5) forçando estado de FRENZY_CHECK com bloqueio estruturado de turnos, e resolução interativa de teste de autocontrole por WebSocket.
- [Sessão 1] Implementação total da "Dark UI V5" (Frontend Passivo), Macro-Geometria Desktop (Grid 2/3 e 1/3) com App-Shell, Acessibilidade WCAG AA, e Single DOM responsivo.

## IN_PROGRESS
Bloqueio: NENHUM

## NEXT_STEP
1. Iniciar Módulo A (Evolução e XP) ou Módulo B (Frenesi e Torpor) conforme prioridade definida no plano arquitetural.

## ERROS_ENCONTRADOS_E_RESOLUCOES_IMPLEMENTADAS
- **ValidationError ao instanciar TrackersModel em testes unitários:** O script de validação obrigatório de humanidade e máculas resultava em falha de inicialização por ausência de `health` e `willpower` no payload.
  *Resolução:* Os atributos `health` e `willpower` foram reconfigurados como `Optional[TrackerDetail] = None` em `api/state_service.py` para permitir inicializações e validações parciais no motor e nos testes unitários, sem alterar a desserialização de dados já existentes.
- **Instabilidade no teste test_pipeline_willpower_reroll:** O arquivo residual de teste em disco `test_wp.json` persistia em execuções consecutivas do `pytest`, causando acúmulo indesejado de dano superficial no tracker de vida e quebrando a asserção do turno 1.
  *Resolução:* Remoção manual do arquivo residual antes das execuções e recomendação de limpeza na fixture do teste.
- **Warning de Tipagem do Pyright (Falta de Stubs):** Ausência de stubs de tipo para o módulo `aiofiles`.
  *Resolução:* Adicionados `aiofiles` e `types-aiofiles` ao arquivo `requirements.txt` e instalados no ambiente virtual `.venv`.
- **TypeError em save_session_state:** A alteração do schema de estado na Sessão 3 mudou a assinatura da função de persistência para receber um objeto `StateUpdateEvent`, gerando exceções nas chamadas em `api/orchestrator_service.py` que enviavam 4 argumentos posicionais.
  *Resolução:* A função `sync_event_from_context` foi movida para `api/state_service.py`. A assinatura de `save_session_state` foi ajustada para aceitar polimorficamente `StateUpdateEvent` ou `dict` (que é convertido internamente via `sync_event_from_context`), além de aceitar argumentos posicionais adicionais para retrocompatibilidade.
- **Erro de Atribuição de Tipos (status_override):** O parâmetro `status_override` na função `sync_event_from_context` estava anotado com o tipo estrito `str` mas possuía valor padrão `None`, além de receber literais com valor opcional no fluxo do WebSocket.
  *Resolução:* A anotação do parâmetro foi alterada de `str` para `Optional[str] = None`.

## BLOCKERS
- NENHUM
---