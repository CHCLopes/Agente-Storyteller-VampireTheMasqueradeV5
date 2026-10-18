# HYP-005 L2-B — observação OpenRouter gratuita

Data da revisão: 2026-09-27  
Batch: `47f0c07f-ed8a-49b1-a9a6-4b760e7c4ffd`  
Hipótese: `HYP-005-OPENROUTER-FREE-L2-OUTPUT-BUDGET`

## Resultado executivo

O lote L2-B foi executado uma única vez com a única alteração aprovada:
`max_output_tokens` de 768 para 2048. O verificador offline reconstruiu e
aprovou os artefatos.

Foram feitas duas chamadas. O primeiro caso do Nemotron concluiu com rota
verificada e custo reportado exatamente zero. A segunda chamada recebeu
`provider_unavailable/openrouter_provider_overloaded`; o fail-closed global
preservado pulou os 22 slots restantes. Não houve retry, reparo, fallback, troca
de alvo ou chamada paga.

Nenhum candidato atingiu 8/8 e nenhum narrador é elegível ou admitido.

## Efeito da variável experimental

Em L1, o mesmo caso `hold-silent-bell` do Nemotron terminou por
`generation_truncated` com 768 tokens. Em L2-B, ele concluiu o JSON com 2048.
Isso sustenta, para esse caso, que o teto anterior impedia a observação da saída.
Não prova qualidade semântica nem generaliza para os demais casos.

## Revisão semântica independente

A saída concluída preservou todas as unidades autorizadas: sino imóvel, corda
fora do alcance, arco visível, ar frio e eco baixo da respiração ambiente. A
repetição de que o jogador permanece parado corresponde à ação já declarada e não
a estende. A pergunta devolve a próxima escolha ao jogador.

Entretanto, a afirmação de que “o silêncio [...] envolve o sino e a pedra”
introduz um estado ambiental ausente do plano fechado. Portanto,
`unlisted_render_claim: true` e o critério fatal falha.

A ficha byte-vinculada está em
`evals/narrator/reviews/openrouter-free-narrators-l2-47f0c07f-partial-codex.json`.
Os 23 registros não concluídos não receberam pontuação semântica.

## Evidência

- preflight: `bdb6969a598932d1f4bf9c4acbb744a97130b5bc3d0c03e4de4437c07c5f35fc`
- summary: `5e21e0eea47073273e7741127215bfbcc18c938444d2f0fa4b31091235f4b0fa`
- records: `61ca88fa5046b0e875e631ba30fff4d159ccb0e65c9ee163ed5e8336190cf111`
- revisão: `70a6299593ab9e98e392d6e78d8f0bcbecd1ab1a5e85fa3410934385232afedf`
- verificação de artefatos: aprovada, exit 0
- execução do lote: exit 2, classificação obrigatória pendente

## Classificação proposta para aceite humano

- Nemotron: inelegível neste lote; 1/8 concluído e o caso concluído falhou um
  critério semântico fatal.
- Liquid: inconclusivo e inelegível neste lote; nenhuma chamada foi despachada
  após a indisponibilidade global.
- DeepSeek: inconclusivo e inelegível neste lote; nenhuma chamada foi despachada
  após a indisponibilidade global.
- Nenhum candidato elegível; nenhum narrador admitido; nenhum default criado.

Reexecutar após sobrecarga, permitir retry estrito ou modificar raciocínio seria
uma hipótese nova e exige decisão separada. O lote L2-B não deve ser repetido por
arrasto.

