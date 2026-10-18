---
goal: Implementar a fronteira LLM-001 e o fluxo transacional de turnos, eventos e memória do Agente Storyteller
version: 1.2
date_created: 2026-08-24
last_updated: 2026-08-25
owner: Codex
status: 'Completed'
tags: [architecture, feature, llm, persistence, migration, testing]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Este plano implementa, no monólito modular local-first existente, a fronteira agnóstica LLM-001 e um fluxo de turno no qual resultados determinísticos, narrativa, eventos canônicos, memória derivada, relações e estado são validados e confirmados em uma única transação. O checkout original permanece somente leitura; todas as mudanças ocorrem neste worktree.

Decisões humanas preservadas: ARC-001 (monólito modular local-first), LLM-001 (fronteira agnóstica e sem troca silenciosa) e a arquitetura em camadas de eventos/memória. Escolhas técnicas delegadas para esta implementação: SQLite da biblioteca padrão, protocolo interno, schema/migração e integração incremental. Permanecem fora de escopo LLM-002/003, seleção de provedores/modelos, roteamento, orçamento monetário e fallback.

## 1. Requirements & Constraints

- **REQ-001**: Toda chamada de domínio para LLM deve atravessar um contrato interno agnóstico de provedor; somente `api/llm/adapters/` pode conhecer `httpx`, Chat Completions, SSE ou tipos específicos de integração.
- **REQ-002**: Cada invocação deve receber um alvo explícito e imutável composto por `target_id`, rótulo de provedor e `model`; adaptador e endpoint são vinculados somente no composition root, e qualquer divergência entre modelo solicitado e modelo efetivamente reportado deve falhar conservadoramente.
- **REQ-003**: O contrato deve expor capabilities com suporte `native`, `emulated`, `unsupported` ou `unknown`; requisitos não atendidos devem falhar antes do dispatch e nenhuma degradação pode ocorrer silenciosamente.
- **REQ-004**: Streaming deve produzir eventos ordenados, no máximo um terminal, nenhum delta após o terminal e distinção entre conclusão, falha, timeout e cancelamento; saída parcial nunca equivale a sucesso.
- **REQ-005**: Geração estruturada deve associar um JSON Schema derivado de modelo Pydantic à requisição e somente retornar sucesso após validação Pydantic local.
- **REQ-006**: Cancelamento deve ser distinto de timeout, e toda chamada deve usar deadline finito de ponta a ponta.
- **REQ-007**: Erros devem ser normalizados em taxonomia neutra, preservando apenas metadados seguros como categoria, retryability, status e `retry_after`; respostas, headers, prompts e segredos não podem vazar.
- **REQ-008**: Resultados devem carregar proveniência solicitada e efetiva, versão do adaptador, usage reportado ou indisponível e custo reportado, estimado ou indisponível; ausência nunca deve virar zero.
- **REQ-009**: Deve existir teste sintético explícito de conexão sem dados de campanha e suíte de conformidade offline com adaptador falso.
- **REQ-010**: H0, H1, H4 e H6 devem usar a mesma fronteira LLM; fallbacks determinísticos existentes permanecem na aplicação e devem ser observáveis, sem troca de alvo.
- **REQ-011**: Os módulos de regras existentes continuam sendo autoridade para cálculos, invariantes e transições; seus resultados devem ser preservados como fatos estruturados e não reduzidos apenas a texto.
- **REQ-012**: Cada turno narrativo deve criar um rascunho em cópia do estado, montar contexto estruturado, gerar narrativa, validar candidatos de memória e somente então promover estado, narrativa, eventos, relações e memória ao estado canônico.
- **REQ-013**: Falha, timeout ou cancelamento da narrativa deve preservar o snapshot canônico anterior; a tentativa e qualquer conteúdo parcial conhecido podem ser auditados separadamente sem confirmar fatos do turno.
- **REQ-014**: Eventos canônicos devem ser imutáveis e conter identificadores estáveis, ordem, fatos/resultados, fontes determinísticas, atores, lugar, tempo, importância, visibilidade, pendência e referências.
- **REQ-015**: Candidatos de memória somente podem resumir eventos referenciados, não podem criar fatos, alterar resultados mecânicos ou ampliar visibilidade; somente candidatos validados geram memória episódica.
- **REQ-016**: A recuperação de contexto deve filtrar visibilidade antes de pontuar e selecionar por relevância, recência, importância e pendência, com desempate determinístico e orçamento de tokens configurável.
- **REQ-017**: Contexto quente de cena, memória episódica, estado semântico do mundo e arcos/pendências devem ser camadas distintas no pacote enviado ao narrador.
- **REQ-018**: Consolidações de cena e sessão devem ser explícitas, versionadas, idempotentes e preservar `source_event_ids`; nenhuma fonte pode ser apagada ou sobrescrita.
- **REQ-019**: Persistência deve usar SQLite da biblioteca padrão, transações `BEGIN IMMEDIATE`, foreign keys e WAL, sem ORM ou dependência nova; uma transação deve confirmar todo o agregado do turno. Snapshots e turnos usam CAS por `state_revision`; tentativas pendentes anteriores ao início do processo são recuperadas conservadoramente. O MVP continua explicitamente limitado a um único processo/worker.
- **REQ-020**: Migração dos três JSON legados deve ser lazy, idempotente, validada e não destrutiva; arquivos legados não podem ser apagados, renomeados, reformatados ou sobrescritos.
- **REQ-021**: O protocolo WebSocket deve preservar os nomes de eventos existentes, acrescentar `turn_id`, terminal tipado e histórico reidratável, e nunca promover chunks parciais a narrativa concluída.
- **REQ-022**: A seleção de provedor/modelo permanece fora de escopo; o adaptador OpenAI-compatible é somente uma ponte de protocolo e exige configuração explícita, sem fallback para outro target.
- **SEC-001**: `.env` não pode ser aberto, reproduzido, registrado, copiado ou incluído no diff; segredos somente entram no adaptador por `SecretStr` e nunca em representações ou exceções.
- **CON-001**: O checkout original, externo a este worktree, deve permanecer intocado e no commit `5e563824fcba4c53cc37b5084a8ce65f3fa30356`.
- **CON-002**: Não introduzir cloud, microsserviços, provedor específico, roteamento multi-provider, orçamento monetário, tabela de preços, retry automático de transporte ou fallback de modelo; permanece permitida apenas a repetição de validação estruturada H1 já especificada, no mesmo alvo e deadline.
- **CON-003**: Não reescrever motores de regras, catálogos JSON, frontend ou infraestrutura além do necessário para o fluxo autorizado.
- **CON-004**: Usar o menor conjunto coerente de mudanças, manter compatibilidade das assinaturas públicas quando viável e diferenciar falhas preexistentes de regressões.
- **GUD-001**: Defaults locais reversíveis: deadline H0 15 s, H1 30 s, H4 20 s e H6 60 s; orçamento de contexto 2400 tokens estimados; pesos de recuperação configuráveis, não tratados como política de custo.
- **GUD-002**: Vocabulário de visibilidade interno: `public`, `player`, `storyteller` e `system`; candidatos e consolidações derivados nunca podem aumentar o alcance da visibilidade da fonte mais restritiva.
- **PAT-001**: Usar composition root em `api/llm/runtime.py`, injeção opcional para testes, modelos Pydantic imutáveis para contratos e `asyncio.to_thread` para operações SQLite bloqueantes.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Estabelecer o contrato LLM-001, o adaptador isolado e a suíte de conformidade offline.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Criar `api/llm/contract.py` com alvos, mensagens, requests, capabilities, eventos de stream, resultados, proveniência, usage/cost, cancelamento e teste de conexão; tornar value objects imutáveis. | [x] | 2026-08-24 |
| TASK-002 | Incluir no contrato a taxonomia neutra e conversão segura para eventos/resultados sem tipos HTTP. Depende de TASK-001. | [x] | 2026-08-24 |
| TASK-003 | Definir `LLMGateway` com preflight de capabilities, deadline ponta a ponta, cancelamento, validação estruturada e normalização de terminal único. Depende de TASK-001 e TASK-002. | [x] | 2026-08-24 |
| TASK-004 | Criar `api/llm/adapters/openai_compatible.py` como único adaptador que importa `httpx`, mapeando Chat Completions e SSE para o contrato sem escolher provedor. Depende de TASK-001 e TASK-002. | [x] | 2026-08-24 |
| TASK-005 | Refatorar `api/core/config.py` e criar `api/llm/runtime.py` para composição explícita a partir de campos neutros, preservando aliases legados sem default remoto nem troca silenciosa. Depende de TASK-001 a TASK-004. | [x] | 2026-08-24 |
| TASK-006 | Criar a suíte `tests/llm/` e um adaptador falso offline; cobrir invariantes REQ-002 a REQ-009. Depende de TASK-001 a TASK-005. | [x] | 2026-08-24 |
| TASK-007 | Adicionar teste AST que falha se `httpx`, protocolo ou autorização vazarem para fora do adaptador. Depende de TASK-004. | [x] | 2026-08-24 |

### Implementation Phase 2

- GOAL-002: Migrar H0, H1, H4 e H6 para a fronteira LLM sem alterar a autoridade dos módulos determinísticos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-008 | Refatorar `api/h0_controller_service.py` para geração estruturada tipada com gateway injetável e fallback determinístico observável. Depende de GOAL-001. | [x] | 2026-08-24 |
| TASK-009 | Refatorar `api/parser_service.py` para gerar apenas `H1IntentPayload` semântico, com uma repetição explícita no mesmo target e validação local; `V5ActionPayload`, autorização e dificuldade permanecem determinísticos. Depende de GOAL-001. | [x] | 2026-08-24 |
| TASK-010 | Refatorar `api/h4_lore_expert_service.py` para geração textual via gateway e fallback estático na camada de aplicação. Depende de GOAL-001. | [x] | 2026-08-24 |
| TASK-011 | Refatorar H6 em `api/orchestrator_service.py` para consumir eventos tipados de stream, propagar cancelamento/deadline e acumular narrativa/proveniência/usage sem HTTP direto. Depende de GOAL-001. | [x] | 2026-08-24 |
| TASK-012 | Atualizar testes de integração LLM para usar fake gateway e provar que todos os fallbacks permanecem no mesmo alvo e são observáveis. Depende de TASK-008 a TASK-011. | [x] | 2026-08-24 |

### Implementation Phase 3

- GOAL-003: Criar modelos de eventos, memória, contexto e recuperação determinística.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-013 | Criar `api/turn_models.py` com `CanonicalFact`, `CanonicalEvent`, `TurnDraft`, `NarrativeRecord`, `MemoryCandidate`, `EpisodicMemory` e `Consolidation`, todos versionados e com referências validadas. | [x] | 2026-08-24 |
| TASK-014 | Criar `api/context_service.py` com camadas separadas, filtro de visibilidade, estimativa de tokens, score configurável de relevância/recência/importância/pendência e seleção determinística sob orçamento. Depende de TASK-013. | [x] | 2026-08-24 |
| TASK-015 | Criar `api/memory_service.py` compatível com o novo modelo: derivação semântica de candidatos a partir de eventos+narrativa, validação de fontes/visibilidade/fatos, promoção episódica e consolidação versionada. Depende de TASK-013. | [x] | 2026-08-24 |
| TASK-016 | Estender `api/orchestrator_service.py` para preservar resultados dos motores em `TurnDraft.facts` e projetar `system_log` apenas como visão textual. Depende de TASK-013. | [x] | 2026-08-24 |
| TASK-017 | Criar testes de eventos/contexto/memória para imutabilidade, integridade referencial, não ampliação de visibilidade, orçamento, score, candidatos inválidos e consolidação source-preserving. Depende de TASK-013 a TASK-016. | [x] | 2026-08-24 |

### Implementation Phase 4

- GOAL-004: Implementar o repositório SQLite transacional e a migração legada não destrutiva.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-018 | Criar `api/persistence.py` com schema SQLite versionado e migrações transacionais para campanhas, tentativas, turnos, eventos, candidatos, memórias e consolidações; habilitar WAL, foreign keys e transações explícitas. Depende de TASK-013. | [x] | 2026-08-24 |
| TASK-019 | Implementar `commit_turn` idempotente por `operation_id`, confirmando snapshot, relações, narrativa, fatos/eventos e memória em uma única transação; rejeitar duplicação e turnos não monotônicos. Depende de TASK-018. | [x] | 2026-08-24 |
| TASK-020 | Implementar registro de tentativa terminal falha/cancelada/timeout sem promover o rascunho canônico. Depende de TASK-018. | [x] | 2026-08-24 |
| TASK-021 | Implementar migração lazy dos JSON de estado, memória e relações, com hash dos arquivos, tabela `legacy_imports`, validação e import idempotente; nunca escrever nos legados. Depende de TASK-018. | [x] | 2026-08-24 |
| TASK-022 | Adaptar `api/state_service.py` e `api/relationship_service.py` como projeções/reposições de compatibilidade sobre SQLite, mantendo APIs usadas pelo restante do backend. Depende de TASK-019 e TASK-021. | [x] | 2026-08-24 |
| TASK-023 | Criar testes com bancos/diretórios temporários para atomicidade, rollback, concorrência, restart, idempotência e preservação byte a byte dos fixtures legados. Depende de TASK-018 a TASK-022. | [x] | 2026-08-24 |

### Implementation Phase 5

- GOAL-005: Integrar o commit pós-narrativa ao WebSocket e fornecer recuperação/consolidação operacionais.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-024 | Refatorar `api/main.py` para validar e prealocar uma operação idempotente, clonar o contexto, produzir `TurnDraft`, montar contexto em camadas, transmitir chunks provisórios e executar `commit_turn` antes de publicar `state_update` e terminal concluído. Depende de GOAL-002 a GOAL-004. | [x] | 2026-08-25 |
| TASK-025 | Mapear desconexão WebSocket para cancelamento; em erro, timeout ou cancelamento emitir terminal distinto, registrar tentativa e preservar o snapshot anterior. Depende de TASK-024. | [x] | 2026-08-24 |
| TASK-026 | Reidratar contador de turno, snapshot, relações e histórico narrativo em toda conexão, inclusive reconexões, preservando campos legados. Depende de TASK-022 e TASK-024. | [x] | 2026-08-24 |
| TASK-027 | Expor operações explícitas de consolidação de cena/sessão e recuperação contextual no backend sem inferir fronteiras por LLM; reinjetar a versão consolidada mais recente no contexto. Depende de TASK-015 e TASK-018. | [x] | 2026-08-24 |
| TASK-028 | Atualizar `client/src/App.tsx` e extrair o redutor do protocolo para tratar terminal tipado e não promover parcial, mantendo compatibilidade visual. Depende de TASK-024 e TASK-025. | [x] | 2026-08-24 |
| TASK-029 | Atualizar testes WebSocket e de pipeline para ordem terminal, rollback, bloqueios, reconexão, replay de narrativa e compatibilidade dos eventos existentes. Depende de TASK-024 a TASK-028. | [x] | 2026-08-24 |

### Implementation Phase 6

- GOAL-006: Validar o conjunto, inspecionar o diff e registrar o estado final do plano.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-030 | Criar `.venv` ignorada no worktree e instalar os manifests existentes somente se necessário para executar testes; não instalar no checkout original ou globalmente. | [x] | 2026-08-24 |
| TASK-031 | Executar testes focados por fase, depois `pytest` completo; classificar falhas como regressão, teste estagnado ou dependência externa. Depende de GOAL-001 a GOAL-005. | [x] | 2026-08-25 |
| TASK-032 | Executar validação estática/compilação Python, build/teste do frontend e prova de que nenhum teste padrão depende de rede/LLM real. Depende de TASK-031. | [x] | 2026-08-25 |
| TASK-033 | Inspecionar `git diff --check`, diff completo, arquivos não rastreados, imports proibidos, ausência de `.env` no diff e estado do checkout original. Depende de TASK-031 e TASK-032. | [x] | 2026-08-25 |
| TASK-034 | Atualizar os marcadores deste plano para refletir somente tarefas realmente concluídas e relatar limitações verificadas. Depende de TASK-033. | [x] | 2026-08-25 |

## 3. Alternatives

- **ALT-001**: Manter três JSON separados. Rejeitada porque não oferece commit único entre estado, narrativa, memória e relações.
- **ALT-002**: Criar um JSON agregado por sessão com `os.replace`. Rejeitada porque reescreve um documento crescente, coordena apenas um processo e dificulta consultas/retrieval; SQLite da biblioteca padrão oferece transação real sem dependência nova.
- **ALT-003**: Usar SQLAlchemy, já listado no manifest da API. Rejeitada porque não é utilizado pelo código atual e adicionaria uma camada ampla sem benefício necessário para este MVP.
- **ALT-004**: Gerar candidatos de memória com uma chamada LLM adicional em todo turno. Rejeitada como default porque adiciona latência/custo e dependência de capability; a primeira implementação deriva candidatos semanticamente dos eventos e da narrativa e mantém a fronteira pronta para propostas estruturadas futuras.
- **ALT-005**: Confirmar a mecânica antes da narrativa. Rejeitada porque reproduz a inconsistência atual; a unidade canônica aprovada é o turno completo.
- **ALT-006**: Bufferizar toda narrativa antes de enviar qualquer chunk. Rejeitada porque elimina streaming percebido; chunks continuam provisórios até o terminal e o cliente não os promove em falha.
- **ALT-007**: Escolher Gemini, OpenRouter, Groq, Mistral ou um servidor local como target padrão. Rejeitada porque LLM-002 não foi aprovada; a implementação exige configuração explícita e não muda de alvo.

## 4. Dependencies

- **DEP-001**: Python 3.11+ e módulos de biblioteca padrão `asyncio`, `sqlite3`, `json`, `hashlib`, `uuid` e `datetime`; a suíte local foi executada em Python 3.12.
- **DEP-002**: FastAPI, Pydantic v2, pydantic-settings, httpx, pytest e pytest-asyncio já declarados em `api/requirements.txt`.
- **DEP-003**: Motores determinísticos existentes em `api/rules_service.py`, `api/economy_service.py`, `api/combat_service.py`, `api/discipline_service.py`, `api/metagame_service.py` e `api/physiology_service.py`.
- **DEP-004**: Catálogos e fichas JSON existentes permanecem somente como fontes versionadas de regras/lore; nenhum cálculo novo será movido para JSON.
- **DEP-005**: Configuração explícita de target LLM em variáveis neutras é necessária apenas para chamadas reais; todos os testes de contrato e integração devem funcionar offline.

## 5. Files

- **FILE-001**: `api/llm/__init__.py`, `api/llm/contract.py`, `api/llm/testing.py`, `api/llm/runtime.py` — nova fronteira interna e adaptador sintético offline.
- **FILE-002**: `api/llm/adapters/__init__.py`, `api/llm/adapters/openai_compatible.py` — isolamento HTTP/protocolo.
- **FILE-003**: `api/core/config.py`, `api/.env.example`, `api/requirements.txt` — configuração neutra documentada e dependências preservadas, sem segredos reais.
- **FILE-004**: `api/h0_controller_service.py`, `api/parser_service.py`, `api/h4_lore_expert_service.py`, `api/orchestrator_service.py`, `api/npc_service.py`, `api/relationship_service.py`, `api/turn_execution_service.py`, `skills/H1_vtm_rules_parser.md`, `skills/H6_vtm_narrator.md` — migração de H0/H1/H4/H6, resolução local, execução tipada e preservação de fatos canônicos e agência do jogador.
- **FILE-005**: `api/turn_models.py`, `api/context_service.py`, `api/memory_service.py` — eventos, contexto e memória em camadas.
- **FILE-006**: `api/persistence.py`, `api/state_service.py`, `api/relationship_service.py` — transações, migração e projeções de compatibilidade.
- **FILE-007**: `api/main.py` — integração WebSocket, cancelamento, commit e reidratação.
- **FILE-008**: `client/src/App.tsx`, `client/src/narrativeProtocol.ts`, `client/src/narrativeProtocol.test.ts`, `client/src/components/ActionPanel.tsx`, `client/src/components/ActionPanel.test.tsx`, `client/src/hooks/useWebSocket.ts`, `client/src/hooks/useWebSocket.test.tsx` — envelope idempotente, terminal tipado, histórico, retenção de input rejeitado e reconexão.
- **FILE-009**: `tests/conftest.py`, `tests/llm/`, `tests/test_turn_models.py`, `tests/test_context_service.py`, `tests/test_memory_service.py`, `tests/test_persistence.py`, `tests/test_turn_execution_service.py`, `tests/test_turn_pipeline_integration.py`, `tests/test_llm_service_integration.py`, `tests/test_operational_contract_api.py`, `tests/test_websocket_transactional.py` — nova suíte focada e isolamento do store de testes.
- **FILE-010**: `tests/test_perf_sec.py`, `tests/test_websocket_flows.py`, `tests/test_relationship_service.py` — atualização mínima de testes legados e regressões determinísticas afetadas.
- **FILE-011**: `.env.example`, `api/.env.example`, `README.md`, `LEIA-ME_PRIMEIROS_PASSOS.md`, `INICIAR_JOGO.bat`, `SESSION_LOG.md`, documentos históricos de design/produto, `scripts/initialize_game.py` e `scripts/validate_phase0.py` — contrato operacional neutro de provedor e desambiguação de documentação superada.
- **FILE-012**: `plan/architecture-llm-memory-turns-1.md` — plano executável e rastreabilidade de conclusão.

## 6. Testing

- **TEST-001**: Suíte de conformidade LLM offline prova capabilities, target imutável, terminal único, parcial, structured validation, cancelamento, deadline, erro, proveniência, usage/cost e teste sintético.
- **TEST-002**: Teste AST prova que o domínio não importa `httpx`, protocolos externos ou tipos de adaptador.
- **TEST-003**: Integrações H0/H1/H4/H6 com fake gateway provam prompts, schema, fallbacks observáveis e ausência de troca de target.
- **TEST-004**: Eventos e candidatos provam imutabilidade, autoridade mecânica, referências, derivação sem novos fatos e visibilidade não ampliada.
- **TEST-005**: Recuperação prova filtro de visibilidade anterior ao score, seleção por quatro critérios, desempate estável e orçamento nunca excedido.
- **TEST-006**: Consolidação prova versão crescente, idempotência por chave de origem e preservação de eventos/memórias fonte.
- **TEST-007**: SQLite prova atomicidade do turno, rollback de falha injetada, idempotência, monotonicidade e consistência sob concorrência.
- **TEST-008**: Migração prova importação lazy única e igualdade byte a byte dos três arquivos JSON antes/depois.
- **TEST-009**: WebSocket prova que chunks são provisórios, sucesso confirma e reidrata narrativa, falha/timeout/cancelamento não promove estado nem parcial.
- **TEST-010**: Regressão prova TORPOR, FRENZY, reroll, lore query, XP e módulos determinísticos preservados.
- **TEST-011**: `pytest` completo, `python -m compileall api tests scripts`, testes/build/lint focado do cliente, `git diff --check`, isolamento de imports e prova de integridade do checkout original.

## 7. Risks & Assumptions

- **RISK-001**: A suíte atual contém testes estagnados e um teste vivo de LM Studio; a implementação deve torná-los offline ou classificá-los explicitamente sem ocultar regressões.
- **RISK-002**: SQLite em WAL deixa arquivos auxiliares em execução; o repositório deve fechar conexões por operação e os testes devem usar diretórios temporários.
- **RISK-003**: Transmitir chunks antes do commit permite que o usuário veja texto que depois é descartado; o terminal tipado e a UI devem comunicar que o conteúdo é provisório.
- **RISK-004**: A primeira migração pode encontrar JSON corrompido; deve falhar de modo explícito e preservar todos os bytes, nunca assumir sessão vazia.
- **RISK-005**: O orquestrador atual mistura regras, LLM e I/O; a extração deve ser incremental para evitar reescrita oportunista.
- **RISK-006**: Resultados aleatórios não podem ser recalculados em retry; o cliente deve reutilizar `operation_id`, a tentativa deve ser prealocada antes de H0/H1/H4 e o commit deve ser idempotente.
- **RISK-007**: Recovery de tentativas pressupõe um único worker. Bancos legados que não satisfaçam shape, UNIQUE, FOREIGN KEY e CHECK do schema suportado são recusados antes de qualquer mutação, em vez de reconstruídos automaticamente.
- **ASSUMPTION-001**: O MVP executa em um único host e um único processo/worker FastAPI; SQLite serializa múltiplas conexões, mas os locks de sessão são locais ao processo.
- **ASSUMPTION-002**: Um candidato determinístico composto por resumo semântico do evento, narrativa validada, tags e fontes satisfaz a exigência inicial de memória pequena reutilizável sem invocação LLM extra.
- **ASSUMPTION-003**: Encerramento de cena/sessão será uma operação explícita da aplicação; nenhuma heurística ou decisão LLM será introduzida.
- **ASSUMPTION-004**: O adaptador OpenAI-compatible preserva o protocolo já usado sem aprovar qualquer provedor, catálogo ou ordem de fallback.

## 8. Verification Outcome

Implementação e auditoria concluídas em 2026-08-25:

- backend completo: **229 testes passaram**; o único aviso é um
  `PendingDeprecationWarning` de `python_multipart` emitido por Starlette;
- `python -m compileall -q api tests scripts`: passou;
- frontend: **17 testes passaram**, build TypeScript/Vite passou e ESLint focado
  em todos os arquivos alterados passou;
- o ESLint global continua vermelho somente em `useCharacterState.ts` e
  `useInitializationLog.ts` (**3 erros e 1 aviso preexistentes**); esses arquivos
  não foram modificados neste trabalho;
- `git diff --check`: passou, com apenas avisos de normalização LF para CRLF;
- `httpx` aparece somente em `api/llm/adapters/openai_compatible.py`; nenhum SDK
  de provedor vazou para o domínio;
- `.env` permaneceu ignorado, ausente do status/diff e não foi aberto;
- o checkout original permaneceu limpo na branch `master`, commit
  `5e563824fcba4c53cc37b5084a8ce65f3fa30356`;
- nenhum alvo LLM real foi selecionado ou chamado. A conformidade foi verificada
  offline com o adaptador sintético; qualidade narrativa em português e catálogo
  de provedores/modelos continuam para LLM-002 e aceitação humana posterior.

## 9. Related Specifications / Further Reading

- Handoff V5 lido integralmente no thread de origem e tratado como fonte de decisões; não será copiado para o repositório.
- Decisões aprovadas no thread de origem: ARC-001 `Aprovada`; refinamento LLM-001 v0.1 `Pronta` e agora autorizado para implementação.
- Itens relacionados mantidos separados da escolha de provedor: CAP-001, LLM-002, LLM-003, SEC-001, NAR-002, STATE-001, DATA-002, RULE-002 e RULE-SRC-001.
