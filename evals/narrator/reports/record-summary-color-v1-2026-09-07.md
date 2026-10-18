# Par de atribuição de cor Qwen — preparação histórica

Na etapa de preparação, **68 testes novos distintos passaram**, sem falhas, mais revisão independente, reconstrução dos dois pedidos, preflight real e integração com chave vazia; essa etapa não enviou chamadas ao provedor. A execução posterior terminou no [lote 0e7b0ac3](record-summary-color-observation-0e7b0ac3-2026-09-07.md): duas chamadas HTTP 200/stop, rota/schema válidos, exit 0. Os resumos cumprem o limite de 25 palavras, mas ambos deixam a atribuição da cor ambígua conforme os critérios prévios. Isso não aprova fidelidade, runtime ou CAP-001.

O [lote anterior 95dd9fd2](record-summary-budget-observation-95dd9fd2-2026-09-07.md) permanece encerrado: uma chamada HTTP 200, schema válido e resumo de 23 palavras cujas afirmações retidas encontraram suporte na fonte. Esse caso não demonstra confiabilidade geral ou efeito causal da redução de orçamento. O par anterior 1edf4d3e permanece encerrado por 429, sem preencher seu segundo caso.

## Pedidos e critérios congelados

O [desenho prévio](record-summary-color-design-95dd9fd2-2026-09-07.md) e o [dossiê HTTP](record-summary-color-dossier-95dd9fd2-2026-09-07.json) fixam duas fontes novas de 35 palavras: reading-room-a tem luminária de base azul, sem cor de luz declarada; reading-room-b declara emissão de luz azul, sem cor de base. A segunda unidade é idêntica nas duas fontes. Não se reutiliza observatory-a/b nem station-clock.

Mantêm-se o SYSTEM record-summary-budget-v1, schema/protocolo record-summary-only-v1, modelo qwen/qwen3.8-27b na rota Groq direta gratuita declarada, reasoning_effort=none, temperatura 0,65, stream=false e teto de 768 por chamada. Cada corpo difere do pedido budget somente em messages[1].content. O procedimento passa a permitir dois casos A→B e até 1.536 tokens de saída no total. Não é comparação causal nem estimativa de taxa.

Atribuir luz azul a A ou base azul a B acrescenta uma relação sem suporte. Omissão da cor é permitida e não informativa. Formulações ambíguas, como “luminária azul”, não demonstram preservação da distinção. Revisar também as outras afirmações e relações; paráfrase é permitida, sem exigir gabarito literal. Os critérios não são enviados ao modelo no USER.

| Pedido | SHA-256 do corpo |
| --- | --- |
| reading-room-a | 25be06f95bc681bf84a9cf7c4fd62fedd726c150c508a4a3cd28b7307e339065 |
| reading-room-b | 032ce8babd9e14b2c55515c7e502c05c1ca2126ce41c2f49c50ba3edd47a5d3a |

Dossiê SHA d998a881504ac935a7a4a5ca248afa33b2a78c966668af3e52a0fcacd1a44915.
Executor SHA 2caf4e3f673876477e1da7d52c771a092d3ae8de7933b62e4e44523fe25f6f26.
Wrapper SHA 24ba566dba9ae99cefda863aa012db6167d0a04149bff6ca7bff46130c07bba8.

## Implementação e verificação

Executor e wrapper novos derivam do fluxo anterior de dois casos por substituições finitas de identidade, fonte, prompt, fingerprints e teto. O executor separa variante do prompt de protocolo. Cada caso usa uma instância de uso único vinculada ao corpo exclusivo. O avaliador compartilhado recebeu somente 12 linhas que recusam os novos marcadores nas duas entradas de replay CAP; contrato, adaptadores e runtime não mudaram.

| Verificação focada | Resultado |
| --- | --- |
| Executor: dois corpos, ordem, uso único, fonte/teto divergentes, espera/deadline, falha/skip e retenção literal | 22 passaram |
| Wrapper: preflight, fingerprints, SecureString, status/exit, artefatos e restauração do ambiente | 35 passaram |
| Fronteira CAP: marcadores isolados no replay direto/CLI e comportamento legado | 11 passaram |

As matrizes históricas não foram repetidas. O aviso Starlette/multipart preexistente permanece fora do escopo. A integração real PowerShell 7/Python concluiu o preflight e terminou com código 3 na validação de chave vazia, sem envio, stderr ou artefato novo. A revisão independente não encontrou problema material.

A auditoria final confirmou nove arquivos desta preparação, 71 históricos e 18 artefatos brutos anteriores, com CLI sem credencial idêntico ao preflight importado. A evolução explícita do arquivo compartilhado é separada dos fingerprints históricos; não reescreve resultados. [Registro completo da preparação e evidências](record-summary-color-v1-2026-09-07.json).

## Parada e continuidade

Espera inicial e espaçamento entre inícios de pelo menos 60 segundos; deadline de 60 segundos por chamada depois da espera. O primeiro erro operacional encerra chamadas e persiste os casos restantes como skips. Não há diagnóstico, retry, fallback, substituição de caso, juiz ou geração narrativa. Exceder 25 palavras ou falhar na revisão semântica não bloqueia B quando A é operacionalmente válido; esses resultados ficam separados do exit.

PID 25276 terminou em 2026-09-07T21:17:39.7995660Z, exit 0; chave descartada. Lote 0e7b0ac3-b88a-4962-b383-cc6f813c9d4a encerrado: duas chamadas, nenhum skip. Não relançar a janela/wrapper ou repetir reading-room-a/b. [Resultados literais, revisão autorada e auditoria](record-summary-color-observation-0e7b0ac3-2026-09-07.json). Os cinco campos históricos da preparação e os brutos foram preservados.

A continuidade autorizada é a preparação de compressão relacional: dois braços controle→variante, uma fonte sintética NOVA e mesmo USER, Qwen/schema/none/768/temperatura 0,65, até duas chamadas, parada no primeiro erro operacional. Selecionar poucas afirmações completas é a orientação experimental da variante, sem exemplos de cor. O desenho está em curso, ainda não declarado pronto. Uma amostra por braço permite só descrição, sem causalidade; encerrar após esses braços ou primeiro erro, sem sequência de reformulações para elevar taxa. Não há novo envio neste registro nem nova aprovação genérica pendente.
