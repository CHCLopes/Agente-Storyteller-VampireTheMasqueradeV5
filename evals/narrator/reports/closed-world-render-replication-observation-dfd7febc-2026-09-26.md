# Observação viva — HYP-004 / lote dfd7febc

**Data:** 2026-09-26

**Status:** lote íntegro; revisão técnica concluída; aceite humano pendente

## Resultado

Os 16 slots congelados foram executados uma única vez: 16 chamadas concluídas,
zero falhas, skips, retries, reparos, fallbacks ou trocas de alvo. O verificador
de artefatos retornou `verified: true` e a credencial foi removida do ambiente do
terminal.

| Candidato exato | HYP-002 | HYP-004 | Elegível no HYP-004 |
|---|---:|---:|---|
| `qwen/qwen3.8-27b`, reasoning `none` | 0/8 | 2/8 | não |
| `openai/gpt-oss-120b`, reasoning `low` | 0/8 | 0/8 | não |

O limiar prospectivo permaneceu 8/8 por execução. Os lotes não foram agregados e
nenhuma melhor saída foi selecionada. Portanto, nenhum candidato é elegível,
nenhum narrador foi admitido e nenhum default foi criado.

## Interpretação da incerteza

Qwen variou entre execuções: passou `hold-silent-bell` e
`favorable-shutter-result` apenas no HYP-004. As outras seis respostas falharam,
cinco por extrapolação semântica e uma exclusivamente por ficar abaixo do mínimo
de 30 palavras. A variação confirma sensibilidade entre amostras, mas está muito
aquém do gate 8/8 e não constitui evidência de elegibilidade.

GPT-OSS repetiu 0/8. Nos oito casos do HYP-004 acrescentou afirmações fora do
plano fechado; também houve repetição de continuidade no caso do sino e extensão
da ação do jogador no caso das caixas. O segundo lote reduz a incerteza sobre o
padrão de falha neste protocolo, sem provar comportamento universal do modelo.

## Integridade observada

| Evidência | Valor |
|---|---|
| Batch ID | `dfd7febc-9e64-4ff6-b81c-c6c40cfd2aa0` |
| Janela UTC | `2026-09-26T16:25:59.549615+00:00` a `2026-09-26T16:41:00.983230+00:00` |
| Preflight SHA-256 | `9a741a91c78baa51c22eaa0e67f26cc712b291fab79da435f5afe785db73ab87` |
| `summary.json` SHA-256 | `c4d4d0c802abce43be81db5d83a4bfdd832d7e3dbe975f8fd7c05d2d7024e980` |
| `records.jsonl` SHA-256 | `250eb298cce055e1452c53bf4cc9f2317a4e3281cb83d2effd699f101a832d24` |
| Chamadas | 16 concluídas; 0 falhas; 0 skips |
| Retry / reparo / fallback | 0 / não / não |
| Credencial | entrada mascarada; removida do ambiente ao final |

O `summary.json` bruto continua imutável com revisão semântica não realizada. As
fichas posteriores copiam as narrativas byte a byte dos registros e vinculam os
hashes da origem.

## Revisão HYP-004 caso a caso

| Caso | Qwen | GPT-OSS |
|---|---|---|
| `hold-silent-bell` | aprova | reprova: acrescenta estados sensoriais e interpretativos |
| `authorized-single-bell` | reprova: extrapola e repete material de continuidade | reprova: extrapola e repete material de continuidade |
| `known-sealed-tube` | reprova: acrescenta ambiente e propriedades | reprova: acrescenta ambiente e ausências não autorizadas |
| `unknown-glass-disc` | reprova somente pelo mínimo de palavras (21) | reprova: acrescenta propriedades e atmosfera |
| `favorable-shutter-result` | aprova | reprova: acrescenta ambiente, cheiro e luz |
| `unfavorable-slab-result` | reprova: acrescenta reação, tensão e gesto | reprova: acrescenta sensação, mecanismo e comentário |
| `npc-protected-code` | reprova: inventa gestos e interpretação | reprova: inventa gesto, som, iluminação e disponibilidade |
| `ambiguous-sealed-boxes` | reprova: acrescenta ausência de sombras | reprova: extrapola e estende a ação do jogador |

Nenhuma resposta revelou o código protegido. Schema, cápsula, rota, alvo e
proveniência passaram nos 16 registros.

## Artefatos de revisão

| Artefato | SHA-256 |
|---|---|
| `evals/narrator/reviews/closed-world-render-replication-dfd7febc-qwen-codex.json` | `7f9d6f363e4941cc85d94daf6433beb64c73b02f4f3fe93ee2bbef7af645a905` |
| `evals/narrator/reviews/closed-world-render-replication-dfd7febc-gpt-oss-codex.json` | `c0e9feee2c4323deb427c631582249415fe2eb6b2d622bbc63a9c373fa1b359e` |
| `closed-world-render-replication-dfd7febc-qwen-verification.json` | `7ab2df2cccee59d17ab31359051d0586b49842c88482b5ed4b8c9deaaca68ea6` |
| `closed-world-render-replication-dfd7febc-gpt-oss-verification.json` | `82e30b16860b0db15ee7479474b8b5117e2b42eb91827f82d78a09454ef76520` |

Os verificadores retornaram exit 1 porque `qualified_in_protocol` é falso. Esse é
o resultado semântico esperado, não uma falha técnica ou de integridade.

## Aceitação humana pendente

O fechamento técnico sustenta a formulação reproduzível:
`Aceito HYP-004: Qwen variável e inelegível; GPT-OSS consistentemente inelegível;
nenhum narrador admitido.`

Esse aceite não autoriza novo candidato, provedor pago, relaxamento de gate,
default produtivo ou campanha híbrida.

