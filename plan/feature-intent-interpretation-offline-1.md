---
goal: Avaliar contrato de interpretação delimitada com corpus sintético offline
version: 1
date_created: 2026-10-22
last_updated: 2026-10-22
owner: Agente Storyteller
status: 'Completed'
tags: [experiment, intent, offline]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Humano escolheu B em 22/10/2026. Executar desenho, 24 casos e verificação offline;
não integrar ou avaliar modelo real. Respostas autoradas não medem capacidade de LLM.

## 1. Requirements & Constraints

- REQ-001: Saída tipada known_intent/clarification/unsupported e enum existente.
- REQ-002: Vincular entrada/sessão/operação/versão/hash de estado e evidência literal.
- REQ-003: Separar validade estrutural de equivalência semântica.
- SEC-001: Não aceitar campos de narrativa/cânone/estado, duplicatas JSON ou trechos inexistentes.
- CON-001: Sem gateway, rede, RNG, mutação de sessão, dependências ou arquivos congelados.
- CON-002: Nenhuma proposta vira consequência; mesmo elegibilidade offline não é integração.
- CON-003: Primeira falha de autoridade reprova/encerra a variante; diagnóstico adversarial separado.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Preparar contrato e corpus antes de medir.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-001 | Criar api/experiments/intent_interpretation_offline.py com Envelope, Proposal, EvidenceSpan, parse_proposal e assess; JSON estrito <=4096 bytes e guard independente baseado no classificador existente. | [x] | 2026-10-22 |
| TASK-002 | Criar evals/narrator/spikes/intent-interpretation-2026-10-22/corpus.json com 24 rótulos autorados: 8 paráfrases, 4 ambiguidades, 4 negação/ator, 4 métodos inéditos, 4 injeções. Congelar hashes antes da execução. | [x] | 2026-10-22 |

### Implementation Phase 2

- GOAL-002: Avaliar limitações sem fingir desempenho de modelo.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-003 | Criar scripts/evaluate_intent_interpretation_offline.py: baseline, propostas de referência e contraprovas; formato/literalidade em shadow e guard independente; nenhum acesso a executor/DB. | [x] | 2026-10-22 |
| TASK-004 | Criar tests/test_intent_interpretation_offline.py para bindings, parsing, limites, negação, ator, replay e matriz de 24 casos. Executar teste focado e regressão do browser. | [x] | 2026-10-22 |
| TASK-005 | Executar uma observação congelada; registrar resultados/casos não resolvidos em relatório, atualizar retomada/checklist e preparar próximo gate humano. | [x] | 2026-10-22 |

### Implementation Phase 3

- GOAL-003: Executar a opção C como catálogo exato e preparar o gate de integração.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-006 | Criar api/experiments/intent_interpretation_catalog.py com seis strings exatas e nenhuma normalização, substring ou execução. | [x] | 2026-10-22 |
| TASK-007 | Criar scripts/evaluate_intent_paraphrase_admission_offline.py e doze casos (seis aprovados/seis controles), com manifesto de hashes e custo zero. | [x] | 2026-10-22 |
| TASK-008 | Criar testes focados, executar observação e regressão conjunta; registrar relatório e preparar E/F sem admitir integração. | [x] | 2026-10-22 |

## 3. Alternatives

- ALT-001: Confiar no campo de confiança/proposta/evidência literal não prova semântica; medir contraprova.
- ALT-002: Aceitar novas paráfrases por labels do corpus na função assess vazaria o gabarito; proibido.
- ALT-003: Acoplar imediatamente ao A2 ou resolvedor amplia o aceite; não executar.

## 4. Dependencies

- DEP-001: Pydantic/pytest existentes e CampaignIntentKind/classify_campaign_intent congelados.
- DEP-002: Propostas B e C aprovadas, preservando a autoridade causal determinística.

## 5. Files

- FILE-001: api/experiments/intent_interpretation_offline.py.
- FILE-002: evals/narrator/spikes/intent-interpretation-2026-10-22/corpus.json.
- FILE-003: scripts/evaluate_intent_interpretation_offline.py.
- FILE-004: tests/test_intent_interpretation_offline.py.
- FILE-005: evals/narrator/reports/intent-interpretation-offline-2026-10-22.md e estado de retomada.
- FILE-006: api/experiments/intent_interpretation_catalog.py.
- FILE-007: scripts/evaluate_intent_paraphrase_admission_offline.py e tests/test_intent_paraphrase_admission_offline.py.
- FILE-008: evals/narrator/reports/intent-paraphrase-admission-offline-2026-10-22.md.

## 6. Testing

- TEST-001: Estrutura/referências/evidências inválidas rejeitadas; tipos estritos e duplicatas recusadas.
- TEST-002: Contraprovas de negação, ator, novo método e cânone não elegíveis no guard.
- TEST-003: Proposta semanticamente fiel mas não reconhecida permanece pendente, sem fingir cobertura.
- TEST-004: Baseline desconhecida não equivale a intenção errada; apresentar falso bloqueio/aceite separados.
- TEST-005: 32 fontes A2/L86 mantêm hashes; browser não recebe o contrato novo.
- TEST-006: Seis strings aprovadas elegíveis e seis controles recusados por igualdade exata.

## 7. Risks & Assumptions

- RISK-001: Guard baseado na baseline mantém seu teto de cobertura; não é solução de interpretação livre.
- RISK-002: Corpus pequeno autorado; resultados não probabilísticos nem benchmark de modelos.
- ASSUMPTION-001: Literalidade e vínculo são condições necessárias, não prova de equivalência.

## 8. Related Specifications / Further Reading

- [Escopo B](proposal-expression-selection-next-scope-2026-10-22.md)
- [Observação navegador A2](../evals/narrator/reports/expression-selection-browser-review-2026-10-22.md)

Resultado:61 testes focados e197 da regressão conjunta passaram. Contrato estrutural
não prova semântica; guard mantém cobertura atual. Gate C/D preparado, não aprovado.

Opção C aprovada em 22/10/2026: catálogo exato de seis equivalências em variante
separada, sem API, integração, RNG ou autoridade causal. A variante foi executada;
o próximo gate E/F decide se esse catálogo entra no ensaio A2.
