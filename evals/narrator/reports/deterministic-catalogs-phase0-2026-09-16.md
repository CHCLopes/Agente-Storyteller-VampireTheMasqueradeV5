# Catálogos determinísticos — Fase 0

## Escopo e preflight

A frente foi escolhida pelo usuário em 16/09/2026. O trabalho ocorreu no worktree
`codex/planejamento-agente-storyteller-v5`, preservando as alterações acumuladas.
`state/PROJECT_STATE.md` não existe. Nenhum `.env`, segredo ou credencial foi
lido, impresso ou alterado. Nesta fase não houve edição dos sete catálogos V5.

## Inventário programático

| Catálogo | Entradas | Campos | Consumidores observados | Cobertura observada | Lacunas materiais |
|---|---:|---|---|---|---|
| `clans.json` | 16 | `engine_data`: `bane_severity_multiplier`, `compulsion_dice_penalty`, `favored_disciplines`; `narrative_data`: seis campos | `clan_service`, `lore_service`, `orchestrator_service` | carga tipada, lore e penalidade de compulsão | disciplinas favorecidas, multiplicador de bane e penalidade comportamental não têm aplicação completa |
| `weapons.json` | 10 | quatro campos mecânicos e três narrativos | `combat_service`, `lore_service`, `orchestrator_service` | modificador de dano e agravado são consumidos | tipo e ocultabilidade não governam resolução; ID desconhecido equivale a bônus zero |
| `disciplines.json` | 8 | cinco campos mecânicos e dois narrativos | `discipline_service`, `lore_service`, `orchestrator_service` | custo, requisitos parciais, agravado e modificadores especiais | não declara família, nível ou IDs de pré-requisito; `dice_bonus_stat` não é consumido; há hardcodes por poder |
| `predator_types.json` | 5 | `hunting_pool`, ressonância e dois campos narrativos | `physiology_service`, `lore_service` | carga tipada e método narrativo em alimentação | pool e preferência de ressonância não entram no motor |
| `blood_potency.json` | 11 | surge, cura, bane e rerrolagem | `physiology_service`, `orchestrator_service` | surge e cura são consumidos | severidade de bane e nível de rerrolagem não estão ligados à regra correspondente |
| `npc_hierarchy.json` | 9 | cinco campos mecânicos e três narrativos | `npc_service`, `lore_service`, `scene_resolution_service` | aliases limitados, contexto narrativo e adaptação de cena | uso mecânico é parcial; catálogo genérico não representa objetivos/limites de NPC individual |
| `progression_costs.json` | 7 | custo base, multiplicador e descrição | `progression_service`, endpoints em `main` | cálculo de custo e mutação de ficha | categoria/trait/nível desconhecido não falha fechado; custo zero pode autorizar mutação inválida |

Os catálogos não possuem `schema_version` nem manifesto de fonte, edição, página,
licença, revisão ou hash. Cada loader mantém cache próprio e os aliases não têm
registro referencial único. `lore_service.get_contextual_lore` e
`orchestrator_service._scene_query_static_lore` ainda aplicam cortes posicionais
antes da política de orçamento. O default `unarmed` pode competir por contexto
mesmo sem seleção explícita de arma.

## Topologia de chamadas congelada

O perfil padrão mantém `llm_h0_enabled=false`, `llm_h1_enabled=false` e
`llm_h4_action_enrichment_enabled=false`. Um turno ficcional observado em teste
usa uma única `H6.direct_scene`. A consulta direta de lore exercitada usa H4 e
nenhuma H6; no teste que habilita H0 explicitamente, a proveniência é
`h0.triage` seguida de `h4.answer_lore_query`.

Verificação corrigida: **4 testes passaram**, zero falhas e três avisos de
ambiente já conhecidos. A primeira invocação de pytest não executou testes porque
um nome de caso não existia; ela não constitui falha de produto.

## Conclusão

TASK-001, TASK-002 e TASK-004 estão concluídas. O inventário confirma o problema
arquitetural sem alterar dados ou runtime. TASK-003 depende das cinco decisões do
brief. Nenhuma fase dependente está autorizada por inferência deste relatório.
