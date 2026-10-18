# Observação HYP-003 Gemini Free L2

**Data:** 2026-09-26  
**Lote:** `d64fd149-7f9e-499d-8566-e72207833114`  
**Classificação:** inconclusivo; candidato inelegível por evidência incompleta.

O lote L2 usou o projeto Free Tier confirmado, o target direto Google Gemini
`gemini-3.8-flash` com thinking `low` e o envelope REST corrigido. Foram feitas
três chamadas: duas concluíram e a terceira recebeu HTTP 503
`provider_unavailable`. O runner encerrou globalmente e pulou os cinco slots
restantes. Não houve retry, reparo, fallback, troca de alvo nem gasto pago
autorizado. A credencial foi removida do ambiente pelo launcher.

O verificador passou no launcher e novamente offline. Preflight SHA-256:
`bc167e76728dcaabc2c224f2b05d2d08ae58e1062b71f1fb941258e8abc8e4d9`.
`summary.json` e `records.jsonl` têm, respectivamente, SHA-256
`c05115087bc0f936be705fa63fd5ce05143285560b8a56fa9d1c465ff0544f9f` e
`b3e120f0869c49ccc97ec13a86c1495b7bb5b560154a1008a7b49ee9eab0dee6`.
O provedor reportou 2.503 tokens de entrada e 147 de saída; custo permaneceu
indisponível e o orçamento autorizado continuou US$ 0,00.

## Revisão semântica parcial

As duas respostas concluídas passaram individualmente o contrato fechado:

- `map-cylinder-hold`: unidades obrigatórias, unidade opcional e odor autorizado,
  sem transição, contato ou presença inventada; próxima escolha preservada;
- `map-lamp-transition`: única transição autorizada, cilindro preservado, paleta
  residual correta, sem causa ou chegada inventada; próxima escolha preservada.

A ficha byte a byte está em
`evals/narrator/reviews/gemini-free-closed-world-d64fd149-partial-codex.json`.
Isso é sinal positivo limitado, não qualificação: seis dos oito casos não têm
resposta observável. O candidato não satisfaz o gate integral, nenhum narrador é
admitido e nenhum default é criado.

## Limite decisório

O lote L2 está encerrado e não pode ser retomado ou repetido. Executar um L3 seria
um novo experimento e exigiria decidir entre preservar o mesmo conjunto integral
ou testar somente os seis casos ausentes; essa escolha altera a comparabilidade e
permanece fora deste resultado.
