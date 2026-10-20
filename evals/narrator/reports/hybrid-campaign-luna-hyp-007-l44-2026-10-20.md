# HYP-007-L44 — condição aberta confundida com decisão realizada

Batch e062fff3-b7f9-4021-9593-b828d1f60ac0: quatro chamadas/três turnos,
01 preserved, parada R-03B/02 em “se você decidir agir”. Agência genérica
rejeita choice, embora a condição não afirme decisão concreta. Hipótese
integral v9 inconclusiva; R-02 ainda não alcançado. Sem retry/fallback.

Custo final estimado USD 0.0035662, 13103 tokens entrada/788 saída.
Não confirma cobrança. records SHA256
a38e1335e1d2c7fbad33e18fb28bcd81de94740041984b278ed6280cae2a04d4.
Gate fechado/latch/saídas preservados; não reclassificar após fix.

Sete casos novos de decisão condicional (18→25), duas falhas pré-fix.
Correção limitada a se + sujeito jogador + decidir agir + pontuação/fim.
Sem se, escolha concreta ou ação posterior/coordenada continuam rejeitados.
Commit/reinício/replay sem RNG/geração extra. 92 relacionados aprovados,
XML hyp-007-l44-correction-2026-10-20.xml. Rodada anterior ampliada: 380
aprovados, seleções sobrepostas; não somar como testes distintos.

L45 novo mantém v9/alvo/corpus/limites e testa somente essa correção local.
Até 17 chamadas, 768 tokens/20.000 bytes/60s/USD 0.15 total estimado,
primeira falha para. Autorização contínua e avaliação intermediária delegada,
sem admissão/default/release ou mudança de arquitetura/canon.
