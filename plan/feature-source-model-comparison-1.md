---
goal: Comparar Qwen e GPT-OSS no fluxo B declarativo para recomendação de piloto restrito
version: 1
date_created: 2026-09-11
last_updated: 2026-09-11
owner: Agente Storyteller
status: 'Completed'
tags: [narrative-source, comparison, groq, synthetic]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-green)

Prioridade da retomada após reinício: preparar e executar comparação delimitada
entre os dois candidatos no fluxo B atual. O transporte optativo segue pendente;
esta preparação não o ativa nem decide produto ou modelo default.

## 1. Requirements & Constraints

- **REQ-001**: Corpus e rubrica prévios em evals/narrator/source_comparison_v1.json
  e source_comparison_protocol_v1.md; duas cenas novas, três turnos declarativos,
  quatro blocos Q/c1,G/c1,G/c2,Q/c2, máximo12 chamadas.
- **REQ-002**: Usar setup→produtor→retenção→executor real B com bancos separados,
  replays somente leitura sem RNG/gateway e fontes próprias completas.
- **REQ-003**: Alvos explícitos Qwen none/GPT-OSS low, SYSTEM progress-v1 preservado,
  schema strict, temperature0.65,768 tokens/call,60squiet/pacing/deadline.
- **REQ-004**: Congelar corpo por alvo, código, manifesto, corpus, protocolo e schema;
  orçamento no hook HTTP global, artefatos auditáveis inclusive falhas/skips.
- **REQ-005**: Separar integridade, disponibilidade e qualidade narrativa. Aplicar
  critérios do protocolo e revisão independente; aceitar resultado sem vencedor.
- **CON-001**: Não editar avaliadores/artefatos encerrados, runtime, gates, UI,
  default ou checkout original. Sem .env/segredo em arquivos ou publicação GitHub.
- **CON-002**: Sem retry, fallback, reparo, diagnóstico ou API paga. Credencial
  somente após preparação verificada, por mecanismo protegido.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Preparação completa e verificável sem depender de credencial.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Definir corpus/protocolo e verificar documentação oficial dos dois alvos; reconciliar prioridade com transporte e retomada. | Sim | 2026-09-11 |
| TASK-002 | Criar scripts/evaluate_source_comparison.py com preflight, quatro blocos, budget global, captura segura e verificador de bancos/requests/cronologia. | Sim | 2026-09-11 |
| TASK-003 | Criar scripts/run_groq_source_comparison.ps1 com entrada protegida, freeze, filho isolado e auditoria sem credencial. | Sim | 2026-09-11 |
| TASK-004 | Criar tests/test_source_comparison.py e tests/test_source_comparison_launcher.py; executar contraprovas, revisão independente e preflight real sem chave. | Sim | 2026-09-11 |

### Implementation Phase 2

- GOAL-002: Uma execução delimitada e avaliação sem repetição para elevar nota.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Executar novo lote somente após freeze e acesso protegido à credencial; respeitar parada por cadeia e global do protocolo. | Sim | 2026-09-11 |
| TASK-006 | Auditar todos os artefatos, revisar textos por critérios prévios e revisor independente; registrar recomendação limitada ou resultado inconclusivo. | Sim | 2026-09-11 |

## 3. Alternatives

- **ALT-001**: Trocar globais do harness Qwen antigo deixa body/observador/auditoria
  presos a none/Qwen; usar código novo com configuração explícita.
- **ALT-002**: Parear investigação exigiria controlar resultado RNG; manter fora
  deste piloto evita confundir sorte com qualidade sem alterar motor real.
- **ALT-003**: Comparar resultados históricos não usa as mesmas condições atuais;
  conservar história como diagnóstico e criar novos blocos.

## 4. Dependencies

- **DEP-001**: Serviços B já implementados e provas locais preservadas.
- **DEP-002**: Credencial Groq no processo live; ausência no agente não impede
  preparar código, testes, protocolo e comando de execução.

## 5. Files

- **FILE-001**: Dois scripts e dois arquivos de testes novos mencionados em TASK-002/004.
- **FILE-002**: Corpus/protocolo; relatórios de preparação/observação em evals/narrator/reports.
- **FILE-003**: PROMPT_RETOMADA_2026-09-06.md e nota de prioridade no plano de transporte.
- **FILE-004**: Artefatos novos em eval-results/source-comparison-<UUID>.

## 6. Testing

- **TEST-001**: HTTP MockTransport verifica none/low, schema, corpo e rota correta;
  candidato trocado e alterações do corpo são recusados antes de certificação.
- **TEST-002**: Três turnos, duas fontes próprias e isolamento entre quatro bancos;
  falha por cadeia/global, replay sem produção e orçamento/pacing entre blocos.
- **TEST-003**: Adulteração rehashada de resumo, request, receipt, história, modelo,
  deadline e cronologia recusada; originais intactos após verificador offline.
- **TEST-004**: Launcher sem rede/chave em preflight/verificador, credencial apenas
  no filho live, eco sintético bloqueado, drift e saída incompleta falham fechados.

## 7. Risks & Assumptions

- **RISK-001**: Duas cenas e seis turnos por candidato não demonstram campanha
  longa, generalização, combate, investigação nem capacidade com segredos autorados.
- **RISK-002**: Histórias se diferenciam após T1 e reasoning difere entre modelos;
  comparação de configurações, sem conclusão causal isolada.
- **RISK-003**: Conta/quota/disponibilidade podem impedir evidência completa;
  documentação oficial não comprova essas condições.
- **ASSUMPTION-001**: Autorização contínua cobre preparação e observação sintética
  delimitada; não cobre promoção automática de produto ou cobrança.

## 8. Related Specifications / Further Reading

- [Protocolo prévio](../evals/narrator/source_comparison_protocol_v1.md)
- [Corpus executável](../evals/narrator/source_comparison_v1.json)
- [Último teste do produtor](feature-source-player-probe-1.md)
- [Transporte pendente](feature-narrative-source-transport-1.md)

Preparação offline concluída: [relatório e evidências](../evals/narrator/reports/source-comparison-preparation-2026-09-11.md). TASK-005/006 concluídas no lote 61b83a2f: auditoria íntegra, nenhum candidato qualificado. Não repetir o lote.

Fechamento: [relatório](../evals/narrator/reports/source-comparison-observation-61b83a2f-2026-09-11.md). Correção local do falso positivo de agência segue em plano separado; os resultados desta comparação permanecem imutáveis.
