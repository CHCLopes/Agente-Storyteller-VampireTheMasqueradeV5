---
goal: Tornar o A2 determinístico revisável em navegador antes da decisão CAMP-24
version: 1
date_created: 2026-10-22
last_updated: 2026-10-22
owner: Agente Storyteller
status: 'Completed'
tags: [experiment, browser, deterministic, a2]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-green)

Ensaio adicional dentro do experimento isolado já aprovado e da continuidade
autônoma solicitada. Não promove A2 ao produto nem altera seu contrato congelado.
O ensaio torna a experiência fechada revisável; a decisão CAMP-24 continua humana.

## 1. Requirements & Constraints

- REQ-001: Reutilizar SelectionStore/SelectionConfig(mode=deterministic)/execute.
- REQ-002: Sem gateway, chave, inferência, novo conteúdo causal ou RNG adicional.
- REQ-003: Nova sessão sintética, começo explícito, histórico, desfecho, reload/restart.
- REQ-004: Entrada fora do catálogo preserva turno/estado/rascunho; não narrar fracasso.
- REQ-005: Retomada explícita usa preparação/seleção retidas; não repetir RNG.
- SEC-001: Loopback, LocalRequestBoundary e token local; sem listener público.
- CON-001: Não editar módulos congelados, produto/original, saves ou defaults.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Criar superfície experimental mínima com persistência existente.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-001 | Criar scripts/run_expression_selection_browser_trial.py com create_app e endpoints /api/start, /api/session, /api/action e /api/resume; página usa textContent, IDs idempotentes e localStorage isolado. | [x] | 2026-10-22 |
| TASK-002 | Criar tests/test_expression_selection_browser_trial.py para ciclo completo, input fora do catálogo, repetição de operação, restart, recuperação e bloqueios locais/sem gateway. | [x] | 2026-10-22 |

### Implementation Phase 2

- GOAL-002: Verificar navegador e preparar gate de experiência com evidência concreta.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-003 | Executar testes focados; iniciar ensaio somente em 127.0.0.1; verificar início, ajuda, input fora do catálogo, desfecho e reload em navegador. | [x] | 2026-10-22 |
| TASK-004 | Registrar cobertura atual e lacuna CAMP-24; preparar decisão com escopo/alternativas/aceitação sem marcar MVP aprovado. | [x] | 2026-10-22 |

## 3. Alternatives

- ALT-001: Integrar diretamente em api/main.py amplia produto antes de aceite; não executar.
- ALT-002: Novo lote de seletor não mostrou necessidade após L86; não preparar.
- ALT-003: Demonstração por textos não permite avaliar interação/reconexão; complementar com harness local.

## 4. Dependencies

- DEP-001: A2 v1 e renderer crítico A1 congelados já presentes.
- DEP-002: FastAPI/uvicorn/pytest existentes, sem instalação.
- DEP-003: Aceite final CAMP-24 fora destas fases; não presumir cobertura de improvisação.

## 5. Files

- FILE-001: scripts/run_expression_selection_browser_trial.py.
- FILE-002: tests/test_expression_selection_browser_trial.py.
- FILE-003: evals/narrator/reports/expression-selection-browser-review-2026-10-22.md.
- FILE-004: PROMPT_RETOMADA_2026-09-06.md e checklist de campanha.

## 6. Testing

- TEST-001: 403 sem token/origem externa; modo de modelo não é executado pelo harness.
- TEST-002: Início/ajuda/resgate/desfecho e idempotência/restart conservam narrativa.
- TEST-003: Input fora do catálogo e falha não avançam a sessão.
- TEST-004: Retomada preparada não reclassifica/rola/chama gateway.
- TEST-005: Verificação real em navegador e reload; nenhuma inferência.

## 7. Risks & Assumptions

- RISK-001: Catálogo fechado não cobre improvisação; mostrar limite sem transformá-lo em fracasso ficcional.
- RISK-002: Página é ensaio de um operador local, não interface de produto pronta.
- ASSUMPTION-001: Autonomia vigente cobre harness reversível isolado para tornar a revisão concreta; não cobre novo cânone ou mudança do MVP.

## 8. Related Specifications / Further Reading

- [A2/L86](../evals/narrator/reports/expression-selection-l86-observation-2026-10-22.md)
- [CAMP-24](checklist-planejamento-campanha-hibrida.md)

Verificação: 10 testes focados passaram e fluxo real no navegador interno conferido.
CAMP-24 permanece aberto. Gate A/B descrito na proposta de próximo escopo.
