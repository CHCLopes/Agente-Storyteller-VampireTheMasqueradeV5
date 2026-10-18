# Prontidão offline — HYP-006 OpenAI Luna low

**Data:** 2026-09-26

**Status:** implementação offline concluída; execução paga bloqueada

O candidato exato é `gpt-5.6-luna`, com `reasoning_effort: low`, nos mesmos oito
casos do contrato fechado. O lote admite no máximo oito chamadas, 768 tokens de
saída por chamada e 6.144 tokens de saída no total. Não há retry, reparo,
fallback, troca de alvo, agregação ou best-of. O limiar permanece 8/8.

A documentação oficial observada registra USD 0,20 por milhão de tokens de
entrada e USD 1,20 por milhão de tokens de saída. O launcher exige, antes de
qualquer chamada, três gates independentes:

1. autorização persistida de inferência paga;
2. autorização persistida de gasto;
3. confirmação mascarada literal `PAID-USD-0.05` e chave temporária.

O teto de USD 0,05 é um limite de conta obrigatório, não uma previsão de gasto.
O protocolo limita chamadas e saída, mas somente o painel do provedor pode impor
um teto monetário absoluto considerando toda a conta.

Verificação offline: 48 testes focados passaram, o launcher tem zero erro de
parse PowerShell, o preflight produz zero chamada e não inspeciona credencial, e
uma tentativa `--live` é recusada antes de ler chave ou criar diretório enquanto
o gate pago estiver fechado.

Nenhuma chave OpenAI foi solicitada, nenhuma chamada foi feita e nenhum gasto foi
autorizado ou incorrido.

O transporte foi reconciliado com a documentação oficial: o runner agora usa
`POST /v1/responses`, `reasoning.effort: low`, `store: false` e Structured Outputs
por JSON Schema. Um transporte simulado comprovou endpoint, corpo, parsing,
proveniência e uso reportado sem chamada externa. O preflight congelado tem
SHA-256 `b7eb390e974ee0187482d2042c31b8d555545eacc5a896ab10e02b0f9623dc51`.
