---
goal: Preparar entrada optativa B com origem explícita e produtor confiável antes de H6
version: 1
date_created: 2026-09-11
last_updated: 2026-09-11
owner: Agente Storyteller
status: 'Completed'
tags: [narrative-source, opt-in, entry, planning]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

O núcleo B já cria campanha com origem explícita, lê história elegível, prepara e
retém recibo resolvido, executa/reproduz o turno e consulta seu estado sem reenvio.
Falta o chamador que recebe a intenção do jogador e produz esse recibo com autoridade
de servidor. Este plano reconcilia essas entregas com a primeira entrada optativa.
Escopo deste plano concluído em 11/09/2026: contrato de entrada e guarda interna
implementados, 161 testes focados passaram; desenho do produtor revisado no plano
próprio. Reserva, produção e transporte não são entregas deste fechamento.

A direção B preserva fonte narrativa e separa sua interpretação. Ela não revoga a
decisão de produto de improvisar, reagir, avançar a cena e respeitar o jogador.
Uma sala de teste que só repete atmosfera não satisfaz a experiência desejada.

## 1. Requirements & Constraints

- **REQ-001**: Selecionar a entrada B explicitamente antes de `load_session_state`
  e da reserva genérica do WebSocket. Campanha nova deve usar
  `create_narrative_source_campaign`; sessão v1 não se torna B por payload ou flag.
- **REQ-002**: Cliente fornece somente sua intenção e identidade estável da operação.
  Não aceitar `TurnDraft`, `ResolvedActionPreparation`, faces de dados, resultados,
  fatos, alvo LLM ou estado canônico enviados pelo cliente como autoridade do servidor.
- **REQ-003**: Separar elegibilidade da sessão, classificação da ação e resolução
  mecânica. Aprovar a primeira não prova as outras. A guarda inicial não promete
  reconhecer intenção semântica, impedir RNG ou reservar operação por si só.
- **REQ-004**: Preservar o domínio H6 e a cápsula existentes. A reserva genérica
  `attempt-{operation_id}` de `main.py` não pode ocupar a operação H6 B. O produtor
  anterior ao recibo necessita contrato próprio antes de implementação.
- **REQ-005**: Durante investigação desse produtor, mapear todos os caminhos RNG
  e efeitos: teste ordinário, frenesi, despertar, economia, metajogo e rerrolagem.
  A primeira entrada pode excluir caminhos não suportados, mas não tratá-los como
  declaração simples nem aplicar suas consequências parcialmente.
- **REQ-006**: Manter pending/terminal sem takeover ou reenvio. Identidade estável
  da mesma operação preserva idempotência; mesmo texto com ID novo é outra ação.
  Não adicionar leases, expiração, retry, recuperação da rolagem ou estado paused.
- **REQ-007**: Preparar ensaio opcional de uma cena nova como proposta de validação:
  local conhecido, ao menos um NPC já presente e objetivo imediato do jogador.
  Setup público explícito fornece lugar/elenco; a introdução apresenta somente esses
  dados e o objetivo declarado, sem fabricar fonte/invocação/turno de LLM.
- **REQ-008**: Gate de experiência exige reação ou avanço concreto, consequências
  compatíveis com sucesso/falha, agência preservada e continuidade posterior.
  Verificações de schema, HTTP ou armazenamento não substituem esse gate.
- **REQ-009**: Abertura sem cena, transições de local, novos NPCs, segredos,
  pendências de longo prazo e campanha híbrida seguem fora da capacidade B atual.
  Isso deve aparecer como limite do ensaio antes do uso, nunca como promessa
  silenciosa de jogo completo. Não transformar esse recorte em proibição geral de improviso.
- **SEC-001**: Nenhuma leitura de `.env`, chave, banco real ou migração de save.
  Qualquer observação futura mantém alvo explícito, credencial pelo mecanismo seguro,
  parâmetros e regra de parada previamente registrados; nenhuma chamada neste plano.
- **CON-001**: Não ativar rota pública, frontend, default ou CAP-001 nesta preparação.
  A disponibilidade do Groq relatada pelo usuário não comprova aceitação narrativa.
- **CON-002**: Não executar o plano superseded de resultados canônicos conservadores.
  Não implementar as decisões de pausa/retomada DEC-001/002/003 por arrasto.

### Fronteiras verificadas em 11/09/2026

| Fronteira | Evidência atual | Consequência para a entrada B |
|---|---|---|
| Inicialização WebSocket | `api/main.py:696`; `api/state_service.py:222` chama migração legada. | Seleção B precisa anteceder essa inicialização. |
| ID de entrada | `api/main.py:158` aceita operation_id; texto simples recebe outro UUID em 181. | O cliente deve conservar a identidade em reconexão. |
| Reserva anterior ao produtor | `api/main.py:814`; `api/persistence.py:1575`. | Reserva genérica já protege o legado, mas impede a retenção B se reutilizada como H6. |
| H0/H1 | `api/orchestrator_service.py:1742` e 1834; H4 condicional em 1770. | Não importar o pipeline inteiro supondo que seja puro ou sempre produza recibo. |
| RNG externo ao pipeline | `api/main.py:901`; controle de frenesi em 933. | Guarda apenas na preparação não cobre toda a rolagem. |
| RNG e efeitos internos | `api/orchestrator_service.py:1981`, 2035, 2043, 2055, 2091 e 2134. | Enumerar rotas e excluir explicitamente as não suportadas antes dos seus efeitos. |
| Recibo e draft | `api/orchestrator_service.py:2159` e 2364. | O recibo vem após decisões e efeitos preparados em cópia. |
| Fronteira B existente | `api/narrative_source_coordinator.py:36`. | Recebe preparação já confiável; não autentica um recibo enviado pelo cliente. |

Linhas são referências da versão inspecionada; confirmar pelo nome da função antes de editar.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Fixar o contrato de entrada e a fronteira de confiança sem chamada ou efeito.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Reconciliar entregas B e inventariar produtor, inicialização, identidade e RNG nos arquivos acima; registrar experiência e limites neste plano. | Sim | 2026-09-11 |
| TASK-002 | Em novo `api/narrative_source_entry.py`, implementar `SourcePlayerActionRequest` estrito com somente `operation_id` e `player_input`; sessão vem da rota/chamador, nunca de campo extra. IDs seguem limite literal 1..240 da cápsula, texto não vazio, recusando padding externo para compor com o preparador atual sem normalização destrutiva; limite confirmado de 500 caracteres do texto integral, conforme api/main.py:154/758. O ID B de 240 segue cápsula e não altera o ID v1 de 128. Implementar guarda interna `validate_source_entry_snapshot(snapshot, *, session_id)` que revalida `SourceContextSnapshot`, origem B vinculada ao session_id fornecido pelo servidor e cena conhecida, sem I/O ou declaração de prontidão/retry. Documentar que aceitar envelope não classifica nem autoriza mecanicamente a ação. | Sim | 2026-09-11 |
| TASK-003 | Criar `tests/test_narrative_source_entry.py` com envelope legítimo, tipos/IDs inválidos, todos campos privilegiados rejeitados, snapshot forjado/legado, ausência de mutação e ausência de import/chamada ao pipeline, gateway ou RNG. Verificar os limites herdados em vez de inventar novos. Depende de TASK-002. | Sim | 2026-09-11 |

### Implementation Phase 2

- GOAL-002: Tornar o desenho do produtor anterior ao recibo implementável antes de escrevê-lo.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | Em novo `plan/feature-narrative-source-input-producer-1.md`, definir o domínio da reserva anterior a H0/H1/RNG, o pedido imutável, identidade do recibo, vínculo à cápsula, estados e comportamento em cada janela de crash. Confrontar `start_attempt`, `save_source_preparation` e `complete_control_attempt`; não mudar esses métodos nesta tarefa documental. Depende de TASK-003. | Sim | 2026-09-11 |
| TASK-005 | No mesmo plano, especificar adaptação somente dos produtores locais de declaração/teste ordinário e recusa dos demais caminhos antes do respectivo RNG/efeito. Mapear retornos esclarecimento/lore/cena/ação protegida sem presumir que todos são `TurnDraft`. Escolhas de recuperação que mudem política vigente devem permanecer propostas e impedir apenas sua implementação dependente. | Sim | 2026-09-11 |
| TASK-006 | No mesmo plano, fechar matriz de teste da criação/setup, introdução, intenção, classificação, reserva, resolução, retenção, H6, commit, diagnóstico e reconexão; definir arquivos e invariantes antes de implementar o produtor. Revisão independente e atualização deste plano. Depende de TASK-004 e TASK-005. | Sim | 2026-09-11 |

## 3. Alternatives

- **ALT-001**: Substituir apenas H6 no WebSocket atual descartado: inicialização v1,
  reserva genérica e efeitos anteriores continuam ativos e conflitam com B.
- **ALT-002**: Receber recibo pronto do cliente descartado: tipagem não autentica
  mecânica nem origem. O contrato atual exige produtor servidor.
- **ALT-003**: Outra camada de consulta/replay descartada: a consulta de status já
  está implementada. O trabalho restante está antes do recibo e na experiência.
- **ALT-004**: Nova paráfrase de SYSTEM ou repetição dos lotes encerrados descartada
  como próximo passo. A próxima validação deve representar interação com objetivo,
  depois de fechar a entrada e seus critérios, sem alegação causal entre lotes.
- **ALT-005**: Cena curta optativa escolhida como proposta de ensaio delimitado;
  campanha completa continua dependente de abertura/progressão e do planejamento
  híbrido. A proposta não substitui a preferência anterior do usuário por testar o jogo completo atual.

## 4. Dependencies

- **DEP-001**: Origem/leitores, preparador, cápsula/coordenador e consulta B concluídos.
- **DEP-002**: Contrato de transporte e limites de `api/main.py` precisam ser
  inspecionados em TASK-002; nenhuma instalação ou serviço é necessário.
- **DEP-003**: As tarefas internas da fase 1 não precisam de credencial nem de
  decisão sobre campanha. Implementação do produtor vem depois de contrato e revisão.
- **DEP-004**: Qualquer nova política de recuperação antes do RNG que conflite com
  pending/terminal ou com decisões de pausa abertas é dependência arquitetural,
  não um detalhe a escolher silenciosamente. Preparar alternativas concretas antes
  de pedir decisão; concluir as tarefas independentes primeiro.
- **DEP-005**: Ativação de experiência B depende de testes técnicos, avaliação
  narrativa e aceitação do recorte. Este plano não concede CAP-001 nem troca de default.

## 5. Files

- **FILE-001**: Este plano e o topo de `PROMPT_RETOMADA_2026-09-06.md` registram a etapa.
- **FILE-002**: Novos `api/narrative_source_entry.py` e `tests/test_narrative_source_entry.py` na fase 1.
- **FILE-003**: Novo `plan/feature-narrative-source-input-producer-1.md` na fase 2.
- **FILE-004**: `api/main.py`, `api/orchestrator_service.py`, `api/state_service.py`,
  `api/rules_service.py`, `api/economy_service.py` e `api/metagame_service.py` são
  fontes de inspeção. Nenhuma alteração nesses caminhos é autorizada por tarefa documental.

## 6. Testing

- **TEST-001**: Modelo de entrada aceita somente os dois campos públicos; recusa
  receipt/draft/state/target/facts/roll e campo session_id inserido no envelope.
- **TEST-002**: Guarda de snapshot recusa origem ausente, legado e modelos forjados;
  não muta entrada nem executa efeitos. Não se apresenta como reserva pré-RNG.
- **TEST-003**: Matriz do produtor documenta duplicação simultânea, ID novo com mesmo
  texto, crash antes/depois RNG, antes/depois cápsula, pending, terminal e reinício.
- **TEST-004**: Matriz da experiência inclui introdução útil, ação com NPC, sucesso
  com consequência, falha com movimento, espera com reação e continuidade dependente.
  Distingue casos autorados offline de capacidade observada do modelo.
- **TEST-005**: Revisão do plano não contabiliza testes futuros como executados;
  documentação deve manter todas as tarefas de código pendentes até sua verificação.

## 7. Risks & Assumptions

- **RISK-001**: Bloquear toda novidade para simplificar a integração contrariaria
  IMP-001..009. Limites do primeiro ensaio não redefinem o produto.
- **RISK-002**: Conservar apenas duas fontes recentes não resolve pendências longas.
- **RISK-003**: A reserva antes do produtor pode impedir repetição, mas crash após
  RNG e antes da retenção deixa resultado incerto. Não prometer recuperação desse
  resultado ou inventar rerrolagem automática.
- **RISK-004**: Um modelo pode satisfazer schema e ainda produzir estagnação ou
  causas não sustentadas. Os lotes anteriores continuam evidência dessas limitações.
- **ASSUMPTION-001**: Uma cena com interlocutor e objetivo é proposta de cobertura
  mais representativa; não é evidência de que o modelo melhorará.
- **ASSUMPTION-002**: CAMP-01..24 permanecem abertas. Sessão zero, arco misto e
  culminação não serão definidos implicitamente pelo setup desse ensaio.

## 8. Related Specifications / Further Reading

- [Consulta B concluída](../evals/narrator/reports/narrative-source-operation-status-2026-09-11.md)
- [Desenho histórico de integração](../evals/narrator/reviews/narrative-source-integration-design-2026-09-07.md)
- [Coordenador e retenção](architecture-narrative-source-coordinator-1.md)
- [Direção improvisacional vigente](../spec/spec-improvisational-scene-direction.md)
- [Pausa/retomada proposta, decisões separadas](feature-narrator-pause-resume-1.md)
- [Checklist de campanha híbrida, ainda aberto](checklist-planejamento-campanha-hibrida.md)

Revisão independente encerrada em 11/09/2026: contrato/guarda sem bloqueadores;
161 testes passaram (72 novos + 89 regressões diretas). Desenho do produtor revisado
com terminalização segura, CAS e finalização P/K atômica explícitos. Tarefas de
código do produtor são contabilizadas somente no plano próprio; nenhuma rota,
teste de uso ou default foi ativado por esta entrega.
Prova: [relatório da entrada](../evals/narrator/reports/narrative-source-entry-2026-09-11.md).
