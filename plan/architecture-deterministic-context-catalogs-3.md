---
goal: Selecionar contexto de domínio deterministicamente e tornar explícita a completude do subconjunto V5 suportado
version: 1.0
date_created: 2026-09-05
last_updated: 2026-09-21
owner: Codex
status: 'Completed'
tags: [architecture, context, catalogs, v5, rules, lore, testing, provenance]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

Este plano descreve trabalho futuro para substituir cortes posicionais de lore por
seleção determinística baseada em obrigatoriedade, relevância e orçamento, e para
declarar com precisão quais dados e mecânicas V5 o produto realmente suporta. Sua
criação não autoriza implementação. Código, catálogos, contratos, prompts e testes
permanecem inalterados até uma autorização humana posterior e explícita.

O repositório possui cinco contratos Markdown (`H0`, `H1`, `H2`, `H4`, `H6`) e
sete catálogos JSON, sem uma skill ou um modelo por item. Os catálogos contêm 16
clãs, 10 categorias de arma, 8 poderes, 5 tipos de predador, 11 níveis de potência
de sangue, 9 categorias de NPC e 7 categorias de progressão. Esses dados são
carregados localmente por serviços tipados e suas consultas não consomem chamadas
de modelo.

No perfil padrão, H0 e H1 operam deterministicamente, o enriquecimento H4 de ação
está desativado e um turno ficcional normal chama somente H6 uma vez. Uma consulta
direta de lore chama H4 uma vez e não chama H6. Esta topologia é preservada: H6
continua sendo o único narrador até que avaliações demonstrem uma falha específica
que justifique separar planejamento e prosa. Um segundo modelo não pode compensar
fatos ausentes, referências inválidas ou mecânicas incompletas.

O plano preserva a direção improvisacional vigente: o narrador recebe fatos já
selecionados e pode propor continuidade ficcional dentro das fronteiras de
admissão, mas não inventa mecânica, não corrige lacunas de catálogo e não promove
sua própria saída a cânone.

## 1. Requirements & Constraints

- **OBS-001**: `api/lore_service.py:get_contextual_lore` monta blocos na ordem
  predador, clã, poder, arma e NPC e aplica `blocks[:3]` antes que
  `api/context_service.py:assemble_context` possa pontuá-los. O teste
  `tests/test_perf_sec.py:test_lore_extraction_latency` atualmente cristaliza a
  perda do NPC depois dos três primeiros blocos.
- **OBS-002**: `api/rules_service.py:V5ActionPayload.weapon_category` usa
  `unarmed` como default; `get_contextual_lore` interpreta esse valor como arma
  contextual mesmo quando a ação não é agressiva e nenhuma arma foi escolhida.
- **OBS-003**: `api/orchestrator_service.py:_scene_query_static_lore` também põe
  o clã antes dos NPCs e aplica `blocks[:3]`, criando um segundo corte anterior ao
  orçamento contextual.
- **OBS-004**: A cobertura é desigual. Há campos catalogados sem consumidor
  mecânico, incluindo `favored_disciplines`, `bane_severity_multiplier`,
  `behavioral_penalty`, `dice_bonus_stat`, `weapon_type`, `is_concealable`,
  `hunting_pool`, `blood_resonance_preference`, `bane_severity`,
  `rouse_reroll_level`, `base_dice_pool` e `has_true_faith`.
- **OBS-005**: A ontologia de disciplinas está fragmentada: clãs referenciam
  famílias, a ficha armazena IDs de poderes e o catálogo de poderes não declara
  família ou nível. Progressão, aliases, pré-requisitos e autorização não possuem
  um registro referencial único.
- **OBS-006**: Os sete catálogos não registram `schema_version`, edição, fonte,
  página, licença ou revisão. O formato atual trata cada chave raiz como entrada;
  inserir `_meta` diretamente quebraria os loaders existentes.
- **REQ-001**: Substituir toda ordem fixa e todo corte `blocks[:3]` por candidatos
  de contexto tipados, identificados e pontuáveis antes de qualquer omissão.
- **REQ-002**: Reservar primeiro os itens obrigatórios. Um item é obrigatório
  somente quando representa mecânica aplicada no turno, fato canônico necessário,
  proteção de segredo, resultado resolvido ou entidade explicitamente selecionada
  cuja omissão tornaria a narrativa incorreta. Excesso de itens obrigatórios deve
  falhar de forma observável, nunca omiti-los silenciosamente.
- **REQ-003**: Classificar itens opcionais por sinais determinísticos de menção ou
  seleção explícita, regra acionada, participação na cena, relevância textual,
  importância e ID estável. A política e o desempate devem ser versionados e
  testáveis; a ordem física dos arquivos não pode decidir inclusão.
- **REQ-004**: Aplicar o orçamento efetivo de H6 uma única vez, usando o menor
  valor entre os limites de contexto já configurados. Cada omissão deve conservar
  `item_id`, motivo, tokens estimados e posição de prioridade para diagnóstico
  seguro, sem persistir prompt completo nem segredo.
- **REQ-005**: O contexto de `unarmed` só pode concorrer ao orçamento quando a
  ação for agressiva, o combate exigir esse dado ou a categoria tiver sido
  explicitamente selecionada. O default de payload não constitui relevância.
- **REQ-006**: Produzir uma matriz versionada do subconjunto V5 com uma linha por
  entrada e estados distintos para presença no catálogo, referência válida,
  mecânica implementada, narrativa coberta, testes positivos, testes negativos e
  limitações conhecidas. `catalogued` nunca deve significar `supported`.
- **REQ-007**: Unificar a ontologia de disciplina em IDs distintos para família e
  poder, com nível, pré-requisitos, aliases normalizados, vínculo com clã, ficha e
  progressão. A compatibilidade de saves existentes deve ser explícita e
  não destrutiva.
- **REQ-008**: Validar schemas, IDs e referências cruzadas na carga ou no preflight
  do produto. Clã, predador, NPC, arma, poder, família, atributo, habilidade,
  potência ou categoria de progressão desconhecidos ou não autorizados devem
  falhar fechados antes de custo, rolagem, dano, mutação de XP ou commit.
- **REQ-009**: Completar deterministicamente o subconjunto humano aprovado antes
  de ampliar o inventário. A conclusão exige pools de predador, banes e
  compulsões, propriedades mecânicas de armas e regras de cada poder declarado
  como suportado. Campos apenas narrativos devem ser marcados como tais.
- **REQ-010**: Fundamentar consultas H4 diretas em resultados tipados dos
  catálogos. Quando não houver cobertura, retornar uma resposta limitada e
  observável; H4 não pode preencher a lacuna como fato nem criar mecânica.
- **REQ-011**: Separar lookup/Q&A fundamentado de enriquecimento atmosférico
  opcional. Se o enriquecimento for mantido, ele recebe apenas fatos selecionados,
  preserva as fontes, não aumenta o número máximo atual de chamadas e não altera a
  rota H4-direta/H6-ausente.
- **REQ-012**: Eliminar drift entre contrato e runtime depois da decisão humana de
  fonte de verdade. Atualmente H1 e H6 carregam Markdown, H0 e H4 usam prompts
  inline, e H2 documenta persistência JSON anterior à persistência transacional.
- **REQ-013**: Manter os cinco contratos por papel cognitivo ou determinístico;
  não criar skill, prompt, adaptador ou modelo por clã, arma, poder, NPC ou outra
  entrada de catálogo.
- **REQ-014**: Manter uma única chamada H6 por continuação normal. Separar
  planejamento e prosa exige avaliação específica e decisão humana futura; não é
  solução permitida para incompletude de dados.
- **REQ-015**: Entregar a H6 somente itens já selecionados, com domínio, ID,
  conteúdo permitido, visibilidade, obrigatoriedade, importância e referência de
  origem. H6 não recebe o catálogo integral nem decide quais fatos são vinculantes.
- **REQ-016**: Registrar proveniência editorial em manifesto versionado separado,
  sem alterar silenciosamente o envelope dos sete catálogos. Os metadados mínimos
  propostos incluem versão de conteúdo, data de revisão, fonte, edição, página
  quando aplicável, licença ou fundamento de uso e hash do arquivo.
- **REQ-017**: Evitar reprodução integral de livros ou grandes trechos protegidos.
  Conteúdo deve ser mínimo e funcional; legalidade, licença e fonte aceitável
  exigem análise própria e não podem ser concluídas por inferência do código.
- **SEC-001**: Não abrir, copiar, registrar, imprimir ou incluir `.env` no diff.
  Testes de catálogo e seleção devem ser offline e não depender de credencial.
- **SEC-002**: Filtrar visibilidade antes de pontuar e medir orçamento. Conteúdo
  confidencial não pode influenciar score, omissão ou telemetria de uma audiência
  que não tem permissão para conhecê-lo.
- **AUT-001**: Quando, e somente quando, a implementação deste plano for
  explicitamente autorizada ou iniciada pelo usuário, o agente poderá realizar sem
  nova permissão todas as alterações locais, reversíveis e estritamente necessárias
  para cumprir o escopo e os critérios de aceite já aprovados, incluindo código,
  catálogos, testes e documentação diretamente relacionados.
- **AUT-002**: A autonomia de `AUT-001` não autoriza implementação nesta tarefa
  documental, redefinição da intenção do produto, decisão de arquitetura pendente,
  alteração de decisão bloqueada, expansão material de escopo, ação destrutiva ou
  difícil de reverter, exposição de segredo, custo externo, contato com terceiro,
  troca de provedor/modelo, dependência material ou fallback pago. Problemas fora
  do escopo permanecem em `report-don't-touch`.
- **AUT-003**: Durante futura execução autorizada, o agente deve reinspecionar o
  estado antes de alterar, preservar mudanças do usuário, produzir o menor conjunto
  coerente e verificar empiricamente cada fase.
- **CON-001**: Esta tarefa altera somente este plano. Nenhum item técnico abaixo
  possui status aprovado, em execução ou concluído.
- **CON-002**: Preservar React + FastAPI no monólito modular local-first, a
  persistência transacional vigente, LLM-001, a admissão narrativa e a autoridade
  dos módulos determinísticos.
- **CON-003**: Não adicionar tecnologia de busca vetorial, banco, serviço externo
  ou dependência. Os catálogos pequenos devem usar seleção local determinística.
- **CON-004**: Não escolher provedor/modelo, alterar roteamento multimodelo,
  habilitar H0/H1/H4, mudar limite de chamadas, criar fallback ou introduzir custo.
- **CON-005**: Não expandir indiscriminadamente os catálogos. Entradas novas só
  podem ser propostas depois que o subconjunto selecionado estiver completo e
  testado.
- **CON-006**: Não converter cálculos, invariantes ou transições em blobs JSON. JSON
  contém dados, parâmetros e proveniência validados; o motor Python executa regras.
- **DEC-001 (Approved 2026-09-16)**: O compromisso inicial cobre somente entradas
  alcançáveis pela ficha base e fluxos expostos; as demais permanecem `catalogued`,
  `partial` ou `deferred` até evidência completa.
- **DEC-002 (Approved 2026-09-16)**: Markdown versionado será a fonte editorial
  única de H0/H1/H4/H6, carregada pelo runtime; código conserva composição,
  validação e fallback técnico não editável.
- **DEC-003 (Approved 2026-09-16)**: H2 será descontinuado como “skill” cognitiva;
  o motor relacional será documentado como módulo determinístico.
- **DEC-004 (Approved 2026-09-16)**: H4 direto recebe somente lookup tipado e
  fundamentado; pode reformular fatos selecionados, sem criar enriquecimento
  atmosférico factual. Cobertura ausente retorna `not_covered`.
- **DEC-005 (Approved 2026-09-16)**: O manifesto sidecar registra versão, revisão,
  fonte, edição, página/seção, fundamento de uso, notas editoriais e SHA-256. Dados
  não comprovados permanecem `unverified`; não se inventa proveniência.

## 2. Implementation Steps

### Implementation Phase 0

- GOAL-001: Revalidar o baseline e resolver somente as decisões materiais que
  bloqueiam a execução.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Repetir o preflight no worktree: ler a cadeia `AGENTS.md` e `state/PROJECT_STATE.md` quando existirem, registrar branch/status, inspecionar diff e confirmar que `.env` não será lido. | [x] | 2026-09-16 |
| TASK-002 | Inventariar programaticamente os sete catálogos e gerar uma tabela de cobertura atual por entrada, distinguindo campos presentes, consumidores reais em código, referências, testes e lacunas. Não editar conteúdo V5 nesta tarefa. | [x] | 2026-09-16 |
| TASK-003 | Produzir um brief para `DEC-001` a `DEC-005`, com impacto, alternativas e recomendação, e obter decisão humana antes de qualquer tarefa dependente. Não transformar recomendação em decisão. | [x] | 2026-09-16 |
| TASK-004 | Fixar como baseline verificável a topologia de chamadas do perfil padrão: H0/H1 locais, H4-action desligado, no máximo uma H6 por turno ficcional e H4 direto sem H6. Depende de TASK-001. | [x] | 2026-09-16 |

Evidência da Fase 0 em
`evals/narrator/reports/deterministic-catalogs-phase0-2026-09-16.md`. O brief de
TASK-003 foi produzido em
`plan/decisions-deterministic-context-catalogs-2026-09-16.md`; a tarefa permanece
aberta exclusivamente porque `DEC-001` a `DEC-005` exigem decisão humana.

### Implementation Phase 1

- GOAL-002: Criar contratos versionados de catálogo, suporte e proveniência sem
  ampliar o inventário.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Criar `api/catalog_models.py` com modelos Pydantic `extra="forbid"` para IDs, aliases, referência cruzada, estado de suporte e proveniência; preservar modelos públicos existentes por adaptadores de compatibilidade. Depende de TASK-002 e DEC-005. | [x] | 2026-09-16 |
| TASK-006 | Criar `api/catalog_service.py` como registro local único que carrega os sete catálogos, normaliza IDs/aliases, valida referências e expõe lookups tipados sem LLM. Não mover regra mecânica para o loader. Depende de TASK-005. | [x] | 2026-09-16 |
| TASK-007 | Criar `data/catalogs/v5_support_matrix.json` com versão de schema e uma linha por entrada contendo estados separados `catalogued`, `references_valid`, `mechanics`, `narrative`, `positive_tests`, `negative_tests` e `limitations`. Depende de DEC-001. | [x] | 2026-09-16 |
| TASK-008 | Criar `data/catalogs/catalog_manifest.json` como sidecar versionado com hash, revisão, fonte, edição, página e licença/fundamento aprovados; não adicionar `_meta` às raízes atuais. Depende de DEC-005. | [x] | 2026-09-16 |
| TASK-009 | Migrar `clan_service.py`, `combat_service.py`, `discipline_service.py`, `physiology_service.py`, `npc_service.py` e `progression_service.py` para o registro validado, preservando suas APIs externas durante a transição. Depende de TASK-006 a TASK-008. | [x] | 2026-09-16 |

TASK-008 registra como origem editorial a compilação privada do projeto
`Organizando Regras de Vampiro para IA`, no caderno NotebookLM informado pelo
usuário. A origem confirma o encadeamento editorial e a edição declarada, mas não
identifica páginas dos manuais nem comprova licença sobre publicações subjacentes.
Esses limites permanecem explícitos no manifesto. TASK-009 foi aceita após essa
dependência e a regressão focada dos seis consumidores.

### Implementation Phase 2

- GOAL-003: Unificar IDs de disciplina/ficha/progressão e fechar caminhos de
  autorização inválida.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-010 | Estender a representação versionada de poderes com `discipline_family_id`, `power_id`, `level`, `prerequisite_power_ids`, `amalgam_requirements` e aliases; mapear cada referência existente sem inventar conteúdo ausente. Depende de TASK-007. | [x] | 2026-09-16 |
| TASK-011 | Atualizar `data/schema_save.json`, `api/rules_service.py` e a leitura de ficha para validar clã, predador, potência, família e poder contra o registro; implementar leitura compatível dos saves legados sem reescrevê-los. Depende de TASK-009 e TASK-010. | [x] | 2026-09-16 |
| TASK-012 | Refatorar `api/orchestrator_service.py` para resolver aliases por meio do registro único e autorizar somente um `power_id` conhecido, possuído e no nível requerido; remover tabelas duplicadas apenas depois de equivalência testada. Depende de TASK-010 e TASK-011. | [x] | 2026-09-16 |
| TASK-013 | Corrigir `api/progression_service.py` para validar categoria, trait, nível e transição antes de calcular custo ou mutar XP/ficha; categoria ou ID desconhecido retorna erro tipado e preserva o objeto original. Depende de TASK-009 a TASK-011. | [x] | 2026-09-16 |

TASK-010 mantém `null` quando a compilação não identifica nível, pré-requisito ou
amálgama. A conclusão significa que todas as referências existentes foram
representadas de modo tipado e honesto; não significa que todos os poderes tenham
regra V5 completa ou suporte mecânico aprovado.

TASK-011 valida as referências durante a construção de `PlayerSheetModel`. IDs e
aliases legados são aceitos sem normalizar ou reescrever o objeto lido; entradas
desconhecidas, potência fora do catálogo e nível fora de 0 a 5 falham antes do uso.
As famílias reconhecidas são derivadas dos metadados dos poderes, requisitos de
amálgama e disciplinas favorecidas dos clãs, sem criar uma segunda fonte editorial.

TASK-012 removeu a tabela de aliases do orquestrador. A seleção determinística não
concede posse: a ativação exige poder diretamente adquirido ou família possuída e
seleção autorizada; níveis, amálgamas e pré-requisitos conhecidos são verificados.
TASK-013 valida toda a transação antes do custo e opera sobre cópia profunda. Erros
de categoria, trait, nível e transição possuem códigos tipados e preservam a ficha.

### Implementation Phase 3

- GOAL-004: Completar as regras do subconjunto MVP aprovado antes de considerar
  qualquer entrada adicional.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-014 | Para cada clã aprovado, implementar e testar somente os efeitos de bane/compulsão declarados pela matriz; classificar `favored_disciplines` e demais campos como mecânicos, narrativos ou não suportados. Depende de DEC-001 e GOAL-003. | [x] | 2026-09-16 |
| TASK-015 | Para cada tipo de predador aprovado, transformar `hunting_pool` em pool determinístico validado e definir o papel mecânico de ressonância; alimentação genérica não pode mascarar ausência de regra específica. Depende de DEC-001 e GOAL-003. | [x] | 2026-09-20 |
| TASK-016 | Para cada poder aprovado, implementar custo, pool, nível, pré-requisitos, modificadores e efeitos permitidos no motor; remover hardcodes por ID apenas quando a equivalência estiver coberta. Depende de TASK-010 a TASK-012. | [x] | 2026-09-20 |
| TASK-017 | Para cada arma aprovada, implementar e testar dano, tipo, ocultabilidade e efeitos especiais realmente suportados; arma desconhecida não pode equivaler a modificador zero. Depende de DEC-001 e TASK-009. | [x] | 2026-09-20 |
| TASK-018 | Para NPCs e potência de sangue aprovados, ligar somente campos com regra definida e marcar os demais como narrativos ou não suportados; atualizar a matriz apenas depois dos testes positivos e negativos. Depende de DEC-001 e TASK-009. | [x] | 2026-09-20 |

No escopo `base_reachable`, apenas Brujah está aprovado. Sua compulsão mecânica de
dois dados já é aplicada exclusivamente pelo estado determinístico e possui teste
positivo. A perdição exige resistência a Frenesi de Fúria, motor inexistente no
MVP, e permanece explicitamente não suportada. `favored_disciplines` orienta
catálogo/progressão; `behavioral_penalty` permanece narrativo e não pode alterar
Fome por texto do narrador.

No escopo `base_reachable`, apenas Alleycat está aprovado. O pool padrão
Strength + Brawl é convertido em enums e aplicado a uma ação explícita de
alimentação quando o jogador não escolhe outro teste. A preferência colérica é
somente pista narrativa de alvo: não concede bônus, ressonância ou sucesso. Tipos
de predador adiados falham fechados nesse caminho.

No escopo `base_reachable`, apenas `unarmed` está aprovado. O catálogo fixa
Strength + Brawl, tipo BRAWL e modificador de dano zero; por isso o dano é igual à
margem. Categoria desconhecida agora falha antes do cálculo, sem herdar o zero de
`unarmed`. A ocultabilidade está catalogada, mas continua informativa enquanto não
existir um motor de inventário/ocultação.

Os três poderes `base_reachable` usam semântica tipada do catálogo. Armas Ferais
custa um Rouse Check, concede +2 de dano de Briga e produz dano superficial não
reduzido contra vampiros, sem convertê-lo em agravado. Salto Ascendente é passivo,
sem rolagem, com multiplicadores vertical 3 e horizontal 5 registrados; a distância
aguarda geometria de cena. Fascínio é nível 1, gratuito e contextual: soma Presença
somente a ações suportadas de Carisma; a ativação isolada não inventa rolagem.

Príncipe e Xerife são os únicos arquétipos de NPC `base_reachable`. Nível de
ameaça, natureza sobrenatural e índice de corrupção são mecânicos; pool-base não é
consumido, Fé Verdadeira é falsa e descrição/táticas/posição são narrativas. Os
demais arquétipos não alteram regras. Potência de Sangue 1 é o único nível
alcançável: Surto +1 e Cura 1 estão ligados; severidade da perdição e rerrolagem de
Rouse permanecem catalogadas, mas não suportadas no runtime.

### Implementation Phase 4

- GOAL-005: Selecionar fatos de catálogo deterministicamente sob o orçamento real
  antes de montar a solicitação H6.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Introduzir em `api/catalog_models.py` um `CatalogContextCandidate` imutável com domínio, entry ID, texto mínimo, visibilidade, obrigatoriedade, sinais de relevância, importância e referências de origem. Depende de GOAL-002. | [x] | 2026-09-20 |
| TASK-020 | Substituir `api/lore_service.py:get_contextual_lore` por produção de candidatos tipados antes do corte; manter uma projeção textual temporária apenas onde compatibilidade exigir. Remover `blocks[:3]`. Depende de TASK-019. | [x] | 2026-09-20 |
| TASK-021 | Definir e versionar a política determinística: obrigatórios primeiro; depois menção/seleção explícita, regra acionada, entidade ativa na cena, relevância textual, importância e ID estável. Aplicar `unarmed` conforme REQ-005 e registrar omissões seguras. Depende de TASK-020. | [x] | 2026-09-20 |
| TASK-022 | Integrar cada candidato como `ContextItem` individual em `api/orchestrator_service.py:_assemble_narrator_context` e reutilizar `api/context_service.py:assemble_context` para visibilidade, orçamento e desempate. Não concatenar catálogos antes da seleção. Depende de TASK-021. | [x] | 2026-09-20 |
| TASK-023 | Substituir o corte de `api/orchestrator_service.py:_scene_query_static_lore` pelo mesmo produtor/política, incluindo todos os NPCs reconhecidos como candidatos independentes. Depende de TASK-021 e TASK-022. | [x] | 2026-09-20 |
| TASK-024 | Garantir que a montagem final de H6 contenha somente os fatos selecionados, sem catálogo integral, duplicação ou conteúdo omitido por posição; preservar fatos canônicos obrigatórios, segredos e a admissão improvisacional. Depende de TASK-022 e TASK-023. | [x] | 2026-09-20 |

### Implementation Phase 5

- GOAL-006: Fundamentar H4 nos catálogos e eliminar drift de contratos sem alterar
  a topologia de modelos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-025 | Criar lookup tipado em `api/catalog_service.py` que retorna fatos, fontes, cobertura e limitações para uma pergunta de lore; consulta desconhecida deve produzir `not_covered`, não texto inventado. Depende de GOAL-002. | [x] | 2026-09-20 |
| TASK-026 | Refatorar `api/h4_lore_expert_service.py:answer_lore_query` para receber o resultado fundamentado e limitar a resposta aos fatos selecionados; manter no máximo a chamada H4 atual e nenhuma chamada H6. Depende de TASK-025 e DEC-004. | [x] | 2026-09-20 |
| TASK-027 | Separar, em contrato e testes, Q&A fundamentado de enriquecimento atmosférico opcional; este último não pode criar mecânica, remover limitações nem transformar inferência em fato. Depende de TASK-026 e DEC-004. | [x] | 2026-09-20 |
| TASK-028 | Após DEC-002, tornar uma única representação a fonte de verdade de H0/H1/H4/H6 e fazer o runtime carregá-la ou gerá-la deterministicamente; remover somente duplicação comprovada. Depende de DEC-002. | [x] | 2026-09-20 |
| TASK-029 | Após DEC-003, atualizar `skills/H2_vtm_relational.md` para a persistência transacional vigente ou marcá-lo formalmente como descontinuado; não reintroduzir persistência JSON. Depende de DEC-003. | [x] | 2026-09-20 |

### Implementation Phase 6

- GOAL-007: Provar integridade, completude, seleção correta e ausência de chamadas
  LLM nos caminhos determinísticos.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-030 | Implementar os testes TEST-001 a TEST-010 em arquivos dedicados; substituir as asserções de `test_perf_sec.py` que tratam omissão por posição como comportamento correto. Depende de GOAL-002 a GOAL-006. | [x] | 2026-09-20 |
| TASK-031 | Executar primeiro testes de catálogo/serviço, depois integração de turno e, por fim, a suíte offline completa com dotenv, rede e bytecode desativados; não instalar dependência. Depende de TASK-030. | [x] | 2026-09-21 |
| TASK-032 | Inspecionar `git diff --check`, diff completo e arquivos não rastreados; provar ausência de `.env`, segredo, conteúdo integral de livro, alteração de provedor/modelo e mudança no limite de chamadas. Depende de TASK-031. | [x] | 2026-09-21 |
| TASK-033 | Atualizar `v5_support_matrix.json` somente com evidência de testes; entradas parciais ou sem fonte permanecem explicitamente `partial` ou `unsupported`. Depende de TASK-031 e TASK-032. | [x] | 2026-09-21 |
| TASK-034 | Solicitar aceitação humana final com inventário suportado, limitações, resultados de testes e decisões preservadas. Nenhum campo do plano é marcado concluído antes da evidência correspondente. Depende de TASK-033. | [x] | 2026-09-21 |

## 3. Alternatives

- **ALT-001**: Criar uma skill ou um modelo por clã, arma ou poder. Rejeitada
  porque multiplica prompts e chamadas sem resolver integridade referencial; itens
  de domínio permanecem dados locais e modelos futuros só podem ser separados por
  papel cognitivo mediante decisão própria.
- **ALT-002**: Enviar todos os catálogos a H6. Rejeitada por desperdiçar contexto,
  reduzir relevância, aumentar risco de conflito e transferir seleção de fatos ao
  modelo.
- **ALT-003**: Manter `blocks[:3]` e apenas reordenar os blocos. Rejeitada porque
  outra combinação volta a perder informação; obrigatoriedade e orçamento não são
  equivalentes à posição.
- **ALT-004**: Usar embeddings, busca vetorial ou serviço externo. Rejeitada para
  o inventário atual porque acrescenta tecnologia, dependência e estado sem ganho
  necessário sobre seleção local determinística.
- **ALT-005**: Pedir a H4 ou H6 que complete regras e fatos ausentes. Rejeitada
  porque viola a autoridade do motor e torna cobertura impossível de auditar.
- **ALT-006**: Expandir para todo o conteúdo V5 antes de testar o inventário atual.
  Rejeitada porque aumenta a lacuna entre catálogo e suporte real.
- **ALT-007**: Inserir `_meta` na raiz de cada JSON existente. Não escolhida porque
  os loaders atuais tratam toda chave raiz como entrada; o manifesto sidecar reduz
  a migração e mantém reversibilidade.
- **ALT-008**: Adicionar agora um segundo modelo para planejar a cena. Rejeitada
  neste plano; H6 único permanece até que avaliações demonstrem uma falha cognitiva
  específica independente da falta de dados.

## 4. Dependencies

- **DEP-001**: `plan/architecture-llm-memory-turns-1.md`, concluído, fornece
  `ContextItem`, orçamento, visibilidade, eventos, memória e commit transacional.
- **DEP-002**: `spec/spec-improvisational-scene-direction.md` define a autoridade
  atual entre fatos vinculantes, ficção improvisável e admissão.
- **DEP-003**: Sete catálogos em `data/catalogs/` e os serviços locais que os
  consomem; o plano não pressupõe novos pacotes ou infraestrutura.
- **DEP-004**: Pydantic v2, Python, pytest e o fake gateway já existentes.
- **DEP-005**: DEC-001 e DEC-005 bloqueiam a conclusão de GOAL-002/GOAL-004;
  DEC-002 a DEC-004 bloqueiam apenas as tarefas explicitamente dependentes.
- **DEP-006**: Fontes editoriais aprovadas e análise de licença separada são
  necessárias antes de adicionar ou completar conteúdo V5.
- **DEP-007**: A implementação requer autorização humana futura; `AUT-001` define
  autonomia depois desse gatilho, não antes.

## 5. Files

- **FILE-001**: `plan/architecture-deterministic-context-catalogs-3.md` — único
  arquivo alterado nesta tarefa documental.
- **FILE-002**: `data/catalogs/clans.json`, `weapons.json`, `disciplines.json`,
  `predator_types.json`, `blood_potency.json`, `npc_hierarchy.json` e
  `progression_costs.json` — dados existentes a validar/completar futuramente.
- **FILE-003**: `data/catalogs/v5_support_matrix.json` — matriz versionada proposta.
- **FILE-004**: `data/catalogs/catalog_manifest.json` — sidecar de proveniência
  proposto.
- **FILE-005**: `api/catalog_models.py` e `api/catalog_service.py` — contratos e
  registro local propostos.
- **FILE-006**: `api/lore_service.py`, `api/context_service.py` e
  `api/orchestrator_service.py` — produção, seleção e montagem de contexto.
- **FILE-007**: `api/clan_service.py`, `api/combat_service.py`,
  `api/discipline_service.py`, `api/physiology_service.py`, `api/npc_service.py`,
  `api/progression_service.py` e `api/rules_service.py` — consumidores
  determinísticos e autorização.
- **FILE-008**: `api/h0_controller_service.py`, `api/parser_service.py` e
  `api/h4_lore_expert_service.py` — alinhamento futuro de contratos e H4
  fundamentado.
- **FILE-009**: `data/schema_save.json` — referências e compatibilidade de ficha.
- **FILE-010**: `skills/H0_vtm_orchestrator.md`, `H1_vtm_rules_parser.md`,
  `H2_vtm_relational.md`, `H4_vtm_lore_expert.md` e `H6_vtm_narrator.md` — fonte
  contratual a alinhar somente após DEC-002/DEC-003.
- **FILE-011**: `tests/test_catalog_integrity.py`,
  `tests/test_discipline_service.py`, `tests/test_combat_service.py`,
  `tests/test_sheet_and_progression_catalog_refs.py`,
  `tests/test_lore_selection.py` e
  `tests/test_deterministic_paths_do_not_call_llm.py` — suítes futuras dedicadas.
- **FILE-012**: `tests/test_context_service.py`, `tests/test_perf_sec.py`,
  `tests/test_turn_pipeline_integration.py` e
  `tests/test_llm_service_integration.py` — regressões e integração existentes.

## 6. Testing

- **TEST-001**: `test_all_entries_validate_against_versioned_schema` valida os
  sete catálogos com `extra="forbid"`, tipos, faixas e versões esperadas.
- **TEST-002**: `test_catalog_ids_aliases_and_cross_references_are_unique` detecta
  colisões após normalização e exige que família, poder, clã, ficha, pré-requisito
  e progressão apontem para IDs existentes.
- **TEST-003**: `test_supported_subset_matrix_matches_catalog_and_tests` falha se
  uma entrada marcada suportada não possuir regra, fonte, teste positivo, teste
  negativo e limitação explícita quando aplicável.
- **TEST-004**: Matriz parametrizada cobre cada poder do subconjunto para conhecido,
  desconhecido, possuído, não possuído, nível, pré-requisito, Rouse, Fome, pool,
  modificador e efeito; qualquer ID inválido falha antes da rolagem.
- **TEST-005**: Matriz parametrizada cobre cada arma do subconjunto para pool,
  autorização de inventário, dano, tipo, alvo e efeito especial; categoria
  desconhecida nunca equivale a `unarmed` ou bônus zero.
- **TEST-006**: Ficha/progressão rejeita clã, predador, família, poder, atributo,
  habilidade, potência e categoria desconhecidos; falha preserva XP e ficha byte a
  byte na representação serializada.
- **TEST-007**: Combinação predador + clã + poder + arma + múltiplos NPCs usa o
  orçamento real configurado, inclui todos os obrigatórios, escolhe opcionais por
  relevância e produz omissões auditáveis com desempate estável.
- **TEST-008**: Investigação sem arma explícita não inclui `unarmed`; combate
  desarmado inclui a categoria quando ela é mecanicamente relevante. Clã não entra
  apenas por posição e NPC/poder explícito não pode ser descartado pelo índice.
- **TEST-009**: Lookup H4 responde apenas com fatos e fontes cobertos, marca
  `not_covered` quando necessário, nunca cria mecânica e mantém consulta direta sem
  chamada H6.
- **TEST-010**: Sentinela no runtime LLM prova zero chamadas para carga/consulta de
  catálogo, validação de ficha, regras, progressão e seleção de contexto; o perfil
  padrão mantém H0/H1 locais, H4-action desligado e exatamente uma chamada H6 no
  turno ficcional válido.
- **TEST-011**: Testes de segurança provam filtragem de visibilidade antes do score,
  ausência de prompts/segredos nos diagnósticos e ausência de rede em toda a suíte
  de catálogo.
- **TEST-012**: Teste de proveniência exige manifesto completo, hash correspondente
  e metadados aprovados para cada catálogo/entrada suportada, sem afirmar legalidade
  além da análise registrada.
- **TEST-013**: Validação futura executa, no mínimo,
  `.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider` para as seis novas
  suítes, os quatro arquivos de regressão listados em FILE-012 e depois a suíte
  offline completa.
- **TEST-014**: Critério de aceite final: nenhum `blocks[:3]`; nenhuma inclusão de
  `unarmed` por default irrelevante; nenhuma entrada suportada parcial; nenhum ID
  desconhecido aceito; nenhum cálculo pelo LLM; nenhum segundo modelo; topologia de
  chamadas e fronteiras de improviso preservadas.

## 7. Risks & Assumptions

- **RISK-001**: Cobertura aparente pode ser confundida com regra correta. A matriz
  separa presença, implementação e teste para impedir essa promoção.
- **RISK-002**: Unificar família/poder pode invalidar saves antigos se a leitura
  compatível não vier antes da validação estrita.
- **RISK-003**: Aliases sem namespace podem colidir entre poder, família, NPC e
  arma; normalização precisa reportar ambiguidade e falhar fechada.
- **RISK-004**: Itens obrigatórios podem exceder o orçamento. A falha explícita é
  preferível à narrativa sem fatos vinculantes; qualquer aumento de orçamento é
  decisão separada.
- **RISK-005**: A estimativa atual por caracteres não equivale ao tokenizer de todo
  provedor. O plano exige consistência determinística, não precisão monetária.
- **RISK-006**: Alterar H4 sem fixar sua fronteira pode misturar fato e atmosfera;
  DEC-004 bloqueia essa etapa.
- **RISK-007**: Texto derivado de material V5 pode possuir restrições autorais. O
  manifesto de proveniência não substitui revisão legal e não autoriza reprodução.
- **RISK-008**: O worktree contém muitas mudanças prévias. A futura execução deve
  preservar arquivos do usuário e evitar refatoração oportunista.
- **RISK-009**: Atualizar apenas a documentação Markdown não elimina drift se o
  runtime continuar usando prompt inline; DEC-002 exige uma fonte operacional.
- **ASSUMPTION-001**: Os inventários observados em 2026-09-05 são o baseline, não
  uma promessa de suporte completo.
- **ASSUMPTION-002**: O registro e a seleção permanecem locais no monólito modular
  e podem ser implementados com bibliotecas já instaladas.
- **ASSUMPTION-003**: Eventos passados e resultados mecânicos permanecem
  imutáveis; somente novos fatos admitidos evoluem cena e mundo.
- **ASSUMPTION-004**: H6 pode improvisar apresentação e continuidade, mas recebe
  fatos vinculantes somente depois da seleção determinística.

## 8. Related Specifications / Further Reading

- [Plano concluído de LLM, memória e turnos](architecture-llm-memory-turns-1.md)
- [Especificação de direção improvisacional](../spec/spec-improvisational-scene-direction.md)
- [Contrato H0](../skills/H0_vtm_orchestrator.md)
- [Contrato H1](../skills/H1_vtm_rules_parser.md)
- [Contrato H2](../skills/H2_vtm_relational.md)
- [Contrato H4](../skills/H4_vtm_lore_expert.md)
- [Contrato H6](../skills/H6_vtm_narrator.md)
- [Seletor contextual atual](../api/context_service.py)
- [Produtor de lore atual](../api/lore_service.py)
