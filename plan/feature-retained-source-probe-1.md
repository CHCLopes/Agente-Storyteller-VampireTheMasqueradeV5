---
goal: Preparar observação sintética delimitada da entrada B com preparação retida
version: 1
date_created: 2026-09-10
last_updated: 2026-09-10
owner: Agente Storyteller
status: 'Completed'
tags: [feature, evaluation, narrative-source, synthetic]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-green)

Continuidade autorizada depois do coordenador B. Preparar um avaliador separado,
com banco novo exclusivo por lote, para observar dois turnos dependentes do
coordenador real. Esta tarefa conclui código, preflight e provas offline antes
de qualquer inserção de credencial. Observação ao vivo continua sem resultado.

## 1. Requirements & Constraints

- REQ-001: Novo scripts/evaluate_retained_source.py usa create_narrative_source_campaign, prepare_retained_source_turn e execute_retained_source_turn, sem produtor legado, em dois turnos sintéticos declarados: observar uma galeria conhecida sem tocar e aguardar no mesmo lugar.
- REQ-002: Fixar cena Galeria sem NPCs, prompt narrative-source-v1 existente, alvo qwen-3.8-27b-groq-free-synthetic-nonthink do manifesto já autorizado, Groq direto e reasoning none. Não alterar prompt/perfil/manifesto nem reutilizar lote histórico.
- REQ-003: Limites: até2 chamadas dependentes,768 tokens/call,total1536,temp0.65,espera inicial60s,intervalo mínimo60s,deadline60s/call. Primeira falha operacional/política interrompe a cadeia. Sem diagnósticos,retry,reparo,fallback ou baseline.
- REQ-004: Preflight offline vincula versões/hashes do avaliador, componentes, prompt, manifesto e cenário; execução deve confrontar preflight e lote antes de ler a credencial.
- REQ-005: Persistir summary.json e evidência sintética com identidade por lote/operação, cápsulas e resultados; distinguir preparação retida, chamada iniciada, resposta observada, turno admitido e dependente pulado. Verificar artefatos offline e replay sem nova chamada após recriar SQLitePersistence.
- REQ-006: Novo scripts/run_groq_retained_source_probe.ps1 suporta -PreflightOnly e solicita chave somente após preflight validado usando Read-Host -AsSecureString. Variável temporária exclusiva STORYTELLER_RETAINED_GROQ_KEY é removida em finally. Não consultar chave existente em GROQ_API_KEY, .env ou processos.
- SEC-001: Nenhuma credencial em argumento, log, SQLite, artefato ou exceção impressa. Erros somente códigos fechados/metadados sanitizados; não imprimir saída bruta do provedor. Recursos runtime não entram na cápsula.
- CON-001: Zero execução live nesta preparação; nenhuma janela nova antes de completar testes. Sem UI/default/save real, migração, CAP-001 ou aprovação de qualidade geral.
- CON-002: Preservar scripts e resultados históricos; lote novo não é A/B causal nem repetição/regularização das falhas anteriores. Não alterar funções de aplicação concluídas por conveniência do harness.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Implementar avaliador e wrapper independentes com contrato CLI alinhado; wrapper depende da forma do preflight.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Implementar scripts/evaluate_retained_source.py com cenário fixo, preflight, lote novo, observador limitado, coordenador, evidências e verificação de artefatos; adicionar tests/test_retained_source_probe.py com FakeLLM/HTTPXMock. | Sim | 2026-09-10 |
| TASK-002 | Implementar scripts/run_groq_retained_source_probe.ps1 e tests/test_retained_source_probe_wrapper.py com preflight antes da chave, -PreflightOnly, limpeza da variável exclusiva e fechamento seguro de status. | Sim | 2026-09-10 |

### Implementation Phase 2

- GOAL-002: Verificar offline e entregar um único comando protegido pronto para a dependência humana real.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-003 | Rodar preflight real e testes focados de corpo/rota/limites, cadeia, recusa, corrupção, reexecução do lote, cancelamento e wrapper; conferir hashes e revisar diffs. | Sim | 2026-09-10 |
| TASK-004 | Registrar preparação em evals/narrator/reports/retained-source-probe-preparation-2026-09-10.md/json e atualizar retomada com o comando seguro, preservando seu histórico. | Sim | 2026-09-10 |

## 3. Alternatives

- ALT-001: Alterar avaliador histórico descartado: preservação de evidência exige novo executável/lote.
- ALT-002: Exercitar UI ou save real descartado: ainda são superfícies distintas do coordenador sintético.
- ALT-003: Repetir H6 failed/pending descartado: a retenção não autoriza retry e esta observação interrompe na primeira falha.

## 4. Dependencies

- DEP-001: Coordenador B concluído e575 regressões locais verdes; SQLite temporário/FakeLLM existentes.
- DEP-002: GroqAdapter, manifesto fixo de candidatos e prompt narrative-source-v1 existentes; verificar hashes na preparação.
- DEP-003: Observação live exige credencial fornecida diretamente pelo usuário em prompt protegido, depois da preparação.

## 5. Files

- FILE-001: scripts/evaluate_retained_source.py e tests/test_retained_source_probe.py.
- FILE-002: scripts/run_groq_retained_source_probe.ps1 e tests/test_retained_source_probe_wrapper.py.
- FILE-003: evals/narrator/reports/retained-source-probe-preparation-2026-09-10.md/json e PROMPT_RETOMADA_2026-09-06.md.

## 6. Testing

- TEST-001: Preflight não lê chave nem chama rede; target/cena/prompts/hashes e teto de chamadas fechados.
- TEST-002: Dois turnos válidos carregam fonte anterior integral pela entrada retida e replay após reinício não chama gateway.
- TEST-003: Primeira recusa/falha implica segundo skip e nenhuma segunda chamada; retém cápsula e falha terminal sem promoção.
- TEST-004: Lote/diretório já usado, preflight alterado, target/request incompatível e tentativa adicional recusados sem efeito externo.
- TEST-005: Wrapper -PreflightOnly termina sem chave; finally limpa variável própria, códigos seguros e sem exposição de exceção/saída do filho.

## 7. Risks & Assumptions

- RISK-001: Fixtures provam integração; não preveem admissão ou qualidade narrativa do provedor.
- RISK-002: Limite de duas fontes/perfil de cena conhecida e recibo já resolvido permanece; nenhuma progressão geral de campanha.
- ASSUMPTION-001: Autorização contínua cobre observação sintética necessária. Apenas inserção de credencial impede execução live após preparação.

## 8. Related Specifications / Further Reading

- [Coordenador concluído](architecture-narrative-source-coordinator-1.md)
- [Provas da retenção](../evals/narrator/reports/narrative-source-coordinator-2026-09-10.md)
- [Avaliador histórico preservado](../scripts/evaluate_narrator_source.py)

## 9. Resultado verificado

Preparação concluída com72 testes distintos verdes e preflight real offline exit0.
Zero chamada externa; somente a entrada protegida de credencial impede a observação
ao vivo. Ver relatório `evals/narrator/reports/retained-source-probe-preparation-2026-09-10.md/json`.
