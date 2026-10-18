# Gate de rota do Narrador após HYP-002

**Data:** 2026-09-25

**Status:** rota A aprovada; seleção de alvo/provedor/custo ainda pendente

**Escopo:** escolher como voltar a buscar um Narrador admissível para o MVP após
HYP-001 e HYP-002 encerrarem sem candidato elegível. Este gate não autoriza
inferência, credencial, custo, provedor, candidato, default ou campanha híbrida.

## Estado observado

- HYP-001: Qwen 2/8 e GPT-OSS 5/8; nenhum elegível.
- HYP-002: Qwen 0/8 e GPT-OSS 0/8 no contrato fechado; nenhum elegível.
- Os dois lotes foram íntegros e aceitos pelo usuário.
- O checklist aprovado exige escolher e admitir o Narrador antes de iniciar a
  arquitetura e implementação da campanha híbrida.
- Repetir os mesmos alvos ou relaxar retrospectivamente os gates não produziria
  evidência prospectiva válida.

## Rotas possíveis

### A — avaliar um candidato novo mantendo arquitetura e gates — recomendada

Pesquisar e selecionar um único alvo mais capaz, com modelo e provedor exatos,
e preparar HYP-003 prospectiva com casos sintéticos inéditos. Preserva autoridade
canônica, resolvedor, agência, segredo, política de admissão e a separação entre
resultado mecânico e prosa.

Consequências: exige escolher alvo, provedor, custo máximo e forma segura de
credencial antes da rede; pode terminar novamente sem elegível. É a menor mudança
que ainda pode produzir um Narrador sem redefinir a arquitetura aprovada.

Resposta de autorização: `Aprovo NARRATOR-ROUTE-A`.

### B — criar renderização determinística/híbrida para classes de alto risco

Substituir ou limitar a geração livre em espera, mecânica, segredo e ação ambígua,
usando templates/realizador determinístico e reservando o modelo para superfícies
menos arriscadas. Pode aumentar previsibilidade, mas altera a divisão de autoridade,
o produto narrativo e a arquitetura do turno.

Consequências: exige decisão arquitetural própria, novos contratos e implementação
antes de nova admissão. Não está coberta pelas decisões atuais.

Resposta de autorização: `Aprovo NARRATOR-ROUTE-B`.

### C — admitir GPT-OSS provisoriamente por exceção

Aceitar explicitamente um candidato que não atingiu os gates e restringi-lo com
recusa runtime. Esta rota transforma evidência insuficiente em risco aceito e
exige critérios de revogação, fallback, custo, `CAP-001` e escopo provisório.

Consequências: maior risco de estado inventado, agência indevida e estagnação;
contraria a política de admissão aplicada até aqui. Não recomendada.

Resposta de autorização: `Aprovo NARRATOR-ROUTE-C`.

### D — interromper o MVP no checkpoint do Narrador

Preserva todos os resultados e evita nova despesa ou arquitetura, mas impede a
campanha curta completa e a aceitação integral do MVP no escopo aprovado.

Resposta: `Escolho NARRATOR-ROUTE-D`.

## Recomendação

Escolher A. Ela preserva as decisões bloqueadas e muda somente o candidato, com
uma hipótese nova e critérios prospectivos. Depois da autorização, o trabalho
autônomo será pesquisar uma lista curta atual, comparar capacidade, custo, rota e
segurança, e voltar com um alvo exato e orçamento para uma decisão separada antes
de qualquer chamada.

## Decisão registrada em 26/09/2026

O usuário respondeu `Aprovo NARRATOR-ROUTE-A`. A aprovação autoriza pesquisa e
preparação prospectiva preservando arquitetura e gates; não admite um narrador
nem autoriza por arrasto um provedor pago. A pesquisa oficial e a proposta
concreta HYP-003 estão em
`narrator-route-a-hypothesis-003-proposal-2026-09-26.md` e `.json`.
O próximo checkpoint é a escolha do alvo, provedor e orçamento ali delimitados,
não uma nova aprovação da rota A.
