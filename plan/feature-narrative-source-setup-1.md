---
goal: Compor setup B explícito, introdução autorada e ação real antes do transporte optativo
version: 1
date_created: 2026-09-11
last_updated: 2026-09-11
owner: Agente Storyteller
status: 'Completed'
tags: [narrative-source, setup, introduction, internal]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

O produtor interno já pode receber intenção, reservar a operação antes de interpretar,
produzir um recibo e retê-lo; o coordenador narrativo consome essa cápsula. O próximo
incremento reúne essas peças com uma preparação inicial compreensível, sem ativar
frontend ou converter o jogo v1. Incremento concluído em 11/09/2026; 488 casos distintos passaram, 184 novos.

A primeira composição é sintética e interna. Um briefing autorado apresenta local,
NPCs e objetivo declarado; não é narrativa atribuída ao modelo nem decisão de campanha.

## 1. Requirements & Constraints

- **REQ-001**: Criar somente campanha nova B, com origem explicit_server_seed,
  cena de local/elenco e summary/details/open_threads vazios, last_turn=0.
  Repetição de sessão recusa, sem overwrite ou migração de save v1.
- **REQ-002**: Setup público versionado com local, elenco e objetivo declarado.
  Ficha elegível ao perfil, estado, relações, identidade da sessão e configuração
  LLM pertencem ao servidor. Cliente não envia recibo, faces, SourceProjection,
  prompt, provider, efeitos ou resumo histórico como autoridade.
- **REQ-003**: Briefing identificável como preparação autorada do ensaio. Apresentar
  os dados recebidos e a intenção declarada, sem fabricar pista, incidente, segredo,
  turno, invocação, fonte atribuída ou avanço de revisão pela apresentação.
- **REQ-004**: Objetivo/briefing em state não chegam automaticamente ao H6. O contrato
  atual leva local/elenco, ação atual, recibo e até duas fontes. Não projetar briefing
  como fonte. No primeiro ensaio, o objetivo pode constar da fala realmente escolhida
  pelo jogador; oferecer sugestão não significa enviá-la em nome dele.
- **REQ-005**: Guardar o manifesto de setup separado da fonte narrativa antes de
  prometer reapresentação após reconexão. O contrato puro pode produzir o manifesto
  sem I/O; sua gravação/consulta exigem desenho transacional em TASK-003 antes do código.
  create_narrative_source_campaign atual persiste origem, não objetivo/briefing.
- **REQ-006**: Composição usa prepare_source_player_action e depois
  execute_retained_source_turn por identidade. Não chamar outro classificador,
  reconstruir recibo, reservar H genericamente ou inferir retry de pending/terminal.
- **REQ-007**: Explicitar o recorte antes do uso: cena conhecida, elenco fixo, ficha
  sintética elegível, espera, conversa enquadrada e investigação ordinária. Não
  apresentar esse ensaio como campanha completa ou compreensão geral de texto livre.
- **REQ-008**: Transporte futuro escolhe B antes de load_session_state e de qualquer
  inicialização/reserva legada em main.py. Sessão e autorização de acesso vêm do
  servidor; hashes e IDs não autenticam usuário. Eventos operacionais públicos são
  projeções seguras distintas do request/claim internos completos.
- **CON-001**: Não ativar rota/UI/default, acessar save real/.env/chave ou chamar
  provedor neste incremento offline. Observação real posterior terá manifesto,
  alvo/parâmetros/limites explícitos e mecanismo seguro já autorizado pelo usuário.
- **CON-002**: CAMP-01..24 e DEC-001/002/003 seguem abertas; nenhuma sessão zero,
  trama macro, segredo, culminação ou recuperação incerta decidida por este setup.
- **CON-003**: Não alterar corpus/gates anteriores para fazer o ensaio passar;
  critérios técnicos e experiência narrativa permanecem separados.

### Exemplo de apresentação, ainda proposto

“Preparação autorada deste ensaio. Você está na Galeria, onde Mara está presente.
Seu objetivo declarado é conhecer melhor o lugar por meio dessa conversa.”

Uma ação sugerida, a ser efetivamente escolhida pelo jogador, poderia ser
`Pergunto a Mara: "Quero conhecer melhor este lugar. O que você pode me contar?"`.
O briefing não envia essa fala, não cria fonte e não promete o conteúdo da resposta.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Fixar setup/briefing público e sua separação dos dados autoritativos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Criar api/narrative_source_setup.py com modelos puros estritos de pedido público e manifesto versionado, cópias/limites literais compatíveis com SceneState/entrada e briefing autorado. Vincular local/elenco/objetivo sem gerar fonte. Ficha/configuração servidor em argumentos separados. | Sim | 2026-09-11 |
| TASK-002 | Criar tests/test_narrative_source_setup.py: tipos, extras privilegiados, origem falsa, cena enriquecida/legada, literalidade, objetivo como intenção e ausência de RNG/LLM/persistência. Revisão independente antes de congelar. | Sim | 2026-09-11 |

### Implementation Phase 2

- GOAL-002: Tornar a criação e reapresentação do setup duráveis, sem história inventada.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-003 | Inspecionar contratos de metadata/origem e escolher formato versionado do manifesto público e gravação atômica com criação. Documentar leitura/reconexão, fonte de verdade e conflito de sessão existente antes de escrever persistência. Preferir estruturas existentes sem DDL; não afirmar que a API atual já persiste manifesto. | Sim | 2026-09-11 |
| TASK-004 | Implementar o serviço interno de setup e somente os métodos de persistência necessários conforme TASK-003. Testar campanha nova, sessão existente, origem, manifesto íntegro após restart, contadores iniciais, zero P/K/H/fonte pela introdução e rollback. Preservar caminhos existentes. | Sim | 2026-09-11 |

### Implementation Phase 3

- GOAL-003: Exercitar o percurso completo e preparar transporte separado.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Criar composição interna setup→ação escolhida→produtor→K→H6 com FakeLLM e banco temporário. Provar conversa com objetivo, investigação com sucesso/falha, espera, fonte anterior íntegra, reentrada/reconexão sem nova resolução/chamada. Documentar que fixture autorada não demonstra capacidade live. | Sim | 2026-09-11 |
| TASK-006 | Preparar plano separado de transporte optativo: seleção anterior ao legado, sessão servidor, eventos seguros para P/recusa/K/H e briefing reapresentável. Registrar superfície/arquivos, limites e verificações antes de rota ou frontend; relatório, README e retomada atualizados. | Sim | 2026-09-11 |

### Desenho transacional fixado em 11/09/2026 — TASK-003

O manifesto usa `narrative-source-setup-manifest-v1`, kind `authored_trial_setup`,
pedido público, origem, briefing determinístico e fingerprint SHA256. O pedido
`narrative-source-setup-request-v1` contém apenas location, npcs_present e
declared_objective. A factory pura recebe session_id do servidor separadamente;
nenhum hash autentica autoria ou acesso à sessão.

Persistência em `campaigns.metadata_json`, com ORIGIN_KEY e
`narrative_source_setup_manifest` escritos juntos. Não há nova tabela ou DDL.
`create_source_setup_campaign(session_id, *, manifest, initial_state,
relationships=None, chronicle_name="")` valida e copia os argumentos antes do
primeiro await, abre banco existente mode=rw e BEGIN IMMEDIATE, recusa qualquer
sessão existente, insere a campanha uma vez e confere a linha antes do commit.
Bootstrap do banco é explícito e separado; o método não inicializa/migra schema.
Falha reverte a transação e fecha a conexão. Não criar campanha e anexar manifesto
em duas operações, porque permitiria uma campanha parcialmente preparada.

`read_source_setup_manifest(session_id)` abre mode=ro e uma transação de leitura,
confere schema, manifesto bruto, sessão e origem integral, e usa o leitor interno
de snapshot na mesma conexão para validar a história. Funciona depois de avanços
e reinício; ausência/corrupção recusa, sem reconstrução de objetivo. Não chama
initialize nem o wrapper mutante de snapshot. Retorna cópia validada do manifesto.

`create_source_trial_setup(*, session_id, request, store, initial_state,
relationships=None, chronicle_name="")`, em narrative_source_setup_service.py,
constrói o manifesto e assenta a única criação mesmo sob cancelamento repetido.
Ficha, relações e identidade são fornecidas pelo servidor; a configuração LLM
permanece no produtor de ação. Elegibilidade mecânica é verificada nesse produtor,
sem criar ação fictícia para testá-la durante a apresentação.

Erros fechados SourceSetupPersistenceError: query_invalid, database_unavailable,
schema_incompatible, campaign_exists, campaign_missing, manifest_missing,
manifest_invalid, history_invalid e arguments_invalid, com prefixo source_setup_.
Nenhum diagnóstico bruto é exposto. Contadores começam em zero; apresentação não
cria P/K/H, fonte ou recibo. Commits B preservam os metadados existentes.

Limite: o escritor genérico update_campaign_snapshot continua capaz de substituir
metadados que não sejam ORIGIN_KEY. O novo fluxo não o utiliza; leitura detecta
remoção ou corrupção, sem prometer imutabilidade global contra escritores externos
ou autenticidade criptográfica. Métodos existentes permanecem preservados.

Desenho registrado antes da implementação da persistência; testes e revisão
concluídos posteriormente, conforme relatório de setup. TASK-005 foi uma composição dos serviços existentes em testes, sem
wrapper de runtime redundante. Nenhuma rota ou UI é ativada.

## 3. Alternatives

- **ALT-001**: Trocar somente H6 no WebSocket descartado: inicialização, migração e
  reserva v1 já ocorreriam antes; preservação de B exige seleção mais cedo.
- **ALT-002**: Converter briefing autorado em SourceProjection descartado: inventa
  atribuição/invocação. Apresentação e fonte do modelo têm origens distintas.
- **ALT-003**: Colocar objetivo em state e supor que H6 o lê descartado: pacote atual
  não exporta campos opacos do estado. Usar ação realmente escolhida ou planejar
  futuramente extensão explícita de contexto, sem aplicá-la silenciosamente aqui.
- **ALT-004**: Reapresentar briefing só em memória pode servir a um teste isolado,
  mas não satisfaz reconexão durável; formato/armazenamento devem ser resolvidos.

## 4. Dependencies

- **DEP-001**: Produtor pré-recibo e coordenador retido verificados no relatório
  narrative-source-input-producer-2026-09-11; nenhuma biblioteca nova necessária.
- **DEP-002**: Perfil source-local-ordinary-v1 e dados autorados elegíveis; ensaio
  não deve alterar ficha real para satisfazer limitações técnicas.
- **DEP-003**: Setup puro, persistência sintética e composição FakeLLM não exigem
  chave nem nova intervenção humana. Credencial só importa na observação externa.
- **DEP-004**: Escolhas de campanha e mudança do contrato de contexto permanecem
  separadas. A preferência pelo jogo completo atual não é substituída por este ensaio.

## 5. Files

- **FILE-001**: Novos api/narrative_source_setup.py e tests/test_narrative_source_setup.py.
- **FILE-002**: Serviço de setup e composição, nomes e assinaturas fixados em TASK-003/005.
- **FILE-003**: api/persistence.py somente após desenho TASK-003, com verificações próprias.
- **FILE-004**: api/main.py e client/ são referências para o plano de transporte,
  sem alteração neste incremento. README, relatório e retomada registram resultados.

## 6. Testing

- **TEST-001**: Setup/briefing não criam turno, invocação, fonte, recibo ou avanço de revisão.
- **TEST-002**: Manifesto recuperado após restart corresponde ao setup original;
  sessão existente/legada e manifesto adulterado recusam sem overwrite.
- **TEST-003**: No primeiro turno, o objetivo do setup só é acrescentado ao pacote
  por ação realmente escolhida pelo jogador. Briefing não é injetado nem promovido
  a fonte; fontes posteriores continuam seguindo o contrato atual. Nenhuma fala automática.
- **TEST-004**: Conversa, resolução real controlada de sucesso/falha e espera chegam
  ao H6 uma vez; repetição/reconexão conservam recibo, identidade e fonte anterior.
- **TEST-005**: Critério narrativo posterior exige reação/avanço concreto, consequência
  compatível, agência e continuidade dependente. HTTP/schema não bastam.
- **TEST-006**: Bancos temporários, FakeLLM, conftest, dotenv desabilitado, revisão e
  hashes estáveis; nenhum live, default, frontend ou save real afetado.

## 7. Risks & Assumptions

- **RISK-001**: Briefing útil ao jogador não implica contexto útil ao modelo.
- **RISK-002**: História limitada a duas fontes não sustenta automaticamente campanha
  longa, pendências persistentes, novos NPCs ou mudança de local.
- **RISK-003**: Gramática local é limitada; documentação deve evitar frustração por
  prometer liberdade que esse ensaio ainda não oferece.
- **ASSUMPTION-001**: NPC presente e objetivo em fala escolhida são hipótese de ensaio
  mais representativo; não evidência de melhora do modelo ou aceitação narrativa.
- **ASSUMPTION-002**: Nenhuma decisão de campanha híbrida foi fixada pelo exemplo.

## 8. Related Specifications / Further Reading

- [Produtor interno concluído](feature-narrative-source-input-producer-1.md)
- [Relatório técnico do produtor](../evals/narrator/reports/narrative-source-input-producer-2026-09-11.md)
- [Origem e leitores B](architecture-narrative-source-readers-1.md)
- [Entrada optativa](feature-narrative-source-opt-in-entry-1.md)
- [Campanha híbrida, perguntas abertas](checklist-planejamento-campanha-hibrida.md)
- [Direção improvisacional](../spec/spec-improvisational-scene-direction.md)

Revisão documental independente em 11/09/2026: contrato e limites conferidos;
critério de objetivo esclarecido para distinguir primeiro turno de fontes posteriores.
Na revisão inicial todas as tarefas estavam pendentes. O desenho TASK-003 acima foi registrado posteriormente; não há ativação de rota.

Fechamento em 11/09/2026: todas as seis tarefas concluídas. A criação também
recusa linhas órfãs da mesma sessão em attempts/turns/events/memórias. 110 funções
anteriores e schema preservados. Correção de configuração sintética NPC após
falha inicial, com evidência mantida; nenhuma política afrouxada.
[Relatório e verificação](../evals/narrator/reports/narrative-source-setup-2026-09-11.md).
[Transporte preparado](feature-narrative-source-transport-1.md), ainda sem ativação.
