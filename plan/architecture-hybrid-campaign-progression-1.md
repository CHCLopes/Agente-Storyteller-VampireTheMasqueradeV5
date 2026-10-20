---
goal: Planejar progressão e campanha híbrida mínima com Luna low prioritário e contratos portáveis
version: 1.0
date_created: 2026-09-29
last_updated: 2026-10-20
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
| TASK-013 | Ensaio isolado preparado e observado; admissão/experiência completa continuam abertas. L75 completou matriz técnica mas falhou auditoria qualitativa; L76–L82 interrompidos e preservados. L82 também revelou objetivo trocado e ação repetida no epílogo aceitos antes dos fixes locais. Não admitir Luna/default/CAMP-24 por lote verde. Decisão proposta A/B em hybrid-campaign-luna-validation-checkpoint-2026-10-20.md; histórico integral da antiga célula em hybrid-campaign-task013-historical-2026-10-20.md. Autorização contínua de testes <= USD 0.15 vigente, sem pedir aprovação financeira por lote. | [ ] | — |

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

### Checkpoint vigente — aceite delimitado L4 e prontidão L5 — 18/10/2026

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-016 | Registrar aceite humano delimitado L4 sem admissão; renovar manifesto prospectivo L5 com 22 arquivos pós-auditoria, incluindo segurança Host/Origin; bloquear drift/retry/fallback e preservar manifestos históricos. Passaram 15 testes L5 e seleção relacionada de 78 (inclui os 15); preflight CLI de 17 turnos sintéticos/zero chamadas reais e parser PowerShell válido. Custo USD 0, sem credencial ou launcher. Relatório de prontidão ligado abaixo. Não inclui execução paga nem aceitação da campanha. | [x] | 2026-10-18 |

O resultado L4 aceito foi duas chamadas, um turno completo e parada de política
R-05; USD 0,0014972 é estimativa histórica, não cobrança conferida. A reprodução
local da atribuição ambígua de pronome motivou o prompt v3 prospectivo já existente;
ele foi preservado, sem relaxar detector. Não há prova live de que resolve o caso.

Novo manifesto L5: `../evals/narrator/reports/hybrid-campaign-luna-l5-live-gate-2026-10-18.json`.
L4 e o manifesto L5 de 03/10 não foram reescritos. Os flags paid/live L5 estão
false. Proposta, ainda não aprovada: até 17 chamadas Luna low, teto estimado
adicional USD 0,15, 768 tokens de saída, 20.000 bytes por requisição, sem
retry/fallback. Primeiro obter autorização própria; somente depois entrada
protegida da chave em terminal externo e execução única. Nenhum saldo de lote
anterior é transferido. TASK-013/CAMP-24 e a admissão permanecem pendentes.

[Evidências, comandos e limitações da preparação](../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l5-readiness-2026-10-18.md).
As dependências descritas acima para L3/L4 são históricas e foram atendidas.
Posteriormente, em 18/10, o usuário declarou "Novo lote pago autorizado.
Continue", aprovando L5 nos limites acima. Somente os flags paid/live do novo
manifesto foram ativados, sem alterar os 22 hashes, prompt ou parâmetros.
O próximo checkpoint é a entrada protegida da chave no PowerShell externo L5;
não pedir orçamento novamente nem repetir L4. Nenhuma chamada foi iniciada
pela edição do gate. Ao fim da execução, apresentar custo e fechar live.

### Resultado L5 — 18/10/2026

L5 executou três chamadas, dois turnos completos; CAMP-EVAL-01 concluiu ajuda e
salvamento. Parou no primeiro R-03 de CAMP-EVAL-02 por política. Custo final
estimado USD 0,0022452, não cobrança confirmada. Os demais 14 slots não foram
executados nem ficam autorizados para repetição. Gate paid/live fechado, trava
atômica preservada; registros e prompt v3 intactos. O marcador de prontidão do
terminal ficou histórico e não significa que ainda aguarda credencial.

Reprodução offline: a obrigação R-03 é realizada, mas o detector genérico atribui
ao jogador uma ação social na construção de Mara "Ela ergue os olhos para você
e fala". Nomear Mara mantendo a construção não resolve; trocar apenas por
"Mara diz em voz baixa" passa localmente. Não mudar detector/prompt retrospectivo
ou contar o turno rejeitado como admitido. Proposta de conclusão: inconclusivo
por falso positivo NPC; nenhum narrador admitido. TASK-013/CAMP-24 continuam
abertos e exigem avaliação de experiência, não apenas estrutura ou ID correto.
33 testes focados de fechamento passaram; não é suíte integral verde.

[Resultado, reprodução e custo](../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l5-2026-10-18.md).
Próximo checkpoint: aceite ou contestação humana da conclusão delimitada;
posterior tratamento prospectivo do falso positivo sem reforma lexical geral,
novo orçamento, reabertura de lote ou admissão automática.

### Correção prospectiva e prontidão L6 — 18/10/2026

O usuário respondeu "continue", autorizando continuidade técnica, não aceite
formal narrativo/produtual. A revisão automática recusou registrar essa
inferência; aceite explícito L5 continua pendente. Não admitir narrador,
reclassificar turno rejeitado ou autorizar gasto adicional por essa resposta.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-017 | Corrigir apenas a atribuição da fala na construção local de olhar para o jogador em `api/scene_director_service.py::_mask_known_npc_gaze_report`. Reprodução exata L5, sujeito NPC comprovado, pronomes/aliases/aspas/coordenações indevidas bloqueados; commit/reinício/replay e rollback de promessa indevida verificados. 31 testes novos e seleção final relacionada de 754 aprovados. Nenhuma admissão live retroativa ou mudança canônica/RNG. | [x] | 2026-10-18 |
| TASK-018 | Preparar runner, preflight, lançador e manifesto próprios HYP-007-L6 com mesmo prompt v3/17 turnos, 22 hashes pós-correção e flags paid/live false; 12 testes L6 e 16 de isolamento histórico L5 na checagem conjunta de 59 com os 31 de atribuição (sobrepostos à seleção ampliada). CLI de 17 turnos/zero chamadas, corpo máximo 13.415 bytes, AST PowerShell válido, custo USD 0. Não inclui gasto ou aceite narrativo. | [x] | 2026-10-18 |

A prova de sujeito cobre a construção observada, não linguagem arbitrária.
O helper mascara somente o verbo de relato comprovado do NPC, preservando
offsets, texto original, fala citada e verificação das demais ações. Antecedente
incerto/aliases pessoais no quadro de objeto invalidam a prova. Sem resolver
todos os itens da observação lexical separada. O manifesto L5 executado fica
intacto e recusa a implementação corrigida; testes fake usam manifesto isolado
em diretório temporário, seguindo o padrão L2/L3.

Próximo checkpoint: aceite explícito delimitado L5 e novo orçamento L6,
até 17 chamadas Luna low e USD 0,15
estimados adicionais, 768 tokens/20.000 bytes, sem retry/fallback. O lote segue
fechado até autorização específica; depois entrada protegida no Windows
Terminal identificado. Sem transferência de slots L5. TASK-013/CAMP-24 abertos.
[Evidência de correção e prontidão L6](../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l6-readiness-2026-10-18.md).

### Autorização explícita L6 e aceite L5 — 18/10/2026

O usuário declarou "L5 foi aceito, assim como o teto de L6" e esclareceu que
"continue"/"prossiga" aprovam a proposta anterior. L5 está aceito somente na
conclusão delimitada inconclusiva, sem admissão. L6 autorizado nos limites já
propostos: 17 chamadas Luna low, USD 0,15 estimados adicionais, 768 tokens e
20.000 bytes por chamada, sem retry/fallback. Somente os flags paid/live L6
foram ativados, sem mudar hashes, código ou prompt. Não pedir novamente aceite
ou teto. Próxima dependência: entrada protegida em Windows Terminal externo
identificado após preflight; executar uma vez, relatar custo e fechar live.
Esta atualização substitui as pendências históricas de aceite/orçamento acima.
TASK-013/CAMP-24 continuam abertos e nenhum narrador está admitido.

### Resultado L6 e preparação delimitada L7 — 18/10/2026

L6: uma chamada, zero turnos completos, parada no R-01/CAMP-EVAL-01. Estimativa
USD 0,0007156, sem cobrança conferida. Hash de records confere com summary;
gate paid/live fechado e trava preservada. Não repetir ou transferir 16 slots.
Reprodução: a pergunta tem 19 palavras, recusada por `scene_player_prompt_too_long`
contra limite existente de 15; `_realizes_rule` passa. Mesma narrativa com q
curto aberto passa offline. Não é falso positivo de agência, nem prova de que
Luna completaria o resto. L6 não alcançou o ponto R-03 corrigido após L5.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-019 | Diagnosticar a rejeição real L6 sem alterar records/prompt v3/validador; preparar prompt v4 explicitando q aberto único/15 palavras e L7 separado com mesmo alvo/corpus/limites, 22 hashes e flags paid/live false. 13 testes focados e seleção de 127 relacionados aprovados (sobrepostos); CLI 17 turnos/zero chamadas, corpo máximo 13.614 bytes, AST PowerShell válido. Custo preparação USD 0; não inclui gasto, aceite narrativo ou admissão. | [x] | 2026-10-18 |

Conclusão delimitada proposta: L6 inconclusivo para a campanha integral por
rejeição de q e lacuna de instrução, nenhum narrador admitido. Próxima proposta
humana: aceitar a conclusão e autorizar L7 até 17 chamadas/USD 0,15 estimados
adicionais, sem retry/fallback. Continue/prossiga aprova a proposta nos limites
apresentados; não exigir frase ritual. L7 segue fechado até essa aprovação.
Sem novo gate ou critério de produto, sem elevar limite para acomodar a saída.
TASK-013/CAMP-24 continuam abertos.
[Resultado L6, diagnóstico e prontidão L7](../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l6-2026-10-18.md).

### Autorização L7 e aceite delimitado L6 — 18/10/2026

O usuário respondeu "prossiga" à proposta delimitada imediatamente anterior.
Pela convenção explícita registrada em AGENTS.md, a conclusão L6 foi aceita e
L7 autorizado: até 17 chamadas Luna low, USD 0,15 estimados adicionais, 768
tokens/20.000 bytes, sem retry/fallback. Somente paid/live L7 ativados, sem
mudar prompt v4, hashes, código ou critérios. Não pedir novamente orçamento ou
aceite. Próxima dependência: chave em terminal externo L7 identificado após
preflight; observar execução única, custo e fechamento live. Não reabrir L6.
Nenhum narrador admitido; TASK-013/CAMP-24 e MVP continuam abertos.

### Resultado L7, pergunta possessiva e preparação L8 — 18/10/2026

L7 executou três chamadas/dois turnos: ajuda e salvamento CAMP-EVAL-01, depois
parada em R-03/CAMP-EVAL-02. USD 0,0022832 estimados, não cobrança conferida.
Falso positivo de q com 10 palavras: "Qual é a sua próxima ação diante do
risco imediato?" recusada como não acionável; remover apenas artigo passa.
Não é falha do limite de 15 de L6. Registros/manifestos executados preservados,
gate L7 fechado, sem repetição ou transferência dos 14 slots restantes.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-020 | Corrigir forma possessiva com artigo por fullmatch em `api/scene_director_service.py::_validate_player_prompt`, sem relaxar teto de 15 ou autorizar NPC/instrução/segunda frase/menu. Resposta exata L7 e commit/reinício/replay fake passam; pergunta sobre decisão de Mara deixa estado/fonte intactos. 22 testes novos e regressão final de 819 aprovados, incluindo casos de tamanho com contagens explícitas. Sem reclassificação live. | [x] | 2026-10-18 |
| TASK-021 | Preparar runner/preflight/lançador/manifesto próprios L8, mesmo prompt v4 e parâmetros, 22 hashes e flags paid/live false. 12 testes L8 e 34 junto à reprodução (sobrepostos à seleção ampliada); CLI 17 turnos/zero chamadas, corpo 13.614 bytes, AST PowerShell válido. Custo preparação USD 0; não inclui autorização paga, aceitação narrativa ou admissão. | [x] | 2026-10-18 |

Testes L6/L7 agora usam manifesto temporário isolado, como L2/L3/L5; testes
dedicados exigem hashes históricos intactos e rejeição do runtime corrigido.
Não reescrever evidência executada para obter verde. Observação de linguagem
de estado em prosa está em `observation-campaign-state-language-1.md`, sem
implementação, requisito novo, prioridade ou gate retroativo.

Conclusão delimitada proposta: L7 inconclusivo para a campanha integral por
falso positivo de pergunta acionável, nenhum narrador admitido. Próxima proposta:
aceitar a conclusão e autorizar L8 até 17 chamadas Luna low/USD 0,15 estimados
adicionais, sem retry/fallback. Continue/prossiga aprova nos limites apresentados;
até lá L8 fechado. TASK-013/CAMP-24 permanecem abertos.
[Resultado, correção e prontidão](../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l7-2026-10-18.md).

### Autorização L8 e esclarecimento da fila — 18/10/2026

O usuário aprovou por "Prossiga", solicitando informar a fila antes de começar.
Foi explicado antes de ativar/executar: L8 é uma bateria paga preparada, oito
percursos e 17 chamadas; se passar, resta julgamento humano de narrativa/UX e
ensaio a delimitar. Não há número fixo de tentativas futuras ou de baterias do
MVP inteiro, nem autorização de lote posterior. Contraprovas/regressões offline
não são novos lotes pagos. Demais incrementos permanecem na ordem aprovada.

L7 aceito somente na conclusão delimitada inconclusiva, sem narrador admitido.
L8 autorizado até 17 chamadas Luna low/USD 0,15 estimados adicionais, 768 tokens
e 20.000 bytes por chamada, sem retry/fallback. Somente flags paid/live L8
ativados; código, prompt v4 e hashes intactos. Próxima dependência: chave em
Windows Terminal L8 identificado após preflight. Não pedir novo aceite/teto.
Depois: execução única, custo/gates/resultado e fechamento live.

### Resultado L8, condicional e preparação L9 — 18/10/2026

Autorização posterior: "continue" aceita a conclusão delimitada L8 inconclusiva
por falso positivo de condicional, sem narrador admitido, e autoriza L9 até
17 chamadas Luna low e USD 0,15 estimados adicionais, sem retry/fallback.
Flags paid/live L9 ativados; demais limites e hashes preservados. Entrada
protegida da chave é a próxima dependência humana, não novo aceite/orçamento.

L8 encerrou após uma chamada, zero turnos, primeiro R-01/CAMP-EVAL-01.
USD 0,0007162 estimados, não cobrança confirmada. Falso positivo: o infinitivo
com clítico em "Se você precisar movê-lo" foi lido como movimento executado.
Gate L8 fechado e trava/records/manifesto preservados; não repetir 16 slots.

| Task | Description | Completed | Date |
|---|---|---|---|
| TASK-022 | Corrigir só a condicional delimitada de necessidade com infinitivo/clítico em `_validate_declared_player_actions`, preservando texto/offsets e recusa de ações afirmativas ou posteriores. Resposta exata L8 e commit/reinício/replay fake passam; movimento indevido não deixa estado/fonte/entrega parcial. 18 testes novos e regressão final de 850 aprovados. Sem reclassificar L8 ou alterar RNG/cânone. Limitação separada de pronome após alias conservada e documentada. | [x] | 2026-10-18 |
| TASK-023 | Preparar runner/preflight/lançador/manifesto L9 separados, mesmo prompt v4/alvo/corpus/limites, 22 hashes e paid/live false. 12 testes L9 e 43 focados junto à reprodução/histórico L8 (sobrepostos à seleção ampliada); CLI 17 turnos/zero chamadas, corpo 13.614 bytes, AST PowerShell válido. Custo adicional USD 0; não inclui orçamento, aceitação narrativa ou admissão. | [x] | 2026-10-18 |

Testes L8 seguem padrão de manifesto temporário isolado e teste dedicado de
hash preservado/recusa do runtime novo pelo manifesto executado. Não reescrever
evidência histórica para obter verde. O escopo não inclui resolver todo pronome
ou condição de linguagem natural; o bloqueio de alias/pronome continua conservador.

Conclusão proposta: L8 inconclusivo por falso positivo de ação em condicional,
nenhum narrador admitido. Próxima proposta: aceitar conclusão delimitada e
autorizar L9 até 17 chamadas Luna low/USD 0,15 estimados adicionais, sem
retry/fallback. Continue/prossiga aprova nos limites apresentados; L9 fechado
até lá. Não garantir quantidade de tentativas futuras. TASK-013/CAMP-24 abertos.
[Resultado, correção e prontidão](../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l8-2026-10-18.md).

### Resultado L9 e preparação L10 — 18/10/2026

Autorização posterior: "Continue" aceita a conclusão delimitada L9 e autoriza
L10 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo prompt v4 e
limites, sem retry/fallback/admissão automática. Flags paid/live ativados;
hashes preservados. Próxima dependência humana: chave protegida no terminal.

L8 aceito e L9 autorizado por continue. L9 executou 12 chamadas/11 turnos,
cinco percursos concluídos; parada R-07/CAMP-EVAL-06 por falso positivo nominal
partes/partir. USD 0,0097762 estimados, não cobrança. Gate L9 fechado, trava e
histórico preservados; 07/08 não alcançados. Nenhum narrador admitido.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-024 | Corrigir apenas leitura depart de partes no quadro entre as partes preservadas em api/scene_director_service.py. Oito testes novos: nominal, partida real, R-07, rollback e replay/reinício sem nova geração/RNG. Não reclassificar live; registrar ressalvas narrativas R-01/R-07 no relatório L9. | [x] | 2026-10-18 |
| TASK-025 | Preparar scripts e manifesto L10 separados, 22 hashes, paid/live false, mesmo prompt v4/alvo/limites, teto adicional proposto USD 0,15/17 chamadas. 12 testes L10 e 33 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.614 bytes e AST válido. Sem autorização, chave, lançador ou chamada live L10. | [x] | 2026-10-18 |

Conclusão L9 inconclusiva integral e orçamento L10 são proposta delimitada;
continue/prossiga aprova ambos. TASK-013/CAMP-24 e MVP permanecem abertos.
Regressão ampliada relacionada: 871 aprovados, um aviso preexistente, XML
eval-results/hyp-007-l10-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L10 e preparação L11 — 18/10/2026

Autorização posterior: Continue aceita a conclusão delimitada L10 e autoriza
L11 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo prompt v4,
sem retry/fallback/admissão automática. Flags paid/live ativados; hashes e
limites preservados. Próxima dependência humana: chave protegida no terminal.

L9 aceito e L10 autorizado por Continue. L10 uma chamada/zero turnos,
USD 0,0007104 estimados, não cobrança; parada no primeiro R-01 por falso
positivo de decisão pendente. Gate fechado, trava e originais preservados.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-026 | Corrigir apenas quadro até que + jogador conhecido + decida como proceder + fronteira em api/scene_director_service.py. Dez testes novos: exato L10, decisão/ação real, aliases, R-01, rollback/replay/reinício sem nova geração/RNG. 58 focados de política aprovados; não reclassificar resultado live. | [x] | 2026-10-18 |
| TASK-027 | Preparar runner/preflight/lançador/manifesto L11 separados e fechados, mesmo v4/alvo/corpus/limites e 22 hashes. 12 testes L11 e 35 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15 sem retry/fallback; sem chave/terminal/chamada live L11. | [x] | 2026-10-18 |

Conclusão L10 inconclusiva e orçamento L11 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada 894 aprovada, um aviso preexistente; XML
eval-results/hyp-007-l11-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L11 e preparação L12 — 18/10/2026

Autorização posterior: Continue aceita conclusão delimitada L11 e autoriza
L12 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo prompt v4,
sem retry/fallback/admissão automática. Flags paid/live ativados; hashes e
limites preservados. Próxima dependência humana: chave protegida no terminal.

L10 aceito e L11 autorizado por Continue. Seis chamadas/cinco turnos,
CAMP-EVAL-01 concluído, parada no R-06/02; USD 0,0052376 estimados, não cobrança.
Falso positivo avanço ambiental, gate L11 fechado, trava e histórico preservados.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-028 | Corrigir somente atribuição advance de antes que a umidade avance mais com fronteira. Oito testes novos, 44 focados de política aprovados; exato R-06, ações indevidas/rollback/replay/reinício sem nova geração/RNG. Não reclassificar live. | [x] | 2026-10-18 |
| TASK-029 | Preparar scripts/manifesto/testes L12 separados, 22 hashes e paid/live false, mesmo v4/alvo/limites. 12 testes L12/33 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15 sem retry/fallback; sem terminal/chave/chamada L12. | [x] | 2026-10-18 |

Conclusão L11 inconclusiva e orçamento L12 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido; TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada: 915 aprovados, um aviso preexistente; XML
eval-results/hyp-007-l12-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L12 e preparação L13 — 18/10/2026

Autorização posterior: prossiga aceita conclusão delimitada L12 e autoriza
L13 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo prompt v4,
sem retry/fallback/admissão automática. Flags paid/live ativados; hashes e
limites preservados. Próxima dependência humana: chave protegida no terminal.

L11 aceito e L12 autorizado por Continue. Uma chamada/zero turnos, parada
R-01/01, USD 0,0007374 estimados; falso positivo de estado do objeto. L12
fechado/histórico preservado, sem retry/fallback ou reclassificação live.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-030 | Corrigir apenas remain/permaneca no quadro evitando que o registro permaneça exposto ao risco atual com fronteira. Oito testes novos, 52 focados de política aprovados; exato R-01/espera real/rollback/replay/reinício sem geração/RNG extra. Fragilidade lexical registrada sem refatoração geral. | [x] | 2026-10-18 |
| TASK-031 | Preparar scripts/manifesto/testes L13 separados e fechados, 22 hashes, mesmo v4/alvo/limites. 12 testes L13/33 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15 sem retry/fallback; sem chave/terminal/chamada L13. | [x] | 2026-10-18 |

Conclusão L12 inconclusiva e orçamento L13 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada 936 aprovada, um aviso preexistente; XML
eval-results/hyp-007-l13-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L13 e preparação L14 — 18/10/2026

Autorização posterior: prossiga aceita conclusão delimitada L13 e autoriza
L14 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo prompt v4,
sem retry/fallback/admissão automática. Flags paid/live ativados; hashes e
limites preservados. Próxima dependência humana: chave protegida no terminal.

L12 aceito e L13 autorizado por prossiga. Três chamadas/dois turnos, resgate
intacto concluído; parada R-03/02, USD 0,0022426 estimados. Gate L13 fechado,
trava/histórico preservados. Falso positivo de atribuição atmosférica.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-032 | Corrigir apenas close/fechar no quadro explícito o Arquivo parece se fechar ao redor da bancada baixa com fronteira. Oito testes novos/60 focados de políticas aprovados, exato R-03/ações reais/rollback/replay/reinício sem RNG/geração extra. Sem reclassificar live. | [x] | 2026-10-18 |
| TASK-033 | Preparar scripts/manifesto/testes L14 separados e fechados, mesmo v4/alvo/limites/22 hashes. 12 testes L14/33 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15, sem retry/fallback; sem terminal/chave/chamada L14. | [x] | 2026-10-18 |

Conclusão L13 inconclusiva e orçamento L14 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada 957 aprovada, um aviso preexistente; XML
eval-results/hyp-007-l14-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L14 e preparação L15 — 18/10/2026

Autorização posterior: Continue aceita conclusão delimitada L14 e autoriza
L15 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo prompt v4,
sem retry/fallback/admissão automática. Flags paid/live ativados; hashes e
limites preservados. Próxima dependência humana: chave protegida no terminal.

L13 aceito e L14 autorizado por prossiga. Seis chamadas/cinco turnos, resgate
intacto concluído, parada R-06/02; USD 0,0051728 estimados. Gate L14 fechado,
trava/histórico preservados. Lacuna lexical da realização parcial.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-034 | Acrescentar frase explícita o que ainda permanece legível é salvo ao grupo lexical de parcialidade R-06 em api/campaign_source_profile.py; reconhecer continua no guard existente de estado contraditório. Seis testes novos/33 focados de perfil/integração/trajetórias aprovados, exato R-06/contradição/rollback/replay/reinício sem RNG/geração extra. Sem reclassificar live. | [x] | 2026-10-18 |
| TASK-035 | Preparar scripts/manifesto/testes L15 separados/fechados, mesmo v4/alvo/limites/22 hashes. 12 testes L15/31 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15, sem retry/fallback; sem terminal/chave/chamada L15. | [x] | 2026-10-18 |

Conclusão L14 inconclusiva e orçamento L15 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada 976 aprovada, um aviso preexistente; XML
eval-results/hyp-007-l15-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L15 e preparação L16 — 18/10/2026

Autorização posterior: Prossiga aceita conclusão delimitada L15 e autoriza
L16 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo prompt v4,
sem retry/fallback/admissão automática. Flags paid/live ativados; hashes e
limites preservados. Próxima dependência humana: chave protegida no terminal.

L14 aceito e L15 autorizado por Continue. Três chamadas/dois turnos, resgate
intacto completo, parada R-03/02; USD 0,0022494 estimados. L15 fechado/trava/
histórico preservados, sem repetição. Falso positivo de escolha futura.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-036 | Corrigir apenas ao que + jogador conhecido + decidir fazer + fronteira na política de decisões pendentes. Oito testes novos/68 focados de políticas aprovados, exato R-03/ações reais/rollback/replay/reinício sem geração/RNG extra. Sem reclassificar live. | [x] | 2026-10-18 |
| TASK-037 | Preparar scripts/manifesto/testes L16 separados/fechados, mesmo v4/alvo/limites/22 hashes. 12 testes L16/33 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.614 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15 sem retry/fallback, sem terminal/chave/chamada L16. | [x] | 2026-10-18 |

Conclusão L15 inconclusiva e orçamento L16 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada 997 aprovada, um aviso preexistente; XML
eval-results/hyp-007-l16-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L16 e hipótese v5/L17 — 18/10/2026

Autorização posterior: Continue aceita conclusão delimitada L16 (violação
terminal real/Luna não admitido v4) e autoriza hipótese L17/v5 até 17 chamadas
Luna low/USD 0,15 estimados adicionais, mesmos critérios/limites, sem retry/
fallback/admissão automática. Flags paid/live ativados; hashes preservados.
Próxima dependência humana: chave protegida no terminal.

L15 aceito/L16 autorizado por Prossiga. Seis chamadas/cinco turnos, resgate
intacto completo, parada R-06/02; USD 0,0052150 estimados. Violação real de q
terminal, não falso positivo. Gate fechado/trava/histórico preservados.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-038 | Comprovar violação terminal L16 com cinco testes novos: q não vazio recusado em partial, rejeição atômica wet/revisão três/sem entrega, contrafactual offline q vazio e replay sem geração/RNG extra. Sem relaxar validador ou reclassificar live. | [x] | 2026-10-18 |
| TASK-039 | Preparar hipótese prompt v5/L17 separada/fechada: só regra q prioriza outcome/partial terminal. Mesmo alvo/corpus/limites/22 hashes; CLI 17 sintéticos/zero chamadas/13.952 bytes e AST válido. Teto adicional proposto 17 chamadas/USD 0,15 sem retry/fallback, sem chave/terminal/chamada L17. Preservar v4/manifesto L16 válido fechado. | [x] | 2026-10-18 |

Proposta: aceitar violação real terminal L16/Luna não admitido no perfil v4 e
autorizar L17/v5 nos limites acima. Continue/prossiga aprova ambos. TASK-013/
CAMP-24/MVP abertos, sem admissão ou nova arquitetura por arrasto.

### Resultado L17 e preparação L18 — 18/10/2026

Autorização posterior: Prossiga aceita conclusão delimitada L17 e autoriza
L18/v5 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmos critérios/
limites, sem retry/fallback/admissão automática. Flags paid/live ativados;
hashes/prompt v5 preservados. Próxima dependência humana: chave protegida.

L16 aceito e L17/v5 autorizado por Continue. Seis chamadas/cinco turnos, resgate
intacto completo, parada R-06/02; USD 0,0051470 estimados. q terminal vazio
observado no caso, sem prova geral de eficácia v5. Falso positivo de retirada
clítica do registro, gate fechado/trava/histórico preservados.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-040 | Corrigir somente withdraw/afastando-o da infiltração com antecedente local retira o registro e fronteiras. Nove testes novos/82 focados de política/terminal aprovados, exato R-06/antecedente/ações reais/rollback/replay/reinício sem geração/RNG extra. Sem reclassificar live. | [x] | 2026-10-18 |
| TASK-041 | Preparar scripts/manifesto/testes L18 separados/fechados, mesmo v5/alvo/limites/22 hashes. 12 testes L18/48 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.952 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15 sem retry/fallback, sem chave/terminal/chamada L18. Preservar manifestos executados L16/L17 com testes temporários isolados. | [x] | 2026-10-18 |

Conclusão L17 inconclusiva e orçamento L18 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada 1.038 aprovada, um aviso preexistente; XML
eval-results/hyp-007-l18-readiness-2026-10-18.xml. Não é suíte integral verde.

### Resultado L18 e preparação L19 — 18/10/2026

Autorização posterior: continue aceita conclusão delimitada L18 e autoriza
L19/v5 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmos critérios/
limites, sem retry/fallback/admissão automática. Flags paid/live ativados;
hashes/prompt v5 preservados. Próxima dependência humana: chave protegida.

L17 aceito/L18 autorizado por Prossiga. Sete chamadas/seis turnos, 01/02
completos, parada R-03/03; USD 0,0061390 estimados. Gate fechado/trava/histórico
preservados. Falso positivo de autoria da fala do NPC.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-042 | Acrescentar prova anterior completa NPC conhecido acompanha as marcas de umidade sem tocar no objeto no mask existente de olhar/fala. Dez testes novos/85 focados aprovados, exato R-03/jogador/coerção/citação/rollback/replay/reinício sem geração/RNG extra. Não reclassificar live. | [x] | 2026-10-18 |
| TASK-043 | Preparar scripts/manifesto/testes L19 separados/fechados, mesmo v5/alvo/limites/22 hashes. 12 testes L19/35 focados conjuntos aprovados; CLI 17 sintéticos/zero chamadas/13.952 bytes, AST válido. Teto adicional proposto 17 chamadas/USD 0,15 sem retry/fallback, sem chave/terminal/chamada L19. Manifesto histórico L18 preservado/testes temporários isolados. | [x] | 2026-10-18 |

Conclusão L18 inconclusiva e orçamento L19 são proposta delimitada; continue/
prossiga aprova ambos. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Regressão ampliada relacionada 1.061 aprovada, um aviso preexistente; XML
eval-results/hyp-007-l19-readiness-2026-10-18.xml. Não é suíte integral verde.

### Encerramento L19 — falha de provedor, 18/10/2026

Estado vigente de TASK-013: L18 aceito por continue; L19/v5 autorizado e executado,
uma chamada/zero turnos, http_429/campaign_source_provider_failure. Sem resposta
narrativa; não é reprovação narrativa. Custo final indisponível por falta de usage,
não USD zero. Gate fechado/trava preservada, sem retry/fallback/novo lote.
As propostas/pendências L18/L19 acima são históricas. TASK-013/CAMP-24 permanecem
abertos, nenhum narrador admitido. Humano deve verificar saldo/limites no painel;
não ampliar gastos automaticamente. Relatório L19 contém evidência e hashes.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-044 | Encerrar L19, conferir hashes e reproduzir custo indisponível, fechar paid/live e preservar trava; registrar HTTP 429 sem inferir causa ou qualidade narrativa. Verificação focada em eval-results/hyp-007-l19-closure-2026-10-18.xml. Nenhuma nova inferência. | [x] | 2026-10-18 |

### Continuidade L20 após limite externo — 18/10/2026

Humano informou limite anterior USD 0,05 removido e pediu continuidade.
L19 preservado/inconclusivo, custo indisponível; causa externa informada pelo
humano, não discriminada no registro HTTP. TASK-013 continua aberto, agora com
L20 separado verificado/autorizado nos mesmos limites, dependente de chave.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-045 | Preparar evaluate/preflight/run_hybrid_campaign_luna_l20, manifesto e testes isolados; alterar somente identidade, preservar v5/runtime e L19. 34 testes focados aprovados/um aviso preexistente; CLI 17 sintéticos/zero chamadas/13.952 bytes, 22 hashes e AST válidos. Gates ativados para até 17 chamadas/USD 0,15 estimados sem retry/fallback/admissão; entrada protegida ainda necessária. XML eval-results/hyp-007-l20-readiness-2026-10-18.xml. | [x] | 2026-10-18 |

### Resultado L20 e preparação L21 — 18/10/2026

L20 três chamadas/dois turnos, CAMP-EVAL-01 completo/intacto. Parada R-03/02
por movimento da infiltração atribuído ao jogador. USD 0,0023168 estimados,
não cobrança; gate fechado/trava/histórico mantidos. TASK-013/CAMP-24 abertos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-046 | Corrigir apenas gerúndio aproximando com sujeito infiltração/predicado/destino explícitos em api/scene_director_service.py. Nove regressões novas e 39 focados aprovados: caso exato, troca de ator, ações posteriores, commit/rejeição atômica, reinício/replay sem RNG/geração extra. Não reclassificar live. | [x] | 2026-10-18 |
| TASK-047 | Preparar scripts evaluate/preflight/run L21, manifesto/testes isolados fechados, mesmo v5/alvo/limites/22 hashes. 34 focados aprovados, CLI sintético zero chamadas e AST válido; XML hyp-007-l21-readiness-2026-10-18.xml. Sem chave/terminal/inferência L21. | [x] | 2026-10-18 |

Proposta delimitada: L20 inconclusivo integral/um percurso completo e L21 até
17 chamadas/USD 0,15 estimados adicionais, 768 tokens/20.000 bytes/60s, sem
retry/fallback/admissão. Continue/prossiga aprova ambos; até lá gate L21 fechado.
Nenhum narrador admitido. Relatório hybrid-campaign-luna-hyp-007-l20-2026-10-18.md.

### Autorização L21 — 18/10/2026

Prossiga aceita L20 inconclusivo integral/um percurso completo e autoriza
L21 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmos v5/limites,
sem retry/fallback/admissão. Preflight revalidado, zero chamadas/22 hashes.
Flags paid/live ativados. Entrada protegida da chave é a dependência humana;
após execução, observar artefatos/custo e fechar gate. TASK-013/CAMP-24 abertos.

### Resultado L21 e preparação L22 — 18/10/2026

L21 três chamadas/dois turnos, 01 completo/intacto. Parada R-03/02 por falso
positivo lexical de aviso, não agência. USD 0,0022768 estimados, não cobrança;
gate fechado/trava/histórico mantidos. L20 aceito. TASK-013/CAMP-24/MVP abertos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-048 | Reconhecer somente a ameaca agora e evidente como equivalente no grupo R-03 de api/campaign_source_profile.py. Oito testes novos, duas falhas reproduzidas antes da correção, 39 focados aprovados; negação/dano/ausência NPC/agência indevida, atomicidade/reinício/replay sem RNG/geração extra. Não reclassificar live. | [x] | 2026-10-18 |
| TASK-049 | Preparar scripts evaluate/preflight/run L22, manifesto/testes isolados fechados; mesmo v5/alvo/limites. 30 focados aprovados, 17 sintéticos/zero chamadas/13.952 bytes/22 hashes/AST válidos. XML eval-results/hyp-007-l22-readiness-2026-10-18.xml. Sem terminal/chave/chamada L22. | [x] | 2026-10-18 |

Proposta: L21 inconclusivo integral/um percurso completo e L22 até 17 chamadas/
USD 0,15 estimados adicionais, mesmo v5/Luna low/768 tokens/20.000 bytes/60s,
sem retry/fallback/admissão. Continue/prossiga aprova ambos; até lá gate fechado.
Nenhum narrador admitido. Relatório hybrid-campaign-luna-hyp-007-l21-2026-10-18.md.

### Autorização L22 — 18/10/2026

Prossiga aceita L21 inconclusivo integral/um percurso completo e autoriza
L22 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo v5/limites,
sem retry/fallback/admissão. Preflight revalidado, zero chamadas/22 hashes.
Gates paid/live ativados. Próxima dependência: chave protegida no lançador
externo; depois observar artefatos/custo e fechar gate. TASK-013/CAMP-24 abertos.

### Resultado L22 e preparação L23 — 18/10/2026

L22 seis chamadas/cinco turnos, 01 completo/intacto e parada R-06/02 por
falso positivo de agência ambiental. USD 0,0052084 estimados, não cobrança;
gate fechado/trava/histórico mantidos. L21 aceito. TASK-013/CAMP-24/MVP abertos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-050 | Tornar mais opcional na exceção antes que a umidade avance em _action_signature_matches de api/scene_director_service.py, preservando sujeito/fronteira. Oito regressões novas, duas falhas reproduzidas antes da correção, 43 focados aprovados; troca de ator/ação posterior/parcialidade/atomicidade/reinício/replay sem RNG/geração adicional. Não reclassificar live. | [x] | 2026-10-18 |
| TASK-051 | Preparar evaluate/preflight/run L23, manifesto/testes isolados fechados, mesmo v5/alvo/limites/22 hashes. 33 focados aprovados; CLI 17 sintéticos/zero chamadas/13.952 bytes/AST válido. XML eval-results/hyp-007-l23-readiness-2026-10-18.xml. Sem chave/terminal/chamada L23. | [x] | 2026-10-18 |

Proposta: L22 inconclusivo integral/um percurso completo e L23 até 17 chamadas/
USD 0,15 estimados adicionais, Luna low/v5/768 tokens/20.000 bytes/60s, sem retry/
fallback/admissão. Continue/prossiga aprova ambos; até lá gate fechado.
Nenhum narrador admitido; relatório hybrid-campaign-luna-hyp-007-l22-2026-10-18.md.

### Autorização L23 — 18/10/2026

Continue aceita L22 inconclusivo integral/um percurso completo e autoriza
L23 até 17 chamadas Luna low/USD 0,15 estimados adicionais, mesmo v5/limites,
sem retry/fallback/admissão. Preflight revalidado, zero chamadas/22 hashes.
Gates paid/live ativados. Próxima dependência: chave protegida no lançador
externo; depois observar artefatos/custo e fechar gate. TASK-013/CAMP-24 abertos.

### Resultado L23 e hipótese L24/v6 — 18/10/2026

L23 quatro chamadas/três turnos, 01 completo/intacto; parada R-03B/02 por
silêncio imposto após Espero: violação real, não flexibilizar gate. USD 0,0032892
estimados, não cobrança; gate fechado/trava/histórico mantidos. L22 aceito.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-052 | Provar rejeição correta da amostra L23, sem mudar runtime. Seis regressões novas/72 focados aprovados; contraprova de espera literal, R-03B atômico/reinício/replay sem geração/RNG adicional. XML eval-results/hyp-007-l23-review-2026-10-18.xml. | [x] | 2026-10-18 |
| TASK-053 | Preparar prompt hybrid-campaign-source-v6.md explicitando espera sem silêncio/imobilidade não declarados e scripts/manifesto/testes L24 separados/fechados; mesmos alvo/limites/22 hashes. 31 focados aprovados, 17 sintéticos/zero chamadas/14.457 bytes/AST válido. XML eval-results/hyp-007-l24-readiness-2026-10-18.xml. Sem chave/terminal/inferência. | [x] | 2026-10-18 |

Proposta: L23 violação real de agência/inconclusivo integral/um percurso completo
e L24/v6 até 17 chamadas/USD 0,15 estimados adicionais, Luna low/768 tokens/
20.000 bytes/60s, sem retry/fallback/admissão. Continue/prossiga aprova ambos;
até lá gate fechado. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
Relatório hybrid-campaign-luna-hyp-007-l23-2026-10-18.md.

### Autorização L24/v6 — 18/10/2026

Continue aceita L23 com violação real de agência/inconclusivo integral e autoriza
L24/v6 até 17 chamadas Luna low/USD 0,15 estimados adicionais, 768 tokens/
20.000 bytes/60s, sem retry/fallback/admissão. Preflight revalidado, zero chamadas/
22 hashes válidos. Gates paid/live ativados; depende de chave protegida no
lançador externo. Depois observar artefatos/custo e fechar gate. MVP aberto.

### Resultado L24 e preparação L25 — 18/10/2026

L24/v6 quatro chamadas/três turnos, 01 completo/intacto, parada R-03B/02 por
adjunto canônico de espera tomado como novo alvo. USD 0,0033604 estimados,
não cobrança; gate fechado/trava/histórico mantidos. L23 aceito. MVP aberto.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-054 | Corrigir adjunto no/na mais local canônico exato em espera explicitamente sem alvo, em _validate_declared_player_actions. Oito regressões novas/duas falhas reproduzidas antes da correção/80 focados aprovados; destino distinto/alvo/silêncio/ação posterior continuam protegidos, R-03B atômico/reinício/replay sem RNG/geração extra. Não reclassificar live. | [x] | 2026-10-18 |
| TASK-055 | Preparar evaluate/preflight/run L25, manifesto/testes separados fechados; mesmo v6/alvo/limites/22 hashes. 149 relacionados aprovados incluindo diretor de cenas/integração/preparação; 17 sintéticos/zero chamadas/14.457 bytes/AST válido. XML eval-results/hyp-007-l25-readiness-2026-10-18.xml. Sem terminal/chave/inferência. | [x] | 2026-10-18 |

Proposta: L24 inconclusivo integral/um percurso completo e L25 até 17 chamadas/
USD 0,15 estimados adicionais, Luna low/v6/768 tokens/20.000 bytes/60s, sem retry/
fallback/admissão. Continue/prossiga aprova ambos; até lá gate fechado.
Nenhum narrador admitido, TASK-013/CAMP-24 abertos. Relatório
hybrid-campaign-luna-hyp-007-l24-2026-10-18.md.

### Probe unitário após sessão temporária — 19/10/2026

Humano autorizou UMA chamada, não a bateria L25 inteira. Teto USD 0,15 passa a
padrão previamente aprovado por teste, sem autorizar quantidade/escopo extras.
L26 unitário executou uma tentativa/zero turnos; transport_or_response_invalid,
sem resposta/usage, custo indisponível/não zero. Gate fechado/latch preservado;
supervisora voltou idle sem nova chave. L25 segue fechado/nunca executado.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-056 | Preparar probe L26 com MAX_CALLS=1/schedule unitário e authorized_calls=1 obrigatório; envelope técnico antigo não é autorização para 17. 46 focados aprovados antes/depois. Executar uma tentativa autorizada, registrar custo indisponível e autenticidade inconclusiva, fechar gate sem retry. Relatório luna-single-call-probe-2026-10-19.md. | [x] | 2026-10-19 |

Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos. Nova inferência requer
autorização da quantidade, não nova aprovação do mesmo teto padrão. Antes:
diagnóstico offline seguro, sem log de exceção/body/headers/credencial.

### Retomada L28 e preparação L29 — 19/10/2026

Após probe L27 funcional, humano pediu retomar testes narrativos. L28 até 17
chamadas foi encerrado após 12/11 turnos, cinco percursos completos (01–05).
R-07/06 rejeitado por falso positivo partes ainda legíveis como partida.
Custo final estimado USD 0.0102126, não cobrança; gate fechado/latch preservado.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-057 | Executar L28/v6 uma vez pela supervisora corrigida; registrar 12 chamadas/11 turnos, cinco percursos e rejeição R-07. Sem retry ou admissão. Relatório hybrid-campaign-luna-hyp-007-l28-2026-10-19.md. | [x] | 2026-10-19 |
| TASK-058 | Corrigir somente quadro nominal de suas partes ainda legíveis em _action_signature_matches, preservando ações posteriores. Dez regressões novas, duas falhas pré-fix, atomicidade/reinício/replay sem RNG/geração adicional; 193 relacionados aprovados. | [x] | 2026-10-19 |
| TASK-059 | Preparar L29 separado/fechado, mesmo v6/alvo/limites; 22 hashes atuais, 17 sintéticos/zero envios/14.457 bytes. Não reescrever manifesto live L28. XML hyp-007-l28-correction-l29-readiness-2026-10-19.xml. | [x] | 2026-10-19 |

L28 integral inconclusivo/cinco percursos completos; nenhum narrador admitido.
L29 aguarda aprovação individual, teto padrão USD 0.15 não exige reconfirmação
separada. Continue/prossiga aprova a proposta delimitada do relatório L28.
TASK-013/CAMP-24/MVP permanecem abertos.

### Resultado L29 e preparação L30 — 19/10/2026

Prossiga aceitou classificação L28 e autorizou L29. Executado pela supervisora
20604: 12 chamadas/11 turnos, cinco percursos completos, parada R-07/06.
USD 0.0102446 finais estimados, não cobrança; gate fechado/latch preservado.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-060 | Executar L29 uma vez com limites aprovados e classificar resultado inconclusivo integral/cinco percursos completos. Relatório hybrid-campaign-luna-hyp-007-l29-2026-10-19.md, artefatos/hash/custo preservados. | [x] | 2026-10-19 |
| TASK-061 | Corrigir quadro nominal entre as partes ainda legíveis e marcador afirmativo explícito recupera/recuperou informação útil em scene_director_service. Filtros de sujeito/negação/asserção e rejeição simétrica em falha; testes de 10 para 26, 344 relacionados aprovados, atomicidade/reinício/replay sem geração/RNG extra. | [x] | 2026-10-19 |
| TASK-062 | Preparar L30 separado fechado, mesmo v6/alvo/limites; preflight 17 sintéticos/zero chamadas/14.457 bytes, 22 hashes atuais. XML hyp-007-l29-correction-l30-readiness-2026-10-19.xml. Sem nova inferência. | [x] | 2026-10-19 |

L29 não reclassificado após correção; L30 aguarda aprovação individual conforme
proposta delimitada no relatório. Continue/prossiga aprova execução única até
17 chamadas/USD 0.15 total estimado, sem retry/fallback/admissão. Não pedir
novamente teto padrão. Nenhum narrador admitido; TASK-013/CAMP-24/MVP abertos.

## 8. Related Specifications / Further Reading

Atualização operacional 19/10: humano autorizou L30 e testes futuros necessários
com tetos <= USD 0.15 por lote; registrar hipótese/limites/hash/parada e custo,
sem pedir novo aceite individual, sem retry silencioso/admissão automática.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-063 | Executar L30 com autorização contínua, analisar cinco chamadas/quatro turnos e falso positivo de ameaça ambiental R-01/02; custo USD 0.0043758 estimado, gate fechado/histórico preservado. Relatório hybrid-campaign-luna-hyp-007-l30-2026-10-19.md. | [x] | 2026-10-19 |
| TASK-064 | Corrigir somente enquanto a infiltração ameaça a bancada baixa em _action_signature_matches; oito regressões/duas falhas antes da correção; 137 agência/integração e 55 preparação/supervisora/custo aprovados, seleções sobrepostas. Commit/atomicidade/reinício/replay sem RNG/geração extra. | [x] | 2026-10-19 |
| TASK-065 | Executar L31 v6 uma vez: cinco chamadas/quatro turnos, falso positivo tom/tomar; USD 0.0043730 estimados, gate fechado/histórico preservado. Corrigir quadro nominal com duas falhas pré-fix, testes 8→15; 170 relacionados aprovados. Relatório L31. | [x] | 2026-10-19 |
| TASK-066 | Executar L32 após correção nominal: uma chamada/zero turnos, USD 0.0007964 estimados; rejeição real de decisão coletiva preservada. Quatro regressões novas, atomicidade/replay; gate fechado. Relatório L32. | [x] | 2026-10-19 |
| TASK-067 | Preparar v7 explicitando agência coletiva sem mudar runtime/critérios; 20 relacionados e 11 preparação aprovados (sobrepostos). Executar L33: 12 chamadas/11 turnos/cinco percursos, USD 0.0106532 estimados; falso positivo de leitura seguindo marcas. Gate fechado. Relatório L33. | [x] | 2026-10-19 |
| TASK-068 | Corrigir leitura somente no quadro explícito de exame do registro; duas falhas pré-fix, testes 26→33, 177 relacionados/40 preparação sobrepostos aprovados. L34 executou 13 chamadas/12 turnos/seis percursos, USD 0.0111458 estimados; falso positivo R-08 de falha não reconhecida, gate fechado. Relatório L34. | [x] | 2026-10-19 |
| TASK-069 | Corrigir falha explícita/umidade alcançando páginas; 11 regressões/seis falhas pré-fix, 289 relacionados/18 preparação sobrepostos aprovados. L35 uma chamada/zero turnos, USD 0.0007748 estimados, falso positivo de pergunta aberta; gate fechado/histórico mantido. Relatório L35. | [x] | 2026-10-19 |
| TASK-070 | Reconhecer pergunta completa Que ação você pretende realizar agora?; duas falhas pré-fix/31 testes de pergunta/165 relacionados/38 preparação sobrepostos aprovados. L36 nove chamadas/oito turnos, USD 0.0080752 estimados, avanço ambiental rejeitado; gate fechado. | [x] | 2026-10-19 |
| TASK-071 | Corrigir avanço da água sobre registro no quadro explícito; oito regressões/duas falhas pré-fix, 145 relacionados/15 preparação sobrepostos aprovados. L37 uma chamada/zero turnos, USD 0.0007564 estimados, condicional manipulá-lo rejeitada; gate fechado. | [x] | 2026-10-19 |
| TASK-072 | Estender condicional clítica já existente a manipulá-lo; quatro falhas pré-fix/27 condicionais/156 relacionados/34 preparação sobrepostos aprovados. L38 12 chamadas/11 turnos/cinco percursos, USD 0.0103988 estimados, plural útil rejeitado; gate fechado. | [x] | 2026-10-19 |
| TASK-073 | Reconhecer plural informações úteis sob mesmos filtros de sujeito/negação/falha; testes 33→39, duas falhas pré-fix/264 relacionados/46 preparação sobrepostos aprovados. L39 dez chamadas/nove turnos/três percursos, USD 0.0087130 estimados; omissão NPC na desistência, gate fechado. | [x] | 2026-10-19 |
| TASK-074 | Preservar obrigação NPC R-09, sem relaxar runtime. Três regressões novas/26 relacionados/dez preparação sobrepostos aprovados; preparar v8/L40, 22 hashes/17 sintéticos/zero rede/15.038 bytes. L40 executado: 17/17 turnos/oito percursos, USD 0.0152410 estimados; gate fechado/histórico preservado. | [x] | 2026-10-19 |
| TASK-075 | Verificação técnica final L40: 521 relacionados aprovados, hashes/proveniência/uso/faixas de palavras/desfechos conferidos; XML hyp-007-l40-final-related-2026-10-19.xml. Total L30–L40 86 chamadas/USD 0.0753034 estimados, não cobrança. Não é suíte de release nem admissão. | [x] | 2026-10-19 |
| TASK-076 | Preparar luna-l40-human-review-2026-10-19.md com oito percursos/17 entradas e respostas literais verificadas, procedimento de julgamento de progressão/role play/clareza/encerramento. Nenhuma nova chamada para ler. | [x] | 2026-10-19 |
| TASK-077 | Julgamento humano recebido em 20/10: resultados L40 aprovados com ressalva de linguagem artificial de segredo. Não repetir pedido de aceite. Registrar correção antes de fechar admissão; não inferir aceite de UI, default ou MVP completo. | [x] | 2026-10-20 |
| TASK-078 | Implementar prompt v9 com recusa diegética e sem recapitulação de segredo fora de contexto; nenhum motivo/lore inventado. Três testes naturais e 30 relacionados aprovados, identidade/agência/atomicidade/reinício/replay preservados. Validadores/runtime/catálogo inalterados. | [x] | 2026-10-20 |
| TASK-079 | Preparar L41 novo/fechado, mesmos oito percursos/alvo/limites e teto USD 0.15; 22 hashes/preflight 17 sintéticos/zero rede/16.770 bytes. Testar diff v8 intacto fora do bloco de estilo. XML hyp-007-l41-natural-refusal-readiness-2026-10-20.xml. | [x] | 2026-10-20 |
| TASK-080 | Executar e observar L41/v9: três chamadas/dois turnos/01 preserved, USD 0.0027948 estimados; parado R-03/02 por falso positivo de infiltração avança. R-02 não alcançado, naturalidade integral inconclusiva. Gate fechado/latch mantido; autenticação funcional observada. Relatório L41. Execução observada não equivale a hipótese aprovada. | [x] | 2026-10-20 |
| TASK-081 | Corrigir apenas quadro ambiental de infiltração avança pelas bordas da sala; oito regressões/duas falhas pré-fix/53 relacionados aprovados. Commit/reinício/replay sem RNG extra. Preparar L42 independente: 22 hashes/17 sintéticos/16.770 bytes/16 preparação aprovados; mesma v9 e teto USD 0.15. | [x] | 2026-10-20 |
| TASK-082 | Executar L42: quatro chamadas/três turnos, USD 0.0035764 estimados; parado R-03B/02 por páginas umedecidas não reconhecidas. Gate fechado/histórico preservado. Reconhecer cláusula afirmativa exata de dano, sem aceitar negação/hipótese/desejo/contradição/ação indevida. Seis regressões/uma falha pré-fix/36 relacionados aprovados. Relatório L42. | [x] | 2026-10-20 |
| TASK-083 | Preparar e executar L43/v9: 14 preparação aprovados, uma chamada/zero turnos, USD 0.000861 estimados; deliberação aberta enquanto você decide como proceder rejeitada. Oito casos novos/duas falhas pré-fix/58 relacionados aprovados após correção delimitada; escolha concreta/ação posterior continuam bloqueadas, replay sem RNG/geração extra. Gate fechado/histórico mantido. Relatório L43. | [x] | 2026-10-20 |
| TASK-084 | Preparar/executar L44: 26 preparação aprovados, quatro chamadas/três turnos, USD 0.0035662 estimados; condição se você decidir agir tomada como escolha executada. Sete casos novos/duas falhas pré-fix/92 relacionados aprovados após correção delimitada. Ações concretas/posteriores continuam rejeitadas; replay sem RNG/geração extra. Gate fechado/histórico mantido. Relatório L44. | [x] | 2026-10-20 |
| TASK-085 | Preparar/executar L45: 33 preparação e 387 ampliados aprovados, 11 chamadas/10 turnos/quatro percursos, USD 0.0103846 estimados. Parada por avaliação retrospectiva de Mara Você fez a escolha certa tratada como choice. Manter guard conservador; v10 pede reação física concreta. Três regressões/25 relacionados aprovados, mesma consequência/atomicidade/reinício/replay. Gate fechado/histórico mantido. Relatório L45. | [x] | 2026-10-20 |
| TASK-086 | Preparar/executar L46/v10: 12 preparação aprovados, 13 chamadas/12 turnos/seis percursos, USD 0.0119550 estimados. Parada R-08/07 por negativa de recuperação não reconhecida; frase nada legível também contradiz wet. Doze testes novos/45 relacionados aprovados: negativa assertiva delimitada reconhecida, perda total em wet recusada, uma rolagem/geração/commit/reinício/replay preservados. Gate fechado/histórico mantido. Relatório L46. | [x] | 2026-10-20 |
| TASK-087 | Preparar/executar L47/v11 após distinção tentativa falha vs perda total: 22 preparação e 404 ampliados aprovados, sete chamadas/seis turnos/dois percursos, USD 0.0067858 estimados. Parada R-03/03 por gerúndio ambiental avançando atribuído ao jogador. Oito casos novos/duas falhas pré-fix/70 relacionados aprovados após correção delimitada; ações reais continuam bloqueadas, replay sem RNG/geração extra. Gate fechado/histórico mantido. Relatório L47. | [x] | 2026-10-20 |
| TASK-088 | Preparar/executar L48: 26 preparação/412 ampliados aprovados, 13 chamadas/12 turnos/seis percursos, USD 0.0124300 estimados; parado por ambiente carrega tensão tomado como posse. Oito casos novos/duas falhas pré-fix/53 relacionados aprovados após correção delimitada; posse real/sucesso/transporte indevido continuam rejeitados, uma rolagem/geração/replay. Gate fechado/histórico mantido. Relatório L48. | [x] | 2026-10-20 |
| TASK-089 | Preparar/executar L49: 30 preparação/420 ampliados aprovados, oito chamadas/sete turnos/dois percursos, USD 0.0079160 estimados. Toque de água atribuído ao jogador e dano wet insuficientemente explícito. Seis casos novos/duas falhas pré-fix/34 relacionados aprovados; corrigir somente sujeito ambiental e preservar rejeição de mero contato. V12 pede dano concreto sem perda total. Gate fechado/histórico mantido. Relatório L49. | [x] | 2026-10-20 |
| TASK-090 | Preparar/executar L50/v12: 23 preparação/427 ampliados aprovados, seis chamadas/cinco turnos/01 completo, USD 0.0060612 estimados. Parada R-06/02 por O que ainda é legível é salvo não reconhecido como parcial. Cinco regressões/uma falha pré-fix/39 relacionados aprovados após reconhecimento afirmativo delimitado; negação/pergunta/hipótese/ação extra rejeitadas, dano/posição/replay sem RNG/geração extra mantidos. Gate fechado/histórico preservado. Relatório L50. | [x] | 2026-10-20 |
| TASK-091 | Preparar/executar L51: 16 preparação/432 ampliados aprovados, dez chamadas/nove turnos/três percursos, USD 0.0098572 estimados. Parada R-09/04 por imobilidade não declarada; rejeição/guard preservados. Três regressões/28 relacionados aprovados: retirar somente imobilidade aceita mesmo abandono/posição/reação NPC, ação posterior bloqueada, replay sem RNG/geração extra. V13 esclarece posição de objeto vs postura do jogador. Gate fechado/histórico mantido. Relatório L51. | [x] | 2026-10-20 |
| TASK-092 | Preparar/executar L52/v13: 15 preparação/436 ampliados aprovados, 13 chamadas/12 turnos/seis percursos, USD 0.0127004 estimados. Parada R-08/07 por negativa de tentativa não reconhecida e alcance ambiental tomado como sucesso. Onze casos novos/quatro falhas iniciais/duas do segundo predicado/64 relacionados aprovados após correções delimitadas; contraprovas/uma rolagem/geração/replay preservados. Gate fechado/histórico mantido. Relatório L52. | [x] | 2026-10-20 |
| TASK-093 | Preparar/executar L53: 43 preparação/447 ampliados aprovados, 13 chamadas/12 turnos/seis percursos, USD 0.0127096 estimados. Negativa possessiva/água alcança páginas não reconhecidas; contraprova revelou sucesso posterior a aspas fechadas ignorado. Onze casos novos/75 relacionados aprovados após correções delimitadas; sucesso/posse real e citação preservados, replay com uma rolagem/geração. Gate fechado/histórico mantido. Relatório L53. | [x] | 2026-10-20 |
| TASK-094 | Preparar/executar L54/v13 com mesma matriz/ordem 08 primeiro: 55 preparação/459 ampliados aprovados, 12 chamadas/11 turnos/três percursos, USD 0.0122714 estimados. Recusa/ajuda/resgate de 08 naturais sem relatório de segurança/repetição/lore inventada, avaliação intermediária positiva delegada ao agente. Integral parou R-04/03 por água atravessando páginas tomada como viagem do jogador. Seis casos novos/duas falhas pré-fix/52 relacionados aprovados após correção delimitada. Gate fechado/histórico mantido. Relatório L54. | [x] | 2026-10-20 |
| TASK-095 | Preparar/executar L55: 27 preparação/465 ampliados aprovados, duas chamadas/um turno, USD 0.0019168 estimados. Parada R-01/08 por condição se você decidir como agir tomada como escolha. Seis casos novos/duas falhas pré-fix/84 relacionados aprovados após extensão delimitada de condição aberta; ações concretas/coordenadas/posteriores continuam rejeitadas, replay sem RNG/geração extra. Gate fechado/histórico mantido. Relatório L55. | [x] | 2026-10-20 |
| TASK-096 | Preparar/executar L56: 44 preparação/471 ampliados aprovados, 15 chamadas/14 turnos/seis percursos, USD 0.0148946 estimados. Parada R-07/06 por exame e recuperação útil coordenados não reconhecidos. Nove regressões/duas falhas pré-fix/84 relacionados aprovados após reconhecimento delimitado; negação/hipótese/NPC/citação/ação extra rejeitados, uma rolagem/geração/replay. Gate fechado/histórico mantido. Relatório L56. | [x] | 2026-10-20 |
| TASK-097 | Preparar/executar L57: 22 preparação/480 ampliados aprovados, dez chamadas/nove turnos/três percursos, USD 0.0100426 estimados. Parada R-03/03 por infiltração avança pelas proximidades bancada atribuída ao jogador. Oito casos novos/quatro falhas pré-fix/84 relacionados aprovados após correção de sujeito explícito independente do complemento espacial; apenas token avança dispensado, demais verbos/atores protegidos. Replay sem RNG/geração extra. Gate fechado/histórico mantido. Relatório L57. | [x] | 2026-10-20 |
| TASK-098 | Preparar/executar L58: 37 preparação/488 ampliados aprovados, dez chamadas/nove turnos/três percursos, USD 0.0100744 estimados. Parada R-03/03 por umidade que avança atribuída ao jogador. Seis casos novos/duas falhas pré-fix/90 relacionados aprovados após reconhecer sujeito ambiental relativo explícito; demais atores/verbos protegidos, replay sem RNG/geração extra. Gate fechado/histórico mantido. Relatório L58. | [x] | 2026-10-20 |
| TASK-099 | Preparar/executar L59: 43 preparação/494 ampliados aprovados, 16 chamadas/15 turnos/sete percursos, USD 0.0157842 estimados. Parada R-08/07 em fechamento retrospectivo ambíguo deixa de revelar o que você procurava. Guards conservadores mantidos, não declarar concessão canônica comprovada. Quatro regressões/79 relacionados aprovados: alternativa direta mesma wet/posição, ação extra/sucesso bloqueados, uma rolagem/geração/replay. V14 orienta falha direta sem objetivo anterior presumido. Gate fechado/histórico mantido. Relatório L59. | [x] | 2026-10-20 |
| TASK-100 | L60/v14 encerrado: uma chamada/zero turnos, USD 0.0008756 estimado; recusa contextual sem literal fundadora rejeitada. Gate fechado, histórico preservado. Sete regressões: vínculo anafórico direto/contextual aceita sem liberar hipótese, segredo ou ação extra; reinício/replay sem RNG extra. Prompt v15 evita atenção da cena. Relatório L60; 499 relacionados anteriores à correção. | [x] | 2026-10-20 |
| TASK-101 | L61/v15 encerrado: sete chamadas/sete turnos, USD 0.0068490 estimado. Oitava etapa bloqueada antes de envio por 20.093 bytes, confirmado offline; 507 relacionados aprovados. Gate fechado/histórico preservado. V16 compacto, mesmo histórico completa fake17 em 19.455 bytes; dois comparativos aprovados. Relatório L61. | [x] | 2026-10-20 |
| TASK-102 | L62/v16: 12 chamadas/11 turnos, USD 0.0121282 estimado; corpo passou ponto L61 sem elevar teto. R-04/03 água atravessa registro atribuída ao jogador; duas falhas pré-fix, correção delimitada/contraposições, 156 relacionados aprovados. Gate fechado/evidência preservada, relatório L62. | [x] | 2026-10-20 |
| TASK-103 | L63: duas chamadas/um turno, USD 0.0018726 estimado. R-01/08 repetiu recusa fora de contexto; erro técnico combat por material confundido com matar. Gate fechado/histórico preservado. Uma falha pré-fix/fix nominal exato/quatro regressões/142 relacionados aprovados; v17 prioriza entrada atual sem repetir recusa histórica. Relatório L63. | [x] | 2026-10-20 |
| TASK-104 | L64/v17 nove chamadas/oito turnos, USD 0.0092450 estimado. R-06/02 clítico do registro confundido com retirada do jogador; duas falhas pré-fix, correção delimitada/16 regressões de retirada/151 relacionados aprovados. Gate fechado/histórico preservado; relatório L64. | [x] | 2026-10-20 |
| TASK-105 | L65 12 chamadas/11 turnos, USD 0.0123666 estimado. R-04/03 água continua avançando atribuída ao jogador. Duas falhas pré-fix, correção de sujeito explícito/28 regressões ambientais/163 relacionados aprovados. Gate fechado/evidência preservada, relatório L65. | [x] | 2026-10-20 |
| TASK-106 | L66 duas chamadas/um turno, USD 0.0019282 estimado. R-01/08 passiva futura examinado confundida com ação executada. Fix delimitado de token/família, seis regressões/141 relacionados aprovados, sequência diálogo/reinício/replay sem RNG extra. Gate fechado/evidência preservada; relatório L66. | [x] | 2026-10-20 |
| TASK-107 | L67 oito chamadas/sete turnos, USD 0.0080808 estimado. Pergunta aberta Como você quer proceder com o registro molhado? não reconhecida; duas falhas pré-fix/equivalência restrita de campo inteiro, 171 relacionados e 53 questão/contexto aprovados, sem liberar NPC/menu/ação extra. Gate fechado/evidência mantida; relatório L67. | [x] | 2026-10-20 |
| TASK-108 | L68 12 chamadas/11 turnos, USD 0.0123238 estimado. Mas a infiltração avança atribuído ao jogador; duas falhas pré-fix, sujeito ambiental imediato independente de conjunção, 202 relacionados aprovados/ações posteriores protegidas. Gate fechado/histórico mantido; relatório L68. | [x] | 2026-10-20 |
| TASK-109 | L69 seis chamadas/cinco turnos, USD 0.0058922 estimado. Contato negado de Mara atribuído a jogador objeto do gesto. Duas falhas pré-fix, atribuição restrita fora de citação/220 relacionados e 45 ambientais/NPC aprovados; ator desconhecido/jogador/citação/ação extra protegidos. Gate fechado/evidência mantida, relatório L69. | [x] | 2026-10-20 |
| TASK-110 | L70 quatro chamadas/três turnos, USD 0.0039672 estimado. Pergunta sim/não real rejeitada corretamente; guard/runtime mantidos. 38 relacionados aprovados, v18 orienta q aberta existente exatamente quando não terminal, vazio no desfecho, só perfil sintético. Gate fechado/histórico preservado, relatório L70. | [x] | 2026-10-20 |
| TASK-111 | L71 sete chamadas/seis turnos, USD 0.0068850 estimado. Onde ele estava ambíguo, guard mantido. Alternativa na bancada baixa realiza mesmo wet; 15 regressões de dano aprovadas com agência/atomicidade/replay. V19 reforça nomear registro em posição/estado. Gate fechado/histórico mantido, relatório L71. | [x] | 2026-10-20 |
| TASK-112 | L72 15 chamadas/14 turnos, USD 0.0150288 estimado. R07 recuperação nominal parcial não reconhecida; duas falhas pré-fix, marcador assertivo delimitado/sucesso e proibição da mesma concessão na falha. 199 relacionados aprovados, replay com uma rolagem/geração. Gate fechado/evidência mantida, relatório L72. | [x] | 2026-10-20 |
| TASK-113 | L73 15 chamadas/14 turnos, USD 0.0149588 estimado. R07 recupera parte da informação não reconhecido e parte nominal como partir. Duas causas corrigidas com sujeito explícito, falha/hipótese/citação/NPC/negação/partida real bloqueadas; 212 relacionados aprovados. Gate fechado/histórico mantido, relatório L73. | [x] | 2026-10-20 |
| TASK-114 | L74 13 chamadas/12 turnos, USD 0.0131672 estimado. R09 recebendo sua escolha após você aciona choice; guard mantido como L45. Alternativa Mara recebe desistência preserva fechamento/bench; 12 relacionados aprovados. V20 reescreve só orientação de reação à desistência. Gate fechado/histórico mantido, relatório L74. | [x] | 2026-10-20 |
| TASK-115 | L75 17 chamadas/17 turnos/oito percursos integrais, USD 0.0170188 estimado; auditoria independente e 654 relacionados passam. Leitura qualitativa achou secagem não preparada e fala truncada: duas falhas pré-fix/guard prospectivo de secagem/39 relacionados passam, v21 esclarece física/fala completa. Resultado histórico integral preservado, sem admissão; relatório L75. | [x] | 2026-10-20 |
| TASK-116 | L76/v21 executado: 4 chamadas/3 turnos/USD 0.0039206 estimado; falso positivo em mente/mentir reproduzido e corrigido prospectivamente; 146 testes passam. Gate fechado, histórico preservado. Relatório hybrid-campaign-luna-hyp-007-l76-2026-10-20.md. | [x] | 2026-10-20 |
| TASK-117 | L77/v21 executado: 15 chamadas/14 turnos/USD 0.0148322 estimado; partes nominal como partir reproduzido/corrigido prospectivamente. 218 focados/37 inspeção-atomicidade passam, gate fechado, relatório hybrid-campaign-luna-hyp-007-l77-2026-10-20.md. | [x] | 2026-10-20 |
| TASK-118 | L78/v21 executado: 10 chamadas/9 turnos/USD 0.0099626 estimado; gotas que avançam atribuído ao jogador, reproduzido/corrigido prospectivamente. 257 focados passam, gate fechado, relatório hybrid-campaign-luna-hyp-007-l78-2026-10-20.md. | [x] | 2026-10-20 |
| TASK-119 | L79/v21 executado: 12 chamadas/11 turnos/USD 0.0122374 estimado; infinitivo de água atravessar registro atribuído ao jogador, reproduzido/corrigido prospectivamente; 220 testes passam. Gate fechado, relatório hybrid-campaign-luna-hyp-007-l79-2026-10-20.md. | [x] | 2026-10-20 |
| TASK-120 | L80/v21 executado: 17 chamadas/16 turnos/USD 0.0168512 estimado; equivalência parcial faltante e secagem por fora não preparada, reproduzidas/corrigidas prospectivamente; 31 focados passam. Gate fechado, relatório hybrid-campaign-luna-hyp-007-l80-2026-10-20.md. | [x] | 2026-10-20 |
| TASK-121 | L81/v22 executado: 16 chamadas/15 turnos/USD 0.0158616 estimado; falha negativa assertiva faltante reproduzida/corrigida; 184 focados passam. 966 ampliados passam no snapshot anterior ao fix; gate fechado, relatório hybrid-campaign-luna-hyp-007-l81-2026-10-20.md. | [x] | 2026-10-20 |
| TASK-122 | L82/v22 executado: 9 chamadas/8 turnos/USD 0.0091548 estimado, gate fechado. Equivalência parcial passada, tarefa trocada e ações após epílogo corrigidas prospectivamente; 91 focados passam, histórico preservado. Relatório hybrid-campaign-luna-hyp-007-l82-2026-10-20.md. | [x] | 2026-10-20 |
| TASK-123 | L83/v23 preparado e fechado false/false, 22 hashes reais conferidos; 987 testes ampliados passam no snapshot final, incluindo preparação L83. Não executado, sem custo/request/latch/summary. Auditoria consolidada em hybrid-campaign-luna-validation-checkpoint-2026-10-20.md. Não ativar por arrasto. | [x] | 2026-10-20 |
| TASK-124 | Decisão humana proposta DEC-NARR-VALID-001: A revisar desenho da fronteira/contrato (recomendado, sem implementar antes de aprovar contrato); B manter contrato e continuar correções experimentais com risco explícito. Autorização de custo contínua permanece vigente, não solicitar novo teto <= USD 0.15. Nenhum narrador/default/CAMP-24 admitido. | [ ] | — |

- [Problema confirmado](issue-mvp-narrative-progression-1.md)
- [Checklist CAMP-01–24](checklist-planejamento-campanha-hibrida.md)
- [Resolvedor e decisões aprovadas](architecture-scene-resolution-1.md)
- [Contrato do beat](../spec/spec-deterministic-scene-resolution.md)
- [Ponte B e limites](architecture-narrative-source-bridge-1.md)
- [Produtor B, especialmente REQ-013](feature-narrative-source-input-producer-1.md)
- [Ensaio manual rejeitado](../evals/narrator/reports/openai-luna-manual-observation-413d4983-2026-09-28.md)
- [Estado vigente](../PROMPT_RETOMADA_2026-09-06.md)
