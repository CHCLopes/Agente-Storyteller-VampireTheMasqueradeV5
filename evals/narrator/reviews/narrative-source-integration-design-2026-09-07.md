---
goal: Especificar a integração optativa de fontes narrativas atribuídas aos serviços existentes
version: 1.0
date_created: 2026-09-07
status: Planned
scope: TASK-012 e TASK-013 de architecture-narrative-grounding-1
implementation_status: not_implemented
product_default_changed: false
save_migration: none
---

# Introduction

Este documento especifica o encaixe da direção B já aprovada, a partir da inspeção dos serviços reais. É um desenho de integração e de testes futuros: não altera runtime, default, saves, schemas históricos ou CAP-001. A autorização contínua permite preparar e verificar os próximos incrementos delimitados; não é necessário pedir novamente a aprovação da direção B.

O incremento proposto é uma ponte interna optativa, inicialmente exercitada com adaptador falso e SQLite temporário. Ela conserva n integral como fonte atribuída, com q separado, e mantém as transições mecânicas já produzidas pelo servidor. Não converte a fonte em CanonicalFact, resumo semântico, detalhe estabelecido ou pendência canônica. A novidade ficcional permanece identificada como texto narrado, cuja verdade geral não foi avaliada.

O piloto Estufa f97a8568 foi encerrado com uma chamada HTTP 200, um schema válido, rejeição de q, zero projeções e um turno dependente pulado. O segundo USER não foi enviado. Portanto, continuidade entre fontes não foi observada. A leitura autorada da narrativa não muda esses contadores. A observação suplementar Pátio está sendo preparada separadamente para essa lacuna; nenhum resultado dela é pressuposto aqui e ela não preenche o skip da Estufa.

As referências de código abaixo apontam para a versão inspecionada neste worktree; seus hashes constam na seção 8. “Proposto” designa trabalho ainda não implementado. A ausência de prova semântica geral no fluxo v1 é uma limitação da política anterior já documentada, não um novo defeito geral descoberto por este desenho.

## 1. Requirements & Constraints

### 1.1 Invariantes da integração

| ID | Requisito verificável |
|---|---|
| REQ-BI-001 | Manter independentes o protocolo da fonte, o binding, o assessment, o perfil narrativo e o schema 1.0 dos registros históricos. Não incrementar FrozenRecord globalmente. |
| REQ-BI-002 | A fonte é o n completo após a normalização explícita do envelope. q permanece separado. Não chamar esse texto de corpo HTTP bruto nem reconstruir n dividindo arbitrariamente NarrativeRecord.text. |
| REQ-BI-003 | SOURCE_ONLY autoriza somente representação atribuída. Seu estado semântico é not_assessed; não equivale a accepted/confirmed de afirmação derivada. Identidade integral destinada a canonical_assertion permanece indeterminada. |
| REQ-BI-004 | IDs e hashes são produzidos/verificados pelo servidor. O servidor autentica a origem pela operação, tentativa, sessão, turno e invocação que realmente executou; um conjunto autoconsistente fornecido pelo modelo não autentica sua própria origem. |
| REQ-BI-005 | Toda destinação exigida pelo perfil deve estar validada antes de on_chunk, atualização da cópia de cena e commit. Derivação exigida pendente, indeterminada ou rejeitada impede o turno; não entregar enquanto a memória fica pendente. |
| REQ-BI-006 | O perfil source-only exige fonte atribuída persistível, não um candidato abstrativo opcionalmente dispensado após falhar. Seus candidatos/memórias episódicas livres são ausentes por contrato; não há resumo rejeitado escondido por uma coleção vazia. |
| REQ-BI-007 | Preservar fatos mecânicos, estado do personagem e relações produzidos pelos módulos locais, dentro de sua autoridade específica. Nenhuma regra autoriza inferir consequências ficcionais apenas de um sucesso mecânico. |
| REQ-BI-008 | Filtrar origem elegível e audiência antes de ranking, deduplicação e orçamento. Público/jogador, storyteller e system são fronteiras de acesso, não categorias de confirmação semântica. |
| REQ-BI-009 | Manter reexecução idempotente, CAS de revisão, rollback transacional e não consumo de turno em falha. Não incluir LLM ou callback de transporte dentro da transação SQLite. |
| REQ-BI-010 | Não regravar, reclassificar ou migrar v1. Ausência de envelope B significa histórico não avaliado por B, mesmo com validation_status=accepted. Uma consulta v2 incompatível deve recusar explicitamente antes da chamada. |
| REQ-BI-011 | Cobrir todos os leitores: memória episódica, cena quente, fatos reservados, consolidação e consulta direta ao narrador. Trocar somente validate_memory_candidate não fecha a fronteira. |
| REQ-BI-012 | Preservar n acima de 600 caracteres fora de SceneState.summary. Sem truncamento, resumo automático, aumento silencioso de limites ou normalização adicional depois do hash da fonte. |

CON-BI-001: Não adicionar juiz LLM obrigatório, parser semântico geral, comparação por substring como prova de implicação, fallback ou novo alvo padrão. ALT-004 do plano LLM continua preservada.

CON-BI-002: Esta primeira ponte cobre cena conhecida, elenco fixo e metadados compactos vazios, como o perfil puro existente. Não finge resolver abertura, mudança de local, entrada de NPC, criação/fecho canônico de pendências ou integração geral de campanhas.

CON-BI-003: O caminho legado permanece selecionado pelos chamadores atuais. A ponte deve ser uma entrada interna explícita usada inicialmente pelo harness local; não uma flag geral adicionada ao frontend ou uma seleção automática por shape da resposta.

### 1.2 Fronteiras observadas no código atual

| Caminho | Local verificado | Comportamento atual e implicação |
|---|---|---|
| Preparação em cópia | api/main.py:1007; api/orchestrator_service.py:1511 | O chamador passa deepcopy(session.context); a preparação altera essa cópia. A ponte deve conservar essa separação e não publicar a cópia antes do commit. |
| Admissão da cena | api/turn_execution_service.py:452 | _admit_scene_continuation valida, chama project_scene, gera fatos/eventos e modifica context.scene em 632. Não é uma função de armazenamento neutro da prosa. |
| Ordem de entrega | api/turn_execution_service.py:1045, 1068, 1096, 1123 | Schema/política precedem a admissão da cena e on_chunk; o candidato de memória é criado depois do callback. A ponte B deve concluir suas avaliações antes desse callback. |
| Confirmação anterior | api/turn_execution_service.py:1134; api/memory_service.py:216 | semantic_grounding_confirmed recebe proposal is not None. O novo caminho não pode reutilizar esse booleano como prova de fidelidade. |
| Texto entregue | api/turn_models.py:165; api/turn_execution_service.py:1110 | NarrativeRecord.text recebe a composição n+q. Esse registro pode continuar como recibo de apresentação, mas não é idêntico ao n isolado. |
| Pareamento de memória | api/persistence.py:489, 2092, 2148 | O pareamento exige fontes/valores compatíveis e promoção única; a chave atual não contém assessment B. A aceitação v1 não autoriza uma memória B. |
| Digest e transação | api/persistence.py:2174, 2191, 2194, 2340, 2383 | context já entra no digest agregado; BEGIN IMMEDIATE, revisão e rollback protegem a unidade de turno. Metadados B precisam de validação tipada adicional, não só inclusão em JSON. |
| Recuperação episódica | api/persistence.py:2659; api/orchestrator_service.py:1125 | Recupera resumos por visibilidade/orçamento e os restaura como ContextItem; não conhece a distinção entre fonte atribuída e afirmação confirmada. |
| Cena quente | api/scene_service.py:111; api/orchestrator_service.py:1680, 1894, 2283 | scene_fact_text projeta resumo/detalhes/pendências com linguagem de estado estabelecido. Fonte B não pode ser colocada nesses campos. |
| Fatos reservados | api/orchestrator_service.py:1160, 1234 | Fatos world.scene.* storyteller são restaurados diretamente, inclusive pendências antigas; isso contorna a memória episódica. |
| Consolidação | api/persistence.py:2813; api/orchestrator_service.py:1248 | A composição exata dos resumos de origem preserva seus textos, mas não melhora a autoridade semântica dessas origens. |
| Serialização para H6 | api/orchestrator_service.py:243 | _context_prompt agrupa conteúdo por visibilidade em CONHECIDO/CONFIDENCIAL e deduplica pelo texto. Nenhum desses mecanismos preserva sozinho a atribuição B. |
| Consulta de cena | api/orchestrator_service.py:1545, 1667, 1682 | A consulta reutiliza recuperação e pode pedir que H6 estabeleça cena desconhecida. O perfil de fonte conhecida não pode entrar nesse ramo de abertura por acidente. |
| Resposta direta/lore | api/turn_execution_service.py:1311, 1429 | O caminho separado também cria/promove memória. Texto livre de H4 não vira confirmado por estar nesse caminho ou por ter referência de evento. |
| Replay terminal | api/turn_execution_service.py:691 | Operação concluída é restaurada sem nova chamada. A ponte precisa carregar o envelope B quando existir, sem acrescentá-lo ao resultado legado. |

### 1.3 Autoridade canônica disponível e seu limite

A tabela enumera produtores existentes; não cria novas regras semânticas nem declara que qualquer JSON com essas etiquetas veio desses produtores. Na leitura persistida, a origem deve ser ligada ao turno e ao produtor admitidos; copiar uma string deterministic_module para um registro forjado é insuficiente.

| Regra tipada candidata à reutilização | Origem efetiva | Projeção permitida | Inferência que continua proibida |
|---|---|---|---|
| Resolução mecânica | api/orchestrator_service.py:2132–2153; rules_service.calculate_resolution | Dados, pool, dificuldade, is_success, outcome, messy/bestial e recibo estruturado da resolução. | Sucesso implica “porta aberta”, “segredo descoberto” ou “NPC convencido”, sem regra específica de efeito no mundo. |
| Declaração sem teste | api/orchestrator_service.py:2155–2164 | Texto declarado, requires_roll=false e outcome unresolved; evento player_action_declared em 2237. | A declaração prova que o personagem já executou ou concluiu tudo que mencionou. |
| Estado do personagem | api/orchestrator_service.py:2183–2198 | Valores exatos de player_sheet.status após as transições locais previstas; referências ao registro servidor. | Nova emoção, intenção, lembrança ou consequência corporal inventada pelo narrador. |
| Estado relacional | api/relationship_service.py:127; api/orchestrator_service.py:2200–2215 | Valores produzidos pela regra relacional, com sua audiência storyteller; preservar as condições locais de agressão/resultado/habilidade. | A narrativa afirmar uma reação específica do NPC e essa prosa ser tratada como prova do valor ou de um novo vínculo. |
| Cena/cadastro previamente autoritativos | api/scene_service.py:61, 77; api/orchestrator_service.py:1569 | Copiar local/elenco de uma fonte elegível previamente existente ou do seed inserido em criação explícita; conservar status desconhecido quando ausente. | Elevar automaticamente todo resumo/detalhe de um save v1 à avaliação B ou introduzir local/NPC porque apareceu em n. |
| Consulta do estado | api/orchestrator_service.py:1585 | Registrar que o jogador consultou a cena e apresentar campos já elegíveis, sem derivar novidade ficcional. | Confundir “foi narrado após a consulta” com “é consequência canônica comprovada da consulta”. |

Os fatos world.scene.*, scene_advanced, resumos s, fatos f, aberturas t e resoluções r criados a partir da proposta livre em api/turn_execution_service.py:490–615 pertencem à admissão ficcional v1. Não são novas regras determinísticas de equivalência narrativa→registro. O novo caminho não os fabrica a partir de n, nem reutiliza o evento que copiou s como prova circular de que s é fiel.

## 2. Implementation Steps

### Fase 1 — Ponte interna e unidade de admissão

GOAL-BI-001: oferecer um caminho positivo local que entregue fonte atribuída validada e preserve a unidade canônica mecânica, sem ativar o produto. Todos os itens abaixo estão por implementar.

| ID | Ação proposta e dependência | Critério de término | Implementado |
|---|---|---|---|
| TASK-BI-001 | Definir um envelope interno versionado de turno B, separado de FrozenRecord, e um ponto de entrada explícito para o harness. | Ramo legado não muda; respostas n/s/f/t/r não selecionam B automaticamente; fonte e destinações derivadas são tipos distintos. | Não |
| TASK-BI-002 | Tornar o perfil n/q reutilizável por um módulo de aplicação delimitado, conservando o perfil experimental congelado e suas provas. Não importar scripts de avaliação no caminho do produto. | Sem model_construct, fatos falsos ou bypass de agência/sigilo/mecânica; cena incompatível falha antes do LLM. | Não |
| TASK-BI-003 | Implementar construção pura do agregado B depois da resposta e antes de on_chunk. Reusar o núcleo api/narrative_grounding.py. Depende de 001/002. | Toda fonte/binding/assessment é revalidada; nenhuma destinação exigida está pendente; nenhuma chamada a _admit_scene_continuation ou project_scene nesse perfil. | Não |
| TASK-BI-004 | Exercitar entrega provisória e commit com FakeLLMAdapter e SQLite temporário. Depende de 003 e da fase 2. | Fonte fiel chega à recuperação após reinício; referência inválida/derivação indeterminada não entrega chunk nem consome turno. | Não |

Sequência proposta:

1. Resolver a seleção explícita da ponte e sua elegibilidade antes de qualquer chamada ou RNG adicional. Restaurar a cena e as dependências com audiência e origem conferidas. Cena ausente ou dependência v1 incompatível produz erro seguro do perfil; não substituir por cena vazia.
2. Reusar o rascunho mecânico produzido no fluxo existente e suas identidades. H6 recebe os fatos tipados e fontes atribuídas como dados; não recebe resumos livres com autoridade implícita.
3. Validar n/q, limites, idioma, pergunta, ação declarada, outcome e segredos pela política completa. Normalizar whitespace somente no envelope, antes de criar a identidade textual. Uma rejeição encerra a tentativa sem fonte.
4. Criar a fonte com source/session/turn/invocation do servidor e q separado. Avaliar o destino NARRATIVE_SOURCE_VIEW; materializar somente SOURCE_ONLY. Se algum futuro campo derivado for exigido, avaliá-lo por uma regra tipada própria antes de continuar; sem regra, bloquear.
5. Construir um agregado imutável contendo fatos/eventos mecânicos já preparados, NarrativeRecord para apresentação e envelope B para memória atribuída. Não criar evento scene_advanced com resumo copiado do modelo. Os eventos visíveis existentes de declaração/resolução/consulta são os antecedentes do turno, não prova semântica de cada frase nova.
6. Revalidar o agregado completo por uma função pura compartilhada com a persistência, antes de on_chunk. Depois chamar on_chunk com n+q e manter a entrega provisória até o terminal completed. Em seguida, revalidar e confirmar a única transação.
7. Só após commit publicar o novo snapshot e liberar a fonte à recuperação da próxima operação. Não inserir a fonte de uma tentativa falha no contexto vivo, cache ou pacote seguinte.

Não há transação distribuída entre WebSocket e SQLite. A validação prévia impede entrega de conteúdo já conhecido como inadmissível; falha de conexão ou CAS posterior ainda pode ocorrer depois de um chunk provisório. Nesse caso, o terminal falha e o snapshot anterior permanece. O desenho não promete “desenviar” bytes e não muda a regra de apresentação provisória existente.

### Fase 2 — Persistência sem migração de saves

GOAL-BI-002: preservar fonte, identidade e avaliação na mesma unidade transacional, sem mudar os registros v1.

Proposta mínima de armazenamento: acrescentar apenas aos turnos produzidos pela nova ponte um objeto tipado e versionado em context.narrative_source, já abrangido por context_json e pelo digest de commit_turn. O nome de protocolo dessa integração deve ser fixado em TASK-BI-001; não reutilizar schema_version=1.0 como se fosse o protocolo B. Não há necessidade demonstrada de nova tabela ou DDL para a primeira prova local.

Esse envelope proposto contém protocolo de integração, narrative_id, q normalizado, SourceProjection completo e referências aos antecedentes canônicos do turno. A fonte já contém n, source_policy, audiência e identidades; o binding contém hashes e fingerprint integral; o assessment preserva not_assessed/SOURCE_ONLY. Evitar dois exemplares independentes de n no mesmo envelope. NarrativeRecord.text continua sendo a apresentação n + duas quebras de linha + q; a identidade da fonte é calculada somente sobre n.

| ID | Ação proposta | Critério de término | Implementado |
|---|---|---|---|
| TASK-BI-005 | Validar qualquer envelope B presente no limite de commit; marcador presente com shape inválido nunca cai no ramo legado. Exigir correspondência com NarrativeRecord, operação/tentativa e auditoria da invocação. | Troca de n/q/turno/sessão/invocação/visibilidade ou protocolo falha antes da transação e antes da entrega no chamador. | Não |
| TASK-BI-006 | Incluir o envelope validado no agregado antes do digest, preservando o algoritmo para turnos sem envelope. IDs/tempos estáveis vêm do rascunho e da operação; não são regenerados durante replay. | Retry do mesmo agregado retorna o mesmo resultado; trocar qualquer identidade, assessment ou texto com a mesma operation_id gera conflito. | Não |
| TASK-BI-007 | Restaurar a fonte de turnos B comprometidos pelo leitor tipado, conferindo o vínculo com o turno/narrativa armazenados. Tentativas e contextos arbitrários não são fontes. | Reinício não altera n, q, hash ou avaliação; ausência de envelope não provoca backfill. | Não |
| TASK-BI-008 | Preservar a validação e o pareamento v1; não usar MemoryCandidate/EpisodicMemory como contêiner de texto source-only. | Nenhuma memória B é aceita por semantic_grounding_confirmed ou por _derived_memory_key do v1. | Não |

No perfil inicial, memory_candidates e episodic_memories são vazios por definição do novo contrato, e a fonte atribuída é o destino obrigatório de memória. O commit atual permite coleções vazias, mas ainda não valida a obrigação B: TASK-BI-005 deve rejeitar uma tentativa de contorná-la retirando ou adulterando a fonte. A seleção de protocolo da ponte pertence ao servidor; não pode depender apenas de um campo removível do payload do modelo.

Estados devem permanecer separados: tentativa pending/completed/failed/cancelled controla execução; SOURCE_ONLY/INDETERMINATE/REJECTED controla representação; pending/accepted/rejected do candidato abstrativo v1 não traduz automaticamente nenhum deles. Avaliações indeterminadas/rejeitadas de uma tentativa B não geram memória comprometida; o diagnóstico seguro fica na tentativa, sem disponibilizar seu texto à recuperação.

Se um incremento posterior habilitar candidatos abstrativos B, deverá definir modelo próprio de candidato e memória com assessment obrigatório, pareamento incluindo identidade do assessment/política/destino e validação recalculada. Não modificar a chave v1 para reinterpretar memórias antigas. Esse ramo não é necessário para a primeira integração source-only.

### Fase 3 — Leitura, audiência e contexto em todas as rotas

GOAL-BI-003: impedir que uma fonte corretamente persistida seja promovida a fato por um leitor posterior.

| ID | Ação proposta | Critério de término | Implementado |
|---|---|---|---|
| TASK-BI-009 | Criar recuperação tipada de fontes comprometidas da mesma sessão, com identidade e audiência conferidas antes do orçamento. | Objetos forjados, cross-session e fontes não autorizadas não influenciam seleção, contagem, ordem ou conteúdo. | Não |
| TASK-BI-010 | Compor o pacote B com canonical_scene e attributed_sources separados, usando o formato explícito do perfil. Não converter a fonte em ContextItem genérico que _context_prompt envia a CONHECIDO. | n aparece integral na seção atribuída, com identidade e not_assessed; q anterior não entra como fonte. | Não |
| TASK-BI-011 | Aplicar elegibilidade B a memória, cena quente, fatos reservados, consolidação e consultas diretas antes da geração. | Nenhum leitor reintroduz como confirmado um resumo v1 ou uma fonte B apenas por sua tag, camada ou visibilidade. | Não |
| TASK-BI-012 | Registrar seleção/omissão por IDs e preservar limites de fontes/contexto. | Fonte necessária que não cabe causa erro antes da chamada; fonte opcional só pode ser omitida inteira, com registro explícito. | Não |

Para a primeira ponte, manter o pacote separado evita mudar o schema de ContextItem no default. Os fatos tipados existentes podem continuar a usar a seleção determinística, desde que sua elegibilidade seja comprovada antes de criar os itens; as fontes atribuídas entram pelo construtor tipado separado. O orçamento precisa cobrir o pacote final completo, inclusive metadados, sem descontar a seção de fontes por fora da conta.

Tratamento obrigatório por caminho:

- **Cena quente:** no perfil inicial, somente local/elenco herdados e elegíveis são projetados por scene_fact_text. Resumo/detalhes/pendências não vazios tornam o contexto incompatível; não apagá-los para satisfazer o perfil. Textos n nunca são copiados para SceneState.summary, details ou open_threads.
- **Fatos storyteller/system:** o perfil atual só admite fontes public/player. Não encaminhar uma fonte privada ao construtor público. Fatos reservados tipados e elegíveis continuam privados; fatos ficcionais v1 restaurados por _stored_confidential_scene_fact_item não ganham avaliação B. Se necessários ao turno, bloquear explicitamente a ponte, preservando o leitor legado.
- **Memória episódica v1:** preservar a memória e seu acesso pelo modo legado; não restaurá-la em B como confirmação. Não esconder uma dependência necessária apenas porque não há assessment. Dados mecânicos antigos podem ser usados somente por um adaptador de origem e regra tipada verificável, não por accepted=true.
- **Consolidação:** não enviar fontes B ao consolidador de resumos v1. Uma lista/índice de IDs de fontes preserva referências, mas não é resumo semântico. Consolidações antigas continuam históricas; união textual exata de fontes não transforma sua autoridade. Consolidação abstrativa B fica fora da primeira ponte.
- **Consulta direta de cena:** usar a mesma restauração e elegibilidade B. “Onde estou?” em cena ausente não ativa silenciosamente o diretor v1 que inventa local/elenco. A rota direta só apresenta dados tipados elegíveis ou usa a geração n/q da ponte em cena conhecida.
- **Lore/H4 e outras respostas diretas:** não assumir que todo texto desse ramo é projeção determinística. Manter a rota antiga fora da ponte até haver regra de origem/destino explícita. Catálogo versionado é fonte; paráfrase livre de H4 não herda confirmação automática.
- **Deduplicação:** igualdade de texto não permite fundir uma fonte atribuída com um fato confirmado nem fundir origens/audiências diferentes. O envelope B conserva sua identidade; não passa pelo seen de strings de _context_prompt.
- **Instruções embutidas:** fonte narrativa é dado atribuído, mesmo quando contém comandos ou linguagem metanarrativa. A separação estrutural não garante obediência do modelo; os gates de saída e os controles de injeção continuam necessários.

### Fase 4 — Compatibilidade e próximo incremento delimitado

A primeira execução integrada será local, em banco temporário e com fixture explicitamente canônica. Nenhum save real é usado como atalho para provar compatibilidade.

Após analisar a coleta suplementar necessária, implementar TASK-BI-001 a008 e os controles TEST-BI-001 a007 como um incremento único de ponte/commit/restauração. A condição positiva é uma sequência local de três turnos: no segundo, a fonte anterior integral; no terceiro, as duas anteriores, após fechar/reabrir a persistência. Isso cabe no limite atual de duas fontes de entrada, sem aumentar o número de chamadas de qualquer executor histórico. Testes falsos não contam como observação ao vivo.

A prova de passagem real entre fontes permanece um gate de evidência separado. Uma observação ao vivo que termine antes do segundo pedido não o satisfaz, mesmo se as provas locais passarem. Sua ausência não exige nova aprovação B nem autoriza uma série automática de repetições: registrar a limitação e concluir os testes locais permitidos.

Depois, fechar TASK-BI-009 a012 e os controles das rotas indiretas antes de permitir qualquer uso de campanha. Sem essa fase, uma ponte de commit isolada não representa integração concluída. Default, seleção do produto, uso em saves reais e adoção de candidato não mudam como efeito colateral.

## 3. Alternatives

- **ALT-BI-001 — Envelope B no context JSON de novos turnos:** opção mínima proposta para a primeira prova; mantém digest e transação existentes e evita migração. Requer validação tipada no commit e leitura própria; JSON livre sem validação seria insuficiente.
- **ALT-BI-002 — Novas tabelas e tipos globais de memória agora:** adiado. Indexação especializada pode ser necessária com volume, mas ainda não há evidência de que seja necessária à ponte e ampliaria migração/compatibilidade.
- **ALT-BI-003 — Trocar somente o booleano de confirmação:** insuficiente. Cena quente, fatos reservados e consolidações continuariam promovendo textos; além disso, bloquearia candidatos sem oferecer o destino source-only positivo.
- **ALT-BI-004 — Colocar n em summary ou aceitar citação como fato:** recusado. Viola a separação semântica, conflita com o limite de 600 caracteres da cena e permite perder q ou recortar a fonte.
- **ALT-BI-005 — Desativar todo v1 ou migrar automaticamente:** recusado. O perfil novo é optativo; um histórico sem avaliação B permanece histórico, não inválido para seu próprio contrato.
- **ALT-BI-006 — Entregar prosa enquanto a memória derivada espera aprovação:** fora deste desenho; contraria a regra vigente de unidade do turno. SOURCE_ONLY é um destino válido diferente, não uma dispensa dessa regra.
- **ALT-BI-007 — Novo juiz LLM, prompt corretivo ou replay da Estufa:** não é necessário à integração local descrita e não demonstra uma garantia geral de implicação.

## 4. Dependencies

DEP-BI-001: núcleo puro e perfil n/q existentes, preservados com suas versões e provas; qualquer adaptação para aplicação precisa de diff e testes próprios, sem atualizar retroativamente artefatos dos experimentos.

DEP-BI-002: contratos de turno, persistência e recuperação atuais, inclusive locks de sessão, revisão de estado, término idempotente e proibição de rerrolagem por replay. A ponte não muda a política de retry.

DEP-BI-003: origem confiável da cena e dos fatos fornecida pelo servidor. Para a primeira fixture local isso é explícito; para save v1 arbitrário ainda não existe um adaptador B comprovado. Hash e etiqueta de produtor não bastam.

DEP-BI-004: análise encerrada da coleta de continuidade. Estufa não demonstrou a cadeia; Pátio é preparação separada. Não há dependência de credencial para escrever ou executar os futuros testes locais.

DEP-BI-005: atualização coordenada do plano antes de integrar, como exige TASK-013. Este documento detalha o trabalho; não marca código como concluído nem altera o plano por conta própria.

## 5. Files

| Arquivo/superfície futura | Mudança delimitada proposta |
|---|---|
| Novo módulo interno de integração B sob api/ | Envelope versionado, validação do agregado, perfil de origem e entrada explícita do harness. Nome final fixado antes da implementação; sem dependência de scripts de avaliação em runtime. |
| api/turn_execution_service.py | Encaixe de entrega/commit, replay com envelope opcional verificado; deixar o ramo v1 e lore fora da seleção B automática. |
| api/persistence.py | Validação da obrigação B, digest com envelope e leitura de fontes de turnos comprometidos; sem DDL/migração na primeira prova. |
| api/orchestrator_service.py | Montagem optativa do contexto atribuído, elegibilidade antes dos leitores e proteção das consultas diretas. |
| api/context_service.py e api/scene_service.py | Preservar formatos atuais; adaptar somente se uma API compartilhada for necessária à ponte, com tipos e testes explícitos. Não usar tags soltas como autoridade. |
| api/memory_service.py e api/turn_models.py | Preservar os modelos/pareamento v1; novas destinações abstrativas B não fazem parte do primeiro incremento. A fonte não é criada como EpisodicMemory. |
| Novos testes de integração B | Banco temporário, FakeLLMAdapter, payloads autorados, reinício/rollback/contexto; nenhuma chamada externa. |

Nenhum desses arquivos de código foi alterado por este documento. O único arquivo produzido nesta tarefa é este desenho.

## 6. Testing

Todos os testes desta seção são futuros. Os testes existentes citados são referências de comportamento e helpers, não uma alegação de execução nesta tarefa.

| ID | Controle local proposto | Resultado exigido |
|---|---|---|
| TEST-BI-001 | Cena conhecida, ação passiva e n/q válidos; obter agregado B e confirmar em SQLite temporário. | Um turno, fonte integral atribuída, mesmos fatos mecânicos, nenhuma nova scene fact/memória abstrativa. |
| TEST-BI-002 | Três turnos autorados com reinício entre gravação e recuperação; último pedido recebe duas fontes anteriores. | Ordem/identidades/textos preservados, q excluído das fontes e nenhuma ocorrência dos textos atribuídos no bloco CONHECIDO. |
| TEST-BI-003 | n de 601 a1600 caracteres, com acentos/emoji, normalização explícita antes do hash. | Persistência e retorno integrais; SceneState.summary não recebe n; nenhum corte para 600. |
| TEST-BI-004 | Adulterar separadamente source/session/turn/invocation, q, hash, política, audiência, assessment e corpo de NarrativeRecord. | Recusa antes de on_chunk/commit; snapshot/relações/revisão inalterados e nenhuma rolagem adicional após o rascunho ou durante replay; não prometer rollback do PRNG global. |
| TEST-BI-005 | Requerer uma afirmação derivada que transfere atributo, altera negação/modalidade ou parafraseia n sem regra tipada. | INDETERMINATE bloqueia a destinação exigida; não aceitar por referência válida, SOURCE_ONLY paralelo ou coleção vazia. |
| TEST-BI-006 | Retry do mesmo agregado/operação e tentativa de mudar somente o envelope com a mesma operation_id. | Replay idêntico sem LLM/RNG; conflito para conteúdo diferente, inclusive metadados B. |
| TEST-BI-007 | Falha de callback, cancelamento após geração, erro de persistência e CAS concorrente. | Sem commit parcial ou fonte recuperável; chunk eventual é provisório e nunca vira completed em falha. |
| TEST-BI-008 | Abertura sem SceneState e seed só em criação explícita. | A ponte conhecida recusa antes do LLM; não chama seed_scene_context automaticamente. O caminho legado continua com seu comportamento. |
| TEST-BI-009 | Save v1 com summary/details/threads e memória accepted, sem envelope B. | Bytes/valores legados preservados; replay v1 funciona; entrada B incompatível falha explicitamente, sem promoção ou limpeza silenciosa. |
| TEST-BI-010 | Fato storyteller reservado, fonte pública, fonte privada e mesmo texto sob duas origens. | Audiência antes de ranking/orçamento; sem vazamento nem fusão de autoridade; confidencial v1 não ganha avaliação B. |
| TEST-BI-011 | Memória, cena quente, consolidação e consulta direta com texto livre legado adversarial. | Nenhuma rota paralela reintroduz esse texto como confirmado no pacote B. |
| TEST-BI-012 | Fonte obrigatória excede orçamento; fonte opcional inteira não cabe; fonte de três origens excede o limite do perfil. | Recusa ou omissão inteira explicitamente registrada conforme obrigatoriedade; nenhum truncamento/resumo/reclassificação. |
| TEST-BI-013 | Tentativa falha contém texto válido estruturalmente, ou context arbitrário imita fonte completa. | Só turnos comprometidos e autenticados pelo caminho servidor podem alimentar a próxima geração. |
| TEST-BI-014 | Mecânica com sucesso/falha, declaração sem teste e mudança relacional local. | Projeções tipadas preservam valores/visibilidade; sucesso ou menção não autoriza consequência ficcional inventada. |

Bases existentes: tests/test_turn_execution_service.py:293, 381, 429, 475, 693; tests/test_persistence.py:641, 804, 977, 1136, 1358; tests/test_context_service.py:58, 145, 170; tests/test_turn_pipeline_integration.py:436 e1026; tests/test_memory_service.py:181, 193, 303; testes do núcleo e perfil puro.

O critério de término da futura integração é o fechamento dos caminhos positivos e negativos acima com diff revisado. HTTP 200, schema válido ou continuidade textual em uma amostra não substituem essas provas. A mesma suíte não prova verdade geral de n nem aprovação de produto.

## 7. Risks & Assumptions

- **RISK-BI-001 — Perfil restrito:** cena conhecida com elenco fixo não oferece progressão canônica geral. Abertura e transições continuam pendentes; não remover require_forward_motion do v1 nem fabricar f/t/r para esconder a diferença.
- **RISK-BI-002 — Fonte contraditória:** um texto pode passar as verificações delimitadas e ainda conter contradição ou prosa ruim. SOURCE_ONLY conserva autoria/origem, não resolve essa qualidade; revisão autorada continua separada.
- **RISK-BI-003 — Perda de contexto por escala:** a prova de três turnos usa até duas fontes anteriores. Não demonstra continuidade arbitrária além desse conjunto nem define uma política de compressão. Retenção/seleção de história longa precisa de evidência e contrato próprio, sem resumo automático.
- **RISK-BI-004 — Origem de save:** campos tipados antigos não carregam necessariamente a avaliação exigida por B. A ponte recusa dependência incompatível; não faz inferência de autoridade somente pelo nome de classe/tabela.
- **RISK-BI-005 — Digest não é autenticação:** recomputar hashes prova consistência com o conjunto recebido. O limite de confiança continua sendo o servidor que executou/admitiu a invocação e o armazenamento comprometido dessa operação.
- **RISK-BI-006 — Entrega e banco:** on_chunk e SQLite não são atômicos entre si. Preservar o terminal provisório e verificar todos os destinos antes do callback; não prometer rollback de bytes já enviados.
- **ASSUMPTION-BI-001:** o teste de integração pode usar as transações/locks existentes e o context JSON sem nova migração. Essa hipótese deve ser comprovada por TEST-BI-004/006/007, não tomada como implementação já pronta.

Pendências concretas, sem renovar a decisão B: fixar o protocolo e o modelo do envelope integrado; comprovar a passagem real entre fontes; implementar/revisar a ponte local; fechar todos os leitores; definir um adaptador de origem antes de usar dados v1. A aceitação do produto e a mudança de default só entram quando essas provas e os limites de abertura/progressão forem apresentados concretamente. Não há pedido humano necessário para continuar a preparação local autorizada.

## 8. Related Specifications / Further Reading

- [Direção B e TASK-012/013](../../../plan/architecture-narrative-grounding-1.md).
- [Decisão de separação entre fonte e interpretação](narrative-memory-grounding-decision-2026-09-07.md).
- [Fronteira anterior de admissão/memória e controles autorados](narrative-memory-admission-boundary-2026-09-07.md).
- [REQ-012 a018 e alternativas de turno/memória](../../../plan/architecture-llm-memory-turns-1.md).
- [IMP-007, AC-IMP-005 e compromisso de continuidade](../../../spec/spec-improvisational-scene-direction.md).
- [Piloto Estufa encerrado f97a8568](../reports/narrative-source-observation-f97a8568-2026-09-07.md).
- [Preparação do perfil de fonte integral](../reports/narrative-source-preparation-2026-09-07.md).

### Versões de código inspecionadas

| Arquivo | SHA-256 |
|---|---|
| api/narrative_grounding.py | 417962e0fffc216a77153748f742a86e2b761fd5a3041e74181d8803128b61a3 |
| scripts/narrator_source_profile.py | ba6c8e49b8d9dcadb8fcfc7500ebfe812485bbaf3062098f572743fdcd76e112 |
| api/turn_execution_service.py | a44f1739d8447067c41a10e590732aac2258bc2eb3d1748760bbe7fdeacb038c |
| api/turn_models.py | 42707f52d07a3d51dae1d365d283a09c4a03bf5543cc83f2425690e815b71ba7 |
| api/memory_service.py | 4a8bfa8004879053417771b3f69020b48b5eaa18be4af6ca73e2040ca1755cf4 |
| api/persistence.py | 69a31ecf2ad25fad899f3453feca98647200d7b2924889e6ac76ad285e4a63ea |
| api/orchestrator_service.py | 6b3a594d7b20dc215003389512d2f1ce4fa6b36072358ffc8b72e5278d6b7da7 |
| api/scene_service.py | b523534a12c8121a6f0159e0057556f0d7952f1cca9bba71cc23c6f7c924b607 |
| api/context_service.py | 7fcbec6660602aa1b6d7859536b5d1275b2d641a6d198f8d23cb9c69c99bcac3 |
| api/main.py | 861e3991f058b8070ebfeccc7dfbd24bc176fdde5b1268a09c0178ba7a28bdd1 |
| api/relationship_service.py | 6b66c06c2c2eb9e7ef3ec3c4ee15acd614038215af090398d97fc1a00a0b56ce |

Verificação desta tarefa: leitura dos serviços, contratos, plano e relatório encerrado; conferência dos caminhos, identidades e hashes acima; escrita apenas deste documento novo. Nenhum teste, chamada externa, acesso a credencial ou alteração de runtime/save foi realizado.

