---
title: Campanha híbrida mínima e progressão causal na direção B
version: 0.2
date_created: 2026-09-29
last_updated: 2026-10-03
owner: Produto Agente Storyteller
status: Canonical record position v2 approved and verified offline; narrative acceptance pending
tags: [architecture, campaign, progression, narrative-source]
---

# Introduction

DEC-PROG-001 e DEC-PROG-002 foram aprovadas em 29/09/2026: aventura curta no
Arquivo/Galeria, com Mara e um registro público ameaçado, usando um novo perfil
opt-in B com consequências determinísticas. Luna low é referência prioritária,
não narrador admitido. Em 29/09, o usuário escolheu a opção A e autorizou
continuar: a primeira espera dá aviso visível antes do dano. O catálogo é
sintético e opt-in; ainda não constitui campanha jogável nem fato de save real.

## 1. Purpose & Scope

Entregar uma experiência sintética com começo, desenvolvimento, clímax e conclusão,
sem número obrigatório de cenas. Resposta pertinente do NPC e consequência
persistente precedem admissão do narrador. Reutilizar núcleo puro do resolvedor,
mecânica suportada, transações e pausa/retomada, sem segundo LLM.

Fora: sessão zero completa, criação de ficha, migração de save, nova regra V5,
campanhas globais, novos provedores, inferência paga ou admissão automática.

## 2. Definitions

- **Estado confirmado**: projeção derivada de efeitos efetivamente comprometidos.
- **Preparação**: intenção interpretada, recibo e consequência retidos para a
  mesma operação; ainda não altera estado público.
- **Beat**: resultado determinístico vinculante a realizar na prosa.
- **Fonte B**: narrativa integral atribuída e ligada ao turno; não extrai fatos.
- **Marco dramático**: reconhecimento de abertura, desenvolvimento, culminação
  ou epílogo; não uma sequência obrigatória de telas.
- **P/K/H**: operação de produção, cápsula de preparação e operação narrativa.
  Preservar papéis distintos; não reutilizar uma identidade para outra finalidade.

## 3. Requirements, Constraints & Guidelines

- **REQ-001**: Conservar ação literal e normalização de intenção separadas.
  Texto livre é dado; não fornece regras, estado, RNG ou visibilidade.
- **REQ-002**: Diálogo dirigido oferece resposta, condição, recusa pertinente ou
  reação concreta. Silêncio só é possível quando uma causa autorada o justificar.
  A ficha de Mara deste recorte não fornece silêncio como resposta padrão.
- **REQ-003**: Ambiente, informação, opções, relação ou pressão devem mostrar
  consequência causal. Variação de adjetivos não satisfaz progressão.
- **REQ-004**: Somente regras do conteúdo aprovado produzem deltas tipados.
  H6 não define mudanças de estado, condições de vitória ou custo mecânico.
- **REQ-005**: Selecionar regras elegíveis por prioridade e desempate estável
  do resolvedor existente; nenhuma aleatoriedade adicional.
- **REQ-006**: Recibo de teste existente é imutável. Retomada de H6 não executa
  novamente classificação, resolvedor, teste ou consequência.
- **REQ-007**: Gate persistido antes da preparação e imediatamente antes de RNG;
  CAS da revisão antes do commit; uma única mutação terminal por operação.
- **REQ-008**: Segredo da fundadora não é necessário à solução. O pacote público
  só contém restrição de não divulgar identidade; não inclui o segredo literal.
- **REQ-009**: Prosa continua SOURCE_ONLY/not_assessed quanto a verdade independente.
  Efeitos canônicos vêm da regra; anexar ID ao texto não comprova fidelidade.
- **REQ-010**: Sem corte de contexto que elimine consequência obrigatória.
  Incompatibilidade ou orçamento insuficiente falha antes da chamada.
- **REQ-011**: Final de aventura oferece epílogo, não nova ação obrigatória.
  Jogador pode concluir antecipadamente ou abandonar sem retorno artificial ao início.
- **REQ-012**: Medir espera local separada de duração do provedor e confirmação
  do turno. Nenhuma espera fixa de um minuto no perfil Luna interativo.
- **REQ-013**: Todo lançador de teste Luna mostra custo final estimado ou
  indisponível, inclusive falha/interrupção; uso faltante nunca vira zero.
- **CON-001**: Novo perfil/protocolo explícito; nunca ampliar a interpretação de
  source-local-ordinary-v1 ou permitir campos extras por detecção de shape.
- **CON-002**: Não usar o texto gerado para atualizar catálogo, ficha ou projeção.
- **CON-003**: Não avançar ameaça por tempo real, consulta operacional, reconexão,
  latência da API, pausa, erro ou clique repetido.
- **GUD-001**: Reaproveitar material autorado e efeitos sem fala pronta; H6 escolhe
  expressão, linguagem, ritmo, detalhe cosmético e formulação da pergunta.

## 4. Interfaces & Data Contracts

### Contratos propostos

Novas estruturas imutáveis, extra=forbid e versões explícitas; nomes de módulo
e tipos abaixo pertencem ao desenho, não a interfaces já disponíveis.

| Tipo | Campos mínimos e invariantes |
|---|---|
| CampaignProgressState | campaign_id, content_version, policy_version, revision; location=Arquivo/Galeria; record=threatened/warned/wet/preserved/partial/lost; outcome=null/preserved/partial/lost/abandoned; known_information e resolved_objectives como IDs únicos; terminal implica outcome não nulo |
| CampaignIntent | operation_id, raw_input, kind=dialogue/wait/rescue/inspect/withdraw/clarification/unsupported; alvo validado e interpretação versionada; cliente não define kind |
| CampaignPreparedEffect | session_id, operation_id, turn_id, base_revision; rule_id/version; before_hash, after_state, beat, mechanical_receipt opcional e hash próprio |
| CampaignNarratorPacket | ação literal, estado público antes/depois, beat e efeitos obrigatórios, vínculo com a preparação e proibição de revelar identidade; a seleção de fontes B anteriores permanece na futura integração, nunca vem do cliente |
| CampaignSourceProposal | n, q e realized_effects; n/q mantêm limites do perfil B inicialmente; IDs dos efeitos devem corresponder exatamente ao beat; nenhum delta ou fato arbitrário vindo do modelo |

Regra candidata de serialização: JSON UTF-8 canônico com chaves ordenadas,
sem NaN, schema/version, e SHA-256. Hash é integridade, não prova de autoridade.
Identidades derivam da sessão e operação, nunca de relógio ou texto modificado.
A revisão e o hash de antes pertencem ao snapshot capturado no claim.

### Incremento aprovado em 03/10 — posição canônica versionada

A opção A de posição (distinta da opção A de ritmo) foi aprovada pelo usuário.
Novas sessões usam `record-at-risk.v2` e `campaign-progression.v2` com
`record_location: bench | dry_surface`, independente de `location` do jogador.

| Regra | Posição antes | Posição depois |
|---|---|---|
| R-05 / R-06 — resgate intacto/parcial | bench | dry_surface |
| R-07 — recuperação de conteúdo por investigação | bench | bench |
| R-01 / R-02 / R-03 / R-03B / R-04 / R-08 / R-09 | bench | bench |

O seed v2 começa em `bench` (bancada baixa no Arquivo). `dry_surface` significa
superfície seca na Galeria. A mudança é preparada deterministicamente, retida
na cápsula e confirmada apenas no commit de H admitido. O contexto público do
narrador projeta posição antes/depois e rótulos do estado, nunca da prosa.
As versões v1 permanecem legíveis e retomáveis no formato exato anterior, sem
inferir posição retroativa. Versões mistas e v2 retida sem posição são recusadas.
Isso não migra saves, não cria DDL, não altera o seed genérico B e não move o
jogador implicitamente. Testes usam seeds legados sintéticos; não alegam ensaio
de migração sobre bancos pessoais ou validação semântica irrestrita de prosa.

### Conteúdo autorado: abertura e objetivo

Estado inicial: Arquivo; Mara presente; registro público sobre bancada baixa,
ameaçado por água de infiltração visível. Uma superfície seca na Galeria está
acessível. O documento tem função local de registro do acervo, sem pista
obrigatória sobre a fundadora. Abertura explica risco e deixa iniciativa livre.
Nenhuma ação de salvamento é narrada como escolha já feita pelo jogador.

Mara preserva o acervo, é reservada e pode orientar/ajudar, mas não recupera texto
destruído nem revela a identidade protegida. Sua resposta muda de acordo com o
estado do registro; não reinicia a apresentação quando já houve conversa.

| Regra | Pré-condição e intenção | Consequência candidata | Mecânica |
|---|---|---|---|
| R-01 task_answer | diálogo sobre tarefa/ajuda, campanha ativa | Mara explica o risco atual e indica superfície seca; known_information inclui safe_surface; se já conhecida, reconhece conversa anterior e responde à nova pergunta. Pedido específico para Mara levar o registro recebe resposta específica, sem executar resgate ou conceder informação não dita. | Sem RNG |
| R-02 protected_answer | pergunta sobre fundadora | Mara recusa a identidade e redireciona pertinentemente à tarefa, sem conceder nova pista secreta ou aumentar ameaça por punição | Sem RNG |
| R-03 wait_warning | primeira espera explícita, record=threatened | aviso perceptível da infiltração; record=warned, ainda seco; jogador não é movido | Sem RNG |
| R-03B wait_wetting | espera explícita posterior, record=warned | água atinge o registro, record=wet; pressão tense; jogador não é movido | Sem RNG |
| R-04 wait_loss | espera explícita, record=wet | água torna o texto irrecuperável, record=lost; outcome=lost; epílogo | Sem RNG |
| R-05 rescue_intact | intenção explícita de retirar/proteger registro, record=threatened/warned, método coberto | registro preservado; outcome=preserved; epílogo, inclusive antes de diálogo ou investigação | Sem teste quando ação simples não tem obstáculo |
| R-06 rescue_partial | mesma intenção, record=wet | salvar o que ainda é legível; record=partial; outcome=partial; não restaurar o que se perdeu | Sem RNG |
| R-07 inspect_success | examinar/ler para recuperar conteúdo, campanha ativa, recibo favorável | informação útil recuperada; objetivo de recuperação resolvido; record=partial; outcome=partial | Recibo existente de investigação |
| R-08 inspect_failure | mesma intenção, recibo desfavorável | objetivo não obtido; se threatened/warned, torna wet; se wet, torna lost e encerra | Recibo existente de investigação |
| R-09 withdraw | recusa/abandono explícito | outcome=abandoned; epílogo sem atribuir deslocamento não declarado; Mara responde à decisão | Sem RNG |

O ritmo da espera foi escolhido como opção A: aviso, molhamento e perda exigem
três esperas explícitas em sequência. Falha mecânica usa R-08 e pode antecipar
o dano, sem converter diálogos, consultas ou latência em tempo ficcional.
O catálogo sintético offline não representa aceite da experiência narrativa.

R-07/08 reutilizam somente o perfil de investigação já implementado em
produce_source_player_action (Wits + Investigation, dificuldade 3, sem modificadores,
ficha sintética elegível). Essa é referência de implementação existente, não
afirmação de regra universal de V5. Fora dessas condições, recusar preparação
mecânica sem lançar dado. A ficha completa permanece tarefa posterior.

### Cobertura e ações fora do catálogo

Reconhecer intenções equivalentes: retirar o registro, levá-lo à superfície seca
ou protegê-lo da água podem mapear a rescue se método/alvo forem compatíveis.
Não exigir frase pronta. Não tratar menção de água como intenção de destruir.
Fala citada ao NPC não executa automaticamente a ação que menciona.

Pedido composto ambíguo pede esclarecimento antes de RNG. Método plausível não
coberto retorna limitação explícita sem consumir chamada narrativa nem alterar
mundo, preservando rascunho. Não usar falha ficcional para disfarçar lacuna técnica.
A cobertura inicial é limitada; não prometer liberdade irrestrita de campanha.

### Fronteira técnica e persistência

1. Setup opt-in novo cria campanha sintética com versão de conteúdo fixada;
   não migra campanhas B antigas nem altera padrão v1.
2. Claim persistido captura estado/revisão e reserva uma operação.
3. Classificação local valida cobertura e, se necessário, usa o recibo mecânico;
   gate de pausa é consultado novamente imediatamente antes de RNG.
4. Conteúdo produz opções elegíveis; resolve_scene_beat seleciona o beat.
   O estado resultante proposto e o recibo são retidos atomicamente na preparação.
   Um rascunho puro já pode vincular fato `campaign.progression`, evento e
   `StateChange` à mesma operação; o perfil B v1 ainda os recusa corretamente.
5. H6 recebe o mesmo pacote retido. Sem commit, não há novo estado de campanha.
6. Admissão estrutural/agência/sigilo/contradições e correspondência de IDs precede
   commit; confirmação atômica grava fonte, efeito e nova revisão. Falha reverte tudo.
7. Reconexão consulta estado; retomada explícita só narra a preparação original.
   Replay terminal não chama H6; cápsula inconsistente bloqueia em vez de recalcular.

Pontos existentes que exigem extensão explícita: SourceProducerConfig.profile,
union de preparação/cápsula, prepare_source_turn_draft, allowlists de
narrative_source_turn, leitores de contexto, execute_source_turn e commit_turn.
Não basta permitir world.scene.beat_resolution na allowlist: revalidar origem,
delta, versão, revisão e vínculo da operação. Evitar DDL novo enquanto o envelope
versionado e a transação existentes comportarem o contrato com consulta íntegra.
Caso não comportem, documentar necessidade de migração antes de implementá-la.

### Admissão e limites de prova semântica

realized_effects é declaração a conferir, não evidência de que a prosa expressa
o efeito. O primeiro incremento deve reutilizar os gates existentes e acrescentar
contraprovas de omissão/negação/ator incorreto para cada efeito do catálogo.
Não alegar verificação semântica completa por regex ou IDs. A avaliação de texto
e o ensaio humano continuam necessários antes de admitir qualquer narrador.
Se o recorte não puder impedir contradição material com seus gates, bloquear
ativação e reportar a lacuna, sem enfraquecer o contrato ou acrescentar outro LLM.

## 5. Acceptance Criteria

- **AC-001**: Dada pergunta de tarefa, quando Mara responde, há resposta pertinente
  e opção acionável, sem fala/emoção nova atribuída ao jogador.
- **AC-002**: Dado registro já molhado, quando chega outro turno, contexto e prosa
  preservam essa condição; descrição de registro intacto é contraprova.
- **AC-003**: Dado abandono ou resolução antecipada, há epílogo correspondente,
  sem obrigar investigação ou cena final previamente marcada.
- **AC-004**: Dado recibo de falha, não conceder o objetivo; pausa/reconexão
  conservam os mesmos dados e a mesma preparação.
- **AC-005**: Dado segredo solicitado, não revelar identidade; recusa ainda deve
  responder à intenção, e não substituí-la por poeira/luz.
- **AC-006**: Dada operação repetida ou concorrente, um único efeito pode confirmar.
- **AC-007**: Dado narrador diferente, nenhum critério causal ou de segurança muda.
- **AC-008**: Dada sessão Luna conectada, primeiro envio não aguarda cooldown local;
  enquanto ação está pendente, novo envio permanece bloqueado.
- **AC-009**: Dado teste Luna encerrado, custo é apresentado com proveniência;
  interrupção com tokens faltantes mostra total indisponível e subtotal separado.

## 6. Test Automation Strategy

Usar pytest com rede bloqueada e SQLite temporário; Vitest para UI/protocolo.
Começar pelo núcleo puro e fixtures autoradas, depois integração B, persistência,
pausa e concorrência. Não usar live para testar determinismo.
Corpus e trajetórias estão no protocolo relacionado. Sem percentual de cobertura
inventado ou threshold narrativo escolhido depois de ver as respostas.
Medição futura separa t_submit, t_dispatch, t_response e t_commit usando relógio
monotônico por processo; custo usa todos os output_tokens, incluindo raciocínio
contabilizado, sem solicitar nem registrar conteúdo de raciocínio.

## 7. Rationale & Context

O ensaio manual Luna usou microcena B ambiental sem este catálogo; a falha de
experiência não isola modelo versus composição. O desenho reduz essa confusão:
cada trajetória permite comparar efeito esperado, estado confirmado e prosa.
As decisões aprovadas definem recorte e direção; não aprovam automaticamente
as nove consequências candidatas nem demonstram que elas serão divertidas.

## 8. Dependencies & External Integrations

- **EXT-001**: Nenhuma inferência necessária ao planejamento/contraprovas offline.
- **SVC-001**: Luna low somente em futura execução autorizada, alvo exato,
  orçamento delimitado e capability revalidada. Sem troca automática.
- **INF-001**: Persistência local transacional e identidades P/K/H existentes.
- **DAT-001**: Catálogo versionado sintético, ficha elegível e fontes atribuídas.
- **PLT-001**: Python/FastAPI e React/TypeScript existentes; sem pacote novo.
- **COM-001**: Sigilo de credenciais, agência e visibilidade já exigidos no projeto.

## 9. Examples & Edge Cases

- “Mara, como posso ajudar?”: resposta sobre salvamento, não atmosfera.
- “Digo a Mara: leve o registro”: pedido de ajuda, não deslocamento automático do
  jogador nem salvamento realizado; a futura cobertura deve distinguir pedido e ação.
- “Levo o registro até a superfície seca”: se threatened e método coberto,
  preserved; não exigir conversar primeiro.
- Fonte anterior fala de luz tremulando: não derivar pane elétrica ou nova ameaça.
- Falha de HTTP após RNG: preparação retida, nenhuma água avança por latência.
- Campanha encerrada: consultar epílogo é leitura; novas ações exigem decisão
  separada de continuar outra aventura, sem reabrir esta automaticamente.

## 10. Validation Criteria

O ritmo A foi escolhido antes do código. Antes de
ativação, passar contraprovas offline, paridade v1/B antigo, atomicidade e UI;
depois observar trajetórias completas com custo/latência explícitos e aceite humano.
Esta especificação não declara esses testes executados. Mudanças de cooldown
e custo são implementação separada autorizada em 29/09 e documentada em relatório.

## 11. Related Specifications / Further Reading

- [Plano e decisões](../plan/architecture-hybrid-campaign-progression-1.md)
- [Protocolo de avaliação](../evals/narrator/hybrid_campaign_progression_protocol_v1.md)
- [Beat determinístico](spec-deterministic-scene-resolution.md)
- [Fonte B](../plan/architecture-narrative-source-bridge-1.md)
- [Produtor B](../plan/feature-narrative-source-input-producer-1.md)
