# HYP-007-L62 — água atravessando registro não é viagem do jogador

Batch 7688e9ef-63a0-435f-8594-58863d6de4cc: 12 chamadas/11 turnos,
parada R-04/03 campaign_source_policy_failed. Corpo compacto passou o ponto
de bloqueio L61; limite de 20.000 bytes mantido. Texto final:
“Você aguarda no Arquivo, mas a água continua sobre a bancada baixa e atravessa
o registro.” Segue perda irrecuperável, fala direta de Mara, sem nova tarefa.
Guard de agência atribuiu atravessa ao jogador. Gate fechado/histórico mantido.

Custo final estimado USD 0.0121282; 46.739 entrada/2.317 saída, 12 usages.
Não confirma cobrança. records SHA256
e4de7001a67178f1c325c00a0854341ebaa5965ed6e3ddc5fc2fceb091260062.
191 relacionados aprovados na preparação compacta, XML hyp-007-l62-related-2026-10-20.xml.

Dois testes falharam antes da correção; fix distingue apenas o token atravessa
no quadro explícito mas a água continua sobre a bancada baixa e ... o registro.
Não dispensa outras ações, sujeitos ou destinos. 21 regressões ambientais,
incluindo troca por jogador/NPC, ação posterior/coordenada, atomicidade,
reinício/replay sem RNG, e 156 relacionados aprovados após fix.
XML hyp-007-l62-water-fix-2026-10-20.xml.

L63 prospectivo separado mantém v16/alvo/matriz integral/ordem/tetos:
17 chamadas/USD 0.15 total, primeira falha encerra, sem retry/fallback/admissão.
25 preparação/replay/contexto e 517 ampliados aprovados; XML
hyp-007-l63-expanded-2026-10-20.xml. L63 liberado uma vez após hashes/diff check.
Autorização contínua e avaliação intermediária delegada preservadas.
