---
goal: Implementar a fundação da direção B e um piloto de continuidade com fontes narrativas integrais
version: 1.0
date_created: 2026-09-07
last_updated: 2026-09-07
owner: Codex
status: 'Completed'
tags: [architecture, narrative, grounding, memory, evaluation]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-green)

A direção B foi aprovada pelo usuário em 07/09/2026: “Concordo. A direção B parece mais promissora. Prossiga”. Este incremento separa identificação de fonte, identidade textual e autoridade da representação, implementa uma fundação pura e prepara um piloto delimitado antes de integrar o contrato ao turno do produto. A autorização contínua cobre essas etapas e novas observações necessárias; não pedir novamente a decisão B.

O caminho positivo inicial é `projected_source`: conservar a narrativa integral como fonte atribuída, com verdade geral não avaliada. A identidade do texto não autoriza `canonical_assertion`. Uma paráfrase livre permanece indeterminada. O plano não promete resolver implicação semântica geral, não declara que a direção B inteira já está integrada e não reabre a sequência encerrada de refinamentos SYSTEM.

## 1. Requirements & Constraints

- **REQ-001**: `api/narrative_grounding.py` deve definir `NarrativeSource`, `DerivationBinding`, `DerivationAssessment` e `SourceProjection` imutáveis, com versões próprias, sem alterar `FrozenRecord.schema_version=1.0`.
- **REQ-002**: A fonte é o `n` integral efetivamente recebido após a normalização explícita do envelope, separado de `q`. Guardar source/session/turn/invocation, texto UTF-8, hash do texto, política de admissão da fonte e visibilidade. Não chamar esse texto normalizado de corpo HTTP bruto.
- **REQ-003**: O binding vincula as identidades, hash da fonte e do derivado, fingerprint canônico de todos os metadados da fonte e destino fechado. Nenhum caminho arbitrário, aprovação ou referência fornecida pelo modelo concede autoridade.
- **REQ-004**: Assessment separa referência, correspondência textual, estado semântico, decisão e código fechado, com versão da política. `SOURCE_ONLY` é representação atribuída, distinta de `INDETERMINATE` e `REJECTED`; nunca equivale a fato confirmado.
- **REQ-005**: Igualdade integral, sem normalização adicional, permite somente `NARRATIVE_SOURCE_VIEW`. Mesmo texto com destino `CANONICAL_ASSERTION` fica indeterminado. Substrings, paráfrases, alterações de cor, negação, modalidade ou ordem não recebem projeção integral.
- **REQ-006**: Fonte/hash/contexto inconsistentes são rejeitados; materialização recalcula a avaliação. Um assessment forjado ou reaplicado não deve autorizar conteúdo diferente.
- **REQ-007**: A admissão narrativa anterior e a autenticidade das fontes são premissas do chamador servidor; um hash não as comprova. O módulo puro não adquire fontes, não chama LLM e não decide verdade geral.
- **REQ-008**: O piloto usa um envelope novo `n/q`, em cena sintética conhecida e elenco fixo fornecidos pelo servidor. Outcome deriva dos fatos determinísticos. Novidade permanece na fonte textual; não fabricar `f/t/r` para satisfazer o contrato anterior.
- **REQ-009**: A política do piloto verifica n/q, agência, sigilo, mecânica e limites antes de criar a fonte. Usar uma view privada de política somente para reaproveitar verificações existentes; nenhum `model_construct`, fato fictício, projeção canônica ou gravação de campanha.
- **REQ-010**: Contexto do segundo pedido contém a fonte anterior integral em seção atribuída, separada dos dados canônicos da fixture. Pergunta anterior não entra na fonte. Fontes fora da audiência ou com binding inválido são recusadas antes do pedido. Neste piloto, cena com resumo/detalhes/pendências anteriores é recusada; no máximo duas fontes de 40–1600 caracteres, contexto até 12.000 caracteres e USER até 2000 tokens estimados, sem corte.
- **REQ-011**: Piloto vivo: uma cena nova, dois turnos fixos, Qwen/Groq gratuito explícito já usado; máximo duas chamadas de 768 tokens, temperatura 0,65, raciocínio none, espera inicial/intervalo/deadline 60 s. Primeiro erro operacional/política interrompe a cadeia e registra skip do dependente; não repetir, reparar resposta, trocar alvo ou julgar com outra LLM.
- **REQ-012**: Registrar parâmetros, fonte canônica sintética, hashes de SYSTEM/USER/schema/código, invocações, respostas literais, decisão de representação e uso/custo. O USER do segundo turno depende da primeira fonte admitida: registrar sua construção exata; não alegar dois pedidos idênticos nem A/B causal.
- **REQ-013**: Separar sucesso estrutural/projeção de avaliação autorada de agência, continuidade e qualidade. Conservação por construção não é resultado de fidelidade abstrativa do modelo. CAP-001/runtime permanecem sem promoção.
- **REQ-014**: O plano de integração posterior deve cobrir evento, candidato, memória, cena quente, fatos reservados, consolidação e contexto direto de H6. Proteger apenas a memória episódica é insuficiente.
- **REQ-015**: Legado v1 continua histórico e não avaliado por v2. Não regravar, reclassificar ou migrar saves automaticamente; não presumir assessment por `validation_status=accepted`. Uma dependência legada incompatível deverá falhar explicitamente no futuro modo v2 antes da chamada, sem fingir cena vazia.
- **SEC-001**: Nunca ler `.env`, expor chave ou recuperar credencial antiga. Chave somente via prompt local protegido depois de toda preparação. Nenhum dado de campanha.
- **CON-001**: Trabalhar exclusivamente neste worktree; preservar alterações anteriores, brutos e critérios históricos. Sem servidor, instalação, mudança global, commit/PR ou migração como efeito colateral.
- **CON-002**: Não implementar um classificador semântico geral, parser de linguagem, juiz LLM ou chamada extra obrigatória. ALT-004 continua válida.
- **CON-003**: Integração do modo B ao produto não pode entregar narrativa com memória indeterminada por omissão: a regra vigente é rejeitar antes de `on_chunk`/mutação/commit e não consumir turno. O piloto de fonte atribuída não é uma exceção de admissão de derivado indeterminado.
- **CON-004**: O primeiro incremento não implementa `confirmed_canonical` para novidades livres. Projeções tipadas de fatos do domínio exigem regras enumeradas e contraprovas próprias na integração posterior; não inferir uma regra universal de cópia.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Fechar a autoridade da projeção integral em código puro. Término verificado: módulo e 24 testes focados passaram, com revisão independente, sem imports ou mudanças no caminho de turno legado.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Registrar aprovação B no memo e na retomada; preservar os resultados anteriores. | Sim | 2026-09-07 |
| TASK-002 | Implementar os quatro tipos e factories/evaluate/materialize em `api/narrative_grounding.py`, conforme REQ-001 a REQ-007. | Sim | 2026-09-07 |
| TASK-003 | Criar `tests/test_narrative_grounding.py` com fonte integral, destino canônico, transformações, adulteração, versão, visibilidade e projeção forjada; executar somente após freeze. Depende de TASK-002. | Sim | 2026-09-07 |
| TASK-004 | Revisar diff, erros seguros, fingerprints, limites de autoridade e ausência de import no runtime; registrar prova em relatório pertinente. Depende de TASK-003. | Sim | 2026-09-07 |

### Implementation Phase 2

- GOAL-002: Oferecer caminho positivo coerente para fonte narrativa em cena conhecida, sem fabricar campos derivados. Término verificado: 57 casos distintos verdes no perfil puro; fonte n/q válida é aceita e contrato, agência, sigilo e contexto inválido são recusados. A fonte atribuída fica separada do cânone.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Criar `scripts/narrator_source_profile.py`: envelope n/q estrito, view privada de política com outcome/l/p do servidor, s vazio e f/t/r vazios; aplicar verificações existentes sem canonizar a view. Fonte exige cena conhecida no piloto; abertura sem cena fica explicitamente fora deste primeiro recorte. | Sim | 2026-09-07 |
| TASK-006 | Criar `tests/test_narrator_source_profile.py`: caminho positivo, envelope com derivado extra recusado, n/q separados, agência/sigilo/mecânica, cena ausente, fonte adulterada e audiência. Depende de TASK-002 e005. | Sim | 2026-09-07 |
| TASK-007 | Verificar construção do contexto atribuído, contagem/orçamento sem corte e nenhuma promoção a CanonicalFact/EpisodicMemory/CONHECIDO. Registrar a mudança deliberada em relação ao contrato f/t/r. Depende de TASK-006. | Sim | 2026-09-07 |

### Implementation Phase 3

- GOAL-003: Preparar e observar uma cadeia nova de duas fontes narrativas integrais, sem continuar o loop de resumo abstrativo. Término: preparação auditada antes da chave; depois duas posições ou primeira falha, análise e encerramento sem repetição.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-008 | Escrever `evals/narrator/prompts/narrative-source-v1.md`, `evals/narrator/narrative_source_case_v1.json` e relatório de desenho antes do envio. Cena canônica sintética nova, sem NPC, uma observação sem toque seguida de espera no lugar; autorizar somente n/q e atribuição integral como fonte. | Sim | 2026-09-07 |
| TASK-009 | Implementar `scripts/evaluate_narrator_source.py` com o manifesto/observer existentes, protocolo/source profile novo, no máximo duas chamadas, dependência da fonte anterior, parada/skip explícitos e artefatos fora de CAP. Criar testes focados de execução e recusa de replay; não importar módulos experimentais de retorno antigo como fonte canônica. Depende de TASK-007 e008. | Sim | 2026-09-07 |
| TASK-010 | Criar `scripts/run_groq_narrative_source_probe.ps1` a partir do padrão seguro existente; preflight sem chave, integração com chave vazia, descarte de SecureString, saída conferida e nenhum retry. Congelar hashes e testar limites antes de abrir uma única janela protegida. Depende de TASK-009. | Sim | 2026-09-07 |
| TASK-011 | Executar a observação apenas após entrada protegida da credencial. Auditar literalidade, origem, fonte-contexto, pacing/rota/uso e revisão autorada de continuidade/agência. Encerrar sem repetição e sem comparar causalmente aos resumos históricos. Depende de TASK-010. Resultado:1 chamada/rejeição q e1 skip; cadeia não observada; lote encerrado sem repetição. | Sim | 2026-09-07 |

### Implementation Phase 4

- GOAL-004: Especificar o encaixe no turno com base no piloto concluído. Término: plano de integração concreto e revisado, sem migração ou ativação por arrasto; qualquer código de integração terá tarefas/testes definidos antes da edição.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-012 | Após TASK-011, consolidar implicações em `api/turn_execution_service.py` (antes da admissão/entrega), `api/memory_service.py` (assessment vinculado), `api/persistence.py` (pareamento/digest JSON), `api/scene_service.py`/`api/orchestrator_service.py`/`api/context_service.py` (todas as rotas de leitura). Enumerar projeções canônicas tipadas permitidas; até haver regra, derivação livre permanece indeterminada. Desenho inspecionado e revisado; código de integração futuro. | Sim | 2026-09-07 |
| TASK-013 | Definir testes de abertura sem cena, continuidade multietapas, fontes v1 incompatíveis, n completo acima de600 caracteres, rollback/idempotência e fronteiras de audiência. A fonte referenciada deve evitar cortes silenciosos ou expansão automática dos limites antigos. Atualizar o plano antes de integrar; nenhuma alteração do default do produto neste piloto. Depende de TASK-012. Matriz de 14 controles futuros documentada e revisada; implementação futura. | Sim | 2026-09-07 |

### Implementation Phase 5

- GOAL-005: Corrigir o falso negativo comprovado e preparar uma coleta suplementar da passagem entre fontes, ainda não observada no lote encerrado. Nenhum retry ou preenchimento de skip antigo.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-014 | Corrigir família delimitada "O que fazes?" mantendo agência/sigilo/mecânica/interlocutor; RED e274 testes focados,30 novos. Preservar resultado f97. | Sim | 2026-09-07 |
| TASK-015 | Preparar caso novo Pátio com mesmo SYSTEM/perfil, seleção fechada no executor/wrapper e recusa de live da Estufa antes da credencial.66 testes finais de executor/wrapper, incluindo integração real de chave vazia. | Sim | 2026-09-07 |
| TASK-016 | Executar e auditar no máximo duas posições Pátio ou primeira falha, sem retry/reformulação em série. Chave somente no prompt protegido da janela já aberta. Depois analisar implicações e avançar o incremento local delineado no desenho de integração. | Sim:2 chamadas,1fonte admitida,segunda recusada; lote encerrado | 2026-09-07 |

As TASK-012/013 encerraram o **desenho** em [integração B](../evals/narrator/reviews/narrative-source-integration-design-2026-09-07.md). A ponte local subsequente foi implementada e verificada no [plano próprio](architecture-narrative-source-bridge-1.md): 85 casos de contrato, 29 de persistência B, 7 legados e 31 integrados passaram em rodadas focadas. Isso não encerra todos os leitores/rotas do desenho mais amplo nem ativa default ou saves reais. O Pátio permanece uma evidência separada: primeira fonte preservada no segundo USER, segunda resposta recusada pelo limite correto de palavras. Este plano conclui seu escopo de fundação, piloto e desenho; não marca a direção B inteira como pronta para o produto.

## 3. Alternatives

- **ALT-001**: Continuar alterando somente SYSTEM de resumo. Não selecionada: hipótese encerrada com erro/ambiguidades e sem demonstração de ganho geral.
- **ALT-002**: Aceitar citação, substring, similaridade lexical ou fragmento como prova de fidelidade. Não selecionada: o contexto integral pode mudar modalidade, negação, participante ou pressuposto.
- **ALT-003**: Copiar n para s/f para contornar o gate antigo. Não selecionada: recipientes têm limites e autoridade diferentes, e o fato teria semântica além de origem textual.
- **ALT-004**: Juiz/inferência obrigatória adicional por turno. Não selecionada; preserva a rejeição desse padrão no plano de arquitetura anterior.
- **ALT-005**: Desativar imediatamente todos os turnos legados ou declarar os registros antigos aprovados por v2. Não selecionada: exige compatibilidade e mudança explícita, não decorre do piloto.

## 4. Dependencies

- **DEP-001**: Python/Pydantic/pytest e PowerShell7 já disponíveis; nenhuma instalação ou dependência nova.
- **DEP-002**: Política narrativa existente e conftest com isolamento/rede bloqueada. O piloto novo usa suas verificações como limites, sem afirmar prova semântica geral.
- **DEP-003**: Alvo Groq/Qwen explícito, manifesto e observador existentes. Nenhuma credencial é necessária nas fases1/2 ou na preparação da fase3.
- **DEP-004**: Entrada protegida da chave é dependência humana para observações ao vivo TASK-011/016; a chave foi inserida nos dois lotes. Não é nova aprovação de lote ou arquitetura.
- **DEP-005**: Integração do produto depende das evidências do piloto e das condições de compatibilidade em TASK-012/013; CAP-001 e seleção do motor permanecem decisões separadas.

## 5. Files

- **FILE-001**: `api/narrative_grounding.py` e `tests/test_narrative_grounding.py`: fundação pura e regressões.
- **FILE-002**: `scripts/narrator_source_profile.py` e `tests/test_narrator_source_profile.py`: envelope/política/contexto experimentais.
- **FILE-003**: `evals/narrator/prompts/narrative-source-v1.md`, `evals/narrator/narrative_source_case_v1.json` e relatórios de desenho/preparação/resultado: fontes e critérios congelados antes da chamada.
- **FILE-004**: `scripts/evaluate_narrator_source.py`, `scripts/run_groq_narrative_source_probe.ps1` e testes focados correspondentes: execução delimitada e proteção contra replay CAP.
- **FILE-005**: `scripts/evaluate_narrator_models.py`: somente guarda explícita para recusar o protocolo de observação no replay CAP, caso necessária; preservar as guardas históricas.
- **FILE-006**: `evals/narrator/README.md`, `PROMPT_RETOMADA_2026-09-06.md` e memo aprovado: estado durável, limites e próximo passo.
- **FILE-007**: Serviços de turno/memória/persistência/cena/contexto citados em TASK-012 são superfície da integração posterior; não declarados alterados por este piloto.

## 6. Testing

- **TEST-001**: Integral com destino source view é preservado mesmo acima de25 palavras; integral como afirmação canônica fica indeterminado. Os25 não são gate estrutural da fonte.
- **TEST-002**: Modalidade, negação, cor, ordem, fala/antecedente e paráfrase não ganham autoridade por fragmento ou referência correta.
- **TEST-003**: Trocas de sessão/turno/invocação/hash/política/visibilidade, avaliação forjada ou projeção reaplicada não materializam fonte com binding antigo.
- **TEST-004**: n/q estritos; q não é fonte; audiência e cena conhecida conferidas; nenhuma autojustificação por s/f/t/r.
- **TEST-005**: Execução falsa e integração de wrapper verificam limites, espera, deadline, zero chamada antes do preflight, sem retry/repair, skip do dependente e descarte de chave. Conftest e dotenv desabilitado preservados.
- **TEST-006**: Revisão independente do diff e reconstrução dos artefatos; distinguir medição mecânica e julgamento autorado. Executar uma rodada focada final por componente; ampliar somente por alteração, falha ou preocupação concreta.
- **TEST-007**: Futura integração requer caminho positivo de turno e recusa antes de qualquer chunk/commit, fontes históricas sem reclassificação e proteção de cena quente/fatos reservados/consolidação/contexto direto.

## 7. Risks & Assumptions

- **RISK-001**: Identidade integral preserva texto, mas não transforma prosa em prova de mundo, nem garante qualidade, agência ou continuidade geral.
- **RISK-002**: Uma source view pode consumir mais contexto que um resumo. Medir e recusar excesso explicitamente; não truncar e manter status aprovado.
- **RISK-003**: O piloto de cena conhecida não prova abertura, mudança de local/NPC, resolução de pendência ou integração no produto. Esses casos ficam explicitamente na fase4.
- **RISK-004**: Adaptar view de política não pode contornar validação do envelope nem fabricar fatos. Se uma função exigir semântica indisponível, recusar o caso e rever o perfil antes do envio.
- **RISK-005**: Fontes legadas podem contaminar modos novos por caminhos além da memória episódica; exigir proteção de todas as rotas na integração posterior.
- **ASSUMPTION-001**: O servidor fornece fonte/cena/identidades confiáveis ao módulo puro. Fingerprint verifica correspondência com o binding; não autentica um chamador malicioso que substitua todo o conjunto.
- **ASSUMPTION-002**: Separar novidade textual atribuída de interpretações estruturadas oferece um caminho de avaliação útil; isso será observado, não declarado sucesso por construção.

## 8. Related Specifications / Further Reading

- [Direção B aprovada](../evals/narrator/reviews/narrative-memory-grounding-decision-2026-09-07.md)
- [Auditoria da fronteira narrativa–memória](../evals/narrator/reviews/narrative-memory-admission-boundary-2026-09-07.md)
- [Corpus de seis resumos](../evals/narrator/reviews/record-summary-semantic-corpus-v1-2026-09-07.md)
- [Arquitetura LLM, turnos e memória — REQ-015 e ALT-004](architecture-llm-memory-turns-1.md)
- [Direção improvisacional — avanço, fonte e commit](../spec/spec-improvisational-scene-direction.md)

Evidência das fases 1/2 e desenho anterior ao envio: [piloto de fonte integral](../evals/narrator/reports/narrative-source-design-2026-09-07.md), com hashes e provas completas em JSON. A preparação operacional passou em mais 71 casos distintos, totalizando 152; [prova final](../evals/narrator/reports/narrative-source-preparation-2026-09-07.md). TASK-011 foi executada e encerrada após a primeira rejeição de política; [resultado](../evals/narrator/reports/narrative-source-observation-f97a8568-2026-09-07.md). Continuidade entre fontes não observada; correção local da pergunta concluída e TASK-012/013 detalhadas/revisadas; TASK-016 encerrada: primeira fonte integral chegou ao segundo USER; segunda saída155 palavras recusada. Próxima ponte local semnova chamada ao vivo. [Pacote Pátio](../evals/narrator/reports/narrative-source-courtyard-preparation-2026-09-07.md).


Fechamento Pátio: [auditoria f6483710](../evals/narrator/reports/narrative-source-courtyard-observation-f6483710-2026-09-07.md). O incremento local seguinte terá plano e protocolos concretos antes da edição; os resultados ao vivo não serão reclassificados.
