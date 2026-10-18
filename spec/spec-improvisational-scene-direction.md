---
title: Direção Improvisacional e Evolução da Cena
version: 1.0
date_created: 2026-08-26
last_updated: 2026-08-26
owner: Produto Agente Storyteller
status: Implementada no worktree; aceitação humana pendente
tags: [narrative, improvisation, scene, admission, memory, ux]
---

# Direção Improvisacional e Evolução da Cena

## Decisão de produto

O Agente Storyteller não é um jogo roteirizado cuja LLM apenas apresenta textos
previamente autorizados. A LLM exerce direção ficcional limitada: reage à intenção
do jogador e propõe como a cena local continua, enquanto módulos determinísticos
preservam regras, cálculos, resultados mecânicos e transições protegidas.

A formulação canônica é:

> Eventos passados são imutáveis; a cena atual e a projeção do mundo evoluem por
> novos eventos. A LLM propõe ficção; a aplicação valida e admite; somente o commit
> transacional transforma a proposta em verdade da campanha.

Essa decisão substitui o contrato temporário em que H6 copiava literalmente uma
frase conservadora e era impedido de introduzir qualquer detalhe. Aquele contrato
era um guardrail de teste e não representa a experiência pretendida.

## Requisitos de experiência

- **IMP-001 — movimento:** toda entrada ficcional significativa deve provocar uma
  reação externa, revelação, complicação, mudança de pressão ou avanço de pendência.
- **IMP-002 — cena ausente:** uma consulta como `Onde estou?` em uma campanha sem
  cena deve estabelecer local concreto, tensão imediata e um gancho reutilizável.
- **IMP-003 — intenção livre:** ausência de detalhe cosmético não deve causar uma
  pergunta de esclarecimento. O narrador improvisa o que não altera mecânica,
  agência, alvo essencial ou uma decisão protegida.
- **IMP-004 — sucesso:** um sucesso mecânico produz consequência ficcional concreta
  compatível; a narração não pode negar ou esvaziar o resultado.
- **IMP-005 — falha com movimento:** uma falha não concede o objetivo, mas pode
  aumentar pressão, introduzir custo, reação, ameaça ou oportunidade incompleta.
- **IMP-006 — agência:** o narrador controla mundo e NPCs, nunca escolhe ação, fala,
  pensamento, emoção, aceitação ou recusa pelo personagem do jogador.
- **IMP-007 — continuidade:** local, detalhes, NPCs e pendências admitidos devem
  orientar os turnos seguintes e sobreviver a reconexão/reload.
- **IMP-008 — abertura:** cada beat termina com uma pergunta ou pressão concreta,
  sem restringir a pessoa às opções sugeridas.
- **IMP-009 — ciclo de pendências:** um gancho aberto permanece recuperável até um
  beat declarar sua resolução; limites de contexto não podem apagá-lo em silêncio.

Comandos operacionais, texto vazio, falha técnica e ambiguidade que realmente muda
alvo ou mecânica são exceções legítimas à obrigação de avançar a ficção.

## Fronteiras de autoridade

### Vinculante

- ação declarada pelo jogador;
- resultado da rolagem e demais fatos mecânicos;
- ficha, recursos, dano, Fome, XP e invariantes V5;
- eventos passados e estado já admitido;
- lore versionado, visibilidade e segredos recuperados.

### Improvisável sob admissão

- observações e detalhes locais;
- pistas compatíveis com o resultado;
- ações e falas de NPCs;
- complicações, pressão e ganchos;
- transições narrativamente justificadas;
- pendências pequenas que conectam a cena ao contexto maior.

### Proibido

- alterar ou recalcular mecânica;
- decidir pelo personagem do jogador;
- revelar conteúdo confidencial ao jogador;
- contradizer silenciosamente fatos conhecidos;
- mudar local ou presença de NPC sem um acontecimento explícito;
- escrever IDs, caminhos de estado ou mutações arbitrárias;
- transformar diretamente saída do modelo em canon.

## Contrato e admissão

H6 retorna uma `SceneContinuationProposal` estruturada com prosa, outcome, local,
resumo da cena, NPCs presentes, até quatro fatos propostos, pendências abertas,
pendências anteriores resolvidas explicitamente e uma pergunta aberta ao jogador.

A política `scene_director_admission.v1` verifica antes de qualquer mutação:

1. correspondência com sucesso, falha ou turno sem teste;
2. limites de tamanho e ausência de conteúdo interno;
3. preservação da agência do jogador;
4. transição explícita para mudança de local;
5. acontecimento explícito para mudança do conjunto de NPCs;
6. falha sem concessão conclusiva do objetivo;
7. separação entre fatos visíveis e fatos de Storyteller;
8. quantidade e tipos permitidos de novidade.

A aplicação atribui IDs, proveniência e referências de política. A proposta bruta
não é evento, memória ou estado.

## Persistência e memória

Após admissão, o mesmo commit confirma:

- fatos canônicos mecânicos e ficcionais;
- evento visível de cena e, quando necessário, evento confidencial separado;
- nova projeção compacta de `SceneState`;
- narrativa entregue ao jogador;
- candidato de memória e memória episódica derivados do evento admitido;
- relações e demais mudanças determinísticas do turno.

A cena compacta guarda local, resumo, NPCs, detalhes recentes, pendências e número
do último turno. Fatos confidenciais permanecem fora do snapshot entregue ao
frontend e são recuperados internamente de turnos recentes para o contexto
`CONFIDENCIAL` de H6.

Se geração, schema, política, entrega, cancelamento ou persistência falharem, a
proposta não produz mutação parcial e o turno não é consumido. A falha permanece
observável e repetível pela mesma operação; um texto técnico nunca é canonizado
como substituto de um beat ficcional que o Narrador não concluiu.

## Critérios de aceite

- **AC-IMP-001:** `Onde estou?` sem cena gera e persiste uma abertura concreta.
- **AC-IMP-002:** `então estabeleça` desenvolve a cena sem exigir verbo mecânico.
- **AC-IMP-003:** `Investigar o galpão abandonado` preserva o dado e gera uma
  consequência específica compatível.
- **AC-IMP-004:** uma falha aumenta pressão sem conceder a descoberta procurada.
- **AC-IMP-005:** a próxima geração recebe resumo, detalhes e pendências admitidos.
- **AC-IMP-006:** um fato `storyteller` orienta H6 sem aparecer na prosa pública.
- **AC-IMP-007:** mudança de local sem `transition` é rejeitada.
- **AC-IMP-008:** mudança de NPCs sem `npc_action` ou `transition` é rejeitada.
- **AC-IMP-009:** texto que decide pelo personagem é rejeitado sem commit parcial.
- **AC-IMP-010:** reconexão reidrata narrativa e projeção de cena confirmadas.
- **AC-IMP-011:** timeout, cancelamento, truncamento ou schema inválido preservam o
  snapshot anterior e registram somente evidência segura da tentativa.
- **AC-IMP-012:** a experiência normal não usa frases como “nenhum novo detalhe foi
  estabelecido canonicamente” nem pede ao modelo para copiar um template.

## Não escopo

Esta decisão não escolhe provedor, modelo, endpoint, orçamento, política de
gratuidade, roteamento ou fallback entre alvos. `CAP-001` ainda deverá medir, com
um corpus real, português, coerência multietapas, repetição, agência, segurança e
latência. A admissão determinística reduz riscos, mas não prova qualidade semântica
geral nem garante que todo modelo compatível ofereça uma boa experiência.

## Implementação relacionada

- `api/scene_director_service.py`: contrato e política de admissão.
- `api/scene_service.py`: projeção compacta e compatível da cena.
- `api/orchestrator_service.py`: contexto, chamada H6 e proposta estruturada.
- `api/turn_execution_service.py`: admissão, derivação e commit transacional.
- `skills/H6_vtm_narrator.md`: papel e limites do Storyteller.
- `tests/test_scene_director_service.py`: invariantes puras da política.
- `tests/test_turn_execution_service.py`: atomicidade e fallbacks.
- `tests/test_turn_pipeline_integration.py`: continuidade e contrato H6.
- `tests/test_websocket_transactional.py`: experiência e reconexão pelo protocolo.
