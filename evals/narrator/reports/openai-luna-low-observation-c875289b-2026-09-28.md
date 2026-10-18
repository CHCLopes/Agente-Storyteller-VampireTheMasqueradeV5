# Observação HYP-006 — OpenAI Luna low

O lote fechado `c875289b-e3f0-4907-8301-2408781a96ce` executou exatamente oito
chamadas sintéticas em `gpt-5.6-luna`, com esforço `low`. As oito concluíram,
sem falha, skip, retry, reparo, fallback ou troca de alvo. A reconstrução offline
dos artefatos passou e confirmou a rota reportada em todos os casos.

## Uso e limite

A API reportou 9.762 tokens de entrada, 1.473 de saída e 11.235 no total. Pelos
preços congelados no preflight, o custo calculado é aproximadamente USD 0,00372.
Esse número é estimativa derivada dos tokens, não leitura da cobrança da conta.
O hard limit observado antes do lote era USD 0,05. A credencial foi removida do
ambiente do launcher e os gates pagos foram fechados novamente após a bateria.

## Revisão semântica independente

Os oito textos preservaram as unidades autorizadas, os resultados mecânicos, os
segredos e a agência do jogador. Nenhum caso apresentou alegação de mundo não
listada, expansão mecânica, atribuição indevida de ação, vazamento de segredo ou
perda da próxima escolha. A revisão byte-vinculada está em
`evals/narrator/reviews/openai-luna-low-c875289b-codex.json`.

## Classificação

O candidato é tecnicamente e semanticamente elegível para aceitação narrativa
humana final. Esta classificação não admite o narrador e não altera o default.
A admissão exige julgamento humano explícito sobre os oito textos observados.
