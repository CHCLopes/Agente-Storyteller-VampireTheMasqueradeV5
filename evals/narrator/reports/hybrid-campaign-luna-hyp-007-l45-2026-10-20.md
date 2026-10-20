# HYP-007-L45 — rejeição conservadora de avaliação retrospectiva

Batch 3042a633-8934-4132-b88e-c624190c6ab0: 11 chamadas/10 turnos,
quatro percursos completos (01 preserved/02 partial/03 lost/04 abandoned).
Parada R-05/05: Mara diz “Está salvo. Você fez a escolha certa.” após transporte
declarado até a superfície seca. Política genérica atribui choice ao jogador.
O resgate descrito é pertinente; não há nova escolha concreta especificada.
Classificação: rejeição conservadora de avaliação retrospectiva, não prova de
um desvio mecânico do resgate. Hipótese integral de recusa v9 inconclusiva,
pois 08 não foi alcançado. Não reclassificar o lote após alterações posteriores.

Custo final estimado USD 0.0103846: 38405 entrada/2253 saída, usage das 11.
Não confirma cobrança. records SHA256
741b343c5080908eec6b794f5d37044bdd2732cfb8a17d4783e4b8a4996ebddf.
Gate fechado/latch/saídas preservados; primeira falha parou, sem retry/fallback.

Decisão local: manter o guard conservador, sem dispensar genericamente escolhas
retrospectivas. Prompt v10 pede reação física concreta ao resgate, sem juízo
genérico de escolha. Três regressões: saída observada continua recusada,
reação autorada alternativa é aceita com mesmo resultado, ação posterior
indevida continua rejeitada; commit/reinício/replay sem RNG/geração extra.
25 relacionados aprovados, XML hyp-007-l45-prompt-correction-2026-10-20.xml.
387 ampliados antes desta mudança de prompt aprovados; seleções sobrepostas.

L46 novo: mesma matriz 17 turnos/8 percursos, v10 = v9 mais somente orientação
acima. Alvo e gates intactos, até 17 chamadas/USD 0.15 total estimado,
768 tokens/20.000 bytes/60s, primeira falha para, sem retry/fallback/admissão.
Autorização contínua e avaliação intermediária delegada; não nova arquitetura.
