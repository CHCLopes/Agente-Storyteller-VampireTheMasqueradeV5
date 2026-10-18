# Observação HYP-003 Gemini Free L4 com retry de transporte

**Data:** 2026-09-26  
**Lote:** `0a23913a-470e-4f64-9168-c635d9ffff99`  
**Classificação:** inconclusivo; candidato inelegível por ausência de evidência semântica.

O lote L4 iniciou com projeto Free Tier confirmado e ambos os prompts mascarados.
O primeiro caso recebeu HTTP 503 `provider_unavailable` nas três tentativas. As
falhas ocorreram na fase `connect`, sem resposta parcial e sem narrativa
persistida. O retry estrito de transporte aplicou os delays determinísticos de
64 e 186 segundos e encerrou em `per_case_retry_limit`; os sete casos seguintes
foram pulados. Não houve retry narrativo, reparo, fallback, troca de alvo,
seleção de melhor saída ou agregação com L2/L3. O launcher removeu a credencial
ao final.

As tentativas possuem IDs distintos e vínculo causal íntegro: a tentativa 2
referencia a tentativa 1, e a tentativa 3 referencia a tentativa 2. Foram três
chamadas, dois retries de transporte, zero caso concluído, uma falha e sete
skips. O uso reportado foi zero token de entrada e de saída, consistente com a
ausência de resposta do provedor. O orçamento pago autorizado permaneceu
US$ 0,00.

O verificador passou no launcher e novamente offline. Preflight SHA-256:
`34fcef72acca1c676026ee53c79c4cbcdf8b374ec91d1e4017d12c3d7ba273ae`.
`summary.json` e `records.jsonl` têm SHA-256
`029e7eba43a630ec16739e082ac0cf056093142d186e5f1922137fb34516ccb2` e
`d357673535dfad28905f5b5f38469f4f2baf02f5b96f0aaec65c7bf89e6ef14e`.

## Resultado do gate

Nenhum dos oito casos produziu resposta no L4, portanto não há material para
revisão semântica e o gate integral não foi satisfeito. O lote comprova que o
retry estrito foi executado e auditado conforme aprovado, mas não qualifica o
candidato. Nenhum narrador é admitido e nenhum default é criado.

L4 está encerrado e não deve ser retomado, agregado a lotes anteriores ou
repetido sem uma nova decisão explícita. A classificação aguarda aceite humano;
ela não autoriza L5, relaxamento dos gates, provedor pago, `CAP-001` ou campanha
híbrida.
