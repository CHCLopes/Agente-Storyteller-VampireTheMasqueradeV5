---
title: Bandeja de Dados V5 Visível e Interativa
version: 0.1
date_created: 2026-08-25
last_updated: 2026-08-25
owner: Produto Agente Storyteller
status: Aprovada e adiada para o segundo momento
tags: [design, dice, v5, frontend, deterministic-engine, transactional-turn]
---

# Introduction

Esta especificação registra a decisão humana de evoluir a rolagem de dados do
Agente Storyteller para uma pequena aplicação visual e interativa dentro da
interface. Quando uma ação exigir teste, o jogador deverá receber uma proposta
de rolagem, clicar para executá-la, visualizar os dados e somente então receber
a narrativa construída sobre o resultado canônico.

Esta direção foi aprovada em 2026-08-25, mas está deliberadamente adiada. Sua
implementação e o refinamento técnico correspondente somente poderão começar
depois que o trabalho atualmente em curso sobre LLM, turnos, persistência,
eventos e memória estiver concluído e aceito.

## 1. Purpose & Scope

O objetivo é substituir o padrão conversacional genérico de “pedir para rolar”
por uma interação explícita, legível e dramática, compatível com a experiência
de Vampiro: A Máscara V5.

O escopo futuro inclui:

- apresentação do pool proposto pelo motor determinístico;
- confirmação da rolagem por clique;
- execução autoritativa no backend;
- visualização distinta de dados normais e dados de Fome;
- exposição legível do resultado mecânico;
- preservação idempotente do resultado antes de mostrá-lo ao jogador;
- geração narrativa automática baseada no resultado confirmado;
- recuperação após reconexão e retry sem nova rolagem;
- rerrolagem de Força de Vontade baseada na rolagem original.

Ficam fora do primeiro candidato desta funcionalidade:

- modo automático de rolagem;
- RNG autoritativo no navegador;
- alteração manual irrestrita de resultados;
- escolha de mecânica pelo LLM;
- implementação antes da aceitação do escopo atual;
- mudanças oportunistas em outros módulos ou regras.

## 2. Definitions

- **Bandeja de Dados**: componente visual que apresenta a proposta, executa a
  confirmação do jogador e exibe o resultado da rolagem.
- **Proposta de Rolagem**: composição determinística e ainda não resolvida de
  ação, atributo, perícia, pool, dados de Fome, dificuldade e revisão de estado.
- **Resultado de Rolagem**: dados individuais e resultado mecânico calculado
  pelo backend e persistido de maneira imutável.
- **Dados de Fome**: subconjunto visualmente distinto do pool, tratado pelo
  motor de regras V5 existente.
- **Turno aguardando narrativa**: estado durável no qual o jogador já viu um
  resultado canônico, mas a narrativa final ainda não foi concluída.
- **RNG**: mecanismo de geração de números aleatórios usado para resolver dados.
- **Idempotência**: garantia de que repetir a mesma operação não cria uma nova
  rolagem nem altera o resultado existente.

## 3. Requirements, Constraints & Guidelines

- **ROLL-001**: Quando uma ação tiver `requires_roll=true`, o primeiro candidato
  desta funcionalidade deverá exigir confirmação explícita do jogador por meio
  do botão de rolagem.
- **ROLL-002**: Quando `requires_roll=false`, a ação deverá seguir diretamente
  para a narrativa, sem exibir uma bandeja vazia ou exigir clique desnecessário.
- **ROLL-003**: O motor determinístico deverá ser a única autoridade para
  atributo, perícia, pool, dados de Fome, dificuldade, modificadores e resultado.
- **ROLL-004**: O LLM poderá narrar um resultado confirmado, mas não poderá
  selecionar o pool, lançar dados, alterar faces, recalcular sucessos ou
  sobrescrever consequências mecânicas.
- **ROLL-005**: O frontend não poderá produzir o resultado autoritativo. A
  animação deverá representar exatamente as faces devolvidas pelo backend.
- **ROLL-006**: Antes do clique, a interface deverá mostrar, no mínimo, ação,
  atributo, perícia, pool total, quantidade de dados de Fome e dificuldade.
- **ROLL-007**: Dados normais e dados de Fome deverão ser visualmente distintos
  e também diferenciáveis sem depender apenas de cor.
- **ROLL-008**: Depois da confirmação, a interface deverá mostrar os dados
  individuais e a projeção mecânica produzida pelo motor, incluindo sucessos,
  margem e ocorrências especiais reconhecidas pelas regras existentes.
- **ROLL-009**: A narrativa deverá começar automaticamente após a apresentação
  da rolagem confirmada; não haverá um segundo botão obrigatório para narrar.
- **ROLL-010**: Uma solicitação genérica como “quero rolar os dados”, sem ação
  nem pool explícito, não poderá usar valores default ou inventar mecânica. A
  interface deverá pedir uma ação ou uma combinação válida de atributo e perícia.
- **ROLL-011**: Se o motor não puder inferir um pool autorizado, a interface
  poderá oferecer seleção explícita de atributo e perícia a partir das opções
  permitidas pelo estado, ficha e regras locais.
- **ROLL-012**: Assim que um resultado for exibido ao jogador, ele deverá ser
  canônico, imutável e recuperável. Nenhum erro posterior de LLM poderá apagá-lo
  ou causar uma nova rolagem.
- **ROLL-013**: Retry da narrativa deverá reutilizar o mesmo resultado mecânico,
  com os mesmos identificadores e faces.
- **ROLL-014**: Clique duplicado, retransmissão de rede e replay do mesmo
  `operation_id` deverão devolver a rolagem já resolvida, sem consumir RNG outra vez.
- **ROLL-015**: Reconectar deverá restaurar corretamente uma proposta aguardando
  clique ou um resultado aguardando/finalizando narrativa.
- **ROLL-016**: Rerrolagem de Força de Vontade deverá operar sobre a rolagem
  original e somente sobre dados elegíveis segundo o motor existente; o vínculo
  entre rolagem original e rerrolagem deverá ser preservado.
- **ROLL-017**: O resultado resolvido deverá alimentar fatos e eventos
  canônicos. A memória derivada somente poderá resumir esses fatos e a narrativa,
  sem recalcular ou reinterpretar o resultado.
- **UX-001**: A interação por clique deverá funcionar também por teclado e ter
  descrição textual acessível das faces e do resultado.
- **UX-002**: A animação deverá respeitar preferência de movimento reduzido e
  nunca atrasar a disponibilidade do resultado textual correspondente.
- **CON-001**: Esta especificação não autoriza implementação imediata. Ela é uma
  continuação aprovada para o segundo momento, condicionada à conclusão e
  aceitação do trabalho atual.
- **CON-002**: A funcionalidade deverá permanecer dentro do monólito modular
  local-first e não introduzir microsserviço, provedor LLM ou dependência de
  cloud por arrasto.
- **CON-003**: O primeiro candidato usará clique obrigatório nas rolagens. Um
  modo automático poderá ser deliberado posteriormente, mas não será presumido.

## 4. Interfaces & Data Contracts

Os nomes finais e a versão dos schemas serão refinados antes da implementação.
O contrato mínimo conceitual deverá representar os seguintes dados:

```json
{
  "roll_proposal": {
    "proposal_id": "stable-id",
    "operation_id": "client-operation-id",
    "session_id": "campaign-session-id",
    "state_revision": 12,
    "action_label": "Investigar o galpão abandonado",
    "attribute": "Wits",
    "skill": "Investigation",
    "pool_size": 5,
    "hunger_dice": 2,
    "difficulty": 3,
    "status": "awaiting_player_roll"
  }
}
```

```json
{
  "roll_resolution": {
    "resolution_id": "stable-id",
    "proposal_id": "stable-id",
    "operation_id": "client-operation-id",
    "normal_dice": [8, 10, 2],
    "hunger_dice": [1, 7],
    "successes": 3,
    "margin": 0,
    "outcome": "success",
    "special_outcome": null,
    "status": "resolved_pending_narration"
  }
}
```

O protocolo futuro deverá preservar uma única identidade de operação ao longo
de ação, proposta, clique, resultado, narrativa e finalização. A confirmação do
clique deverá conter a revisão de estado/proposta esperada para rejeitar ações
obsoletas sem lançar novos dados.

## 5. Acceptance Criteria

- **AC-001**: Dada uma investigação reconhecida, quando o motor preparar o
  turno, então a interface mostra `Wits + Investigation`, pool, Fome e
  dificuldade antes de qualquer dado ser lançado.
- **AC-002**: Dada uma proposta válida, quando o jogador clicar em “Rolar dados”,
  então o backend resolve e persiste a rolagem antes que o frontend exiba faces.
- **AC-003**: Dado um resultado exibido, quando a geração narrativa falhar,
  então o resultado continua recuperável e uma nova tentativa não relança dados.
- **AC-004**: Dado um clique repetido com o mesmo `operation_id`, quando o backend
  receber a repetição, então devolve exatamente o mesmo `resolution_id`, faces e
  resultado.
- **AC-005**: Dada uma reconexão antes do clique, quando o estado for reidratado,
  então a mesma proposta reaparece aguardando confirmação.
- **AC-006**: Dada uma reconexão depois do clique, quando o estado for reidratado,
  então a mesma rolagem aparece resolvida, ainda que a narrativa esteja pendente.
- **AC-007**: Dada uma ação narrativa sem teste, quando ela for aceita, então não
  há bandeja nem clique e o fluxo segue diretamente para narrativa.
- **AC-008**: Dado “quero rolar os dados” sem ação ou pool, quando a mensagem for
  processada, então nenhum RNG é consumido e o usuário recebe orientação para
  completar a ação.
- **AC-009**: Dada uma resposta LLM incompatível com a mecânica, quando a
  narrativa for validada, então os dados e o resultado canônico permanecem
  inalterados.
- **AC-010**: Dada uma rerrolagem de Força de Vontade, quando ela for confirmada,
  então o resultado referencia a resolução original e somente dados elegíveis
  são afetados.
- **AC-011**: Dada preferência de movimento reduzido, quando a rolagem ocorrer,
  então o resultado textual e as faces ficam disponíveis sem animação obrigatória.

## 6. Test Automation Strategy

- **Unitários**: composição da proposta, validação de pool, transformação de
  resultado, elegibilidade de rerrolagem e reducer visual sem RNG no cliente.
- **Integração**: idempotência entre proposta e resolução, persistência anterior
  à exposição, CAS de revisão, retry de narrativa e recuperação após restart.
- **WebSocket**: sequência proposta → confirmação → resolução → narrativa →
  terminal; duplicações e reconexões em cada fronteira.
- **Frontend**: distinção de dados normais/Fome, teclado, texto acessível,
  movimento reduzido e não promoção de resultado provisório.
- **End-to-End**: investigação completa, ação narrativa sem teste, comando
  genérico incompleto, falha do narrador após rolagem e rerrolagem de Vontade.
- **Dados de teste**: RNG injetável e determinístico nos testes; nenhuma suíte
  deve depender de aleatoriedade real ou LLM remoto.
- **Regressão**: provar que o mesmo `operation_id` nunca produz duas sequências
  de faces e que nenhuma falha posterior apaga uma resolução exibida.

## 7. Rationale & Context

Em Vampiro: A Máscara, a rolagem é um momento de tensão e agência, não apenas
um cálculo oculto. O clique torna legível a mecânica escolhida pelo motor e
elimina a ambiguidade do comando conversacional “rolar os dados”.

A consequência arquitetural central é que um resultado visto pelo jogador já
é um fato do mundo. O fluxo transacional atual, no qual mecânica e narrativa
são promovidas juntas apenas no final, deverá ganhar deliberadamente um estado
durável intermediário: `resolved_pending_narration`. Essa alteração não é um
detalhe visual; é uma nova fronteira de commit e exigirá refinamento específico
antes de qualquer código.

## 8. Dependencies & External Integrations

### Infrastructure Dependencies

- **INF-001**: Persistência transacional local capaz de registrar proposta,
  resolução e estado aguardando narrativa sem duplicar RNG.
- **INF-002**: Protocolo WebSocket idempotente com reidratação e terminais
  explícitos.

### Data Dependencies

- **DAT-001**: Ficha, Fome, dificuldade, estado da cena e modificadores canônicos
  produzidos por módulos locais.
- **DAT-002**: Eventos e fatos canônicos do turno para derivação posterior de
  narrativa e memória.

### Technology Platform Dependencies

- **PLT-001**: Motor determinístico V5 existente no backend.
- **PLT-002**: Interface React existente para bandeja, animação e acessibilidade.

Não há dependência necessária de serviço externo, provedor LLM específico ou
SDK de dados.

## 9. Examples & Edge Cases

### Exemplo principal

```text
Jogador: Investigo o galpão abandonado.

Interface:
Investigar o galpão
Raciocínio 3 + Investigação 2 = 5 dados
Dados de Fome: 2
Dificuldade: 3
[ Rolar dados ]
```

### Casos de borda obrigatórios

- clique duplo ou retransmissão durante perda de rede;
- desconexão antes do clique;
- desconexão depois de o backend persistir, mas antes de a UI receber o resultado;
- falha, timeout ou cancelamento do narrador após o resultado ser exibido;
- mudança de revisão da ficha/estado entre proposta e clique;
- ação puramente narrativa;
- pedido genérico de rolagem sem pool;
- pool determinado explicitamente pelo jogador e validado pelo motor;
- rerrolagem de Vontade após reconexão;
- animações desativadas por acessibilidade.

## 10. Validation Criteria

- O backend é a única origem das faces e resultados.
- Nenhum resultado exibido pode desaparecer ou mudar após retry/reconexão.
- O frontend não contém cálculo autoritativo de regras V5.
- A narrativa não consegue alterar fatos mecânicos.
- O comando genérico não consome RNG nem usa defaults silenciosos.
- O clique obrigatório aplica-se somente a ações com rolagem.
- A suíte automatizada cobre cada transição e recuperação do estado intermediário.
- A implementação não começa antes da conclusão e aceitação do trabalho atual.

## 11. Related Specifications / Further Reading

- `plan/architecture-llm-memory-turns-1.md` — trabalho predecessor que deve ser
  concluído e aceito antes desta continuação.
- Itens futuros relacionados: NAR-002, STATE-001, DATA-002 e RULE-002.
- Decisão humana de 2026-08-25: recomendações de bandeja visual, clique
  obrigatório no primeiro candidato, autoridade do backend, persistência antes
  da exposição e retry sem rerrolagem aprovadas integralmente.
