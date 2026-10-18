---
goal: Produzir resultados canônicos narráveis e validar a projeção enviada ao narrador H6
version: 1.0
date_created: 2026-08-25
last_updated: 2026-08-26
owner: Codex
status: 'Superseded'
priority: 'Do not execute'
authorization: 'Superseded by explicit product direction'
execution_trigger: 'None'
depends_on: 'plan/architecture-llm-memory-turns-1.md'
superseded_by: 'spec/spec-improvisational-scene-direction.md'
tags: [architecture, narrative, grounding, context, validation, follow-up]
---

# Introduction

![Status: Superseded](https://img.shields.io/badge/status-Superseded-lightgrey)

> [!WARNING]
> Não execute este plano. Em 2026-08-26, o usuário definiu que a experiência deve
> usar improviso da LLM para conduzir e evoluir a cena. A formulação abaixo proíbe
> autoria ficcional geral e, portanto, foi substituída por
> `spec/spec-improvisational-scene-direction.md`. O histórico permanece somente
> para rastrear por que a abordagem conservadora produziu o comportamento rejeitado.

Esta é a próxima atividade autorizada para o agente de desenvolvimento. Ela deve começar imediatamente após a aceitação final da tarefa de implementação e validação atualmente em curso. Até esse marco, permanece enfileirada: sua existência não autoriza interromper o trabalho atual, alterar o seu diff nem misturar os dois critérios de aceite.

A atividade corrige a assimetria observada no fluxo atual: o motor determinístico preserva resultados mecânicos completos, mas o narrador H6 recebe sobretudo uma redução binária como `A ação falhou.` ou `A ação teve sucesso.`. Ao mesmo tempo, textos livres de H0/H4 podem carregar detalhes concretos sem fonte canônica. O resultado desejado é o inverso: H6 deve receber fatos narráveis, relevantes e rastreáveis produzidos pelo domínio, sem receber a ficha completa, resultados mecânicos brutos ou liberdade para transformar sugestões do LLM em verdade do mundo.

Este plano sucede `plan/architecture-llm-memory-turns-1.md`, preserva LLM-001 e a arquitetura transacional já implementada e não substitui a aceitação de execução real do predecessor. Antes de iniciar, o agente deve reinspecionar o estado e o diff compartilhados, pois a tarefa em curso pode ter evoluído depois da criação deste documento.

O trabalho é independente das propostas de bandeja de dados, redesenho acessível da interface e política de admissão de motores narrativos. Não decide provedor, modelo, custo, fallback, LLM-002 ou LLM-003.

## 1. Requirements & Constraints

- **REQ-001**: Módulos determinísticos de regras, estado e mundo devem produzir resultados canônicos narráveis além do resultado mecânico binário, sempre associados a uma fonte identificável. Um LLM pode redigir a apresentação, mas não criar o fato que será apresentado como ocorrido.
- **REQ-002**: Introduzir um contrato imutável `NarratableFact` com, no mínimo, `fact_id`, `fact_type`, `content`, `source_refs`, `visibility`, `importance` e `projection`; `source_refs` deve apontar para evento, regra, estado ou conteúdo versionado existente.
- **REQ-003**: Introduzir um agregado imutável `NarrativeProjection` contendo ação declarada, fatos narráveis canônicos, estado relevante, contexto conhecido, contexto confidencial e limites de geração. Cada item deve conservar identidade, origem e visibilidade.
- **REQ-004**: Uma investigação bem-sucedida só pode revelar uma descoberta concreta quando o módulo de mundo ou a entrada determinística fornecer um fato-fonte, por exemplo `warehouse.hatch_marks`. Na ausência de uma descoberta fonte, o preparador deve emitir apenas um resultado genérico explícito e canônico ou falhar como dado narrável insuficiente; nunca deve sintetizar uma pista.
- **REQ-005**: Uma investigação malsucedida sem consequência adicional deve projetar explicitamente que nenhuma conclusão segura foi obtida. Ela não pode transformar a falha em descoberta, perigo, ferimento, presença de inimigo ou mudança do mundo que não exista nos resultados canônicos.
- **REQ-006**: Rolagens, sucessos, dificuldade, dados normais, dados de fome e demais detalhes mecânicos continuam canônicos e persistidos. H6 recebe somente a projeção narrativa autorizada, salvo futura funcionalidade aprovada que peça a exposição de um detalhe específico.
- **REQ-007**: Corrigir a projeção de contexto para que fatos de estado selecionados como obrigatórios sejam efetivamente enviados a H6 uma única vez. Não descartar `ContextLayer.CANONICAL_FACTS` com base na suposição de que `SystemLogBuilder` já os projetou sem prova dessa projeção.
- **REQ-008**: A ficha completa nunca deve ser serializada para H6. Somente campos relevantes ao turno podem chegar como projeções tipadas, mínimas, com fonte e visibilidade. O fato de `player_sheet` estar disponível no orquestrador não autoriza seu envio integral.
- **REQ-009**: H0 não pode introduzir fatos concretos livres por `scene_notes`. Evoluir o contrato para `tone_tags: list[str]` e `scene_fact_ids: list[str]`; aceitar `scene_notes` legado somente para compatibilidade diagnóstica e jamais promovê-lo a fato narrável ou canônico.
- **REQ-010**: `tone_tags` deve conter apenas direções não factuais de apresentação, como `tenso`, `claustrofóbico` ou `silencioso`. Um item que afirme objeto, pessoa, evidência, condição física ou acontecimento deve ser recusado como tag.
- **REQ-011**: H4 permanece consultivo. Sua saída livre não pode virar verdade do mundo; afirmações concretas somente entram nas seções factuais de H6 quando correspondem a uma fonte estática ou canônica identificada.
- **REQ-012**: Filtrar o contexto de lore por relevância. Uma ação de investigação não pode receber automaticamente a entrada de arma `unarmed`; lore de arma só deve ser incluído quando a ação for agressiva ou uma arma for selecionada/usada explicitamente.
- **REQ-013**: O prompt H6 deve possuir seções delimitadas `AÇÃO DECLARADA`, `FATOS NARRÁVEIS CANÔNICOS`, `ESTADO RELEVANTE`, `CONTEXTO CONHECIDO`, `CONTEXTO CONFIDENCIAL` e `LIMITES`, sem duplicar o mesmo fato em mais de uma seção.
- **REQ-014**: `CONTEXTO CONFIDENCIAL` pode orientar omissão, prenúncio ou tom, mas não autoriza revelar o seu conteúdo ao jogador. A projeção deve preservar a separação conhecido/segredo já existente.
- **REQ-015**: H6 continua subordinado aos resultados mecânicos e recebe instrução explícita para não reverter sucesso/falha, não criar recompensa, pista, personagem, ameaça, dano ou transição de estado e não apresentar texto de sistema ao jogador.
- **REQ-016**: Validar deterministicamente a saída final de H6 antes de criar `NarrativeRecord` e antes do commit. A política inicial exige texto não vazio, um parágrafo, uma frase completa, entre 25 e 35 palavras, sem título, lista, rótulo de prompt, log ou detalhe mecânico proibido.
- **REQ-017**: Centralizar a política de forma em `NarrativeTextPolicy`. Contar palavras com expressão Unicode equivalente a `\b[\wÀ-ÿ]+(?:[-'][\wÀ-ÿ]+)*\b`; contar frases por terminadores `.`, `!` ou `?`, ignorando espaços finais; cobrir abreviações admitidas ou proibidas por testes explícitos, sem depender do provedor.
- **REQ-018**: A validação determinística não deve alegar provar ausência total de alucinação semântica. O controle semântico primário é reduzir a entrada a projeções com fonte; testes de integração devem comparar afirmações esperadas com essas projeções e manter avaliações mais amplas fora deste escopo.
- **REQ-019**: Uma saída final inválida deve produzir falha terminal normalizada e não pode ser confirmada como narrativa, evento ou memória. Não criar retry automático de H6, trocar alvo, modelo ou provedor. O usuário pode ter visto deltas provisórios, mas eles permanecem tentativa não canônica.
- **REQ-020**: O streaming deve conservar exatamente um terminal e nenhum delta posterior. A validação ocorre depois da montagem do texto final e antes do commit transacional; cancelamento, timeout, terminal ausente e texto inválido preservam o snapshot canônico anterior.
- **REQ-021**: Eventos canônicos, narrativa válida e memória derivada continuam sendo confirmados como uma unidade transacional. Memória somente deriva de evento e narrativa confirmados, respeitando visibilidade e referências de origem.
- **REQ-022**: Eventos e campanhas existentes devem continuar legíveis. Novos campos devem ter versão e caminho de leitura compatível; não reescrever, apagar ou alterar destrutivamente dados históricos apenas para preencher projeções ausentes.
- **REQ-023**: O pacote exato preparado para H6 deve ser testável offline, com identificadores de fonte preservados para asserções, sem registrar prompts, ficha, respostas ou segredos em logs de produção.
- **REQ-024**: O caso de regressão principal deve usar literalmente `Investigar o galpão abandonado` e provar a sequência: interpretação semântica não substitui o mapeamento determinístico, resultado mecânico gera projeção narrável, H6 recebe somente fatos permitidos e apenas uma narrativa válida é confirmada.
- **SEC-001**: Não abrir, copiar, registrar, imprimir ou incluir `.env` no diff. Nenhum teste deve depender de credencial ou modelo real.
- **CON-001**: O gatilho de execução é a aceitação final, pelo usuário, da tarefa corrente em execução real. O campo `Completed` do plano predecessor, isoladamente, não satisfaz esse gatilho.
- **CON-002**: Antes de editar, executar preflight do worktree, ler a cadeia `AGENTS.md` e `state/PROJECT_STATE.md` quando existirem, inspecionar mudanças do trabalho anterior e estabelecer uma nova linha de base de testes.
- **CON-003**: Não decidir ou alterar provedor, modelo, endpoint, custo, política de gratuidade, roteamento, retry de transporte, fallback, LLM-002 ou LLM-003.
- **CON-004**: Não implementar bandeja de dados, redesign visual, nova tecnologia de persistência, sistema amplo de autoria de conteúdo ou reescrita oportunista de regras/lore.
- **CON-005**: Não adicionar dependências. Usar Pydantic, Python e serviços internos já presentes.
- **PAT-001**: Concentrar a transformação de fatos canônicos em projeções H6 em um serviço pequeno e determinístico `api/narrative_projection_service.py`; não aumentar o orquestrador com regras de conteúdo dispersas.
- **PAT-002**: Concentrar validação formal da narrativa em `api/narrative_validation_service.py`; o serviço não chama LLM, não persiste e produz resultado tipado ou erro normalizado.
- **PAT-003**: Modelos de projeção pertencem a `api/turn_models.py`, devem ser Pydantic imutáveis e devem validar identidade, visibilidade e referência de fonte na fronteira.

## 2. Implementation Steps

### Implementation Phase 0

- GOAL-000: Iniciar a atividade sem colidir com a tarefa predecessor nem incorporar mudanças desconhecidas por arrasto.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Confirmar que o usuário aceitou integralmente a tarefa corrente em execução real; se não aceitou, manter este plano em `Planned` e não editar código. | [ ] | |
| TASK-002 | Ler a cadeia `AGENTS.md`, `state/PROJECT_STATE.md` quando existir, `plan/architecture-llm-memory-turns-1.md` e o diff completo do worktree; registrar somente bloqueios reais e preservar mudanças existentes. Depende de TASK-001. | [ ] | |
| TASK-003 | Executar a suíte focada e a bateria disponível do predecessor para estabelecer a linha de base. Falhas preexistentes devem ser separadas de regressões deste plano. Depende de TASK-002. | [ ] | |

### Implementation Phase 1

- GOAL-001: Definir contratos imutáveis para fatos narráveis e projeção H6 sem alterar a autoridade canônica existente.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | Acrescentar `NarratableFact`, `NarrativeProjection` e tipos auxiliares em `api/turn_models.py`, com schema/versionamento, fonte obrigatória, visibilidade e validação de IDs. Depende de GOAL-000. | [ ] | |
| TASK-005 | Criar `api/narrative_projection_service.py` com transformação pura de `CanonicalFact`, evento, estado selecionado e conteúdo versionado em projeções seguras para H6. Nenhuma função desse serviço pode chamar LLM ou persistência. Depende de TASK-004. | [ ] | |
| TASK-006 | Criar `tests/test_narrative_projection_service.py` cobrindo imutabilidade, fontes obrigatórias, visibilidade, deduplicação, ordenação determinística e recusa de fatos sem origem. Depende de TASK-004 e TASK-005. | [ ] | |

### Implementation Phase 2

- GOAL-002: Produzir desfechos narráveis específicos para investigação sem inventar conteúdo do mundo.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-007 | Estender `DeterministicTurnInputs` ou criar `CanonicalOutcomeInputs` em `api/turn_models.py` para receber descobertas e consequências por ID e referência de fonte. Manter compatibilidade com chamadas que ainda não fornecem esses campos. Depende de GOAL-001. | [ ] | |
| TASK-008 | No serviço determinístico apropriado, mapear sucesso de investigação para a descoberta fornecida e falha sem consequência para `nenhuma conclusão segura`, preservando o resultado mecânico bruto em fato separado. Não criar catálogo amplo de cenas neste plano. Depende de TASK-007. | [ ] | |
| TASK-009 | Cobrir `Investigar o galpão abandonado` com uma descoberta fonte de fixture, como `warehouse.hatch_marks`, verificando que somente sucesso a revela; cobrir também ausência de descoberta e falha. Depende de TASK-008. | [ ] | |

### Implementation Phase 3

- GOAL-003: Fechar as fronteiras de H0 e H4 para que contexto consultivo não se transforme em fato canônico.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-010 | Evoluir o payload H0 em `api/h0_controller_service.py` para `tone_tags` e `scene_fact_ids`; aceitar `scene_notes` antigo somente na leitura de compatibilidade e descartá-lo da projeção factual. Depende de GOAL-001. | [ ] | |
| TASK-011 | Atualizar a instrução H0 correspondente em `skills/` para produzir apenas tags de tom e IDs de fatos já fornecidos, sem criar descrição concreta. Depende de TASK-010. | [ ] | |
| TASK-012 | Alterar `api/lore_service.py` e `api/h4_lore_expert_service.py` para selecionar lore por ação e uso explícito; omitir `unarmed` em investigação e manter texto livre H4 fora das seções canônicas. Depende de GOAL-001. | [ ] | |
| TASK-013 | Adicionar testes que injetem em H0/H4 objetos ou pistas inexistentes e comprovem que eles não aparecem em `FATOS NARRÁVEIS CANÔNICOS` nem são persistidos. Depende de TASK-010 a TASK-012. | [ ] | |

### Implementation Phase 4

- GOAL-004: Montar um prompt H6 estruturado, mínimo, rastreável e sem omissão dos fatos canônicos relevantes.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-014 | Corrigir `api/context_service.py` e a montagem em `api/orchestrator_service.py` para projetar estado relevante exatamente uma vez, removendo a suposição incorreta de que todo `ContextLayer.CANONICAL_FACTS` já foi absorvido pelo log do sistema. Depende de GOAL-001. | [ ] | |
| TASK-015 | Substituir a montagem textual implícita por `NarrativeProjection` com as seis seções exigidas, mantendo filtro de visibilidade antes da seleção e preservando orçamento de contexto. Depende de TASK-005 e TASK-014. | [ ] | |
| TASK-016 | Atualizar `skills/H6_vtm_narrator.md` para consumir exclusivamente a projeção, distinguir fato de orientação e reiterar os limites de não invenção e não reversão mecânica. Depende de TASK-015. | [ ] | |
| TASK-017 | Adicionar um teste de captura do request H6 que prove ausência da ficha completa, `normal_rolls`, `hunger_rolls`, faces, dificuldade e JSON bruto, e presença exata dos fatos narráveis e fontes esperados sem duplicação. Depende de TASK-015 e TASK-016. | [ ] | |

### Implementation Phase 5

- GOAL-005: Validar a narrativa final antes da confirmação transacional e falhar de modo conservador.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-018 | Criar `api/narrative_validation_service.py` com `NarrativeTextPolicy`, contagem Unicode determinística e erros tipados para vazio, quantidade de palavras, múltiplas frases, múltiplos parágrafos, título/lista, rótulos internos e mecânica proibida. Depende de GOAL-001. | [ ] | |
| TASK-019 | Integrar a validação em `api/turn_execution_service.py` ou no ponto imediatamente anterior à criação de `NarrativeRecord`; texto inválido deve finalizar a tentativa como falha e impedir o commit canônico. Depende de TASK-018. | [ ] | |
| TASK-020 | Preservar o protocolo de streaming: deltas continuam provisórios, há um único terminal tipado e nenhuma saída depois dele. Não acrescentar retry automático nem trocar o alvo. Depende de TASK-019. | [ ] | |
| TASK-021 | Criar `tests/test_narrative_validation_service.py` com fronteiras de 24, 25, 35 e 36 palavras, uma e duas frases, título/lista, newline, rótulos de prompt e detalhes mecânicos; incluir português com acentos, hífen e apóstrofo. Depende de TASK-018. | [ ] | |
| TASK-022 | Estender testes transacionais para provar que narrativa inválida, timeout, cancelamento e terminal ausente preservam estado/eventos/memória anteriores e registram somente a tentativa segura já prevista. Depende de TASK-019 e TASK-020. | [ ] | |

### Implementation Phase 6

- GOAL-006: Preservar dados existentes e validar o fluxo completo offline.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-023 | Acrescentar leitura compatível/versionada para eventos sem projeções novas. Não executar reescrita destrutiva; novos campos passam a existir nos turnos criados após esta mudança. Depende de GOAL-004 e GOAL-005. | [ ] | |
| TASK-024 | Estender `tests/test_turn_pipeline_integration.py`, `tests/test_turn_execution_service.py`, `tests/test_llm_service_integration.py` e `tests/test_websocket_transactional.py` apenas onde esses arquivos existirem, usando fake gateway e nenhuma rede. Depende de TASK-023. | [ ] | |
| TASK-025 | Executar os testes focados após cada fase e, ao final, toda a suíte backend e frontend disponível; inspecionar diff, `git diff --check`, arquivos não rastreados e ausência de `.env`/segredos. Depende de TASK-024. | [ ] | |
| TASK-026 | Realizar aceitação manual local com o caso `Investigar o galpão abandonado`, capturando somente metadados seguros: decisão determinística, IDs das fontes projetadas, terminal e efeito de commit. Não registrar o prompt completo nem dados privados. Depende de TASK-025. | [ ] | |
| TASK-027 | Atualizar este plano para `Completed` somente após todos os critérios mensuráveis passarem; registrar limitações reais sem promover avaliações semânticas futuras a requisito cumprido. Depende de TASK-026. | [ ] | |

## 3. Alternatives

- **ALT-001 — Enviar a ficha completa para H6**: rejeitada. Facilita o prompt, mas aumenta exposição, ruído, custo de contexto e oportunidade de o modelo reinterpretar regras. A projeção mínima preserva a autoridade do domínio.
- **ALT-002 — Resolver apenas com um modelo maior ou um prompt mais enfático**: rejeitada. O problema principal é ausência de fatos narráveis com fonte, não apenas capacidade linguística.
- **ALT-003 — Usar um segundo LLM como juiz de grounding**: rejeitada neste escopo. Acrescenta latência, custo e outra superfície de falha e não substitui proveniência canônica.
- **ALT-004 — Aceitar `scene_notes` de H0 como fatos de cena**: rejeitada. H0 não possui autoridade para criar objetos, pistas, ameaças ou acontecimentos.
- **ALT-005 — Gerar toda a prosa determinística no orquestrador**: rejeitada. Espalharia regras de conteúdo em um coordenador e degradaria modularidade; o serviço de projeção deve ser pequeno e testável.
- **ALT-006 — Repetir automaticamente H6 para reparar formato inválido**: rejeitada na primeira versão. A política conservadora é falhar sem commit, no mesmo alvo e sem fallback. Uma estratégia de reparo pode ser deliberada depois com dados de falha reais.
- **ALT-007 — Criar agora um sistema geral de autoria de pistas e cenas**: rejeitada por expansão de escopo. O primeiro incremento aceita entradas canônicas tipadas do módulo atual e fixtures; uma ferramenta de autoria é atividade própria.

## 4. Dependencies

- Aceitação final explícita da execução real coberta por `plan/architecture-llm-memory-turns-1.md`; o status documental isolado não basta.
- Modelos existentes em `api/turn_models.py`: `CanonicalFact`, `CanonicalEvent`, `TurnDraft` e `NarrativeRecord`.
- Orquestração e persistência transacional existentes em `api/orchestrator_service.py`, `api/turn_execution_service.py` e serviços relacionados.
- Camadas e seleção existentes em `api/context_service.py`.
- Fronteira LLM-001 e fake gateway offline existentes em `api/llm/` e `tests/llm/`.
- Contratos atuais de H0, H4 e H6 e respectivas skills locais.
- Nenhuma dependência externa, serviço online ou credencial é necessária.

Ordem crítica: GOAL-000 -> GOAL-001 -> GOAL-002/GOAL-003 -> GOAL-004 -> GOAL-005 -> GOAL-006. GOAL-002 e GOAL-003 podem avançar em paralelo somente depois que os contratos de GOAL-001 estiverem estáveis.

## 5. Files

Arquivos previstos, sujeitos à reinspeção de preflight:

- `api/turn_models.py`: novos modelos imutáveis de fato narrável, projeção e entrada de resultado canônico.
- `api/narrative_projection_service.py`: novo serviço puro de projeção e deduplicação.
- `api/narrative_validation_service.py`: nova política e validação formal da saída H6.
- `api/orchestrator_service.py`: consumir a projeção tipada e remover montagem factual implícita.
- `api/turn_execution_service.py`: validar antes de `NarrativeRecord` e do commit.
- `api/context_service.py`: corrigir projeção de fatos canônicos/estado e deduplicação.
- `api/h0_controller_service.py`: migrar de notas factuais livres para tags e referências.
- `api/h4_lore_expert_service.py`: manter saída consultiva e limitar projeções factuais.
- `api/lore_service.py`: selecionar lore de arma somente quando relevante.
- `api/rules_service.py`: somente se necessário para transportar o resultado canônico tipado; não reescrever regras.
- `skills/H6_vtm_narrator.md`: contrato de prompt estruturado e limites.
- Skill H0 existente sob `skills/`: atualizar somente o arquivo identificado no preflight como fonte ativa do contrato H0.
- `tests/test_narrative_projection_service.py`: novo.
- `tests/test_narrative_validation_service.py`: novo.
- `tests/test_turn_pipeline_integration.py`: regressão ponta a ponta do galpão.
- `tests/test_turn_execution_service.py`: atomicidade diante de narrativa inválida.
- `tests/test_llm_service_integration.py`: captura do pacote H6 e fronteiras H0/H4.
- `tests/test_websocket_transactional.py`: terminal e deltas provisórios.
- `README.md` ou documentação equivalente: atualizar somente se a interface operacional observável mudar.
- `plan/architecture-narratable-canonical-outcomes-2.md`: acompanhamento desta atividade.

`api/parser_service.py` e H1 não devem mudar salvo evidência concreta de que o transporte do novo input exige uma alteração compatível. O mapeamento determinístico Wits + Investigation continua fora da autoridade de H1.

## 6. Testing

Critérios de aceite mensuráveis:

1. Com a entrada literal `Investigar o galpão abandonado`, uma saída H1 maliciosa ou equivocada não substitui o mapeamento determinístico para Wits + Investigation nem a necessidade de rolagem.
2. Dada uma descoberta canônica `warehouse.hatch_marks`, o pacote H6 de sucesso contém seu conteúdo projetado e `source_ref`; o pacote de falha não contém essa descoberta.
3. Sem descoberta canônica fornecida, o fluxo não fabrica pista. Ele usa apenas o desfecho genérico explicitamente modelado ou rejeita a preparação por insuficiência de resultado narrável.
4. O request H6 não contém ficha completa, `normal_rolls`, `hunger_rolls`, faces, JSON bruto ou dificuldade. Esses dados continuam presentes no fato/evento mecânico persistido quando aplicável.
5. Um fato de estado relevante selecionado aparece exatamente uma vez na projeção. Um fato irrelevante ou sem visibilidade não aparece.
6. Um `scene_notes` legado que invente sangue, ferrugem, inimigo ou objeto não entra nas seções factuais, não vira evento e não gera memória.
7. Uma investigação sem arma explícita não inclui lore `unarmed`, punhos, chutes ou socos no pacote H4/H6.
8. Saídas H6 com 24 ou 36 palavras, duas frases, lista, título, múltiplos parágrafos, rótulo interno ou detalhe mecânico proibido falham e não são confirmadas.
9. Saídas H6 com 25 e 35 palavras, uma frase, um parágrafo e conteúdo compatível com a projeção passam nos testes de fronteira.
10. Falha formal, timeout, cancelamento e terminal ausente preservam a revisão anterior de estado, evento, narrativa e memória e não produzem delta depois do terminal.
11. Memória episódica deriva somente do evento e da narrativa válidos e confirmados e mantém referências/visibilidade.
12. Toda a suíte usa fake gateway; nenhuma chamada de teste alcança um modelo local ou API online.
13. A suíte completa disponível mantém a linha de base do predecessor, `git diff --check` passa e nenhum segredo ou `.env` aparece no diff.

Além de testes unitários e de integração, a aceitação manual deve verificar na interface que o narrador responde à intenção de investigar com uma consequência coerente com os fatos fornecidos e nunca com a mensagem genérica de que não entendeu a intenção quando o parser determinístico reconheceu a ação.

## 7. Risks & Assumptions

- **RISK-001**: O produto ainda pode não possuir fonte de conteúdo suficiente para uma pista específica em cada cena. Mitigação: aceitar `CanonicalOutcomeInputs` tipado e explícito neste incremento; não mascarar ausência com invenção do LLM.
- **RISK-002**: O jogador pode ver deltas provisórios que depois falham na validação. Mitigação: manter indicação de geração provisória e terminal de falha; uma futura estratégia de buffer integral exige decisão própria de UX/latência.
- **RISK-003**: A política estrita de 25–35 palavras pode elevar falhas de modelos locais. Mitigação: medir falhas e reportá-las; não afrouxar silenciosamente nem trocar de modelo.
- **RISK-004**: Contagem de frases em português possui abreviações e pontuação ambígua. Mitigação: política determinística documentada, fixtures com acentos/hífens e regras explícitas para abreviações aceitas.
- **RISK-005**: Grounding semântico completo não pode ser garantido por regex. Mitigação: limitar fatos de entrada, separar origem/visibilidade, testar casos adversariais e tratar uma avaliação semântica mais ampla como CAP-001 futuro.
- **RISK-006**: Corrigir a projeção de estado pode aumentar o contexto e duplicar informação. Mitigação: deduplicação por ID/fonte antes do orçamento e teste de ocorrência única.
- **RISK-007**: A migração de `scene_notes` pode afetar fixtures ou consumidores atuais. Mitigação: leitura compatível e descarte somente da autoridade factual, com testes de payload legado.
- **ASSUMPTION-001**: A implementação corrente mantém os serviços e modelos identificados no levantamento de 2026-08-25. O preflight deve atualizar caminhos concretos se o trabalho predecessor os tiver movido, sem mudar os requisitos.
- **ASSUMPTION-002**: O fluxo transacional e a fronteira LLM-001 já estarão aceitos e estáveis quando esta atividade começar.
- **ASSUMPTION-003**: Falhar sem retry automático é a política mínima e reversível coerente com LLM-001; qualquer reparo posterior permanece no mesmo alvo e requer atividade separada.

## 8. Related Specifications / Further Reading

- `plan/architecture-llm-memory-turns-1.md`: predecessor obrigatório, fronteira LLM-001 e transação de turno/evento/memória.
- `spec/design-visible-v5-dice-tray.md`: proposta aprovada e adiada para interação visível de rolagem; não faz parte desta atividade.
- `spec/spec-design-accessible-interface-redesign.md`: proposta aprovada e adiada para contraste/layout/tipografia; não faz parte desta atividade.
- `spec/spec-architecture-narrative-engine-admission-policy.md`: proposta aprovada e adiada para recomendação de motores online e advertências sobre modelos locais; não faz parte desta atividade.
- `skills/H6_vtm_narrator.md`: contrato narrativo H6 atualmente ativo, a ser refinado nesta atividade.

### Definition of Done

A atividade termina somente quando o caso do galpão prova, offline e depois em aceitação manual local, que: a mecânica continua determinística; o modelo recebe fatos narráveis canônicos e relevantes com fonte; texto livre de H0/H4 não cria realidade; saída H6 inválida não é confirmada; narrativa válida, evento e memória permanecem transacionais; dados existentes continuam legíveis; e não houve alteração de provedor, custo, fallback, interface ou tecnologia de persistência.
