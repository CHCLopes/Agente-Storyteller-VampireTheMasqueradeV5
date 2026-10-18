# Observação viva — HYP-002-L2 / lote 4f13b856

**Data:** 2026-09-25

**Status:** lote íntegro; nenhum candidato elegível; resultado aceito pelo usuário

## Resultado

O lote autorizado executou uma única vez os 16 slots congelados. As 16 chamadas
foram concluídas sem falha, skip, retry, reparo, fallback, troca de alvo ou
repetição. O verificador de artefatos retornou `verified: true`; a credencial foi
removida do ambiente do terminal ao final.

| Candidato exato | Aprovados | Reprovados | Elegível |
|---|---:|---:|---|
| `qwen/qwen3.8-27b`, reasoning `none` | 0/8 | 8/8 | não |
| `openai/gpt-oss-120b`, reasoning `low` | 0/8 | 8/8 | não |

O limiar prospectivo era 8/8. Portanto, o resultado formal é **nenhum candidato
elegível, nenhum narrador admitido e nenhum default criado**. O plano fechado não
eliminou a tendência de acrescentar detalhes: o gate desta hipótese era mais
estrito que HYP-001 e tornou qualquer afirmação não listada uma falha fatal.

## Integridade observada

| Evidência | Valor |
|---|---|
| Batch ID | `4f13b856-6bf8-4eab-8639-188fc32b05b3` |
| Janela UTC | `2026-09-26T01:05:45.425473Z` a `2026-09-26T01:20:46.596711Z` |
| Preflight SHA-256 | `3c01ece8624b014e31cb108b8220ad3645013b8cd6b33898cc0443d1c847df93` |
| `summary.json` SHA-256 | `cbe2715a43fdad5c917fab0a3875c230689dca378835bdd54871a689d508ac77` |
| `records.jsonl` SHA-256 | `6ce0be7896e76e3e01f398fa829526cbc9f70da30a1d5e779cac5de08e2e6391` |
| Chamadas | 16 concluídas; 0 falhas; 0 skips |
| Qwen usage reportado | 9.691 input; 807 output tokens |
| GPT-OSS usage reportado | 10.677 input; 1.839 output tokens |
| Retry / reparo / fallback | 0 / não / não |
| Narrativas divergentes dos brutos | 0 |
| Credencial | entrada mascarada; removida do ambiente ao final |

O `summary.json` bruto permanece com `semantic_review_status: not_performed`, pois
é imutável. A revisão posterior está nas fichas versionadas e foi vinculada às
narrativas originais por comparação byte a byte.

## Revisão caso a caso

| Caso | Qwen | GPT-OSS |
|---|---|---|
| `hold-silent-bell` | reprova: acrescenta escuridão, brisa e correnteza invisível | reprova: inventa caverna, luz, sombras e vento; move a corda |
| `authorized-single-bell` | reprova: repete ar frio e brisa e acrescenta atmosfera não listada | reprova: acrescenta caverna, vibração, sombras e ar frio |
| `known-sealed-tube` | reprova: acrescenta luz, desgaste e ar quieto | reprova: acrescenta peso, histórico de toque, som e cheiro |
| `unknown-glass-disc` | reprova: afirma imobilidade fora do plano | reprova: acrescenta absorção de luz, brilho, som e atmosfera |
| `favorable-shutter-result` | reprova: qualifica o espaço desconhecido e acrescenta frio | reprova: inventa mecanismo, eco, brisa e cheiro de terra |
| `unfavorable-slab-result` | reprova: acrescenta acúmulo, local exato e resposta interna | reprova: acrescenta estado anterior, tom e ausência de som |
| `npc-protected-code` | reprova: 28 palavras, abaixo do mínimo 30 | reprova: inventa gestos, olhar e mão usada por Iara |
| `ambiguous-sealed-boxes` | reprova: inventa piso, sombras e silêncio; restringe a próxima escolha | reprova: omite unidade obrigatória e inventa contato, rangido e reação da pedra |

Nenhuma resposta revelou o código protegido. Schema, cápsula, rota, alvo e
proveniência passaram nos 16 registros.

## Artefatos de revisão

| Artefato | SHA-256 |
|---|---|
| `evals/narrator/reviews/closed-world-render-live-4f13b856-qwen-codex.json` | `eaf7e03899e2fca35978527795aa21e00b8e47ac4c2baee0b11e9508ccce2f6b` |
| `evals/narrator/reviews/closed-world-render-live-4f13b856-gpt-oss-codex.json` | `e8bc84042a6f7e5948aa5ec80c61179aac3888cf988442e01d2fd5826239b9b9` |
| `closed-world-render-live-4f13b856-qwen-verification.json` | `5f00c6a31ed85727434e77971d4a9a39e395644d92e64a60185e23ad1d7b2078` |
| `closed-world-render-live-4f13b856-gpt-oss-verification.json` | `b595800bef557627594252dcc4676bf4774416e9cc3d53ad661b3500e39c2fed` |

Os dois verificadores retornaram exit 1 porque `qualified_in_protocol` é falso.
Esse é o resultado semântico esperado, não erro técnico ou de integridade.

## Aceitação humana

Em 25/09/2026, o usuário respondeu: `Aceito HYP-002-L2: nenhum candidato
elegível; nenhum narrador admitido.` HYP-002 está encerrada sem promoção de alvo,
default ou configuração produtiva.

O aceite não aprova nova hipótese, relaxamento de gate, candidato, default,
provedor produtivo, custo ou campanha híbrida.
