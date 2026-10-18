---
goal: Reservar a produção de uma ação B antes de classificação e RNG e reter seu recibo atomicamente
version: 1
date_created: 2026-09-11
last_updated: 2026-09-11
owner: Agente Storyteller
status: 'Completed'
tags: [narrative-source, input-producer, persistence, internal]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Produtor servidor interno concluído em 11/09/2026: modelos, claim/finalize,
adaptador local e serviço, com revisão independente e 594 testes distintos
pertinentes ao produtor aprovados. Incluindo a entrada previamente verificada,
são 683 casos distintos. Nenhuma rota, alvo LLM, frontend ou save real foi ativado.
Plano separado de setup/introdução preparado, ainda sem implementação.

A primeira integração continua interna, com dados sintéticos. Classificação local e
resolução ordinária devem ser demonstradas antes de oferecer o ensaio ao jogador.
Hash, tipo e nome de produtor provam consistência; não autenticam um cliente ou
demonstram por si que o motor foi executado.

## 1. Requirements & Constraints

- **REQ-001**: Manter três identidades separadas: P, controle do produtor;
  K, controle existente da cápsula; H, operação narrativa existente. P deriva somente
  de protocolo/sessão/operation_id lógico; H continua usando o operation_id lógico.
  Base, input, configuração e relógio não criam outro ID para a mesma operação.
- **REQ-002**: Usar protocolo `narrative-source-input-producer-v1` e IDs
  `source-input-operation-`/`source-input-attempt-` seguidos de SHA-256 do JSON canônico
  `[protocol, session_id, operation_id, role]`, role `operation` ou `attempt`.
  JSON UTF-8, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False.
- **REQ-003**: Pedido persistido de P contém protocolo, sessão, operation_id lógico,
  input literal, created_at original definido pelo servidor, SourceContextSnapshot
  completo, estado/relacionamentos da mesma revisão e configuração pública exata.
  Guardar valores necessários à reconstrução, não apenas hashes. Nenhuma credencial,
  gateway, callback, cancellation, deadline ou objeto de conexão é persistido.
- **REQ-004**: `SourceProducerConfig` contém perfil local explícito, target, prompt
  SYSTEM, GenerationParameters, aliases e chronicle_name; valida tipos/cópia/JSON
  pelos contratos B existentes. protected_secrets deve ser vazio neste perfil.
  O perfil inicial permite somente H0/H1 locais e nenhuma H4. Configuração não vem
  do envelope do cliente. Não depender de settings globais para escolher fallback.
- **REQ-005**: `claim_source_input(session_id, request, *, producer_config)` procura
  P existente antes de obter nova base ou novo horário. Mesmo pedido/configuração
  devolve estado original revalidado, sem autorização de produção. Mudança de input
  ou configuração para o mesmo ID conflita. A operação nova captura snapshot,
  estado/relacionamentos e horário dentro da sua transação; cliente não escolhe base.
- **REQ-006**: Para P novo, validar campanha B existente, história e revisão; não
  criar/migrar campanha. Usar `BEGIN IMMEDIATE` para leitura da base e reserva P.
  No primeiro coordenador, serializar entrada por sessão como o fluxo atual. A
  guarda persistente adicional impede dois produtores B ativos para a mesma sessão:
  P pending, ou P completed com K válido e H ausente/pending, mantém a sessão ocupada.
  H terminal ou concluído encerra esse impedimento. Antes de decidir ocupação,
  revalidar identidade/hash e pares P/K/H: estado desconhecido, controle órfão,
  K ausente em P completed ou vínculo divergente recusam por integridade, nunca
  liberam a sessão. Controles de outro domínio ficam fora desta guarda; não criar
  restrição geral aos chamadores internos antigos nem alterar sua concorrência.
- **REQ-007**: Somente o retorno novo de claim autoriza chamar o produtor no processo
  servidor. Duplicatas, reinício, pending ou terminal não recebem essa autorização.
  Não manter transação SQLite aberta durante interpretação, cálculo ou RNG.
- **REQ-008**: `finalize_source_input` primeiro localiza e revalida P na transação.
  Se terminal, aceita somente repetição exatamente idêntica do resultado original,
  revalidando K quando completed; retorna sem escrita e antes do CAS da base atual.
  Somente a primeira finalização de P pending com preparação aplica CAS da base:
  grava K no formato existente e conclui P na MESMA transação, vinculando
  capsule_operation_id e capsule_sha256. Não criar H. Falha/cancelamento/timeout
  validam identidade/hash original, P pending e ausência de K/H, sem exigir base
  atual: gravam somente P terminal com código fechado, sem turno/revisão/efeitos
  ou exceção livre. Base obsoleta termina failed/source_input_base_mismatch sem K.
  Esclarecimento usa failed/source_input_clarification_required; fora de escopo
  usa failed/source_input_out_of_scope. A resposta nova do jogador usa outro ID;
  não reabre o pedido terminal. Conteúdo divergente nunca substitui o original.
- **REQ-009**: Recalcular request_hash a partir da metadata inicial preservada e
  result_hash a partir do resultado terminal, em formatos compatíveis com a tabela
  attempts. Não usar metadata terminal como se fosse metadata do pedido original.
- **REQ-010**: P completed com K válido e H ausente permite ao chamador autorizado
  delegar a primeira H6 ao coordenador atual; P nunca toma a reserva H. H pending ou
  terminal conserva consulta/replay atuais, sem nova chamada ou inferência de retry.
- **REQ-011**: A leitura repetida deve reconstruir o pedido original. Base atual
  diferente não reinterpreta o input; P novo usa a base atual, P antigo conserva a
  sua. Escrita concorrente externa ao novo coordenador continua podendo invalidar
  a base; o CAS recusa reter K e permite terminalizar P como falha segura, sem efeitos preparados.
- **REQ-012**: Não expor snapshots completos, configuração, recibos ou diagnóstico
  livre pela interface futura. Retorno operacional público é projeção separada,
  a ser definida antes de qualquer rota; o modelo interno não é autorização de acesso.
- **REQ-013**: O perfil literal `source-local-ordinary-v1` não produz alterações
  genéricas de estado/relacionamentos: a cápsula de sucesso deve conter valores
  idênticos aos capturados no pedido. Recibo ordinário expressa sucesso/falha;
  novo contrato de efeitos não é criado por este incremento.
- **REQ-014**: Modelos internos puros: SourceInputRequest conserva pedido/base/
  configuração e fingerprint; SourceInputClaim agrega request/status/newly_claimed/
  completion opcional; SourceInputCompletion vincula request_sha256 e, em completed,
  K por capsule_operation_id/capsule_sha256. Demais terminais exigem failure fechado
  e não têm K. newly_claimed só existe como resultado observacional da transação:
  construir/validar esse objeto não autentica posse. O serviço recebe o
  retorno direto de claim_source_input, nunca um claim fornecido pelo cliente.
- **CON-001**: Sem DDL/schema bump, migração, refatoração de métodos existentes,
  retry, takeover, lease, novo estado paused ou liberação automática por relógio.
- **CON-002**: `recover_pending_attempts` continua explícito no startup vigente.
  Não o chamar como parte de consulta. Um P recuperado como cancelled permanece
  terminal; novo ID é outra ação, sem reutilizar resultado incerto da anterior.
- **CON-003**: Nenhum dado real/chave/.env, ativação de UI/default, chamada externa
  ou promoção de CAP-001 nos incrementos locais abaixo.

### Estados, transições e janelas de crash

| Estado persistido | Resposta do novo coordenador | Produção/RNG adicional |
|---|---|---|
| P/K/H ausentes | Claim novo captura base e insere P pending; só vencedor produz. | Permitida uma vez ao vencedor, após os checks de escopo. |
| P pending, K/H ausentes | Retornar pending. Pode ter parado antes ou depois de RNG. | Proibida para reentrada. |
| P pending com K ou H | Par inválido para este produtor. | Proibida. |
| P completed + K íntegro, H ausente | Recuperar preparação original e delegar primeira H6 pela entrada autorizada. | Nenhuma nova interpretação/rolagem. |
| P completed + K íntegro, H pending/terminal | Consultar/reproduzir estado H já existente. | Nenhum novo dispatch por inferência. |
| P completed sem K válido | Recusa fechada por integridade. | Proibida. |
| P failed/timeout/cancelled | Retornar terminal original seguro. | Proibida. |
| K/H sem P no domínio novo | Não adotar como produção validada. Preservar chamadores antigos fora deste coordenador. | Proibida nessa entrada. |

Crash antes do claim não autoriza produção. Depois do claim, antes ou depois do RNG,
P pending não demonstra o que ocorreu. O recibo em memória pode ser perdido; não
prometer recuperá-lo. A gravação atômica elimina a janela K salvo/P não concluído.
Depois dessa transação, o recibo durável pode ser usado sem outra rolagem. Uma falha
de H6 não reabre P nem aplica estado parcial.

### Por que chamadas existentes isoladas não bastam

`start_attempt` pode criar campanha e não captura base por CAS; `complete_control_attempt`
pode completar sem claim e substitui metadata; `save_source_preparation` possui
transação própria e não conhece P. Combinar as três chamadas sequencialmente
deixaria uma janela entre K e P. Acrescentar métodos específicos e reutilizar
validadores/formatos existentes; preservar o texto das funções anteriores.

### Adaptação do produtor local

| Retorno/caminho | Tratamento no primeiro perfil |
|---|---|
| Declaração local reconhecida, sem mecânica ou efeito protegido | DeclaredActionPreparation, sem RNG. Manter input literal. |
| Teste ordinário reconhecido e não oposto, sem arma/poder/flags especiais | Criar V5ActionPayload pelo servidor; calcular pool de ficha confiável; chamar calculate_resolution uma vez e converter recibo real. |
| Fome diferente de zero ou condição que possa exigir consequência especial não coberta | Recusar antes do RNG. Não zerar Fome ou descartar messy/bestial. Esta limitação pertence ao ensaio inicial. |
| Frenesi, despertar, alimentar, cura, sangue, rerrolagem, combate/oposição, poder, economia ou metajogo | Recusa explícita antes do respectivo efeito/RNG. Não transformar em declaração simples. |
| Esclarecimento de alvo/mecânica necessário | P failed/source_input_clarification_required, sem K/H/turno/RNG; resposta operacional sem escolher pelo jogador. Resposta esclarecida usa novo ID; não exigir detalhe apenas cosmético. |
| Lore, consulta isolada de cena ou abertura | Fora do perfil do primeiro produtor; sem H4, sem semear cena v1, sem gerar fato a partir de texto livre. |
| Classificação indeterminada ou intenção composta fora de cobertura | P failed/source_input_out_of_scope sem K/H/efeito/RNG; sem fallback genérico para declaração. A limitação deve aparecer nos critérios do ensaio. |

Todas as recusas de perfil da tabela usam P failed/source_input_out_of_scope.
Esclarecimento não é preparação completa sem cápsula.

H0 `_deterministic_triage` classifica rota; H1 `_create_fallback_payload` conserva
texto, mas não decide mecânica. `_mechanical_action_from_intent` e os detectores
locais do orchestrator possuem caminhos para poderes/economia. A adaptação deve
provar, com corpus positivo e negativo, quais famílias reconhece antes de habilitar
RNG. Não importar `prepare_turn_pipeline` inteiro nem afirmar compreensão geral de
texto livre. Nenhum parser semântico geral ou chamada LLM adicional obrigatória é
criado por este plano.

### Contrato concreto da persistência

```python
async def claim_source_input(self, session_id, request, *, producer_config) -> SourceInputClaim: ...
async def finalize_source_input(
    self, session_id, operation_id, *, request_sha256,
    completion, capsule=None,
) -> SourceInputClaim: ...
```

Recusas da camada de armazenamento usam erro fechado próprio
`SourceInputPersistenceError`, implementado em TASK-003, com códigos
`source_input_database_unavailable`, `source_input_schema_incompatible`,
`source_input_history_invalid`, `source_input_stored_pair_invalid`,
`source_input_operation_conflict`, `source_input_session_busy` e
`source_input_claim_missing`. Não são SourceInputFailure: banco indisponível,
ocupação ou conflito não provam que P se tornou terminal e não escrevem uma falha
na operação de outra execução. Os códigos de modelo existentes ficam preservados.

As duas fronteiras copiam/revalidam argumentos antes do primeiro await e usam
banco existente `mode=rw`, schema atual, transação curta e close explícito. Não
chamam initialize ou outros métodos públicos que abram uma segunda transação.
Na conexão da reserva, `_source_context_snapshot_in_connection` fornece contexto;
estado/relacionamentos e horário do servidor são capturados na mesma transação.
Somente depois do commit confirmado retorna newly_claimed=True.

Finalização compara request_sha256 com o pedido original persistido e recompõe
a conclusão a partir da cápsula completa. A precondição usa o hash do pedido no
formato attempts, distinto do fingerprint do modelo. `_source_preparation_payloads`
fornece formato e hashes de K; INSERT K e UPDATE P pertencem à mesma transação.
Retorno terminal por base obsoleta precisa concluir a transação, sem lançar uma
exceção que desfaça a falha segura acabada de registrar.

`recover_pending_attempts` pode gerar cancelled/process_interrupted com metadata
inicial, sem narrative_source_input_completion, e hash terminal genérico de falha.
O novo leitor deve validar exatamente esse ramo histórico, inclusive erro fixo e
hash original/terminal, e projetar conclusão segura sem reescrever a linha. Isso
não concede recuperação, nova rolagem ou takeover. Teste exige recuperação real
em banco sintético, sem simular que ela já escreva o novo formato.

O snapshot original precisa corresponder ao prefixo histórico, mesmo após sair
da janela das duas fontes recentes. P completed reaproveita a restauração de K;
P pending/failed sem K exige validação específica desse prefixo na conexão atual,
sem fabricar cápsula provisória ou mascarar um SourceInputRequest como cápsula.
Revalidar estado/pares antes de decidir ocupação. Nenhuma função anterior muda.

### Contrato do serviço e cobertura local inicial

`prepare_source_player_action` recebe sessão, request público, store, configuração
servidor, deadline absoluto com fuso e CancellationToken. Não aceita claim, recibo,
pool ou callback de produtor do cliente; chama somente o adaptador local fixo.
Reserva e finalização são operações locais protegidas até sua conclusão, inclusive
sob cancelamentos repetidos. Cancelamento durante claim novo encerra P cancelled
sem produzir; durante finalização pode observar K/P já concluídos e propaga o
cancelamento sem refazer trabalho. Crash incerto deixa pending, sem takeover.

O adaptador síncrono tem gramática finita e pool limitado; deadline é conferido
antes e depois, não é interrupção preemptiva de CPU. Handles não são persistidos.
O produtor recebe cópia própria do pedido. Seu retorno é DeclaredActionPreparation,
ResolvedActionPreparation ou SourceInputFailure; erro inesperado vira código seguro
sem exceção livre ou recibo parcial. O serviço somente prepara K, sem despachar H6;
testes ligam a cápsula ao coordenador narrativo já existente.

Cobertura primeira: espera, fala/pergunta dirigida a NPC conhecido com enquadramento
completo, investigação do local/ambiente conhecido. Investigação segue o mapeamento
local vigente Wits + Investigation, dificuldade servidor fixa 3. Neste perfil,
Wits 1..5, Investigation 0..5 e Fome zero limitam o pool a 1..10; nunca completar
estatística ausente ou aceitar pool/dificuldade digitados pelo cliente.
Observação/vigília/escuta ficam fora: o mapeamento vigente prevê Wits + Awareness,
portanto não serão reclassificadas como declaração. H0/H1/orchestrator não são
importados pelo adaptador, pois trazem settings e fallback amplo; reaproveitam-se
os contratos e o motor de regras, com corpus local explícito.

Inspecionar/rejeitar condições conhecidas em character.status (fora ACTIVE),
context.current_state/blocking/pending_roll, environmental_flags, trackers da ficha
e configuração mecânica incompatível. Guardas só alegam cobertura desses campos
documentados, não detecção universal de extensões desconhecidas. Texto/estado/
relacionamentos permanecem literais; classificar não altera fonte canônica.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Fixar identidades, pedido imutável e resultados internos do produtor.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Criar `api/narrative_source_input.py`: SourceProducerConfig, SourceInputRequest, SourceInputClaim, SourceInputFailure e SourceInputCompletion; IDs P e hash canônico conforme REQ-002/003/009. Preservar raw fields de instâncias forjadas, tipos estritos, cópias, limites de entrada, sessão e ausência de segredos/handles. | Sim | 2026-09-11 |
| TASK-002 | Criar `tests/test_narrative_source_input.py`: IDs independentes de base/horário/conteúdo, fingerprints sensíveis ao conteúdo, conflito vs identidade, forged models, código seguro, snapshots/cópias e nenhuma autoridade/RNG originada do cliente. | Sim | 2026-09-11 |

### Implementation Phase 2

- GOAL-002: Reservar produção e finalizar P/K atomicamente, sem alterar H ou funções anteriores.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-003 | Acrescentar `SQLitePersistence.claim_source_input` e seus helpers privados: primeira consulta de P, comparação do pedido/configuração, validação de origem/história, base capturada da campanha e guarda dos produtores ativos; BEGIN IMMEDIATE sem criar campanha ou chamar RNG. Depende de TASK-001/002. | Sim | 2026-09-11 |
| TASK-004 | Acrescentar `SQLitePersistence.finalize_source_input`: revalidar claim/base, inserir controle K no formato existente e completar P atomicamente; falha/cancelamento sem K; digests separados; nenhum commit de estado/turno. Testar rollback com falha entre as duas gravações. Depende de TASK-003. | Sim | 2026-09-11 |
| TASK-005 | Criar `tests/test_narrative_source_input_persistence.py` com concorrência mesma/diferente operação, base/configuração alteradas, controles legados, corrupção, rollback, estados após restart e compatibilidade do K com load_source_preparation/read_source_operation_status. Incluir recuperação real cancelled/process_interrupted com metadata inicial e pedido histórico fora da janela de duas fontes. Confirmar funções antigas e schema intactos. Depende de TASK-004. | Sim | 2026-09-11 |

### Implementation Phase 3

- GOAL-003: Fechar o produtor de ação antes de expô-lo a qualquer transporte.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-006 | Em `api/narrative_source_input_service.py`, criar `prepare_source_player_action`: validar request/configuração servidor, claim antes de interpretar, chamar produtor somente no claim novo, finalizar P/K, retornar resultado interno. Não despachar H6 dentro da transação; não aceitar produtor/recibo do cliente. Usar produtor autorado nos primeiros testes desse encadeamento. | Sim | 2026-09-11 |
| TASK-007 | Preparar adaptador local de produção em `api/narrative_source_action_producer.py`: inspecionar e reaproveitar apenas funções locais de triagem/intenção/pool necessárias; validar ficha e regras servidor, reconhecer explicitamente cobertura ordinária, recusar caminhos da tabela antes de RNG. Registrar corpus de cobertura e testes antes de ligar adaptador ao coordenador. Não alterar H0/H1 globais ou importar pipeline completo. | Sim | 2026-09-11 |
| TASK-008 | Criar `tests/test_narrative_source_input_service.py` e `tests/test_narrative_source_action_producer.py`: produtor contado, motor real com dados controlados, sucesso/falha, declaração, fora de escopo, erro/cancelamento/restart e entrega da mesma cápsula ao H6 FakeLLM sem reinterpretação. Depende de TASK-006/007. | Sim | 2026-09-11 |
| TASK-009 | Revisão independente, regressões pertinentes uma vez por versão congelada, relatório com hashes/resultados e atualização de README/retomada. Preparar separado o contrato de criação/setup/introdução e transporte optativo; não ativar frontend neste plano. Depende de TASK-008. | Sim | 2026-09-11 |

## 3. Alternatives

- **ALT-001**: Reusar o ID H na reserva pré-RNG descartado: bloqueia retenção e
  conflita com a metadata estática que o executor H6 exige.
- **ALT-002**: Sequenciar save_source_preparation + complete_control_attempt
  descartado: crash entre transações deixa K/P sem conclusão conjunta.
- **ALT-003**: Reabrir pending após timeout descartado: não prova ausência de RNG.
- **ALT-004**: Implementar agora pausa/retomada geral descartado: decisões específicas
  permanecem abertas e são distintas deste controle fechado.
- **ALT-005**: Modificar o pipeline legado para servir B descartado neste recorte:
  inclui inicialização/migração, H4 e efeitos não suportados pelo primeiro produtor.

## 4. Dependencies

- **DEP-001**: SourcePlayerActionRequest e validate_source_entry_snapshot do contrato
  de entrada; congelar e verificar antes de implementar este produtor.
- **DEP-002**: Origem B, validação de contexto, preparação, cápsula, executor e
  consulta de operação já existentes; nenhuma biblioteca nova.
- **DEP-003**: Ficha/estado e configuração provêm do servidor e da base persistida,
  nunca do envelope público. Definir o adaptador concreto em TASK-007.
- **DEP-004**: Não há dependência humana para conservar pending/terminal sem retry.
  Recuperar resultado incerto, reabrir terminal, liberar sessão automaticamente ou
  mudar política de pausa exigiria decisão separada; essas ações não estão no plano.
- **DEP-005**: Uso com jogador depende ainda de setup/introdução, superfície optativa
  e prova de progressão/continuidade. O fechamento técnico não é aprovação de campanha.

## 5. Files

- **FILE-001**: Novos `api/narrative_source_input.py`, `api/narrative_source_input_service.py`
  e `api/narrative_source_action_producer.py`, com testes correspondentes acima.
- **FILE-002**: `api/persistence.py`, somente novos métodos/importações necessários.
- **FILE-003**: README, este plano, relatório em `evals/narrator/reports` e topo da retomada.
- **FILE-004**: `api/main.py`, `api/orchestrator_service.py`, `api/state_service.py`,
  `api/h0_controller_service.py`, `api/parser_service.py`, `api/rules_service.py`,
  `api/economy_service.py` e `api/metagame_service.py` são referências de inspeção;
  adaptação não autoriza refatorar seus caminhos existentes.

## 6. Testing

- **TEST-001**: Duas entradas simultâneas da mesma operação: no máximo um produtor
  e uma resolução; repetição consulta o estado original. Outro ID enquanto P/H
  ativo não inicia outro produtor na nova entrada.
- **TEST-002**: Crash após claim, antes/depois RNG e antes da transação P/K:
  reentrada não chama produtor; startup explícito pode cancelar sem reabertura.
- **TEST-003**: Injeção de falha entre INSERT K e UPDATE P reverte ambos; commit
  bem-sucedido permite recuperar K e concluir H6 sem novo RNG.
- **TEST-004**: Alterar input/configuração para mesmo ID conflita; avanço posterior
  de revisão não reconstrói nem substitui pedido antigo. CAS recusa efeito obsoleto.
- **TEST-005**: Provar fonte real do pool/dificuldade e recibo com motor; H1 só texto
  não fornece números autoritativos. Cliente não escolhe ficha/resultado/flags.
- **TEST-006**: Fome/efeitos especiais não suportados recusados antes de rolagem;
  não ocultar messy/bestial, forçar sucesso ou reclassificar falha como declaração.
- **TEST-007**: Matriz posterior de experiência: introdução do setup, conversa com
  NPC presente, investigação com sucesso/falha, espera com reação e continuação
  dependente. Não exigir os mesmos literais da prosa; critérios narrativos separados.
- **TEST-008**: Bancos temporários, FakeLLM e conftest; preservar schema, funções
  antigas, digests históricos, default/UI e ausência de chamadas externas.

### Matriz de integração e experiência posterior

| Etapa | Prova exigida | Onde executar |
|---|---|---|
| Criação/setup | Nova campanha B com lugar, elenco e objetivo explícitos; sessão v1 recusada sem migração. | Contrato posterior de setup/transporte, ainda não implementado. |
| Introdução | Apresentar setup e oportunidade de ação, sem atribuir texto autorado ao LLM ou fabricar turno histórico. | Ensaio posterior; aceitação narrativa separada. |
| Intenção/classificação | Dois campos públicos; perfil local reconhecido ou recusa explícita antes de RNG. | TASK-001/002/007/008, offline. |
| Reserva/resolução | Um produtor por operação; pool servidor e uma resolução real controlada. | TASK-003/005/008, SQLite temporário. |
| Retenção/H6/commit | P/K atômicos; cápsula recuperada alimenta H6 existente e commit/replay sem nova resolução. | TASK-004/005/008, FakeLLM e banco temporário. |
| Diagnóstico | Falha/esclarecimento por código seguro; completed exige K e não promete prontidão pública. | TASK-001/002/005/008; projeção de transporte posterior. |
| Reconexão/reinício | Mesmo ID conserva estado; pending/terminal sem reentrada de produção; replay após avanço de revisão. | TASK-005/008; reconexão de UI somente no contrato posterior. |
| Progressão | Conversa, sucesso/falha, espera e continuidade causam movimento compatível e preservam agência. | Corpus autorado seguido de observação delimitada; não demonstrado por testes de tipo. |

## 7. Risks & Assumptions

- **RISK-001**: RNG e gravação não são uma única transação. Crash pode perder recibo
  apenas em memória; a garantia é impedir nova produção da mesma operação, não
  recuperar magicamente o resultado ou reverter o gerador global.
- **RISK-002**: A exclusividade vale para a nova entrada/controle P. Outros caminhos
  internos podem modificar a campanha; validar base na finalização continua obrigatório.
- **RISK-003**: Restrição a ações ordinárias/Fome zero é limite do ensaio inicial,
  não política geral V5 e não autoriza modificar a ficha para passar no filtro.
- **RISK-004**: A classificação local tem cobertura delimitada. Não confundir
  ausência de padrão reconhecido com ação seguramente livre de mecânica.
- **ASSUMPTION-001**: Testes autorados da produção isolam confiança/idempotência;
  não demonstram qualidade de narrativa, campanha longa ou capacidade do modelo.
- **ASSUMPTION-002**: Nenhuma alternativa aberta de CAMP-01..24 ou DEC-001/002/003
  foi decidida por este desenho; recuperação nova continua fora dele.

## 8. Related Specifications / Further Reading

- [Entrada optativa](feature-narrative-source-opt-in-entry-1.md)
- [Coordenador e retenção](architecture-narrative-source-coordinator-1.md)
- [Consulta operacional](feature-narrative-source-operation-status-1.md)
- [Preparação do recibo](architecture-narrative-source-preparation-1.md)
- [Pausa/retomada proposta, separada](feature-narrator-pause-resume-1.md)
- [Experiência improvisacional](../spec/spec-improvisational-scene-direction.md)

Revisões independentes documental, de implementação e de evidência encerradas
em 11/09/2026. Todas as tarefas deste plano concluídas no perfil interno descrito;
setup/transporte continuam separados. Relatório:
[produtor interno](../evals/narrator/reports/narrative-source-input-producer-2026-09-11.md).
Próximo plano: [setup e introdução](feature-narrative-source-setup-1.md), ainda Planned.
