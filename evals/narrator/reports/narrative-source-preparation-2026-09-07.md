# Direção B: piloto de fonte integral preparado

Preparação concluída em 07/09/2026, antes da entrada da chave. O usuário já aprovou a direção B e as observações necessárias; nenhuma nova aprovação de lote é requerida.

**152 casos distintos passaram**, com revisão independente: 24 no núcleo de fonte, 57 no perfil n/q, 31 no avaliador, 27 no wrapper (incluindo integração real com chave vazia) e 13 nas barreiras de replay CAP. Uma expectativa de erro de pergunta foi corrigida no perfil; repetiu-se somente a família afetada. O controle adicional do snapshot também rodou isoladamente, sem repetir o grupo anterior. As provas e comandos estão incorporados ao [registro JSON](narrative-source-preparation-2026-09-07.json).

A integração real concluiu o preflight e parou na chave vazia com exit 3 esperado, sem stderr, chamada externa ou alteração do inventário de 181 arquivos de resultados. Os oito brutos do corpus histórico mantiveram seus hashes. O núcleo e o perfil ficaram isolados do runtime; no avaliador compartilhado foram acrescentadas apenas 14 linhas para bloquear o novo protocolo em replay CAP.

## Pedido e limites congelados

- Cena nova Estufa, sem NPC: observar sem tocar; depois esperar no mesmo lugar. Saída somente n/q. O primeiro n normalizado integral segue ao segundo pedido como fonte atribuída, separado de q.
- Qwen `qwen/qwen3.8-27b` via Groq direto, candidato gratuito sintético, reasoning none, structured output nativo, temperatura 0,65. Máximo duas chamadas de 768 tokens/1536 no total, espera inicial, intervalo e deadline de 60 segundos.
- Primeiro corpo: `747c05d4ed2cbff718169f94053f78c032baadabe3a5c5fb853d72fc290c237a`; USER: `ab29bb7fdc090b5648946bfe772660fea4bc690a9a703dd73944651301b808a0`, 137 tokens estimados. O segundo corpo depende da fonte recebida e será registrado literalmente, pelo código congelado.
- Primeira falha operacional, de rota, schema, política ou projeção encerra a cadeia e registra skip. Nenhum retry, reparo, diagnóstico, fallback ou preenchimento posterior.
- O preflight esperado é conferido antes de ler a credencial e depois de cada espera. O verificador reconstrói a cadeia e recusa flags, fontes, contextos, estágios ou snapshots incoerentes. Ele preserva resultados parciais legítimos e não concede admissão retroativa.

Identidade integral comprova preservação textual neste vínculo; a verdade semântica geral permanece não avaliada. Qualidade e continuidade requerem a análise autorada posterior. Não há integração de produto, migração de saves, abertura sem cena ou aprovação CAP-001 neste piloto.

## Execução encerrada

O lote f97a8568 terminou com exit1: uma chamada/schema válido, pergunta recusada e segundo turno pulado. A chave foi descartada pelo wrapper. [Auditoria e leitura autorada](narrative-source-observation-f97a8568-2026-09-07.md) conservam o resultado sem reclassificação. Não relançar. Os campos preparados acima são históricos e imutáveis; o lifecycle registra finished. O próximo trabalho é a correção local da pergunta e o desenho de integração, sem nova chave neste fechamento.
