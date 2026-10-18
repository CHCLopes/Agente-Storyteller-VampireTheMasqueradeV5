---
goal: Preservar ações resolvidas e permitir retomada segura quando o Narrador estiver indisponível
version: 1.0
date_created: 2026-09-05
last_updated: 2026-09-22
owner: Codex
status: 'Completed — technical audit and human acceptance closed'
authorization: 'Implementation explicitly approved by the human on 2026-09-21'
decision_state: 'DEC-001-B, DEC-002-B and DEC-003-B approved on 2026-09-21'
tags: [feature, narrator, pause, resume, resilience, websocket, persistence, ux, accessibility]
---

# Introduction

![Status: In progress](https://img.shields.io/badge/status-In_progress-yellow)

Este plano propõe uma experiência de pausa e retomada quando a ação do jogador já
foi aceita — e possivelmente resolvida mecanicamente — mas o Narrador H6 não pode
concluir a cena por uma indisponibilidade transitória. O objetivo é preservar a
intenção e a resolução determinística, informar o estado com clareza e permitir
que a narração seja retomada sem pedir que o jogador repita a ação, sem rerrolar
dados e sem aplicar efeitos duas vezes.

O pacote foi aprovado para implementação em 2026-09-21. Permanecem escolhidos
`DEC-001-B`, `DEC-002-B` e `DEC-003-B`. A implementação não escolhe provedor ou modelo,
não cria fallback automático, não altera política de custo e não aprova retry
pago. O alvo solicitado permanece fixo durante cada tentativa; qualquer mudança
futura de alvo exige fluxo explícito e decisão própria.

A pausa não transforma um rascunho em cânone. Enquanto a narração não for
validada e o turno não for confirmado transacionalmente, ação, rolagem, fatos,
estado e memória permanecem uma proposta congelada. A interface pode mostrar a
rolagem como preservada para retomada, mas deve explicar que seus efeitos ainda
não foram aplicados ao estado da campanha.

O fluxo conceitual comum às alternativas de `DEC-001` é:

```text
local_draft -> availability_gate(exact_target + applicable_rate_limit_scopes)
availability_gate -> gated_wait | received
received -> claimed -> availability_gate -> mechanics_resolved
mechanics_resolved -> availability_gate -> narration_in_progress
narration_in_progress -> completed | gate_update + paused
paused -> resume_eligible
resume_eligible -> [DEC-003-A: probe controlado] probe_requested -> probing -> available | paused
resume_eligible -> [DEC-003-B: sem probe] resume_requested -> direct_resume_trial -> narration_in_progress
available -> resume_requested -> narration_in_progress -> completed | paused
paused -> abandoned | expired
```

`paused` encerra a tentativa de transporte/stream corrente, mas a semântica de
terminalidade da operação depende de `DEC-001`. Em todas as alternativas, somente
o backend pode criar, validar e consumir a cápsula de retomada.

A linha de base atual torna `DEC-001` material: `attempts` mantém uma relação 1:1
entre tentativa e `operation_id`, aceita apenas `pending`, `completed`, `failed`,
`cancelled` e `timeout`, não permite promover uma falha terminal a conclusão e
converte `pending` herdado de outro processo em `cancelled`. Além disso, H6 gera a
resposta estruturada inteira antes de o backend publicar um único delta já
validado; este plano não deve inventar streaming parcial do provedor como premissa.

O gate P0 é uma consulta local persistente, não uma chamada remota antes de cada
estágio. A evidência de disponibilidade que autoriza uma chamada continua presa ao
target exato, enquanto bloqueios de rate limit usam `gate_scope + scope_key`
hierárquicos: plataforma/conta ou credencial correlacionada sem segredo para o
gateway; rota/provedor/target comprovadamente abrangido para o upstream; e escopo
local conservador do target que falhou quando a origem ou o alcance forem
desconhecidos. Ele é consultado antes de toda invocação H0/H1/H4/H6 habilitada e
novamente antes de qualquer rolagem. Resultados normalizados de chamadas
autorizadas atualizam a disponibilidade sem ampliar o alcance por inferência. Uma
sondagem sintética só existe se `DEC-003-A` for aprovada; ela nunca retoma a
narração, rola dados ou confirma o turno automaticamente. Se `DEC-003-B` for
aprovada, não existe probe: a retomada humana autoriza no máximo uma tentativa
direta H6, single-flight, com a cápsula congelada e sem reinvocar H0/H1/H4/RNG.

## 1. Requirements & Constraints

- **REQ-001**: A aplicação deve distinguir indisponibilidade transitória do Narrador de erro de configuração, rejeição de conteúdo, saída inválida, falha interna e cancelamento voluntário. A UI não pode apresentar toda falha como “tente novamente”.
- **REQ-002**: A taxonomia de elegibilidade deve partir de `NormalizedError.category`, `retryable`, `retry_after_seconds`, fase e presença de saída parcial; não deve inferir elegibilidade apenas de texto livre ou código HTTP.
- **REQ-003**: `model_unavailable`, `provider_unavailable`, `rate_limited`, `transport_failure` e `timeout` podem produzir `paused` somente quando a política local os classificar como transitórios e a cápsula passar em todas as validações. `retryable=false` impede oferta de retomada imediata.
- **REQ-004**: `authentication_failed`, `permission_denied`, `payment_required`, `quota_exceeded`, `configuration_invalid`, `unsupported_capability` e `target_mismatch` devem preservar a cápsula quando for seguro, mas bloquear retomada até a configuração ser corrigida. A UI deve comunicar “configuração necessária”, não disponibilidade transitória.
- **REQ-005**: `invalid_request`, `content_rejected` e `context_limit_exceeded` não podem repetir cegamente a mesma solicitação. A ação deve ser abandonada ou encaminhada a um fluxo de correção futuro fora deste plano.
- **REQ-006**: `invalid_structured_output`, `malformed_response`, truncamento e falha de validação narrativa são falhas de saída, não prova de indisponibilidade. Podem ser estudadas para reparo posterior, mas não entram automaticamente na pausa proposta.
- **REQ-007**: Cancelamento voluntário do jogador e abandono explícito são terminais. Desconexão de transporte não equivale automaticamente a abandono; a decisão deve usar o estado persistido e o handshake de reconexão.
- **REQ-008**: A retomada nunca pode recalcular pool, dificuldade, fome, dados, margem, outcome, custos de recurso, dano, relações, fatos ou qualquer transição mecânica já presente na cápsula.
- **REQ-009**: A retomada nunca pode executar novamente RNG. A mesma resolução deve conservar recibo, faces, pool, dados de Fome, dificuldade, sucessos, margem, outcome e proveniência determinística quando esses campos existirem.
- **REQ-010**: Uma ação sem rolagem também deve poder ser pausada; nesse caso a cápsula conserva intenção, fatos determinísticos, contexto e revisão, com recibo mecânico ausente de forma explícita.
- **REQ-011**: A cápsula deve ser imutável, versionada e persistida no servidor. Deve conter, no mínimo: `capsule_id`, `schema_version`, `session_id`, `source_operation_id`, `source_attempt_id`, `turn_id`, `requested_turn`, `state_revision`, hash da solicitação original, ação declarada, `TurnDraft` ou projeção equivalente, resolução/recibo opcional, fatos e referências canônicas, contexto já selecionado ou suas referências congeladas, alvo LLM solicitado, timestamps, motivo normalizado e política de expiração.
- **REQ-012**: A cápsula não deve conter chave de API, headers de autenticação, objeto de transporte, traceback, prompt bruto, resposta bruta do provedor ou segredos não necessários. Contexto confidencial indispensável deve permanecer em armazenamento server-side com visibilidade preservada e nunca voltar ao cliente.
- **REQ-013**: O hash da solicitação e as referências da cápsula devem impedir substituição da ação, da rolagem ou do contexto por payload enviado pelo cliente.
- **REQ-014**: Antes de retomar, o backend deve validar sessão, propriedade da cápsula, estado permitido, expiração, revisão esperada, integridade referencial, target fixo e ausência de conclusão/abandono anterior.
- **REQ-015**: O commit continua atômico: narrativa admitida, eventos, fatos, estado, relações e memória são confirmados uma única vez. Pausa, repetição da pausa ou falha de retomada não alteram o snapshot canônico anterior.
- **REQ-016**: Cliques duplicados, reconexões, refresh e reenvios devem ser idempotentes. Nenhuma corrida pode gerar duas narrativas confirmadas ou consumir a cápsula duas vezes.
- **REQ-017**: A recuperação da sessão deve reidratar a pausa ativa e a cápsula visível ao jogador sem depender de estado exclusivo do navegador.
- **REQ-018**: Apenas uma ação narrativa não resolvida pode bloquear submissão, rolagem e progressão da mesma sessão. Controles locais de consulta, retomada, abandono e recuperação de conexão permanecem operáveis. O comportamento do editor de texto depende de `DEC-002`.
- **REQ-019**: Abandonar uma cápsula descarta somente a proposta não canônica. Não pode desfazer um turno já confirmado nem aplicar os efeitos mecânicos congelados.
- **REQ-020**: Expiração deve ser explícita e auditável. A duração, o comportamento após expirar e qualquer limpeza física são políticas pendentes; nenhuma exclusão destrutiva é autorizada por este plano.
- **REQ-021**: A pausa deve persistir um checkpoint suficiente e liberar o lock da sessão; nenhuma conexão, request, task ou lock pode permanecer aberto aguardando disponibilidade externa. A retomada readquire o lock e usa CAS de revisão.
- **REQ-022**: No pipeline atual, indisponibilidade de H6 ocorre antes de qualquer delta narrativo validado. O plano deve preservar esse comportamento. Regras para chunks parciais ficam apenas como compatibilidade defensiva caso o transporte mude em outra frente autorizada.
- **REQ-023**: Um gate persistente deve combinar evidência de disponibilidade por target exato com bloqueios hierárquicos de rate limit por `gate_scope + scope_key`. Estado `available` de outro modelo, provedor, alias, rota automática ou target anterior nunca autoriza a chamada corrente. Um bloqueio de gateway comprovadamente aplicável à mesma plataforma/conta ou credencial correlacionada deve alcançar todos e somente os targets desse escopo; um bloqueio upstream alcança apenas a rota/provedor/target comprovados; origem ou alcance desconhecidos falham fechados para o target que produziu a evidência e não se propagam como fato para outros targets.
- **REQ-024**: Toda entrada habilitada em H0, H1, H4 ou H6 deve consultar atomicamente o gate local antes do dispatch. Toda ação que possa rolar dados deve consultar o mesmo gate imediatamente antes do RNG, impedindo rolagem quando a continuidade narrativa já está bloqueada.
- **REQ-025**: A consulta do gate não faz rede. Atualizações por resultado de chamada, tentativa direta ou probe aprovado são single-flight pela menor chave de bloqueio aplicável (`gate_scope + scope_key`) e pela cápsula/operação, persistidas atomicamente e recuperáveis após restart. Requisições concorrentes cobertas por um limite de gateway compartilham a mesma lease; um limite upstream não serializa target independente. Um processo reiniciado deve invalidar qualquer lease remoto abandonado sem disparar outra chamada por silêncio.
- **REQ-026**: O gate deve distinguir, no mínimo, `unknown`, `probing`, `direct_resume_trial`, `available`, `cooldown`, `configuration_blocked`, `unavailable` e `stale`. Evidência `available` ainda válida abre dispatch normal ou rolagem apenas para o target exato e na ausência de bloqueio hierárquico aplicável. Quando a retomada estiver elegível — nunca antes de `retry_not_before` confiável, se presente — apenas o caminho aprovado em `DEC-003` pode adquirir atomicamente uma lease single-flight: probe sintético em `DEC-003-A` ou uma única tentativa direta H6 em `DEC-003-B`. Sem timing confiável, a regra de elegibilidade deve ser aprovada junto de `DEC-003`, sem inventar cooldown; `unknown`/`stale` nunca autorizam RNG.
- **REQ-027**: Todo rate limit deve preservar separadamente `rate_limit_origin` como `gateway`, `upstream` ou `unknown`, `gate_scope`, `scope_key` server-side, fonte e confiança, além de janela e reset somente quando comprovados. Para `gateway`, o escopo pode correlacionar plataforma/conta ou credencial por identificador opaco não reversível, nunca pela chave ou por hash simples exposto; para `upstream`, deve permanecer na menor rota/provedor/target demonstrada. Headers e metadados saneados podem provar origem e alcance; nome do modelo, suposição sobre o catálogo ou texto livre não podem. `unknown` usa política local conservadora explícita para bloquear o target que falhou, sem converter essa política em alegação sobre o alcance remoto. `gateway` nunca pode ser reatribuído ao modelo/upstream, e ausência de escopo ou timing não apaga uma origem conhecida. A taxonomia pública usa `rate_limit_unknown_origin` somente quando `rate_limit_origin=unknown`. A UI pode informar a espera comprovada, se houver, mas nunca inventar “cota diária”, “limite diário”, escopo ou renovação.
- **REQ-028**: H4 não pode tratar falha de capacidade como enriquecimento opcional bem-sucedido, retornar apenas `static_lore` e permitir commit do turno. Se H4 foi habilitado e exigido para a operação, a falha deve bloquear antes da rolagem ou produzir pausa sem commit.
- **REQ-029**: Os únicos fallbacks permitidos para H0/H1 são locais, determinísticos e estritamente semânticos: triagem/roteamento seguro e preservação fiel da intenção. Eles não escolhem mecânica, não geram fatos, não simulam H4/H6 e não tornam o gate H6 disponível.
- **REQ-030**: Todo timing de gate deve nascer no servidor em UTC normalizado e incluir `observed_at`, `server_now`, `retry_not_before`, fonte do timing e nível de confiança. Duração usa relógio monotônico no processo; após restart, somente timestamps UTC persistidos e validados podem orientar espera.
- **REQ-031**: `retry_after_seconds`, headers e reset são evidência somente quando saneados e associados à requisição e ao `gate_scope` comprovado. A normalização deve preservar a atribuição comprovada a gateway ou upstream, registrar separadamente `evidence_scope` e qualquer `policy_scope` conservador e manter origem/alcance como `unknown` quando não houver prova. Relógio, countdown ou `retry_at` enviados pelo cliente não têm autoridade; a política nunca amplia um alcance remoto como se fosse evidência.
- **REQ-032**: Funções locais que não mutam o turno — ficha, histórico, catálogos já carregados, acessibilidade, navegação e rascunho conforme `DEC-002` — devem continuar disponíveis sem chamada LLM. Nenhuma delas pode contornar o bloqueio de submissão/rolagem.

Taxonomia P0 proposta, ainda sujeita ao gate humano:

| Classe de produto | Categorias normalizadas de origem | Estado/ação permitida |
|---|---|---|
| Disponibilidade transitória | `model_unavailable`, `provider_unavailable`, `transport_failure`, `timeout` | `cooldown`/`paused` somente com `retryable=true`; sem retry automático |
| Rate limit do gateway | `rate_limited`, `rate_limit_origin=gateway` comprovado | `evidence_scope` vem somente de metadado saneado; enforcement por `gate_scope=gateway_account` e `scope_key` opaco bloqueia todos e somente os targets da plataforma/conta ou credencial comprovadamente correlacionada; nunca atribuir a cota ao upstream/modelo |
| Rate limit upstream | `rate_limited`, `rate_limit_origin=upstream` comprovado | enforcement por `gate_scope=upstream_target` fica na menor rota/provedor/target comprovada; não bloqueia target independente; `cooldown` até `retry_not_before` quando confiável |
| Rate limit de origem desconhecida | `rate_limited`, `rate_limit_origin=unknown` | motivo público `rate_limit_unknown_origin`; `evidence_scope=unknown`; política conservadora aplica `gate_scope=unknown_conservative` ao grupo de credencial/gateway já conhecido localmente ou, sem essa correlação, ao target que falhou, sempre rotulada como política e nunca como alcance reportado |
| Capacidade/conta bloqueada | `quota_exceeded`, `payment_required` | `configuration_blocked`; exige decisão/correção humana, sem fallback |
| Acesso/configuração | `configuration_invalid`, `unsupported_capability`, `authentication_failed`, `permission_denied`, `target_mismatch` | bloqueado até correção explícita; não sondar repetidamente |
| Solicitação/conteúdo | `invalid_request`, `content_rejected`, `context_limit_exceeded` | não repetir a mesma solicitação; correção ou abandono |
| Saída inválida | `invalid_structured_output`, `malformed_response` | falha de saída, separada de indisponibilidade; sem pausa automática |
| Cancelamento | `cancelled` | terminal quando voluntário; desconexão é classificada pelo estado persistido |
| Falha interna/desconhecida | `adapter_failure`, `unknown` | falhar fechado, diagnóstico seguro e nenhuma sondagem cega |

- **UX-001**: A interface deve mostrar um cartão persistente “Narração pausada” próximo à ação afetada, com ação original, resumo seguro da resolução, motivo compreensível, estado dos efeitos e próximo passo.
- **UX-002**: A mensagem principal deve afirmar que a ação e a rolagem foram preservadas e que os dados não serão lançados novamente. Se os efeitos ainda não foram confirmados, isso deve aparecer em linguagem de produto, sem jargão transacional.
- **UX-003**: O controle primário deve ser “Retomar narração”. Quando houver `retry_not_before` confiável, deve permanecer indisponível até o prazo calculado com referência ao servidor, exibir a espera e habilitar-se sem recarregar a página.
- **UX-004**: O controle secundário deve ser “Descartar ação”; a confirmação deve explicar que a resolução preservada não será aplicada. Erros de configuração devem oferecer instrução segura para corrigir o alvo antes da retomada, sem solicitar chave no chat ou exibi-la na interface narrativa.
- **UX-005**: A UI não deve exibir chunks provisórios como narrativa confirmada. Se houver texto parcial, ele deve ser removido da área canônica ou claramente marcado como tentativa não confirmada.
- **UX-006**: A retomada bem-sucedida deve substituir o cartão de pausa pela narrativa e pelo recibo confirmados sem duplicar a fala do jogador ou a rolagem.
- **UX-007**: Falha de uma retomada elegível deve atualizar a mesma frente visível, conservar a cápsula e apresentar o novo motivo/tempo de espera; não deve criar uma sequência de mensagens de erro indistinguíveis.
- **UX-008**: A UI deve derivar countdown de `server_now` e `retry_not_before`, tolerar clock local divergente e nunca converter `rate_limit_unknown_origin` em alegação de cota diária.
- **UX-009**: Em `DEC-003-A`, “Verificar disponibilidade” e “Retomar narração” são controles separados; a sondagem manual bem-sucedida apenas atualiza o gate e habilita a escolha de retomar, sem enviar automaticamente a ação. Em `DEC-003-B`, a interface não expõe endpoint, comando ou botão de verificação: mostra espera/estado e, somente após a condição de liberação aprovada, “Retomar narração” inicia uma única tentativa direta H6. Nenhum ramo reenvia a ação automaticamente.
- **API-001**: O contrato comum de pausa deve expor apenas metadados seguros: estado, IDs opacos, resumo de ação, recibo de resolução já autorizado à UI, categoria normalizada, mensagem segura, `retryable`, `retry_after_seconds`, `rate_limit_origin` (`gateway`, `upstream` ou `unknown`), `gate_scope` público sem correlação de credencial, escopo/timing somente quando comprovados, timestamps e ações permitidas. `scope_key`, fingerprint, header e identificador interno de conta permanecem server-side.
- **API-002**: O comando de retomada deve carregar apenas IDs opacos e precondições. O cliente nunca envia `TurnDraft`, faces, outcome, fatos, memória, target ou prompt como autoridade.
- **API-003**: O evento que encerra o stream corrente deve distinguir `stream_terminal=true` de terminalidade do ciclo da operação. O formato final de `operation_terminal` depende de `DEC-001`.
- **API-004**: O protocolo deve manter compatibilidade explícita com `operation_id`, `turn_id`, terminal tipado, replay e reidratação existentes; clientes antigos devem receber falha segura, nunca interpretar `paused` como `completed`.
- **API-005**: A projeção pública do gate deve incluir target explícito, estado, `rate_limit_origin`, `gate_scope` saneado, escopo evidenciado somente quando comprovado, `server_now`, `observed_at`, `retry_not_before`, `timing_source`, `timing_confidence` e ações permitidas. Não deve expor `scope_key`, fingerprint, headers brutos ou correlação de conta, confundir gateway com upstream nem sugerir periodicidade não comprovada.
- **API-006**: Em `DEC-003-A`, existe um comando distinto de probe manual, mínimo e sem campanha; probe e retomada nunca se acionam mutuamente. Em `DEC-003-B`, só existe o comando idempotente de retomada, que, após a condição aprovada de liberação, pode adquirir uma lease `direct_resume_trial` e chamar H6 uma vez com a cápsula congelada. Não existe contrato de probe nesse ramo.
- **SEC-001**: Toda retomada deve revalidar a associação entre sessão autenticada/local, cápsula, operação e revisão. Identificadores previsíveis isoladamente não constituem autorização.
- **SEC-002**: O token de retomada, se necessário, deve ser opaco, limitado à sessão, com comparação segura, expiração e rotação/consumo idempotente. Seu valor nunca deve ser registrado em logs.
- **SEC-003**: O backend deve rejeitar cápsula inexistente, expirada, consumida, abandonada, pertencente a outra sessão, com hash divergente ou apontando para target diferente.
- **SEC-004**: Instruções do jogador continuam dados não confiáveis. A pausa não pode promover prompt injection a regra, substituir fatos nem conceder autoridade mecânica ao cliente ou ao LLM.
- **SEC-005**: Logs e métricas não podem incluir ação integral, prompt, narrativa parcial, ficha, fatos confidenciais, segredo, header ou resposta bruta. Mensagens exibidas ao jogador devem usar códigos e textos saneados.
- **OBS-001**: Cada transição deve produzir evento local estruturado com `session_id` pseudonimizado quando necessário, `operation_id`, `capsule_id`, estado anterior/novo, categoria/fase, `retryable`, `retry_after_seconds`, target solicitado/efetivo permitido, `rate_limit_origin`, `evidence_scope`, `gate_scope`, identificador de correlação seguro quando indispensável, timestamps e duração.
- **OBS-002**: Devem existir contadores para pausas por categoria, retomadas solicitadas, retomadas concluídas, novas pausas, abandonos, expirações, conflitos idempotentes e rerrolagens evitadas. Isso não autoriza telemetria externa.
- **OBS-003**: A proveniência da retomada deve permitir provar qual alvo foi solicitado e efetivamente usado, sem registrar credenciais ou conteúdo da campanha.
- **OBS-004**: A UI e os logs devem compartilhar códigos estáveis, mas textos de produto permanecem separados de mensagens técnicas e podem ser localizados.
- **OBS-005**: Observabilidade deve preservar `rate_limit_origin` como `gateway`, `upstream` ou `unknown`, separando `evidence_scope`/confiança de `gate_scope`/política de enforcement. A atribuição nunca é inferida do nome do target: apenas evidência saneada distingue gateway de upstream; escopo/timing ausentes permanecem desconhecidos sem apagar uma origem comprovada. Correlação de plataforma/conta usa somente ID interno ou fingerprint opaco não reversível e não pode aparecer no contrato público.
- **OBS-006**: Eventos de timing devem registrar UTC do servidor, duração monotônica no processo, confiança e correlação do target; nunca usar o relógio do navegador como evidência operacional.
- **A11Y-001**: O cartão de pausa deve possuir título semântico, descrição associada e estado anunciado por região `aria-live`; indisponibilidade transitória usa anúncio não intrusivo, enquanto bloqueio que exige ação pode usar alerta.
- **A11Y-002**: “Retomar narração” e “Descartar ação” devem ser operáveis por teclado, possuir foco visível e nomes acessíveis; nenhuma informação pode depender apenas de cor, spinner ou contagem visual.
- **A11Y-003**: A interface deve preservar foco e leitura durante countdown, reconexão e atualização do cartão. Atualizações por segundo não devem saturar leitores de tela; anunciar somente mudanças relevantes.
- **A11Y-004**: A experiência deve funcionar com zoom, viewport estreito, tema claro/escuro e preferência por movimento reduzido, mantendo contraste e ordem lógica.
- **DEC-001 — B aprovada em 2026-09-21**: nova operação referenciada. A tentativa original permanece terminal e a retomada usa nova `operation_id` ligada por `resumes_operation_id` à cápsula imutável.
- **DEC-002 — B aprovada em 2026-09-21**: rascunho local editável; submissão, atalhos de ação e rolagem permanecem bloqueados e o rascunho nunca substitui a cápsula.
- **DEC-003 — B aprovada em 2026-09-21**: não existe probe. Cada clique deliberado em “Retomar narração” pode adquirir uma lease `direct_resume_trial` e tentar H6 uma vez com a cápsula congelada, sem H0/H1/H4/RNG. `retry_not_before` comprovado é respeitado; sem timing confiável não se inventa cooldown. Falha elegível atualiza o mesmo estado pausado.
- **RET-001 — aprovada em 2026-09-21**: no piloto local não há expiração nem exclusão física automática. A cápsula sobrevive a restart até conclusão ou abandono explícito.
- **CON-001**: Não implementar este plano antes da aprovação explícita de `DEC-001`, `DEC-002`, `DEC-003`, taxonomia, UX e política de retenção/expiração.
- **CON-002**: Não alterar provedor, modelo, endpoint, capacidade, roteamento, custo, orçamento, fallback ou política de gratuidade.
- **CON-003**: Não criar retry automático. Toda retomada é iniciada explicitamente pelo jogador e usa o target fixado, salvo futura mudança de alvo deliberada em escopo separado.
- **CON-004**: Não adicionar dependência, fila externa, serviço de background, microsserviço ou armazenamento de navegador como fonte de verdade.
- **CON-005**: Não usar a pausa para mascarar `invalid_structured_output`, regra ausente, catálogo incompleto ou baixa qualidade narrativa.
- **CON-006**: O plano `plan/architecture-deterministic-context-catalogs-3.md` permanece independente e não deve ser alterado por esta frente.
- **CON-007**: “Retomar” nunca significa retry automático: em `DEC-003-A` só ocorre após uma escolha humana separada da sondagem; em `DEC-003-B` é uma única tentativa H6 explicitamente iniciada pelo jogador. “Sondar” existe apenas em A e é uma chamada sintética única e controlada que não contém ação, ficha, contexto, memória ou narrativa da campanha.
- **CON-008**: Nenhum texto de produto pode alegar cota diária, janela ou reset sem evidência confiável associada ao target exato.
- **CON-009**: Falha de capacidade de H4 não pode degradar silenciosamente para `static_lore` e terminar em commit. H0/H1 mantêm apenas os fallbacks semânticos de `REQ-029`.
- **GUD-001**: Implementar, quando autorizado, a menor extensão coerente dos contratos e da persistência existentes, preservando dados, operações e testes atuais.
- **GUD-002**: Minimizar consumo consultando o gate persistido localmente, respeitando evidência ainda válida e `retry_not_before`, coalescendo concorrência por `gate_scope + scope_key` e evitando chamadas periódicas, em foco, por renderização ou por estágio. B é recomendada por eliminar a chamada de probe; se A for escolhida, usar somente o probe mínimo iniciado pelo jogador.
- **PAT-001**: Representar transições em funções puras/tipos explícitos; handlers WebSocket e componentes React apenas orquestram e apresentam o estado.
- **PAT-002**: Separar cápsula persistida, projeção segura para o cliente e evidência observável. Nenhum desses objetos deve reutilizar diretamente um payload bruto de provedor.

## 2. Implementation Steps

### Implementation Phase 0

- GOAL-000: Tornar o plano pronto para execução sem decidir arquitetura por arrasto.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Registrar aprovação humana de `DEC-001` neste plano e definir a terminalidade de stream/operação sem alterar as invariantes comuns. | [x] `DEC-001-B` | 2026-09-21 |
| TASK-002 | Aprovar a matriz completa de categorias elegíveis, bloqueadas e terminais baseada em `api/llm/contract.py::ErrorCategory`, `NormalizedError.retryable`, fase e `rate_limit_origin` (`gateway`, `upstream`, `unknown`); definir `evidence_scope`, `gate_scope`, `scope_key` e a política conservadora de origem/alcance desconhecidos sem promover policy a evidência; preservar escopo/timing somente quando comprovados, incluir `rate_limit_unknown_origin` apenas para origem desconhecida e proibir alegações de cota diária sem prova. Depende de TASK-001. | [x] Matriz P0 reconciliada | 2026-09-22 |
| TASK-003 | Definir duração, expiração, abandono, recuperação após restart e retenção segura da cápsula; registrar a decisão sem executar limpeza destrutiva. Depende de TASK-001. | [x] Retenção lógica, sem cleanup físico | 2026-09-21 |
| TASK-004 | Reinspecionar `git status`, cadeia `AGENTS.md`, estado durável disponível, schemas, handlers e testes; estabelecer linha de base sem tocar alterações não relacionadas. Depende de TASK-001 a TASK-003. | [x] Preflight repetido no worktree correto | 2026-09-22 |
| TASK-035 | Registrar decisões humanas `DEC-002` (editor bloqueado ou rascunho editável) e `DEC-003` (A com sondagem manual controlada ou B sem sondagem sintética), preservando a recomendação de menor consumo como proposta. Depende de TASK-001. | [x] `DEC-002-B`/`DEC-003-B` | 2026-09-21 |
| TASK-036 | Congelar o contrato do gate P0: disponibilidade por target exato; bloqueios hierárquicos por `gate_scope + scope_key`; mapeamento comprovado de `gateway`, `upstream` e `unknown`; fingerprint opaco não reversível; estados, TTL, leases single-flight condicionais a `DEC-003`, recuperação após restart, timing server-side e comportamento antes de H0/H1/H4/H6/RNG. Depende de TASK-002, TASK-003 e TASK-035. | [x] Contrato e testes de fronteira | 2026-09-22 |

### Implementation Phase 1

- GOAL-001: Introduzir contratos tipados e uma máquina de estados verificável.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Acrescentar em `api/turn_models.py` os modelos imutáveis `NarrationResumeCapsule`, `NarrationPauseProjection`, `NarrationResumeCommand`, `NarratorAvailabilityGate` e enums de estado/transição definidos pelas decisões; exigir IDs, revisão, hashes, target, `rate_limit_origin`, `evidence_scope`, `gate_scope`, `scope_key` server-side, escopo/timing normalizados quando comprovados e resolução opcional. Depende de GOAL-000. | [x] Contratos tipados | 2026-09-21 |
| TASK-006 | Criar `api/narration_resume_service.py` com funções puras `classify_pause_eligibility`, `validate_resume_preconditions`, `transition_narration_state`, `normalize_gate_timing` e `can_dispatch_or_roll`; nenhuma delas chama LLM, persiste ou confia em payload do cliente. Depende de TASK-005. | [x] Política pura e decorador local | 2026-09-22 |
| TASK-007 | Mapear `NormalizedError` para a taxonomia completa sem substituir categoria, fase, `retryable`, `retry_after_seconds` ou proveniência; preservar `rate_limit_origin=gateway|upstream|unknown`, separar alcance comprovado da política local, calcular o menor `gate_scope + scope_key` seguro e gerar `rate_limit_unknown_origin` somente para origem desconhecida. Mensagens técnicas e correlação de credencial ficam fora do contrato público. Depende de TASK-005 e TASK-006. | [x] Origem/escopo preservados | 2026-09-22 |
| TASK-008 | Criar `tests/test_narration_resume_service.py` cobrindo todas as transições, matriz completa de erros, as três origens de rate limit, escopo evidenciado versus enforcement, gateway compartilhado, upstream isolado, política unknown, não vazamento de fingerprint, timing independente, cancelamento, expiração, hash, revisão e target divergentes. Depende de TASK-006 e TASK-007. | [x] Testes de política P0 | 2026-09-22 |

### Implementation Phase 2

- GOAL-002: Persistir a cápsula e preservar idempotência sem confirmar o turno.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Evoluir `api/persistence.py` conforme `DEC-001`: alternativa A adiciona estado `paused` e campos versionados à tentativa; alternativa B adiciona registro de cápsula e correlação `resumes_operation_id`, mantendo a tentativa original terminal. Executar somente a alternativa aprovada. Depende de GOAL-001. | [x] Somente alternativa B | 2026-09-21 |
| TASK-010 | Implementar criação atômica da cápsula a partir do rascunho e resolução já produzidos, antes de publicar o estado de pausa; nenhum campo é aceito do cliente como autoridade. Depende de TASK-009. | [x] Cápsula server-side com hash | 2026-09-22 |
| TASK-011 | Implementar carregamento, consumo idempotente, abandono lógico, expiração lógica e reidratação; não apagar fisicamente conteúdo durante o fluxo de jogo. Depende de TASK-009 e TASK-010. | [x] CAS e retenção lógica | 2026-09-21 |
| TASK-012 | Garantir que `recover_pending_attempts` não converta cápsulas retomáveis em cancelamento indevido na alternativa A e que a alternativa B não confunda falha original com operação ativa. Depende de TASK-009. | [x] Recuperação B separada | 2026-09-22 |
| TASK-013 | Estender `tests/test_persistence.py` com migração segura, rollback, restart, concorrência, consumo único, replay, hash/revisão divergentes e compatibilidade de bancos anteriores. Depende de TASK-009 a TASK-012. | [x] Inclui dez claims concorrentes | 2026-09-22 |
| TASK-037 | Persistir disponibilidade por target exato e bloqueios de rate limit por `gate_scope + scope_key`, com update atômico, lease single-flight do ramo aprovado (`probing` em A ou `direct_resume_trial` em B), origem/escopo/timing normalizados e recuperação determinística de lease abandonada após restart. Persistir somente ID interno ou fingerprint opaco não reversível para correlação; nunca segredo, header, chave ou relógio monotônico entre processos. Depende de TASK-005 e TASK-036. | [x] Gate persistido e lease B | 2026-09-22 |
| TASK-038 | Estender `tests/test_persistence.py` para provar autorização isolada por target, bloqueio gateway em todos e somente os targets do `scope_key` comprovado, isolamento de upstream, política conservadora unknown, CAS concorrente por escopo, no máximo uma lease remota do tipo aprovado, restart, expiração da evidência e não vazamento de correlação. Depende de TASK-037. | [x] Fronteiras, CAS e restart | 2026-09-22 |

### Implementation Phase 3

- GOAL-003: Integrar pausa e retomada ao fluxo transacional e ao protocolo WebSocket.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-014 | Alterar `api/turn_execution_service.py` para capturar somente falhas elegíveis após o rascunho existir e antes de qualquer narrativa ser publicada, congelar a cápsula e retornar estado tipado sem registrar falha terminal incompatível com `DEC-001`. Depende de GOAL-002. | [x] Pausa antes de publicação/commit | 2026-09-21 |
| TASK-015 | Alterar `api/main.py::_turn_failure_payloads`, `_send_recorded_turn_failure`, `_replay_turn_attempt`, lifespan/recovery e `websocket_endpoint` para publicar projeção segura de pausa, liberar o lock, aceitar comando de retomada e reidratar o estado após reconexão/restart. Depende de TASK-014. | [x] Projeção segura e reidratação | 2026-09-22 |
| TASK-016 | Implementar a retomada usando o rascunho, a resolução e o contexto congelados; chamar somente H6, não executar H0/H1/H4, regras, RNG ou atualização relacional novamente. Depende de TASK-014 e TASK-015. | [x] H6 único sobre snapshot | 2026-09-22 |
| TASK-017 | Manter o mesmo target solicitado da tentativa de narração e registrar proveniência efetiva. Target indisponível continua pausado/bloqueado; não há seleção automática de outro alvo. Depende de TASK-016. | [x] Target fixo | 2026-09-21 |
| TASK-018 | Preservar terminal único por stream, nenhum delta narrativo na pausa atual, nenhum delta após terminal de stream e commit único após narrativa válida; qualquer parcial futuro continua não canônico. Depende de TASK-015 a TASK-017. | [x] Terminal/commit único | 2026-09-22 |
| TASK-019 | Estender `tests/test_turn_execution_service.py`, `tests/test_websocket_transactional.py` e `tests/test_websocket_flows.py` para indisponibilidade antes do delta validado, retry-after, retomada, replay, reconexão, restart, liberação de lock, duplicação e conclusão. Depende de TASK-014 a TASK-018. | [x] E2E transacional offline | 2026-09-22 |
| TASK-039 | Consultar atomicamente a evidência do target exato e todo bloqueio hierárquico aplicável antes de cada dispatch H0/H1/H4/H6 habilitado e imediatamente antes do RNG; uma consulta bloqueada não chama rede, não rola e não cria fatos. Depende de TASK-006 e TASK-037. | [x] Decorador de dispatch + `before_rng` | 2026-09-22 |
| TASK-040 | Restringir fallbacks H0/H1 à semântica local e impedir H4 fallback+commit quando a chamada habilitada falhar por capacidade; cobrir também consulta H4 direta sem commit de campanha. Depende de TASK-007 e TASK-039. | [x] H4 falha fechada; H0/H1 semânticos | 2026-09-22 |
| TASK-041 | **Condicional a `DEC-003-A`**: implementar comando de sondagem sintética manual, mínima, campaign-free e single-flight pelo escopo aplicável, separado da retomada. O resultado apenas atualiza o gate; não há H0/H1/H4/H6 narrativo, RNG, confirmação ou ação automática subsequente. Se B for aprovada, registrar esta tarefa como `N/A por DEC-003-B`, sem bloquear GOAL-003. Depende de TASK-037 e TASK-039. | N/A por `DEC-003-B` | 2026-09-21 |
| TASK-046 | **Condicional a `DEC-003-B`**: implementar o único caminho sem sondagem — após a condição de liberação aprovada, o comando idempotente do jogador adquire `direct_resume_trial`, chama somente H6 uma vez com a cápsula congelada e atualiza o gate se falhar; nunca reenvia a ação automaticamente. Se A for aprovada, registrar esta tarefa como `N/A por DEC-003-A`, sem bloquear GOAL-003. Depende de TASK-016, TASK-037 e TASK-039. | [x] Tentativa direta idempotente | 2026-09-22 |

### Implementation Phase 4

- GOAL-004: Entregar uma experiência de recuperação compreensível e acessível.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-020 | Estender `client/src/types/narrative.ts` e `client/src/narrativeProtocol.ts` com estado discriminado de pausa, cápsula pública, ações permitidas e promoção somente após `completed`. Depende de GOAL-003. | [x] Estado discriminado | 2026-09-21 |
| TASK-021 | Atualizar `client/src/hooks/useWebSocket.ts` para não perder a cápsula ao receber terminal de stream, enviar comando idempotente de retomada conforme `DEC-001` e reidratar após reconexão. Depende de TASK-020. | [x] Reconexão e comando explícito | 2026-09-21 |
| TASK-022 | Criar `client/src/components/NarrationPauseCard.tsx` com ação, recibo preservado, motivo, estado canônico, retry-after, botões de retomada/abandono e sem exposição de conteúdo confidencial. Depende de TASK-020. | [x] Cartão seguro | 2026-09-22 |
| TASK-023 | Integrar o cartão em `client/src/App.tsx`, `client/src/components/NarrativeLog.tsx` e `client/src/components/ActionPanel.tsx`; bloquear novas ações, preservar controles de recuperação e remover chunks não confirmados. Depende de TASK-021 e TASK-022. | [x] Integração e bloqueio | 2026-09-21 |
| TASK-024 | Implementar anúncios, foco, contraste, teclado, zoom, responsividade, reduced motion e countdown de baixa verbosidade conforme `A11Y-001` a `A11Y-004`. Depende de TASK-022 e TASK-023. | [x] Automatizado; percepção em `TASK-033` | 2026-09-22 |
| TASK-025 | Criar/estender `client/src/narrativeProtocol.test.ts`, `client/src/hooks/useWebSocket.test.tsx`, `client/src/components/NarrationPauseCard.test.tsx`, `ActionPanel.test.tsx` e `NarrativeLog.test.tsx` para estados, reconexão, duplicação, acessibilidade e temas. Depende de TASK-020 a TASK-024. | [x] 249 testes frontend | 2026-09-22 |
| TASK-042 | Aplicar `DEC-002` em `ActionPanel.tsx`: editor totalmente bloqueado ou rascunho local editável com submissão/rolagem bloqueadas; nenhuma opção substitui a ação congelada. Depende de TASK-020 e TASK-035. | [x] Rascunho editável, envio bloqueado | 2026-09-21 |
| TASK-043 | Aplicar somente o ramo aprovado de `DEC-003`: em A, renderizar “Verificar disponibilidade” separado de “Retomar narração” e depender condicionalmente de TASK-041; em B, não renderizar nem aceitar verificação, mostrar espera/estado e oferecer somente a tentativa narrativa explícita após a condição aprovada, dependendo condicionalmente de TASK-046. Em ambos, derivar countdown do timing server-side, renderizar `gateway|upstream|unknown` sem `scope_key`/atribuição/cota inventada e nunca reenviar a ação automaticamente. Dependências comuns: TASK-021 e TASK-022; exatamente uma dependência condicional entre TASK-041 e TASK-046. | [x] Somente ramo B; relógio do servidor | 2026-09-22 |

### Implementation Phase 5

- GOAL-005: Fechar observabilidade e segurança sem coletar conteúdo da campanha.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-026 | Acrescentar eventos estruturados locais de transição e métricas agregadas nos pontos existentes de observabilidade; aplicar allowlist de campos e redigir IDs quando necessário. Depende de GOAL-003. | [x] Tentativas/cápsulas/gates persistidos | 2026-09-22 |
| TASK-027 | Adicionar testes de não vazamento que proíbam prompt, ação integral, narrativa parcial, ficha, contexto confidencial, segredo e header em logs, erro e projeção pública. Depende de TASK-026. | [x] Projeção pública por allowlist | 2026-09-22 |
| TASK-028 | Adicionar testes adversariais para token/ID forjado, outra sessão, capsule replay, alteração de rolagem, target divergente, revisão obsoleta e corrida entre retomar/abandonar. Depende de GOAL-002 a GOAL-004. | [x] Falha fechada, CAS e replay | 2026-09-22 |
| TASK-029 | Documentar códigos públicos, estados observáveis e procedimento local de diagnóstico sem incluir credenciais nem instruir gravação de segredo no repositório. Depende de TASK-026 a TASK-028. | [x] README + relatório técnico | 2026-09-22 |
| TASK-044 | Registrar métricas de consulta local, lease remota coalescida por `gate_scope + scope_key`, `rate_limit_origin`, `evidence_scope`, enforcement/timing/confiança e bloqueios antes do RNG; provar por allowlist que relógio/payload do cliente não altera evidência e que nenhuma correlação secreta chega ao cliente. Depende de TASK-026 e TASK-037. | [x] Evidência persistida e testes P0 | 2026-09-22 |

### Implementation Phase 6

- GOAL-006: Validar o comportamento ponta a ponta e obter aceitação humana.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-030 | Executar testes focados por fase com gateways falsos e relógio/RNG controlados; nenhuma chamada de teste alcança API, modelo local ou rede. Depende de GOAL-001 a GOAL-005. | [x] Matriz offline focada | 2026-09-22 |
| TASK-031 | Executar suíte backend/frontend disponível, verificador de tipos/lint já instalado, `git diff --check` e inspeção de segredos/diff sem instalar dependências novas. Depende de TASK-030. | [x] Executado; limites amplos registrados | 2026-09-22 |
| TASK-045 | Executar matriz P0 provando consulta local antes de H0/H1/H4/H6 e RNG, disponibilidade isolada por target, bloqueio gateway compartilhado somente no `scope_key` comprovado, upstream independente, policy unknown, single-flight/restart nos dois desenhos de `DEC-003`, fechamento com a tarefa do ramo não escolhido em `N/A`, timing confiável, preservação `gateway|upstream|unknown`, fallback H0/H1 somente semântico e ausência de H4 fallback+commit. Depende de TASK-030. | [x] Matriz técnica reconciliada | 2026-09-22 |
| TASK-032 | Realizar aceitação manual local: gate disponível -> ação com rolagem -> indisponibilidade simulada após o gate -> refresh/restart -> retomada -> narrativa/commit único, provando faces idênticas e ausência de reaplicação mecânica. Depende de TASK-031 e TASK-045. | [x] Aceita pelo usuário com “Prossiga” | 2026-09-22 |
| TASK-033 | Repetir aceitação com ação sem rolagem, rate limit originado no gateway/upstream/desconhecido, escopo/timing ausente, erro de configuração, abandono, clique duplicado, falha durante a retomada e os caminhos aprovados de editor/`DEC-003`; provar que exatamente um ramo é implementado e que o outro fica `N/A`, sem tarefa órfã. Depende de TASK-032. | [x] Aceita pelo usuário com “Prossiga” | 2026-09-22 |
| TASK-034 | Atualizar este plano para `Completed` somente após critérios, DoD e aceitação humana; registrar limitações reais sem promover provedor, modelo, custo ou fallback. Depende de TASK-033. | [x] Plano promovido sem ampliar escopo | 2026-09-22 |

## 3. Alternatives

- **ALT-001 — Operação suspensa (DEC-001-A)**: mantém a identidade original e modela `paused` como estado não terminal da operação. Simplifica a narrativa mental do jogador, mas exige migração do check de status, mudança no replay, distinção entre terminal de stream e de operação e proteção contra a recuperação automática de `pending`.
- **ALT-002 — Nova operação referenciada (DEC-001-B)**: encerra a tentativa original e cria nova operação idempotente ligada à cápsula. Preserva a semântica terminal atual e oferece histórico explícito, mas exige correlação entre operações, prevenção de cadeias ambíguas e UX que ainda pareça uma única ação para o jogador.
- **ALT-003 — Pedir que o jogador envie a ação novamente**: rejeitada. Pode rerrolar, consumir recursos outra vez, perder contexto e fazer o usuário acreditar que sua ação foi descartada.
- **ALT-004 — Guardar a ação somente no navegador**: rejeitada. Não sobrevive a outro cliente/restart, permite adulteração e transforma o frontend em fonte de verdade mecânica.
- **ALT-005 — Retry automático exponencial**: rejeitada. Pode gerar custo, repetição, múltiplas narrativas e espera opaca; também conflita com controle humano e target explícito.
- **ALT-006 — Trocar silenciosamente de modelo/provedor**: rejeitada. Viola proveniência, contrato LLM-001 e política de admissão.
- **ALT-007 — Confirmar mecânica antes da narrativa e completar depois**: não escolhida neste plano. Muda a atomicidade aprovada e cria turno canônico sem continuidade narrativa; exige decisão arquitetural independente.
- **ALT-008 — Reutilizar chunks parciais na retomada**: rejeitada na primeira versão. Texto parcial não foi validado e pode contradizer a resposta final; somente metadados de que houve parcial são preservados.

## 4. Dependencies

- **DEP-001**: `plan/architecture-llm-memory-turns-1.md`, concluído, define LLM-001, tentativa idempotente, terminal tipado, rollback e commit transacional.
- **DEP-002**: `spec/spec-improvisational-scene-direction.md`, que preserva estado quando H6 falha e exige admissão antes do commit.
- **DEP-003**: `spec/design-visible-v5-dice-tray.md`, cujas invariantes de retry sem rerrolagem e resultado preservado devem ser respeitadas sem antecipar todo o redesign da bandeja.
- **DEP-004**: `spec/spec-architecture-narrative-engine-admission-policy.md`, especialmente target explícito, ausência de troca silenciosa e oferta de retry/reconfiguração em indisponibilidade.
- **DEP-005**: `api/llm/contract.py`, fonte da taxonomia neutra, retryability, retry-after, fase, proveniência e terminal de stream.
- **DEP-006**: `api/turn_models.py`, `api/turn_execution_service.py`, `api/persistence.py` e `api/main.py`, que contêm rascunho, tentativa, commit, replay e WebSocket atuais.
- **DEP-007**: `client/src/narrativeProtocol.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/App.tsx`, `client/src/components/NarrativeLog.tsx` e `ActionPanel.tsx`, que controlam estado provisório, operação pendente e input.
- **DEP-008**: Aprovação humana de `DEC-001`, `DEC-002`, `DEC-003`, taxonomia, UX, expiração/retenção, timing e abandono.
- **DEP-009**: Nenhuma nova dependência externa é necessária ou autorizada por este plano.

Ordem crítica: GOAL-000 -> GOAL-001 -> GOAL-002 -> GOAL-003 -> GOAL-004/GOAL-005 -> GOAL-006. GOAL-004 e GOAL-005 podem avançar em paralelo após estabilização dos contratos de GOAL-003.

### Definition of Ready

1. `DEC-001`, `DEC-002` e `DEC-003` estão aprovadas e registradas sem ambiguidade.
2. A matriz completa por `ErrorCategory`, fase e `retryable`, preservando `rate_limit_origin=gateway|upstream|unknown`, `evidence_scope`, `gate_scope`, política unknown, escopo/timing comprovados e `rate_limit_unknown_origin` somente para origem desconhecida, está aprovada.
3. Contrato do gate define disponibilidade por target exato, bloqueios hierárquicos por `gate_scope + scope_key`, correlação opaca não reversível, TTL, lease single-flight, restart e timing server-side; alcance ambíguo permanece risco/política, não fato.
4. Política de expiração, retenção lógica, abandono e restart da cápsula está definida.
5. Contrato público de pausa/retomada e exatamente um caminho de `DEC-003` passaram por revisão de produto e cópia PT-BR: A possui probe manual separado; B não possui endpoint/comando/controle de probe e oferece somente tentativa narrativa explícita após a condição aprovada. A tarefa do ramo não escolhido é registrável como `N/A`, sem bloquear o fechamento.
6. Fluxo de ação com e sem rolagem, funções locais e caráter provisório dos efeitos estão aceitos.
7. Fallbacks semânticos H0/H1 e proibição de H4 fallback+commit foram aceitos como invariantes.
8. Linha de base dos testes e schema de persistência foi registrada; falhas preexistentes estão separadas.
9. A implementação foi autorizada explicitamente; a aprovação deste documento como proposta não basta.

## 5. Files

- **FILE-001**: `api/turn_models.py` — cápsula, projeção pública, comando e estados imutáveis.
- **FILE-002**: `api/narration_resume_service.py` — nova classificação, validação e máquina de estados puras.
- **FILE-003**: `api/persistence.py` — persistência/migração conforme a alternativa aprovada.
- **FILE-004**: `api/turn_execution_service.py` — criação da cápsula e retomada somente de H6.
- **FILE-005**: `api/main.py` — wire contract, replay, reconexão e handlers.
- **FILE-006**: `api/llm/contract.py` — somente se a implementação precisar de tipo de projeção; categorias existentes não devem ser renomeadas por este plano.
- **FILE-007**: `client/src/types/narrative.ts` e `client/src/narrativeProtocol.ts` — estado discriminado e reducer.
- **FILE-008**: `client/src/hooks/useWebSocket.ts` — envio/reenvio seguro e reidratação.
- **FILE-009**: `client/src/components/NarrationPauseCard.tsx` — novo cartão acessível.
- **FILE-010**: `client/src/App.tsx`, `NarrativeLog.tsx` e `ActionPanel.tsx` — integração e bloqueio seletivo.
- **FILE-011**: `tests/test_narration_resume_service.py`, `tests/test_persistence.py`, `tests/test_turn_execution_service.py`, `tests/test_websocket_transactional.py` e `tests/test_websocket_flows.py` — backend.
- **FILE-012**: `client/src/narrativeProtocol.test.ts`, `client/src/hooks/useWebSocket.test.tsx`, `client/src/components/NarrationPauseCard.test.tsx`, `ActionPanel.test.tsx` e `NarrativeLog.test.tsx` — frontend.
- **FILE-013**: `README.md` ou documentação operacional vigente — somente contrato observável e recuperação aprovada.
- **FILE-014**: `plan/feature-narrator-pause-resume-1.md` — acompanhamento do plano.
- **FILE-015**: `api/h0_controller_service.py`, `api/parser_service.py`, `api/h4_lore_expert_service.py` e `api/orchestrator_service.py` — consultas ao gate e fronteiras de fallback, sem mover mecânica para LLM.

## 6. Testing

- **TEST-001**: Cada categoria de `ErrorCategory` produz exatamente uma classe de UX: pausa transitória, configuração bloqueada, correção necessária, saída inválida, cancelamento ou falha interna.
- **TEST-002**: `retryable=false` nunca habilita retomada imediata; `retry_after_seconds` bloqueia e libera no instante controlado.
- **TEST-003**: Ação com rolagem preserva todas as faces e o mesmo receipt antes/depois de pausa, reconexão, restart e múltiplas retomadas falhas.
- **TEST-004**: Ação sem rolagem preserva rascunho e contexto sem fabricar receipt.
- **TEST-005**: Spy/fake de RNG, H0, H1, H4, regras, combate, disciplina e relações prova zero reinvocações durante retomada; somente H6 pode ser chamado.
- **TEST-006**: Sucesso confirma narrativa, evento, fatos, relações, estado e memória uma única vez; falha/pausa/abandono deixa snapshot anterior intacto.
- **TEST-007**: Dois cliques simultâneos, duas abas e reenvio após reconexão devolvem o mesmo resultado idempotente e nunca geram duas narrativas.
- **TEST-008**: Refresh e reconexão reidratam cartão, ação e receipt; cliente antigo não promove `paused` a `completed`.
- **TEST-009**: Indisponibilidade no pipeline atual não publica delta narrativo; um teste defensivo de parcial sintético comprova que conteúdo não validado nunca vira cânone nem aparece após o terminal de stream.
- **TEST-010**: Cápsula adulterada, de outra sessão, expirada, consumida, abandonada, com target/hash/revisão divergente falha fechada e não chama LLM.
- **TEST-011**: Corrida retomar versus abandonar tem uma única transição vencedora e resultado reprodutível.
- **TEST-012**: Erro de autenticação/quota/configuração conserva o que for seguro, mas não executa retry até correção explícita.
- **TEST-013**: Logs, payload público e mensagens não contêm chaves, headers, prompt, ação integral em telemetria, resposta bruta, chunks, ficha ou fatos confidenciais.
- **TEST-014**: Testes de componente verificam teclado, foco, nomes acessíveis, live region, countdown sem spam, contraste nos temas, zoom e viewport estreito.
- **TEST-015**: Toda a suíte usa gateways falsos; nenhuma rede, API remota ou modelo local é acessado.
- **TEST-016**: Migração preserva bancos anteriores, permite rollback seguro e não classifica pausa como turno confirmado.
- **TEST-017**: `git diff --check`, testes focados e suítes backend/frontend disponíveis passam; diff contém somente o escopo autorizado e nenhum segredo.
- **TEST-018**: Evidência `available` de um target nunca autoriza outro. Um limite `gateway` comprovado bloqueia todos e somente os targets associados ao mesmo `scope_key` de plataforma/conta ou credencial; um limite `upstream` não bloqueia target independente. A consulta ocorre antes de cada H0/H1/H4/H6 habilitado e imediatamente antes do RNG sem executar rede.
- **TEST-019**: Dez requisições concorrentes no mesmo `gate_scope + scope_key` e restart durante `probing` ou `direct_resume_trial` produzem no máximo uma lease/chamada válida do caminho aprovado; requisições de escopo independente não são coalescidas indevidamente, e lease abandonada volta a estado seguro sem autorizar dispatch ou RNG.
- **TEST-020**: Rate limits de gateway, upstream e origem desconhecida preservam exatamente `rate_limit_origin`; `evidence_scope` ausente permanece desconhecido, enquanto a política `unknown_conservative` é identificada apenas como enforcement local. Somente `unknown` resulta em `rate_limit_unknown_origin`; nenhum payload público, log, componente ou tradução atribui gateway ao modelo, promove policy a evidência, expõe `scope_key`/fingerprint/credencial ou contém “cota diária”/reset não comprovado.
- **TEST-021**: H4 habilitado com falha de capacidade não retorna `static_lore` como sucesso nem confirma turno; H0/H1 usam somente fallback semântico e ainda obedecem ao gate antes do RNG/H6.
- **TEST-022**: Timing usa UTC do servidor, duração monotônica no processo e fonte/confiança; clock ou timestamp malicioso do cliente não antecipa retomada.
- **TEST-023**: Os dois caminhos de `DEC-003` são concluíveis, mas mutuamente exclusivos: A expõe probe manual mínimo e sem campanha separado da retomada, sem disparar ação/RNG/H6 narrativo automaticamente; B não expõe endpoint/comando/controle de probe e uma retomada explícita concorrente chama somente H6 uma vez com a cápsula. Falha atualiza o gate nos dois ramos, nunca há reenvio automático, e a tarefa do ramo não escolhido fica `N/A` sem dependência órfã.
- **TEST-024**: A alternativa aprovada em `DEC-002` preserva funções locais e impede submissão/rolagem; rascunho editável, se escolhido, não altera a cápsula.

### Definition of Done

1. A alternativa de `DEC-001` foi implementada exatamente como aprovada e a outra não deixou caminhos híbridos.
2. Toda falha recebe classificação estável e somente categorias elegíveis produzem pausa retomável.
3. A ação e a resolução sobrevivem a falha, refresh, reconexão e restart sem rerrolagem ou reaplicação.
4. A retomada chama somente H6 com target explícito e fatos/contexto congelados.
5. O turno é confirmado uma única vez após narrativa válida; pausa, abandono e falha não alteram o cânone.
6. A UX explica ação preservada, efeitos ainda não aplicados, motivo e próximo passo em português claro.
7. Controles e atualizações passam pelos critérios de teclado, foco, leitor de tela, contraste, zoom e responsividade.
8. Eventos locais permitem auditar transições, proveniência e idempotência sem registrar conteúdo sensível.
9. Gate combina disponibilidade por target exato e bloqueios atômicos, single-flight, persistentes e reiniciáveis por `gate_scope + scope_key`; é consultado antes de cada estágio LLM/RNG sem chamada remota implícita e não expõe segredo ou fingerprint ao cliente.
10. Taxonomia completa preserva `rate_limit_origin=gateway|upstream|unknown`, separa escopo evidenciado de enforcement local, bloqueia todos e somente os targets do alcance gateway comprovado, mantém upstream isolado e usa policy conservadora identificada para unknown, sem atribuição ou cota não comprovada.
11. H4 nunca degrada falha de capacidade em commit; H0/H1 permanecem fallback semântico somente.
12. Editor e recuperação seguem exatamente `DEC-002`/`DEC-003`: A separa probe manual de retomada; B não contém probe e usa tentativa direta H6 única após a condição aprovada. Exatamente um ramo está implementado; a tarefa do outro está `N/A`, sem dependência órfã, e o consumo é mínimo no desenho escolhido.
13. Testes unitários, transacionais, WebSocket, segurança, frontend e migração passam offline.
14. Aceitação humana confirma a experiência ponta a ponta e o plano é atualizado para `Completed` somente então.

## 7. Risks & Assumptions

- **RISK-001**: Adicionar estado `paused` à tentativa existente altera invariantes de schema, replay e terminalidade. Mitigação: não escolher a alternativa A sem `DEC-001` e testes de migração/restart.
- **RISK-002**: Nova operação referenciada pode parecer nova ação e gerar cadeias de retomada difíceis de entender. Mitigação: cápsula única, correlação explícita e uma única apresentação visual.
- **RISK-003**: Estado da campanha pode avançar por outro canal enquanto há pausa. Mitigação: bloquear nova ação da sessão e validar revisão antes da retomada; conflito falha fechado.
- **RISK-004**: Mostrar uma rolagem ainda não confirmada pode confundir o jogador. Mitigação: texto explícito de “preservada, efeitos ainda não aplicados” e estado visual distinto.
- **RISK-005**: Rate limits longos podem manter cápsulas por tempo excessivo. Mitigação: política de expiração/abandono aprovada antes de implementação e sem limpeza destrutiva durante o fluxo.
- **RISK-006**: Target pode desaparecer definitivamente. Mitigação: manter cápsula bloqueada, expor diagnóstico seguro e exigir reconfiguração deliberada; nunca trocar silenciosamente.
- **RISK-007**: Uma mudança futura para streaming real pode expor chunks antes da pausa. Mitigação: o pipeline atual continua publicando somente saída estruturada já validada; qualquer alteração dessa premissa exige decisão UX separada.
- **RISK-008**: Observabilidade pode vazar conteúdo de campanha. Mitigação: allowlist de campos, testes de não vazamento e ausência de telemetria externa por padrão.
- **RISK-009**: Uma cápsula ampla pode duplicar dados confidenciais. Mitigação: guardar referências/versionamento sempre que a imutabilidade permitir e nunca enviar a representação server-side completa ao cliente.
- **RISK-010**: Expiração e limpeza podem conflitar com recuperação tardia. Mitigação: separar expiração lógica de exclusão física e deliberar retenção antes de qualquer cleanup.
- **RISK-011**: Uma chamada remota antes de cada estágio consumiria cota e poderia causar o próprio rate limit. Mitigação: cada estágio consulta apenas o gate local; B não usa probe e A permite somente um probe sintético manual single-flight.
- **RISK-012**: Evidência `available` pode ficar obsoleta entre o gate e H6. Mitigação: TTL curto deliberado, nova consulta local antes do RNG/H6 e cápsula para a corrida residual sem rerrolagem.
- **RISK-013**: Relógios divergentes podem habilitar retomada cedo ou criar espera falsa. Mitigação: timing nasce no servidor, usa UTC persistido mais monotônico local e informa fonte/confiança.
- **RISK-014**: Fallback H4 atual pode permitir commit após falha de capacidade. Mitigação: proibição explícita, erro tipado e teste transacional antes de habilitar a feature.
- **RISK-015**: Granularidade ambígua de rate limit pode causar underblocking (novos 429/custo) ou overblocking (indisponibilidade local desnecessária). Mitigação: separar `rate_limit_origin`, `evidence_scope` e `gate_scope`; usar a menor chave comprovada, marcar policy unknown explicitamente, testar fronteiras e reclassificar somente com nova evidência normalizada ou decisão humana.
- **ASSUMPTION-001**: O fluxo transacional, a fronteira LLM-001 e o protocolo terminal atual permanecem a base quando a implementação for autorizada.
- **ASSUMPTION-002**: A resolução mecânica pode ser serializada de modo determinístico sem reexecutar serviços ou RNG.
- **ASSUMPTION-003**: Existe no máximo uma ação narrativa ativa por sessão no MVP local.
- **ASSUMPTION-004**: O jogador inicia a retomada explicitamente; automação em background permanece fora do MVP.
- **ASSUMPTION-005**: Nenhuma mudança de provedor/modelo é necessária para implementar o ciclo de recuperação.
- **ASSUMPTION-006**: Consultar o gate local é barato e não exige rede; evidência remota só muda pelo resultado de uma chamada já autorizada, pelo probe A aprovado ou pela tentativa direta B, nunca por polling silencioso.

## 8. Implementation record — 2026-09-21/22

- `api/turn_models.py` contém cápsula, projeção pública, comando e gate imutáveis.
- `api/narration_resume_service.py` concentra classificação, timing, precondições e transições puras.
- schema SQLite v4 persiste cápsulas e gates; a tentativa fonte continua terminal e a retomada usa nova operação com `resumes_operation_id` em metadado auditável.
- falha H6 transitória somente vira pausa quando `retryable=true` e não existe saída parcial; contexto, resolução e target ficam congelados no servidor.
- reconexão e restart reidratam a pausa; aquisição usa CAS e impede clique duplicado; abandono é lógico.
- retomada reconstrói o turno preparado da cápsula e chama somente H6. H0, H1, H4, regras e RNG não são reinvocados.
- a UI não possui probe, conserva o rascunho local editável, bloqueia submissão/atalhos e exige retomada ou abandono explícitos.
- `TASK-041`: **N/A por DEC-003-B**.
- auditoria final em 2026-09-22: matriz backend focada com 163 aprovados;
  frontend completo com 249 aprovados; lint afetado, build e `git diff --check`
  concluídos. A suíte backend ampla terminou com 8.408 aprovados, 333 ignorados,
  285 falhas e 61 erros concentrados nos fingerprints congelados dos experimentos
  históricos do Narrador (`Final actor schema differs`), já documentados e fora
  deste incremento. Evidências e limites:
  `evals/narrator/reports/narrator-pause-resume-technical-audit-2026-09-22.md`.
  O usuário aceitou `TASK-032`/`TASK-033` com “Prossiga” em 2026-09-22;
  `TASK-034` promoveu somente este plano, sem aprovar modelo, custo, fallback ou
  `CAP-001`.

## 9. Related Specifications / Further Reading

- `plan/architecture-llm-memory-turns-1.md` — contrato LLM, tentativas, streaming e atomicidade.
- `plan/architecture-deterministic-context-catalogs-3.md` — seleção determinística de fatos; frente independente e inalterada.
- `spec/spec-improvisational-scene-direction.md` — autoridade ficcional, validação e preservação de estado.
- `spec/design-visible-v5-dice-tray.md` — recibo visível e retry sem rerrolagem.
- `spec/spec-architecture-narrative-engine-admission-policy.md` — target explícito, indisponibilidade e ausência de fallback silencioso.
- `spec/spec-design-accessible-interface-redesign.md` — requisitos de contraste, teclado, zoom e responsividade.
- `api/llm/contract.py` — taxonomia e evidência neutras do provedor.
- `api/persistence.py` — tentativa idempotente e commit transacional atuais.

### Fechamento humano

As decisões `DEC-001-B`, `DEC-002-B` e `DEC-003-B` foram implementadas. Após a
auditoria e o procedimento reproduzível em
`evals/narrator/reports/narrator-pause-resume-technical-audit-2026-09-22.md`, o
usuário respondeu “Prossiga” em 2026-09-22. Essa resposta fecha `TASK-032`,
`TASK-033` e `TASK-034` somente para pausa/retomada. Ela não escolhe Narrador,
não aprova `CAP-001` e não autoriza campanha híbrida por arrasto.
