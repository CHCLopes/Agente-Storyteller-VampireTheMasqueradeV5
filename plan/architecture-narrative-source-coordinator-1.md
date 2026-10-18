---
goal: Reter a preparação B e coordenar sua primeira execução ou replay interno
version: 1
date_created: 2026-09-10
last_updated: 2026-09-10
owner: Agente Storyteller
status: 'Completed'
tags: [architecture, narrative-source, internal, persistence]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Incremento local autorizado pela continuidade da direção B. Uma cápsula imutável
retém o recibo já resolvido, o rascunho e os argumentos estáticos antes de H6.
A cápsula usa uma operação técnica de controle separada; a tentativa H6 existente
continua sendo a reserva exclusiva por sessão/operação. Conclusão do controle
significa preparação persistida, nunca narrativa aprovada.

## 1. Requirements & Constraints

- REQ-001: Criar SourceTurnCapsule, create_source_turn_capsule e validate_source_turn_capsule em api/narrative_source_capsule.py, com identidade, snapshot-base, preparação tipada, draft reconstituível pela função pura, estado/relacionamentos JSON e configuração estática de H6.
- REQ-002: Reter a cápsula em attempts.metadata_json usando identidade técnica determinística separada, status completed e committed_turn_id nulo. Não alterar DDL/schema ou o estado da campanha.
- REQ-003: save_source_preparation deve validar origem, história elegível e CAS em transação; load_source_preparation deve validar cápsula, identidade, hashes e pareamento do controle sem exigir que a revisão-base ainda seja a atual em replay.
- REQ-004: prepare_retained_source_turn recebe somente classificação/recibo já resolvido, lê o snapshot, monta e retém a cápsula. execute_retained_source_turn carrega essa cápsula e usa execute_source_turn, sem prepare_turn_pipeline, RNG ou classificação.
- REQ-005: Cápsula pronta e H6 ausente permite primeira execução; pending nunca permite takeover; terminal nunca permite retry. Replay concluído mantém a validação existente do turno e de toda a história.
- SEC-001: Não persistir gateway, chave, conexão, callback, cancellation ou deadline. Recusar protected_secrets não vazio neste perfil público; não descartar essa entrada silenciosamente.
- CON-001: Preservar default, UI, save real, regras de admissão, fontes integrais, sigilo/agência e CAP-001. Testes somente offline com SQLite temporário/FakeLLM; nenhuma dependência nova.
- CON-002: A garantia começa na retenção do recibo já resolvido. Não alegar bloqueio anterior ao RNG externo nem execução exatamente uma vez após crash.
- CON-003: Operações distintas conservam a concorrência e o CAS existentes; não adicionar exclusividade por revisão, retry, estado paused, leases ou a política de pausa/retomada futura.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Definir e provar a cápsula pura e sua retenção atômica. TASK-001 e a inspeção de TASK-002 são paralelas; integração de TASK-002 depende do contrato de TASK-001.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Implementar api/narrative_source_capsule.py e tests/test_narrative_source_capsule.py com cópia, revalidação fechada, fingerprint canônico e recomputação pura do draft. | Sim | 2026-09-10 |
| TASK-002 | Adicionar save_source_preparation/load_source_preparation a api/persistence.py e tests/test_narrative_source_capsule_persistence.py, com reserva técnica separada, origem/snapshot/CAS, idempotência e integridade transacionais. | Sim | 2026-09-10 |

### Implementation Phase 2

- GOAL-002: Compor entrada interna e execução retida depois da fase 1, testar concorrência/falha/reinício e documentar evidência.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-003 | Implementar prepare_retained_source_turn e execute_retained_source_turn em api/narrative_source_coordinator.py, preservando as reservas/replays de execute_source_turn sem ativação pública. | Sim | 2026-09-10 |
| TASK-004 | Criar tests/test_narrative_source_coordinator.py e executar regressões focadas de preparação, leitores, ponte, persistência e retomada legada. | Sim | 2026-09-10 |
| TASK-005 | Revisar diffs e registrar resultados/hashes em evals/narrator/reports/narrative-source-coordinator-2026-09-10.md/json; atualizar README.md e somente o topo corrente de PROMPT_RETOMADA_2026-09-06.md. | Sim | 2026-09-10 |

## 3. Alternatives

- ALT-001: Nova tabela ou fase mutável na reserva H6 descartada neste recorte: controle separado preserva o schema e a identidade imutável da tentativa existente.
- ALT-002: Callback que produz RNG após uma reserva adiado: crash entre rolagem e persistência exige outra política de recuperação.
- ALT-003: Retomar pending por timeout descartado: ausência de resposta persistida não comprova ausência de chamada ao provedor.

## 4. Dependencies

- DEP-001: SourceContextSnapshot, origem B e leitura integral elegível já implementados.
- DEP-002: prepare_source_turn_draft puro e execute_source_turn com reserva idempotente, CAS e replay validado existentes.
- DEP-003: SQLitePersistence e testes de isolamento de rede/banco existentes; nenhuma credencial necessária.

## 5. Files

- FILE-001: api/narrative_source_capsule.py e tests/test_narrative_source_capsule.py.
- FILE-002: api/persistence.py e tests/test_narrative_source_capsule_persistence.py.
- FILE-003: api/narrative_source_coordinator.py e tests/test_narrative_source_coordinator.py.
- FILE-004: README.md, PROMPT_RETOMADA_2026-09-06.md e evals/narrator/reports/narrative-source-coordinator-2026-09-10.md/json.

## 6. Testing

- TEST-001: Cápsula preserva literais/recibo e recusa mutação, identidades/tipos inválidos, segredo, campos extras, draft divergente e fingerprint incorreto.
- TEST-002: Retenção não cria turno, não avança revisão; concorrência idêntica é idempotente e divergente conflita; origem, base obsoleta, história e row/hash alterados são recusados.
- TEST-003: Reinício antes de H6 usa a cápsula retida; concorrência da mesma operação despacha no máximo uma chamada; pending e terminais não reenviam H6.
- TEST-004: Falha preserva recibo/draft; commit e replay após avanço posterior não rerrolam, não criam chunks/eventos duplicados e validam o turno original.
- TEST-005: Regressões focadas existentes passam com STORYTELLER_DISABLE_DOTENV=1, bloqueio de rede e SQLite temporário.

## 7. Risks & Assumptions

- RISK-001: Crash depois da reserva H6 é resultado incerto; recuperação legada pode cancelar pending, mas não autoriza reenvio.
- RISK-002: Fingerprint verifica consistência, não autentica servidor nem decide verdade semântica.
- RISK-003: Cápsula guarda conteúdo sintético/público e configuração explícita; não é armazenamento de credenciais ou perfil de segredos.
- ASSUMPTION-001: Chamador interno fornece recibo já resolvido e identidade estável. Execução retida nunca chama o produtor novamente.

## 8. Related Specifications / Further Reading

- [Preparação pura](architecture-narrative-source-preparation-1.md)
- [Origem e leitores](architecture-narrative-source-readers-1.md)
- [Ponte interna](architecture-narrative-source-bridge-1.md)
- [Pausa e retomada futura, separada deste recorte](feature-narrator-pause-resume-1.md)

Fechamento: 575 testes distintos em rodada final focada, 84 novos; zero falhas/erros/skips. [Relatório e hashes](../evals/narrator/reports/narrative-source-coordinator-2026-09-10.md).
