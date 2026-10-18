---
goal: Planejar o resolvedor determinístico de cenas antes da verbalização narrativa
version: 1.0
date_created: 2026-09-14
last_updated: 2026-09-16
owner: Produto Agente Storyteller
status: 'Pilot activation active for catalog-backed Mara dialogue'
tags: [architecture, scene, resolution, npc, narrative, persistence]
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

Este plano promove a proposta de resolvedor determinístico de cenas para uma
arquitetura revisável. A decisão humana de 14/09/2026 aprovou o planejamento, não
a implementação nem escolhas de balanceamento. O objetivo é fazer cada turno
ficcional significativo receber um resultado estruturado antes da verbalização
por H6, preservando agência, fatos canônicos, resultado mecânico e atomicidade.

O recorte inicial produz um único beat de cena. Ele não implementa planejamento
de campanha, autonomia global de NPCs, criação de ficha, bandeja de dados, seleção
de modelo ou uma segunda rolagem. A escolha Qwen/GPT-OSS permanece aberta.

## 1. Requirements & Constraints

- **REQ-001**: A ordem do turno deve ser ação declarada -> resolução mecânica já existente, quando aplicável -> resolução de beat -> verbalização H6 -> admissão -> commit transacional.
- **REQ-002**: O resolvedor deve consumir somente dados estruturados confiáveis: ação declarada, `SceneState`, fatos canônicos relevantes, `ResolutionResult` opcional, ficha mínima dos NPCs presentes e relação persistida.
- **REQ-003**: O resultado do resolvedor deve ser imutável, versionado, serializável e identificável por `session_id`, `operation_id`, `turn_id`, revisão-base e versão de política.
- **REQ-004**: O resultado deve distinguir no mínimo: resultado da intenção, mudança observável, ação ou postura de NPC, pendências abertas/resolvidas, transição permitida e restrições que H6 não pode contradizer.
- **REQ-005**: Um turno ficcional significativo deve conter ao menos uma resposta pertinente, mudança observável, consequência, complicação ou alteração explícita de pendência. Texto meramente recapitulativo não satisfaz o contrato.
- **REQ-006**: O resolvedor não pode criar fala, ação, pensamento, emoção, deslocamento ou decisão para o personagem do jogador além do que ele declarou.
- **REQ-007**: Resultado mecânico existente é vinculante. O resolvedor não recalcula sucessos, dificuldade, margem, Fome, crítico, falha bestial, dano, custo ou recurso.
- **REQ-008**: O primeiro incremento não deve gerar aleatoriedade adicional. Quando houver rolagem mecânica, deve reutilizar exatamente o recibo já produzido; quando não houver, deve escolher deterministicamente entre consequências elegíveis por regras e desempate estável.
- **REQ-009**: Uma falha de H6, schema, admissão, transporte, cancelamento ou persistência não pode produzir nova rolagem, reaplicar consequência nem confirmar beat parcial.
- **REQ-010**: A proposta de H6 deve verbalizar o beat vinculante. Novidade cosmética local continua permitida sob `scene_director_admission.v1`, mas não pode alterar resultado, causalidade, elenco, transição, pendência ou restrição do beat.
- **REQ-011**: A admissão deve verificar correspondência entre proposta narrativa e beat antes do commit. Uma narrativa que omite a mudança obrigatória, contradiz o resultado ou acrescenta transição protegida deve ser recusada integralmente.
- **REQ-012**: Beat, fatos, eventos, narrativa, memória, relação e snapshot devem ser confirmados pela transação existente de `commit_turn`; o beat não se torna canônico antes desse commit.
- **REQ-013**: Retry idempotente da mesma operação deve recuperar o resultado terminal persistido sem resolver, rolar ou chamar H6 novamente.
- **REQ-014**: A ficha mínima de NPC do resolvedor deve ficar separada da projeção de jogador e da futura experiência de criação da ficha. Ela deve representar apenas limites, capacidades, objetivos locais e estado necessários ao beat.
- **REQ-015**: Segredos e intenções internas devem conservar visibilidade `storyteller`; apenas efeitos observáveis podem entrar automaticamente na narrativa e na projeção pública.
- **REQ-016**: O recorte deve manter a direção improvisacional aprovada: regras limitam e vinculam o beat, enquanto H6 ainda escolhe linguagem, ritmo, detalhe sensorial e fala compatível de NPC.
- **REQ-017**: A implementação futura deve começar atrás de uma composição explícita e desativada por padrão até possuir testes de paridade, integração e aceitação de produto.
- **SEC-001**: Nenhum artefato do resolvedor pode registrar prompt, chave, credencial, segredo de ambiente ou texto confidencial em diagnósticos públicos.
- **CON-001**: Não alterar `calculate_resolution` nem introduzir outra fonte de dados aleatórios no primeiro incremento.
- **CON-002**: Não escolher escala 1-5, pesos, temperatura de cena, clamp, tabela de posturas ou balanceamento nesta versão do plano.
- **CON-003**: Não modificar a experiência de criação da ficha do jogador; perfis sintéticos/predefinidos devem cobrir os testes iniciais.
- **CON-004**: Não usar o resolvedor para decidir roteiro macro, final da campanha ou ações fora da cena atual.
- **PAT-001**: Usar modelos Pydantic imutáveis, funções puras para elegibilidade/seleção e IDs estáveis derivados da operação, seguindo `api/turn_models.py` e `api/scene_director_service.py`.
- **PAT-002**: Guardar proveniência das regras e fatos de entrada, sem copiar prosa gerada para diagnósticos estruturados.

### Decisões arquiteturais a confirmar antes da implementação

| ID | Pergunta | Recomendação para o primeiro incremento | Efeito |
|---|---|---|---|
| DEC-RES-001 | Qual parte da direção passa a ser vinculante? | Resultado da intenção, mudança observável, movimento de NPC, transição e pendências. H6 conserva expressão e fala compatível. | Define a fronteira resolvedor/H6. |
| DEC-RES-002 | Como selecionar entre consequências igualmente válidas? | Prioridade determinística e desempate estável; nenhuma rolagem adicional. | Evita duplicar acaso antes de balanceamento. |
| DEC-RES-003 | Qual ficha mínima de NPC entra no MVP? | ID, capacidades/limites, objetivo local, postura atual e referência à relação; segredos em camada separada. | Permite resolver sem antecipar ficha completa. |
| DEC-RES-004 | Como representar pressão? | Estados nomeados sem escala numérica no MVP; persistir somente mudança causal concreta. | Adia pesos e escala 1-5. |
| DEC-RES-005 | Quais turnos exigem beat? | Ações ficcionais, diálogo e espera; comandos, consultas puras, esclarecimento e falha técnica ficam fora. | Delimita obrigação de avanço. |

As cinco recomendações foram aprovadas pelo usuário em 14/09/2026 como arquitetura
do primeiro incremento. Escalas numéricas, pesos, catálogo de consequências e
ativação de produto continuam fora dessa aprovação.

## 2. Implementation Steps

### Implementation Phase 0

- GOAL-001: Fechar a fronteira de autoridade e o contrato mínimo antes de código de produção.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Confirmar DEC-RES-001 a DEC-RES-005 e registrar as respostas neste plano e em `PROMPT_RETOMADA_2026-09-06.md`. | [x] | 2026-09-14 |
| TASK-002 | Especificar `SceneBeatResolution` e seus invariantes em `spec/spec-deterministic-scene-resolution.md`, sem implementar serviço. Depende de TASK-001. | [x] | 2026-09-15 |
| TASK-003 | Criar exemplos autorados de diálogo, espera, ação com sucesso, ação com falha, transição proibida e NPC limitado; cada exemplo deve conter entradas confiáveis, beat esperado e contraprovas. Depende de TASK-002. | [x] | 2026-09-15 |

Critério de conclusão: especificação aprovada, exemplos sem decisões implícitas e nenhuma alteração de runtime.

### Implementation Phase 1

- GOAL-002: Implementar o contrato puro e a seleção determinística de beat sem integrar H6.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-004 | Criar `api/scene_resolution_service.py` com `SceneResolutionInput`, `SceneNpcProfile`, `SceneBeatResolution`, enums fechados e validações REQ-002 a REQ-008. Depende de GOAL-001. | [x] | 2026-09-15 |
| TASK-005 | Implementar funções puras de elegibilidade, prioridade e desempate estável; recusar ausência de consequência elegível em vez de inventar fallback narrativo. Depende de TASK-004. | [x] | 2026-09-15 |
| TASK-006 | Criar adaptadores de leitura para `SceneState`, `ResolutionResult`, `NpcModel` e `NpcRelationship`, sem alterar os modelos persistidos existentes. Depende de TASK-004. | [x] | 2026-09-15 |
| TASK-007 | Criar `tests/test_scene_resolution_service.py` cobrindo os exemplos autorados, determinismo, agência, limites de NPC, visibilidade, causalidade e ausência de RNG adicional. Depende de TASK-004 a TASK-006. | [x] | 2026-09-15 |

Critério de conclusão: chamadas idênticas produzem bytes estruturados idênticos; nenhum teste usa rede, LLM ou estado global aleatório.

### Implementation Phase 2

- GOAL-003: Integrar o beat ao rascunho e ao contrato de H6 sem ativá-lo no caminho padrão.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-008 | Acrescentar o beat como fato/registro derivado no `TurnDraft`, preservando o recibo mecânico original e a revisão-base. A ponte opt-in fica em `api/scene_resolution_integration.py`, sem mudar o caminho padrão. Depende de GOAL-002. | [x] | 2026-09-15 |
| TASK-009 | Acrescentar ao pacote H6 uma seção vinculante de beat com resultado, mudanças obrigatórias, proibições e visibilidade; não expor intenção secreta ao texto público. A instrução viaja no pacote para preservar o teto de 400 palavras do SYSTEM. Depende de TASK-008. | [x] | 2026-09-15 |
| TASK-010 | Estender a admissão em `api/scene_director_service.py` para verificar correspondência da `SceneContinuationProposal` com o beat e emitir códigos seguros específicos. Depende de TASK-009. | [x] | 2026-09-15 |
| TASK-011 | Cobrir composição desativada por padrão, compatibilidade do fluxo anterior e contradições H6/beat em testes focais e nas suítes existentes de direção, pipeline, executor e WebSocket. Depende de TASK-008 a TASK-010. | [x] | 2026-09-15 |

Critério de conclusão: suíte offline prova o novo caminho e a paridade do caminho anterior; nenhuma configuração de produto é alterada.

### Implementation Phase 3

- GOAL-004: Tornar o beat parte do commit atômico e da recuperação idempotente.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Persistir beat admitido, proveniência de regras e referências de entrada na mesma transação de `commit_turn`; nenhuma tabela separada é obrigatória se o modelo de fatos/eventos preservar consulta e integridade. O fato e o recibo usam a transação existente, sem alteração de schema. Arquivos: `api/turn_execution_service.py`. Depende de GOAL-003. | [x] | 2026-09-15 |
| TASK-013 | Fazer replay/rehidratação retornar o mesmo beat e recibo sem nova resolução; cobrir pending/completed/failed e cancelamento antes/depois de H6. O caminho terminal reidrata o recibo persistido; os estados sem commit preservam a ausência de recibo canônico. Depende de TASK-012. | [x] | 2026-09-15 |
| TASK-014 | Derivar `SceneState`, memória e relações apenas do beat admitido e da narrativa validada, sem duplicar efeito ou elevar visibilidade. A admissão beat/proposta ocorre antes das projeções existentes e o beat permanece `storyteller`. Depende de TASK-012. | [x] | 2026-09-15 |
| TASK-015 | Adicionar testes SQLite de uma única confirmação, CAS, rollback, reconexão e hash estável da resolução. Os novos testes de recibo/replay e rollback compõem as coberturas transacionais e WebSocket preexistentes. Arquivos: `tests/test_turn_execution_service.py`, `tests/test_websocket_transactional.py`. Depende de TASK-012 a TASK-014. | [x] | 2026-09-15 |

Critério de conclusão: falhas em qualquer ponto preservam snapshot e recibo anteriores; retry terminal não executa resolver, dado ou H6.

### Implementation Phase 4

- GOAL-005: Avaliar progressão narrativa com corpus congelado antes de qualquer ativação de produto.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-016 | Criar avaliação offline que compare beat esperado, proposta H6 e estado admitido, com gates de causalidade, agência, atribuição, progressão e não contradição. Depende de GOAL-004. | [x] | 2026-09-15 |
| TASK-017 | Executar primeiro com adaptador falso e textos autorados; preservar rubrica e artefatos antes de eventual inferência. O corpus congelado teve 4/4 casos aprovados e zero chamadas externas. Depende de TASK-016. | [x] | 2026-09-15 |
| TASK-018 | Preparar protocolo prospectivo de modelo somente se a avaliação offline revelar uma pergunta discriminante nova. A condição não ocorreu; nenhuma nova inferência ou protocolo de provedor foi aberto. Qualquer chamada real permanece separada e não qualifica CAP-001 automaticamente. Depende de TASK-017. | [x] | 2026-09-15 |
| TASK-019 | Submeter ativação do resolvedor no fluxo padrão à aceitação humana distinta, com resultados técnicos e narrativos separados. Aceite explícito recebido em 15/09/2026. Depende de TASK-016 a TASK-018. | [x] | 2026-09-15 |

Critério de conclusão: evidência revisável demonstra que beats vinculantes avançam as cenas sem decidir pelo jogador; ativação continua uma decisão separada.

### Dependência descoberta na composição padrão

O aceite de TASK-019 autoriza a ativação, mas o runtime ainda não contém a fonte
confiável de `SceneConsequenceOption` exigida por REQ-002 e pela especificação.
As opções atuais existem apenas em fixtures autoradas. Ativar a ponte sem essa
fonte faria turnos reais falharem com `scene_no_eligible_consequence`; fabricar
texto genérico no orquestrador transferiria uma nova decisão de autoria para um
detalhe de implementação. A composição aguarda decisão sobre catálogo por
cena/campanha, templates globais ou uma combinação explicitamente ordenada.

### Implementation Phase 5

- GOAL-006: Preservar a autoria do narrador por meio de um mapa mínimo de palavras-chave e ativação gradual somente onde houver cobertura autorada.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-020 | Separar efeitos semânticos vinculantes de orientações livres de personalidade, reação e objetivo; manter aleatoriedade interna fora do incremento. | [x] | 2026-09-15 |
| TASK-021 | Acrescentar `effect_keys`, `guidance_keys` e `realized_effects` ao contrato, preservando validação literal para beats legados. | [x] | 2026-09-15 |
| TASK-022 | Criar catálogo mínimo tipado de Mara com núcleo, objetivos, capacidades, limites, tópicos e espectros de reação, sem fala ou cena pronta. | [x] | 2026-09-15 |
| TASK-023 | Ativar a composição padrão somente para diálogos explicitamente dirigidos a Mara em Arquivo/Galeria e tópicos cobertos; preservar o fluxo anterior fora do mapa. | [x] | 2026-09-15 |
| TASK-024 | Impedir que perguntas dirigidas a um NPC presente sejam desviadas para H4; rotear fala explícita à cena antes de H0, preservando consultas gerais de lore. | [x] | 2026-09-16 |
| TASK-025 | Reobservar ao vivo o tópico `mara.founder` após reiniciar o servidor e conferir separadamente rota, beat, agência e limite de identidade. | [x] | 2026-09-16 |

Critério de conclusão: H6 declara o efeito semântico realizado, conserva liberdade
de prosa e recebe orientações de personalidade sem transformá-las em texto fixo;
cenas não mapeadas não recebem consequência genérica fabricada.

A observação de 16/09 encontrou uma fronteira de rota: `Mara, quem é a fundadora
deste lugar?` foi confirmada por H4 sem beat ou fatos. TASK-024 corrigiu a rota
prospectivamente; o turno sintético histórico permanece intacto. Após reinício,
TASK-025 confirmou ao vivo `H6.direct_scene`, `mara.founder` e
`mara.responds.without_founder_identity`. Mara reteve nome e rosto, ofereceu uma
pista acionável e preservou a próxima decisão do jogador. O resultado fecha o
incremento Mara; não aprova modelo padrão, campanha, runtime ou CAP-001.

## 3. Alternatives

- **ALT-001**: Apenas reforçar o SYSTEM de H6. Rejeitada como direção principal porque os comparativos mostraram estagnação dependente de cena/modelo mesmo com instrução explícita de avanço.
- **ALT-002**: Deixar H6 gerar beat e prosa juntos, usando somente validação posterior. Mantém no modelo a escolha que o resolvedor pretende tornar causal e reproduzível.
- **ALT-003**: Criar um segundo LLM como diretor. Amplia custo, latência e superfície de falha sem oferecer determinismo.
- **ALT-004**: Adicionar rolagem de direção para cada turno. Adiada até regras, distribuição e balanceamento serem decididos; conflita com o recorte de uma única rolagem mecânica persistida.
- **ALT-005**: Implementar objetivos globais e agenda autônoma de todos os NPCs. Adiada para integração com campanha híbrida; excede um beat local e depende de CAMP-09 a CAMP-11.

## 4. Dependencies

- **DEP-001**: `spec/spec-improvisational-scene-direction.md`, cuja direção ficcional limitada permanece válida.
- **DEP-002**: `api/turn_models.py`, `api/turn_execution_service.py` e `api/persistence.py`, que já oferecem rascunho, fatos/eventos e commit atômico.
- **DEP-003**: `api/rules_service.py`, autoridade exclusiva da resolução mecânica.
- **DEP-004**: `api/scene_service.py` e `api/scene_director_service.py`, projeção e admissão existentes.
- **DEP-005**: `api/npc_service.py` e `api/relationship_service.py`; o catálogo atual é insuficiente para objetivo local/limites e precisa de adaptador ou extensão aprovada.
- **DEP-006**: DEC-RES-001 a DEC-RES-005, bloqueio humano de arquitetura antes de implementação.

## 5. Files

- **FILE-001**: `spec/spec-deterministic-scene-resolution.md` — novo contrato autoritativo após decisões.
- **FILE-002**: `api/scene_resolution_service.py` — novo domínio puro do resolvedor.
- **FILE-003**: `api/turn_models.py` — referência estruturada ao beat no rascunho.
- **FILE-004**: `api/orchestrator_service.py` — composição antes de H6 e contexto vinculante.
- **FILE-005**: `api/scene_director_service.py` — admissão da correspondência beat/proposta.
- **FILE-006**: `api/turn_execution_service.py` — commit, replay e recibo do beat.
- **FILE-007**: `api/persistence.py` — somente se fatos/contexto existentes não preservarem o contrato consultável.
- **FILE-008**: `api/npc_service.py` e `api/relationship_service.py` — adaptadores mínimos; nenhuma ficha visível.
- **FILE-009**: `skills/H6_vtm_narrator.md` — instrução para verbalizar o beat.
- **FILE-010**: testes focais e integrados listados nas fases.

## 6. Testing

- **TEST-001**: Mesma entrada e revisão produzem o mesmo beat e hash em execuções repetidas.
- **TEST-002**: Sucesso, falha, crítico e falha bestial preservam integralmente `ResolutionResult`.
- **TEST-003**: Diálogo, espera e ação sem rolagem produzem resposta ou mudança concreta sem RNG.
- **TEST-004**: Capacidade, limite, objetivo local e relação de NPC alteram somente consequências elegíveis previstas.
- **TEST-005**: Ação, emoção, pensamento ou decisão não declarada do jogador é impossível no beat e recusada na prosa.
- **TEST-006**: Segredo influencia escolha interna sem aparecer em saída pública.
- **TEST-007**: Transição e mudança de elenco sem autorização estruturada são recusadas.
- **TEST-008**: Prosa que omite ou contradiz a consequência vinculante falha sem commit parcial.
- **TEST-009**: Timeout, cancelamento, schema inválido e falha SQLite não reaplicam resolução ou efeitos.
- **TEST-010**: Retry de operação concluída retorna beat, recibo e narrativa persistidos sem nova execução.
- **TEST-011**: Caminho desativado mantém comportamento e contratos atuais.
- **TEST-012**: Corpus autorado mede progressão separadamente de conformidade técnica.

## 7. Risks & Assumptions

- **RISK-001**: Um catálogo de consequências rígido pode tornar cenas repetitivas; mitigar com resultados vinculantes pequenos e liberdade expressiva de H6.
- **RISK-002**: Beat detalhado demais pode transformar improvisação em roteiro; limitar o MVP a causalidade local e restrições indispensáveis.
- **RISK-003**: Beat vago demais não corrige estagnação; exigir mudança observável ou resposta pertinente verificável.
- **RISK-004**: Ficha mínima de NPC pode duplicar catálogos futuros; usar adaptador versionado e manter contrato separado da UI.
- **RISK-005**: Relação atual usa heurísticas simples e não deve ser promovida silenciosamente a psicologia completa do NPC.
- **RISK-006**: Validar correspondência semântica entre beat e prosa apenas por léxico terá falsos positivos/negativos; começar com campos estruturados e invariantes fortes, medindo o restante como qualidade.
- **ASSUMPTION-001**: O monólito modular e o commit SQLite único permanecem decisões vigentes.
- **ASSUMPTION-002**: A direção B continua sendo o caminho experimental de narrativa, sem aprovação de runtime de produto.
- **ASSUMPTION-003**: O primeiro incremento usa perfis sintéticos ou predefinidos e não depende da criação da ficha do jogador.

## 8. Related Specifications / Further Reading

- `spec/spec-improvisational-scene-direction.md`
- `spec/spec-architecture-narrative-engine-admission-policy.md`
- `plan/architecture-llm-memory-turns-1.md`
- `plan/checklist-planejamento-campanha-hibrida.md`
- `evals/narrator/reports/source-dialogue-comparison-observation-095e7efd-2026-09-13.md`
- `evals/narrator/reports/source-model-choice-status-2026-09-14.md`
