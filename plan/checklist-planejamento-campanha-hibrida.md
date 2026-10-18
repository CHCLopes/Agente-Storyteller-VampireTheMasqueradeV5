# Checklist de planejamento — campanha híbrida

Data original: 09/09/2026. Atualização: 03/10/2026.
Estado: **planejamento ativo por PROG-ROUTE-B; respostas de produto em proposta**.

DEC-PROG-001/002 aprovadas em 29/09: aventura curta no Arquivo/Galeria com Mara
e registro ameaçado, em novo perfil B opt-in com consequências determinísticas.
Detalhamento em [especificação](../spec/spec-architecture-hybrid-campaign-progression.md).
CAMP-05: formato curto decidido, sem duração estimada; CAMP-08: culminação
adaptável, não cena final obrigatória; CAMP-23: somente nova sessão sintética
neste incremento. Esses itens são parciais; as demais respostas não são inferidas.
CAMP-17–20 receberam regras candidatas, ainda sem aceite de severidade/ritmo.
O ritmo A foi posteriormente escolhido: primeira espera avisa, segunda molha,
terceira perde. A integração B opt-in e o ensaio autorado offline estão
verificados tecnicamente; CAMP-24 permanece aberto até julgamento humano da
experiência e avaliação do narrador. Esta evidência não responde às demais
perguntas de produto nem torna a campanha o fluxo padrão.
O usuário confirmou depois o funcionamento de envio/nova sessão e a progressão,
resposta de Mara e conclusão da microcena conforme o objetivo de teste. UX não
foi medida, e não houve aceite dos demais percursos. A preferência futura por
fala direta de NPC foi registrada em
[observação separada](observation-npc-direct-dialogue-1.md), sem virar
requisito aprovado ou fechar CAMP-24.
Posteriormente, o usuário confirmou que os desfechos CAMP-EVAL-02–04 foram
executados como esperado no ensaio autorado. Em 30/09, confirmou que 01 já
havia sido executado, que 05 cumpriu o salvamento esperado e que recusa,
orientação e salvamento de 08 fizeram sentido após o procedimento com recarga.
Isso não equivale a narrador admitido ou satisfação integral de UX: a mediação
impessoal da fala de Mara foi apontada como perda de imersão. CAMP-24 permanece
aberto; 06/07 estão cobertos por testes offline com recibos fixos, não por
aceite humano reproduzível no navegador atual.
HYP-007-L2 realizou duas chamadas Luna low, admitiu R-01 e parou por rejeição
de R-05; custo estimado USD 0,0012318. Isso não fecha CAMP-24 nem admite
narrador. A lacuna de localização do registro observada em L2 foi tratada pela
opção A aprovada em 03/10: estado canônico v2 para novas sessões, leitura v1 sem
migração e posição antes/depois no pacote B, verificados offline. Decisão e
limites em [observação separada](observation-campaign-record-location-1.md).
CAMP-24 continua aberto; nova avaliação paga exige autorização própria, sem
reabrir L2 ou presumir que o prompt v2 tornou Luna elegível.

HYP-007-L3 executou uma chamada, zero turnos completos, custo estimado final
USD 0,0007078. A parada reproduzida foi falso positivo de atribuição NPC,
corrigido localmente em TASK-015 sem reclassificar o turno histórico. Texto
identifica a bancada e fala direta, mas não há resgate ou campanha completa.
410 regressões e sete testes específicos passaram (sobrepostos). L4 preparado
offline, gates live/paid false, depende de novo orçamento/aceite delimitado;
nenhum narrador admitido e CAMP-24 aberto. Evidência em
[relatório L3](../evals/narrator/reports/hybrid-campaign-luna-hyp-007-l3-2026-10-03.md).
A [limitação lexical de agência](observation-campaign-agency-vocabulary-1.md)
foi registrada separadamente, sem virar nova frente ou prioridade por arrasto.
Em seguida, o usuário aprovou a conclusão delimitada L3 e HYP-007-L4: até 17
chamadas e teto estimado adicional USD 0,15. Gate exclusivo L4 ativo, entrada
segura da chave pendente; não há resultado ou admissão L4 por essa aprovação.

Em 10/09/2026, o usuário aprovou este roteiro de planejamento: “Plano aprovado.
Vamos continuar.” As 24 perguntas permanecem abertas; a aprovação não define
suas respostas nem inicia a implementação da campanha. Em 29/09/2026,
PROG-ROUTE-B autorizou antecipar este planejamento à retomada da admissão.

Problema confirmado de alto impacto no MVP: progressão narrativa perceptível e
responsividade de NPC. Ele deve ser resolvido antes da aceitação integral; seu
planejamento agora precede a admissão do narrador. O registro delimitado
está em [issue-mvp-narrative-progression-1.md](issue-mvp-narrative-progression-1.md)
e se relaciona especialmente a `CAMP-17`–`CAMP-20`; nenhuma pergunta abaixo foi
marcada como respondida por esse diagnóstico ou pela aprovação da ordem.

Luna low é a referência prioritária solicitada pelo usuário, não um narrador
admitido. A proposta inicial e os critérios portáveis estão em
[architecture-hybrid-campaign-progression-1.md](architecture-hybrid-campaign-progression-1.md).
Ela relaciona CAMP-17–20 a um recorte concreto de CAMP-05–08 e CAMP-21–24,
sem substituir sessão zero, definir um default ou autorizar chamadas.

Este documento organiza as perguntas de planejamento solicitadas pelo usuário.
A preferência por combinar estrutura geral e improvisação orienta a discussão;
as respostas e o desenho de implementação permanecem em aberto. A prioridade
corrente continua registrada no [documento de retomada](../PROMPT_RETOMADA_2026-09-06.md).

## Ponto de partida

- Intenção já registrada: a IA propõe a campanha durante uma sessão zero, em
  construção conversacional passo a passo com o jogador.
- Limites já estabelecidos: preservar a agência do jogador, os acontecimentos
  anteriores e as consequências; soluções plausíveis fora do caminho previsto
  não devem ser bloqueadas ou punidas por esse motivo.
- Estado observado em 09/09: o jogo atual usa uma situação inicial preparada e
  improvisa cenas com memória e pendências. A sessão zero conversacional e uma
  condução global com progressão e encerramento ainda não estão implementadas
  nesse fluxo. Revalidar esse estado quando esta pauta for retomada.

Proposta de referência para discutir:

> A campanha será construída com o jogador na sessão zero, terá conflitos e uma
> estrutura dramática geral preparados, e se desenvolverá por cenas improvisadas.
> Os arcos caminharão para resoluções significativas, com caminhos e desfechos
> determinados pelas escolhas e consequências do jogo.

## 1. Sessão zero e experiência desejada

- [ ] **CAMP-01** — Que experiência a campanha deve oferecer: quais temas, tom e
  conflitos pessoais ou sociais devem ocupar o centro da história?
- [ ] **CAMP-02** — Quais informações a conversa inicial precisa reunir e em que
  ordem, incluindo intensidade, Linhas e Véus, sem se tornar um questionário longo?
- [ ] **CAMP-03** — Como vincular o personagem à premissa e aos NPCs, distinguindo
  o passado aprovado pelo jogador dos detalhes que a IA poderá criar?
- [ ] **CAMP-04** — Qual proposta pública encerra a sessão zero, sem revelar
  segredos, e como o jogador poderá ajustá-la antes da primeira cena?

## 2. Estrutura geral e extensão

- [ ] **CAMP-05** — O primeiro formato será uma aventura curta, uma campanha com
  um arco principal ou uma sequência de arcos, e qual duração esperamos oferecer?
- [x] **CAMP-06** — Qual pergunta ou conflito central dará unidade à campanha e
  permitirá reconhecer que houve uma resolução significativa?
  Resposta do recorte aprovada em DEC-PROG-001: o destino de um registro público
  ameaçado por infiltração, com preservação, recuperação parcial ou perda/abandono.
- [ ] **CAMP-07** — O que será preparado antes de jogar: facções, objetivos,
  conflitos, revelações possíveis, marcos e condições de desfecho?
- [ ] **CAMP-08** — Prepararemos uma cena final específica ou uma culminação
  adaptável, e o que ocorrerá se o jogador a evitar, antecipar ou transformar?

## 3. Mundo, segredos e futuro planejado

- [ ] **CAMP-09** — Quais NPCs ou facções terão objetivos próprios e quais
  acontecimentos poderão decorrer desses objetivos sem intervenção do jogador?
- [ ] **CAMP-10** — Quais ações e passagens de tempo ficcional justificarão o
  avanço desses planos, e como suas consequências se tornarão perceptíveis?
- [ ] **CAMP-11** — Como distinguir fatos já estabelecidos, segredos existentes,
  intenções de NPCs e possibilidades futuras, para que revisar o plano não altere
  retroativamente a história?
- [ ] **CAMP-12** — Quais respostas de um mistério precisam existir desde o início
  e quais espaços podem permanecer abertos para criação posterior coerente?

## 4. Improvisação e liberdade do jogador

- [ ] **CAMP-13** — Quais adições poderão surgir livremente nas cenas e quais
  exigirão avaliar o impacto no arco geral antes de incorporá-las?
- [ ] **CAMP-14** — Como aproveitar uma adição interessante, como os guardas já
  narrados, sem exigir que todo detalhe novo faça parte da trama principal?
- [ ] **CAMP-15** — Como a campanha responderá quando o jogador seguir outro
  interesse, recusar um gancho ou resolver um problema por um caminho inesperado?
- [ ] **CAMP-16** — Que sinais indicarão condução excessiva, e como evitar forçar
  encontros, invalidar sucessos ou criar ameaças apenas para recuperar o plano?

## 5. Ritmo, progressão e culminação

- [ ] **CAMP-17** — Como alternar investigação, conversa, ação, tensão e descanso,
  respeitando os interesses demonstrados pelo jogador?
- [ ] **CAMP-18** — Que mudanças concretas mostrarão avanço do arco e permitirão
  detectar estagnação, repetição ou acúmulo de ganchos sem desenvolvimento?
- [ ] **CAMP-19** — Como escolher quais pendências desenvolver ou encerrar em
  cada momento, preservando as demais para retomada coerente?
- [ ] **CAMP-20** — Quais condições indicarão que o arco está pronto para sua
  culminação, inclusive quando as escolhas do jogador encurtarem o caminho?

## 6. Encerramento, validação e integração futura

- [ ] **CAMP-21** — O que distingue fim de cena, fim de arco e fim de campanha,
  e como o jogador reconhecerá cada um desses marcos?
- [ ] **CAMP-22** — Como apresentar consequências e epílogo para diferentes
  resultados, incluindo acordos, derrotas e abandono do conflito, e permitir
  escolher entre continuar a crônica ou encerrá-la?
- [ ] **CAMP-23** — A construção começará apenas em campanhas novas ou também
  poderá orientar o save atual, preservando seu passado, interesses e liberdade
  sem impor retroativamente uma trama?
- [ ] **CAMP-24** — Qual será a menor experiência completa para validar esse
  desenho e que evidências mostrarão começo, desenvolvimento, resolução,
  improvisação interessante e escolhas com consequências reais?

## Como retomar e registrar respostas

Por PROG-ROUTE-B, começar pelo problema de progressão (bloco 5) em conjunto com
o recorte mínimo proposto, depois preencher os demais blocos conforme dependência.
Não solicitar todas as respostas de uma só vez. Usar o feedback do jogo atual como evidência, sem tratar exemplos
ou possibilidades narrativas como acontecimentos da campanha.

Marcar uma pergunta quando sua resposta estiver registrada. Para cada resposta,
anotar o ID, a formulação, o status (proposta, decisão ou questão ainda aberta) e
as implicações para a experiência. Decisões de produto permanecem com o usuário.

Depois das respostas, consolidar as decisões e suas lacunas em uma especificação
e delimitar o primeiro incremento de implementação. A direção B sobre
representação e memória narrativa continua sendo uma frente distinta.

## Referências de contexto

- [Handoff original: criação da campanha e limites do narrador](C:/Users/skate/Desktop/Codex_Handoff_Agente_Storyteller_V5.md:53), especialmente linhas 53–79.
- [Direção improvisacional de cena](../spec/spec-improvisational-scene-direction.md).
- [Arquitetura atual do turno e memória](../README.md#arquitetura-do-turno).
- [Correção de continuidade dos guardas](../evals/narrator/reports/manual-current-game-guards-continuity-2026-09-09.md).
