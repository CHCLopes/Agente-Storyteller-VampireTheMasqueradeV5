# HYP-007-L49 — toque ambiental e realização insuficiente de dano

Batch 4026f903-b7a9-477d-8ea6-a546fff7b09e: oito chamadas/sete turnos,
01/02 completos e primeiro aviso de 03 aceito, parada R-03B/03.
Primeiro diagnóstico de leitura apontou dano wet não explícito. Reprodução
isolada encontrou também bloqueio anterior: “enquanto a água alcança a bancada
baixa e toca o registro” atribuído ao jogador, undeclared_player_action/interact.
Ambos separados: corrigir sujeito não dispensa realização física do dano.

Custo final estimado USD 0.0079160, 29560 entrada/1670 saída, oito usages.
Não confirma cobrança. records SHA256
a99e77dd6b55fdb745df2f8de1e307703f373f1815e353380866e83855399f85.
Gate fechado/latch/saídas preservados, R-02/08 não alcançado; naturalidade
integral de recusa inconclusiva, sem retry/fallback/admissão.

Seis casos novos (6→12) de contato ambiental/dano; duas falhas pré-fix.
Corrigir somente toca com sujeito água e antecedente/complemento delimitados.
Contato sem dano explícito continua rejeitado pelo perfil; versão autorada
que acrescenta registro molhado é aceita com mesmo efeito, commit/reinício/
replay sem RNG ou geração extra. Toque/ação posterior do jogador bloqueados.
34 relacionados aprovados, XML hyp-007-l49-correction-2026-10-20.xml.
420 ampliados do checkpoint anterior aprovados; seleções sobrepostas.

V12 = v11 mais orientação de mostrar dano wet já ocorrido, não apenas ameaça
ou contato, sem transformar wet em lost. L50 novo mesma matriz/alvo/tetos,
até 17 chamadas/USD 0.15 total estimado, 768 tokens/20.000 bytes/60s,
primeira falha para, sem retry/fallback/admissão. Autorização contínua vigente.
