---
goal: Planejar progressão e campanha híbrida mínima com Luna low prioritário e contratos portáveis
version: 1.0
date_created: 2026-09-29
last_updated: 2026-09-29
owner: Produto Agente Storyteller
status: 'In progress'
tags: [architecture, campaign, progression, narrative, evaluation]
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In%20progress-yellow)

PROG-ROUTE-B foi aprovada em 29/09/2026: planejar progressão e campanha híbrida
mínima antes de retomar a admissão. O usuário escolheu Luna low como referência
prioritária, com melhorias compartilhadas pelos demais candidatos utilizáveis.
Em seguida, o usuário aprovou DEC-PROG-001 e DEC-PROG-002 em 29/09/2026.
O detalhamento documental foi preparado. Em 29/09, o usuário escolheu o ritmo A
e autorizou continuar a implementação: primeira espera avisa, segunda molha,
terceira pode causar perda. Isso não autoriza inferência, gasto, migração ou
admissão. Separadamente, o usuário autorizou avaliar
e implementar redução da espera Luna, e mostrar custo ao final de todo teste Luna.

HYP-006 permanece encerrado e narrativamente inelegível para o MVP. O resultado
formal de oito casos não anulou a rejeição do ensaio manual. Priorizar o candidato
significa investir primeiro na experiência em que ele será reavaliado, não
considerar provada sua superioridade em comparação controlada.

## 1. Requirements & Constraints

### Decisões vigentes

- **REQ-001**: Planejar progressão antes da retomada da admissão; usar Luna low
  primeiro quando houver protocolo futuro autorizado. Referência histórica:
  `gpt-5.6-luna`, esforço `low`; disponibilidade futura deve ser revalidada.
- **REQ-002**: Preservar DEC-RES-001 a DEC-RES-005: beat determinístico,
  consequência vinculante, limites do NPC, pressão nomeada e nenhum RNG adicional.
- **REQ-003**: Preservar direção B: narrativa integral é fonte atribuída,
  não prova independente de mundo nem autorização de mutação.
- **REQ-004**: Exigir resposta pertinente ou consequência observável em entrada
  ficcional significativa, sem escolher pelo jogador; comandos, esclarecimentos
  e falhas técnicas não avançam ficção.
- **REQ-005**: Preservar commit atômico, vínculo de operação, pausa/retomada,
  replay sem nova rolagem e segredos fora das projeções públicas.
- **CON-001**: Não introduzir outro LLM resolvedor/planejador, campanhas globais,
  catálogo V5 abrangente, criação de ficha ou reforma de interface nesta etapa.
- **CON-002**: Nenhum candidato historicamente rejeitado se torna elegível por
  receber o contrato novo. Lotes e prompts congelados não serão reescritos.
- **SEC-001**: Usar dados sintéticos e nenhuma leitura de .env ou credencial.
  Chamada futura requer alvo, custo, limite e autorização próprios.

### Evidência atual e lacuna

| Superfície observada | Evidência no repositório | Limite para esta etapa |
|---|---|---|
| Luna manual | `run_source_local_luna_trial.prepare` reutiliza `base.prepare`; este declara `narrative-source-progress-v1` | Microcena B de espera/diálogo, não campanha completa. |
| Prompt manual | `narrative-source-progress-v1.md` pede acontecimento ambiental e mantém local/elenco | Não é o mesmo pacote de diálogo catalogado do runtime. |
| Beat de Mara | `attach_catalog_scene_resolution` e `mara_scene_options` cobrem fala com Mara, local e tópicos reconhecidos | Sem opção elegível, esse piloto devolve fluxo anterior. Não cobre progressão global nem toda pergunta. |
| Fonte B | REQ-013 do plano do produtor conserva estado/relações; `SourceProducerConfig.profile` é literal; `_checked_scene` recusa resumo/detalhes/pendências | Não conectar beat rico mudando apenas um prompt ou removendo validação. |
| Relato manual | Três turnos completos, duas perguntas sem resposta de Mara | Falha da experiência comprovada; causa exclusiva no modelo não isolada. |

Esses pontos foram inspecionados em código/documentos, sem executar novo ensaio.
Não há evidência nesta etapa de que um modelo específico resolverá a progressão.

### Decisões aprovadas em 29/09/2026

| ID | Proposta recomendada | Consequência e alternativa |
|---|---|---|
| **DEC-PROG-001** | Recorte sintético novo: uma aventura curta no Arquivo/Galeria, com Mara, um conflito local de preservar um registro público ameaçado por infiltração e desfechos de preservação, recuperação parcial ou perda/abandono. | Reutiliza cenário/perfil, permite começo, desenvolvimento, clímax e conclusão. Alternativa: outro conflito escolhido pelo usuário, exigindo novo conteúdo. A sessão atual não recebe essa trama retroativamente. |
| **DEC-PROG-002** | Especificar um novo perfil B opt-in de campanha que consuma consequências estruturadas confiáveis e o núcleo puro do resolvedor; efeitos preparados persistem ligados à operação e só se tornam canônicos no commit final. Prosa continua fonte atribuída. | Amplia explicitamente o perfil restrito sem reinterpretar saves antigos. Alternativa: ensaio somente no piloto v1, mais curto de preparar, mas que não prova campanha na direção B e deixa essa integração pendente. |

O aceite de DEC-PROG-001/002 autorizou o detalhamento; o comando posterior
"continue com A" autorizou iniciar o incremento com esse ritmo.
Contrato, campos/visibilidades, transições e exemplos agora estão em
[especificação revisável](../spec/spec-architecture-hybrid-campaign-progression.md).
O ritmo R-03/R-03B/R-04 foi escolhido explicitamente; R-08 conserva a consequência
de falha já descrita, podendo antecipar o dano. A experiência narrativa completa
ainda exige avaliação humana e não está admitida.
Não é necessário decidir modelo definitivo, custo ou número de chamadas agora.

### Recorte de experiência para DEC-PROG-001

Título de trabalho: **O registro ameaçado**. Todo conteúdo abaixo é proposta
sintética, não lore admitido nem acontecimento do save existente.

- Começo: Mara apresenta um registro público em risco; o jogador compreende
  o problema e pode ajudar, negociar, investigar, propor outro método ou recusar.
- Desenvolvimento: diálogo e ação revelam condições concretas do resgate.
  Mara responde sobre tarefa, risco e ajuda possível; o segredo da fundadora
  não é necessário para resolver o conflito e permanece protegido.
- Clímax: uma escolha ou ação relevante decide o destino do registro quando
  houver condição causal para isso. Não exigir percorrer cenas anteriores;
  solução plausível antecipada pode concluir a aventura.
- Conclusão: epílogo distingue registro preservado, conteúdo parcialmente
  recuperado ou perda/abandono e explicita consequências compatíveis com o
  que ocorreu. Não abrir novo gancho obrigatório para evitar terminar.
- Limite: um conflito, um NPC central e até dois locais já usados. Sem novos
  poderes, facções, escala de pressão ou sistema de tempo real. Ação que exigir
  teste reutiliza mecânica suportada; dificuldade e consequências serão
  especificadas, nunca inventadas neste documento como regra V5.

Os quatro momentos não são quatro cenas obrigatórias nem um número fixo de turnos.
A sessão zero conversacional permanece intenção de produto: para o recorte de
validação propõe-se apresentação e confirmação da premissa com perfil sintético,
sem implementar seu gerador ou afirmar que CAMP-01–04 estão resolvidos.

### Responsabilidades propostas para DEC-PROG-002

| Componente | Responsabilidade | Não pode |
|---|---|---|
| Conteúdo da campanha | Definir conflito, estados, opções de consequência, pré-condições e condições de encerramento | Impor sequência fixa ou alterar passado para recuperar roteiro |
| Resolvedor local | Selecionar consequência elegível com base canônica, ação e recibo mecânico existente | Pedir à LLM que escolha verdade canônica ou rolar novamente |
| Preparação/persistência B | Reter preparação e recibo na operação; confirmar efeitos, fonte e revisão atomicamente após admissão | Aplicar efeitos parciais enquanto H6 está pausado |
| Narrador | Realizar resposta, consequência e personalidade com linguagem própria e pergunta aberta quando pertinente | Omitir efeito, resolver outro conflito, gastar recurso ou decidir pelo jogador |
| Avaliação | Conferir estado, realização em prosa, continuidade e experiência ao longo dos turnos | Considerar ID de efeito, JSON válido ou texto diferente prova suficiente de progresso |

A especificação deve separar estado de campanha confirmado, beat preparado e
fonte textual. Identidade/versão da campanha, nó ou marco, objetivos/pendências,
estado do registro, pressão e visibilidade são campos candidatos, ainda sem schema
aprovado. O formato de persistência será definido após análise de compatibilidade,
sem presumir DDL novo nem reutilizar indevidamente campos livres.

Condições fora do catálogo são uma fronteira a especificar: nunca inventar efeito
genérico ou punir solução criativa só por ser diferente. Distinguir paráfrase
coberta, ambiguidade real e ação plausível ainda não suportada. Esta última deve
ter limitação transparente, não progresso fingido nem rejeição ficcional do sucesso.
O corpus deve provar pelo menos uma solução alternativa prevista em termos de
intenção, sem exigir frase exata.

### Critérios de progressão propostos para o recorte

- Diálogo dirigido deve produzir resposta pertinente, recusa explicada,
  condição de ajuda ou reação com efeito concreto; atmosfera sozinha reprova.
- Não exigir revelação nova em toda fala nem impor perigo para manter ritmo.
  Descanso/espera ainda recebe a reação ou mudança exigida pela arquitetura;
  não usar relógio real ou contador arbitrário para avançar ameaça.
- Pressão só muda por causa autorada observável. Repetição de pergunta não causa
  punição automática; resposta preserva o que já foi dito e desenvolve a interação
  quando houver nova intenção ou consequência elegível.
- Pendência resolvida não reaparece como nova. Informação conhecida não pode
  ser apresentada como descoberta; clímax não apaga sucessos anteriores.
- Sucesso satisfaz sua consequência; falha pode mover a situação sem conceder
  o objetivo. Recusa/abandono têm consequência e conclusão, não retorno ao começo.
- Avaliar tanto efeito previsto versus estado confirmado quanto sua realização
  no texto. Declaração de `realized_effects` não prova sozinha adequação semântica.

### Portabilidade e prioridade Luna

O conteúdo causal, o pacote de contexto, os casos, as proibições e a rubrica
serão comuns aos candidatos. Adaptadores podem traduzir schema e parâmetros
suportados, mas não reduzir segredos, agência ou obrigação de progressão por modelo.
Prosa será livre; não se comparará igualdade textual entre provedores.

Luna low é o primeiro alvo de uma futura avaliação autorizada. Qwen, GPT-OSS,
Gemini e os candidatos OpenRouter já investigados podem reutilizar o mesmo pacote
se voltarem a ter rota/custo/capacidade compatíveis. Isso é potencial técnico,
não lista de candidatos elegíveis; disponibilidade e rejeições continuam separadas.
Não testar todos automaticamente. Primeiro demonstrar o contrato offline; depois
observar Luna e somente então decidir se há pergunta útil para outro candidato.
Limites de tokens e esforço serão registrados por alvo sem fingir equivalência
de tokenização ou raciocínio. Não remover casos difíceis para favorecer Luna.

## 2. Implementation Steps

As fases 1–2 prepararam a especificação. A fase 3 iniciou o núcleo offline
após o comando "continue com A"; inferência e admissão seguem sem autorização.

### Implementation Phase 1

- GOAL-001: Reconciliar estado e produzir proposta revisável.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Registrar PROG-ROUTE-B e referência Luna nos documentos de estado/checklist/problema. | [x] | 2026-09-29 |
| TASK-002 | Inspecionar `prepare`, `attach_catalog_scene_resolution`, `mara_scene_options` e os limites B; separar evidência de inferência neste plano. | [x] | 2026-09-29 |
| TASK-003 | Preparar DEC-PROG-001/002, recorte, alternativas, responsabilidades e matriz de testes sem editar runtime. | [x] | 2026-09-29 |
| TASK-004 | Incorporar decisão humana de DEC-PROG-001/002 aqui e na retomada. Aceite explícito recebido em 29/09. | [x] | 2026-09-29 |

Critério: decisões explícitas e ausência de reclassificação dos lotes.

### Implementation Phase 2

- GOAL-002: Após TASK-004, transformar o recorte aceito em contrato completo.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Criar `spec/spec-architecture-hybrid-campaign-progression.md` com estados, invariantes, política de seleção, cobertura e fronteira B escolhida; mapear métodos existentes sem implementá-los. Documento preparado, não implementação aceita. | [x] | 2026-09-29 |
| TASK-006 | Acrescentar fichas de cena/NPC, regras candidatas R-01–09, segredos e encerramentos; consequências autoradas aguardam revisão de produto. | [x] | 2026-09-29 |
| TASK-007 | Criar `evals/narrator/hybrid_campaign_progression_protocol_v1.md`: oito trajetórias e nove contraprovas, separando estado esperado e prosa. Casos não executados. | [x] | 2026-09-29 |
| TASK-008 | Reconciliar CAMP, preparar fase 3 abaixo e riscos de persistência. Nenhum novo lote live/custo autorizado. | [x] | 2026-09-29 |

Critério: nenhum comportamento causal necessário ao recorte fica delegado a
suposição do narrador; propostas ainda não aprovadas permanecem marcadas.
Não concluir o planejamento inteiro porque este primeiro documento foi criado.

### Implementation Phase 3 — integração B offline verificada; aceite pendente

- GOAL-003: Primeiro incremento após aceite do conteúdo e autorização de implementação.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Registrar escolha A: R-03 avisa, R-03B molha, R-04 perde; R-08 conserva dano por falha da proposta. Não reabrir DEC-PROG-001/002. | [x] | 2026-09-29 |
| TASK-010 | Criar `api/campaign_progression_service.py` e `api/campaign_progression_catalog.py`: modelos imutáveis, catálogo sintético e `resolve_campaign_progression` usando `resolve_scene_beat`, sem I/O, LLM ou RNG extra. Núcleo offline, não integrado ao B. | [x] | 2026-09-29 |
| TASK-011 | Criar `tests/test_campaign_progression_service.py` para oito trajetórias autoradas, precondições, estados terminais, paráfrases e ações não suportadas. 435 testes focados/regressão passaram após correção de três expectativas antigas de schema (3→4); 58 são do núcleo/catálogo de cena. | [x] | 2026-09-29 |
| TASK-012 | Integrar perfil B explicitamente versionado por produtor/preparação/cápsula/contexto/turno, persistência e executor; provar CAS, rollback, replay, pausa e paridade B/v1 sem novo DDL. Evidência em `../evals/narrator/reports/hybrid-campaign-source-offline-2026-09-29.md`. | [x] | 2026-09-29 |
| TASK-013 | Preparar ensaio isolado com mesmo catálogo/corpus, sem novo default; verificar offline e submeter experiência completa antes de admissão. Backend/HTTP offline e oito trajetórias/contraprovas estão prontos. Relato humano cobre o objetivo causal de 01–05/08; 06/07 têm recibos fixos apenas nos testes offline. A crítica de UX é específica: mediação impessoal de Mara reduz imersão. L1 parou em HTTP 400; L2 admitiu R-01 e rejeitou R-05 após duas chamadas (USD 0,0012318 estimado). TASK-014 corrigiu a posição canônica v2. L3 parou na primeira chamada (USD 0,0007078 estimado), falso positivo NPC corrigido por TASK-015; não completou percurso. Conclusão L3 aceita e L4 autorizado até 17 chamadas/USD 0,15 estimados, entrada protegida da chave pendente. A experiência integral e Luna não foram aceitos. | [ ] | — |

Os nomes de TASK-012 agora são arquivos implementados opt-in. A alteração de
latência/custo é separada desta fase e foi implementada sob pedido explícito.

## 3. Alternatives

- **ALT-001**: Trocar novamente o modelo antes de tratar progressão. Não é a
  ordem vigente: PROG-ROUTE-B manda planejar primeiro.
- **ALT-002**: Reforçar somente o prompt ambiental. Insuficiente como desenho de
  campanha: não cria estado causal, condições de término ou cobertura de ações.
- **ALT-003**: Novo perfil opt-in B com núcleo determinístico existente.
  Aprovado em DEC-PROG-002; contrato detalhado em revisão.
- **ALT-004**: Validar exclusivamente no piloto v1. Menor integração inicial,
  porém evidência não transferível automaticamente à direção B.
- **ALT-005**: Roteiro fixo ou segundo LLM que planeja consequências. Fora do
  escopo/autoridade deste incremento; não necessário para o recorte proposto.

## 4. Dependencies

- **DEP-001**: Recorte e extensão B aprovados; ritmo A escolhido. O núcleo
  offline não pode ser tratado como comportamento jogável até TASK-012/013.
- **DEP-002**: Reutilizar o núcleo de resolução e as garantias de pausa/retomada,
  verificando sua composição; testes do fluxo anterior não provam o novo.
- **DEP-003**: Manter sessão zero, ficha e dados como frentes separadas. Nenhum
  fornecedor ou nova biblioteca é necessário para o planejamento offline.
- **DEP-004**: Nova admissão depende de contrato especificado, implementação
  verificada, experiência completa e julgamento humano. Não basta repetir HYP-006.

## 5. Files

Alterados agora: este plano, `issue-mvp-narrative-progression-1.md`,
`checklist-planejamento-campanha-hibrida.md` e `../PROMPT_RETOMADA_2026-09-06.md`.

Inspecionados sem edição: `../api/scene_resolution_default.py`,
`../api/scene_direction_catalog.py`, `../api/narrative_source_profile.py`,
`../api/narrative_source_input.py`, lançadores Luna/Groq e prompt ambiental.

Arquivos futuros documentais estão em TASK-005/007. Superfícies candidatas de
integração são produtor, cápsula, contexto, execução e persistência B; não há
autorização para editá-las nem promessa de que todas precisarão mudar.

## 6. Testing

Matriz proposta, ainda não executada; dados autorados antes de chamada real.

| ID | Trajetória/contraprova | Evidência exigida |
|---|---|---|
| TEST-001 | Pergunta direta sobre objetivo e ajuda, incluindo paráfrase sem repetir palavras do catálogo | Resposta pertinente de Mara, próxima decisão livre; ambiente sem resposta é negativo |
| TEST-002 | Espera seguida de diálogo e ação sobre consequência anterior | Estado novo causal persiste; não retorna à descrição inicial |
| TEST-003 | Sucesso e falha sobre o mesmo objetivo em sessões independentes | Recibos preservados, consequências distintas; falha não concede sucesso |
| TEST-004 | Pergunta de segredo e pedido repetido | Limite protegido com reação pertinente; sem silêncio cosmético ou punição automática |
| TEST-005 | Solução alternativa plausível e resolução antecipada | Método não textual fixo aceito dentro da cobertura; clímax pode ser antecipado |
| TEST-006 | Preservação, recuperação parcial e perda/abandono | Três trajetórias completas com epílogos distintos, sem reset ou gancho compulsório |
| TEST-007 | Pausa antes/depois do RNG, restart, reconexão, duplo clique e replay | Mesma operação/recibo/preparação, sem efeito parcial, nova rolagem ou commit duplicado |
| TEST-008 | Prosa omite consequência mas devolve ID correto; prosa inventa efeito extra | Falha identificada; não contar schema/IDs como êxito semântico |
| TEST-009 | Mesmo pacote em adaptadores falsos de formatos suportados | Mesma autoridade, visibilidade, expectativas e versão, sem relaxamento por provedor |

Implementação seguinte: continuar pelos testes B afetados; ampliar para
persistência/transporte conforme risco e só depois de focados passarem. Não
reexecutar suites históricas congeladas para validar edição documental.
Esta etapa verifica Markdown, links locais, estados/tarefas e hashes dos arquivos
protegidos. Não alega execução de TEST-001–009.

Verificação técnica posterior em 29/09: TASK-012 passou por P/K/H real com
adaptador falso, SQLite schema v4, reinício, reconexão, replay sem RNG/geração,
dois retries H encadeados, rollback de entrega e evento, CAS concorrente e
reconstrução com hash. Os oito CAMP-EVAL-01–08 e nove contraprovas do protocolo
foram exercitados offline nos limites descritos no relatório ligado acima.
70 testes focados do incremento e 288 testes v1/persistência/cena passaram.
Smoke HTTP loopback deu 200. O amplo diagnóstico não ficou verde: 2.608 testes
passaram antes de `wrong_session`/sidecars WAL no Windows; outro grupo histórico
tem hash congelado de schema de ator. Não usar tais falhas como prova de
regressão B, nem corrigi-las oportunisticamente. TEST-001–009 seguem sem
aceitação de produto e sem demonstração por Luna.

Verificação documental de 29/09/2026: diff desta etapa inspecionado contra o
conteúdo anterior (arquivos ainda não rastreados pelo Git); oito seções, sete
campos de front matter e oito links locais válidos; 24 perguntas CAMP continuam
abertas, três tarefas preparatórias concluídas e cinco pendentes. Os hashes de
oito arquivos amostrados de código, prompt e evidência permaneceram idênticos.
Nenhuma suíte de runtime foi executada: houve somente edição documental.

## 7. Risks & Assumptions

- **RISK-001**: Confundir falha do recorte com incapacidade universal do Luna.
  Preservar o veredicto HYP-006 e testar nova hipótese separadamente.
- **RISK-002**: Fazer o narrador apenas parafrasear um roteiro. Catalogar efeitos
  e limites, não falas prontas, caminhos únicos ou cenas obrigatórias.
- **RISK-003**: Campo B genérico virar canal de mutação arbitrária. Exigir contrato
  tipado, origem servidor, versão, visibilidade e commit; schema ainda pendente.
- **RISK-004**: Repetir o mesmo effect_key sem avanço real. Comparar estado,
  histórico e realização narrativa, não apenas a presença do identificador.
- **RISK-005**: Recorte de um conflito ser estreito demais para a experiência
  pretendida. DEC-PROG-001 requer escolha de produto; não expandir por iniciativa.
- **ASSUMPTION-001**: Reaproveitar Mara e Arquivo/Galeria reduz conteúdo novo,
  mas não comprova que o usuário prefira essa premissa. Está em proposta.

O checkpoint humano de ritmo foi atendido com a opção A. Não pedir novamente essa
decisão. TASK-012 está verificado tecnicamente; TASK-013 tem ensaio local autorado
pronto para julgamento de experiência, mas não permite admitir Luna. Novo gasto
live e aceitação narrativa exigem ação humana específica; preservar v1 e recusar
ativação incompleta.

Verificação incremental de 29/09: o rascunho de campanha continua inativo no
executor B v1. A seleção de 435 testes de campanha, resolução de cena e contratos
B anteriores passou. Três testes legados de bancos novos ainda esperavam schema 3
enquanto `SQLitePersistence.SCHEMA_VERSION` e testes de persistência já usam 4;
somente essas expectativas foram atualizadas. Nenhuma migração ou chamada live.

Verificação da implementação lateral de latência/custo:
[relatório](../evals/narrator/reports/luna-latency-cost-preparation-2026-09-29.md).

### Incremento de posição aprovado em 03/10/2026

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-014 | Opção A: posição canônica `record_location` versionada em novas sessões v2, projeção pública antes/depois, reconstrução/retomada v1 sem migração, testes de resgate atômico e oito percursos. 101 testes focados (incluindo preflight prospectivo) aprovados; regressão ampliada: 1.612 aprovados e a falha Windows histórica de sidecars. Relatório `../evals/narrator/reports/campaign-record-location-v2-2026-10-03.md`. | [x] | 2026-10-03 |

A lacuna citada historicamente em TASK-013 foi corrigida offline por TASK-014.
TASK-013 e CAMP-24 permanecem abertos por avaliação narrativa/experiência, não
pela decisão de posição. L2 fica fechado, prompt/manifesto históricos intactos.
O usuário aprovou depois HYP-007-L3: até 17 chamadas Luna low, teto estimado
adicional USD 0,15, com prompt/estado v2 e mesmos gates. Runner, preflight,
lançador e manifesto próprios prontos; 35 testes focados e preflight CLI de
17 turnos/zero chamadas passaram. Relatório de prontidão:
`../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l3-preflight-2026-10-03.md`.
Essa entrada foi realizada: L3 executou uma chamada e parou no gate de política,
com zero turnos completos e custo final estimado USD 0,0007078. A análise
reproduziu um falso positivo por ausência de NPCs canônicos no contexto do
detector; TASK-015 abaixo o corrige sem reescrever a evidência histórica.
Não pedir novamente a opção A ou orçamento L3. O novo lote prospectivo L4
exige autorização própria, e a experiência/admissão continuam pendentes.

### Correção local de atribuição e próximo checkpoint

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-015 | Repassar roster canônico de NPCs à política de campanha; reproduzir o texto L3 exato, preservar bloqueio de jogador/pronome sem antecedente/alias colidente e verificar commit/reconstrução/replay fake. 410 regressões passaram; sete testes específicos e seleção final de dez (sobrepostos). Relatório `../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l3-2026-10-03.md`. Não equivale a admissão narrativa ou validação semântica integral. | [x] | 2026-10-03 |

L3: gate fechado, hashes/registros originais intactos; conclusão técnica proposta
inconclusiva por falso positivo NPC, nenhum narrador admitido. L4 preparado
offline com mesmo prompt/estado v2, parâmetros e critérios, até 17 chamadas,
teto adicional **proposto** USD 0,15, sem retry/fallback. Manifesto separado de
21 arquivos, preflight de 17 turnos/zero chamadas e maior corpo 13.043 bytes;
live/paid false, sem janela de credencial. A próxima ação humana é aceitar ou
contestar a conclusão L3 e autorizar ou ajustar o novo gasto L4 (Sol high).
Após autorização: entrada segura (Sol low), execução e relatório de custo/gates.
O usuário respondeu em seguida "Aprovado. Continue": a conclusão delimitada
L3 foi aceita e o novo gasto L4 autorizado nos limites acima. Somente os flags
live/paid L4 foram ativados; manifesto/prompt/parâmetros preservados. A próxima
dependência é entrada protegida da chave no lançador externo L4 (Sol low),
depois observar execução, custo e experiência, sem nova pergunta de orçamento.
Não iniciar a próxima frente do MVP nem fechar CAMP-24 por esses testes.
A cobertura lexical de retirada descoberta nos testes está em
`observation-campaign-agency-vocabulary-1.md`; reportada sem implementação ou
prioridade automática, permanece limite da admissão futura.

## 8. Related Specifications / Further Reading

- [Problema confirmado](issue-mvp-narrative-progression-1.md)
- [Checklist CAMP-01–24](checklist-planejamento-campanha-hibrida.md)
- [Resolvedor e decisões aprovadas](architecture-scene-resolution-1.md)
- [Contrato do beat](../spec/spec-deterministic-scene-resolution.md)
- [Ponte B e limites](architecture-narrative-source-bridge-1.md)
- [Produtor B, especialmente REQ-013](feature-narrative-source-input-producer-1.md)
- [Ensaio manual rejeitado](../evals/narrator/reports/openai-luna-manual-observation-413d4983-2026-09-28.md)
- [Estado vigente](../PROMPT_RETOMADA_2026-09-06.md)
