# Observação de transporte HYP-003 Gemini Free L1

**Data:** 2026-09-26  
**Lote:** `d56a55b2-e01f-4436-8c97-68dcaebffef2`  
**Resultado:** falha fechada de transporte; sem evidência semântica.

O projeto Free Tier foi confirmado no launcher. O lote fez uma única chamada ao
endpoint oficial e recebeu HTTP 400 `INVALID_ARGUMENT`; nenhuma narrativa foi
produzida. Os sete slots restantes foram pulados. Não houve retry, reparo,
fallback, troca de alvo nem gasto pago autorizado. A credencial foi removida do
ambiente do terminal ao final.

O `summary.json` registra `calls_made=1`, `completed=0`, `failed=1`, `skipped=7`
e uso indisponível `0/0`. Antes da correção local, a verificação dos artefatos
passou com o preflight SHA-256
`67a73046a404c5a433a7ecd095a8cde4d3e1b7c029992c3e626990802336b42a`.

A comparação do corpo congelado com a referência REST oficial encontrou uma
incompatibilidade local: `generationConfig.responseFormat.text.mimeType` é enum e
aceita `APPLICATION_JSON`; o adaptador enviou a string MIME legada
`application/json`. O campo superior `store: false` consta no contrato oficial e
não foi removido. A correção é local e não altera prompt, corpus, gates semânticos,
modelo ou runtime default.

Este lote é histórico, permanece inalterado e não será retomado. Como não houve
resposta narrativa, ele não admite nem rejeita o candidato por qualidade. Uma
nova execução deve possuir identidade L2 própria e novo preflight.
