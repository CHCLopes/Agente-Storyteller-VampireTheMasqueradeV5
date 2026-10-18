# Observação HYP-003 Gemini Free L3 integral

**Data:** 2026-09-26  
**Lote:** `0164d8e2-1c2f-448a-b8db-8a8f744d4466`  
**Classificação:** inconclusivo; candidato inelegível por evidência incompleta.

O lote integral L3 iniciou com projeto Free Tier confirmado e ambos os prompts
mascarados. Foram feitas duas chamadas: o primeiro caso concluiu e o segundo
recebeu HTTP 503 `provider_unavailable`; os seis slots seguintes foram pulados.
Não houve retry, reparo, fallback, troca de alvo ou agregação com L2. O launcher
removeu a credencial ao final.

O verificador passou no launcher e novamente offline. Preflight SHA-256:
`f46060c36cb7792bc4f7ab5a3b5a47ef2a69926cb634f4c8142a6560d89bcbf5`.
`summary.json` e `records.jsonl` têm SHA-256
`ed6b3935f8177b5d53e62d236ad85f107f380d830619cb77469cd43ba80b33bd` e
`1a31c4e55bec63229bcf179be5e76d40acde058f53bce398f55b774c9542b4b7`.
O uso reportado foi 1.201 tokens de entrada e 70 de saída; custo permaneceu
indisponível e o orçamento pago autorizado continuou US$ 0,00.

## Revisão semântica parcial

`map-cylinder-hold` passou: todas as unidades autorizadas foram renderizadas, o
estado permaneceu imóvel e lacrado, não houve afirmação não listada e a pergunta
preservou a próxima escolha. A ficha byte a byte está em
`evals/narrator/reviews/gemini-free-closed-world-0164d8e2-partial-codex.json`.

Uma resposta aprovada não satisfaz o gate integral. Sete casos não possuem
resposta no L3; o candidato não é elegível, nenhum narrador é admitido e nenhum
default é criado.

## Diagnóstico de disponibilidade

A documentação oficial classifica HTTP 503 como serviço temporariamente
sobrecarregado ou indisponível. Limite de requisições ou quota é reportado como
HTTP 429; portanto, a evidência observada não demonstra violação do pacing ou da
quota. A recomendação oficial é retry com backoff em nível superior. O protocolo
aprovado proíbe retry dentro do lote, então adotar backoff/retry exigiria um novo
desenho explícito, separando retry de transporte sem resposta de repetição
narrativa ou seleção de melhor saída.

L2 e L3 estão encerrados e não podem ser retomados. Juntos, mostram três respostas
semanticamente aprovadas em chamadas concluídas, mas nenhum dos lotes produziu os
oito casos exigidos e os resultados não são agregáveis para admissão.
