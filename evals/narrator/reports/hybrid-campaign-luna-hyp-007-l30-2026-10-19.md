# HYP-007-L30 — ameaça ambiental atribuída ao jogador

## Autorização e hipótese

Humano autorizou explicitamente L30 e todos os testes futuros necessários com
tetos planejados <= USD 0.15 por lote, no escopo aprovado. Não exige novo aceite
de cada lote; preserva gates técnicos, ausência de retry/fallback e admissão humana.
L30: v6/Luna low/17 chamadas/768 tokens/20.000 bytes/60s/USD 0.15 total,
primeira falha encerra. 22 hashes revalidados; supervisor ativo/idle e latch ausente.

## Resultado observado

Batch b8ce5b26-f0eb-4833-87c9-980d347d01ac em
eval-results/hybrid-campaign-luna-l30-b8ce5b26-f0eb-4833-87c9-980d347d01ac.
Cinco chamadas/quatro turnos; CAMP-EVAL-01 completo/intacto, 02 interrompido
em R-01/turno 3, campanha integral inconclusiva. Stop campaign_source_policy_failed.
Custo final estimado USD 0.0043758, 15327 tokens entrada/1092 saída; usage em
todas as chamadas. Não confirma cobrança/cache/tarifas/impostos. Nenhum retry.
records SHA256: c9b6a67cc81f89d838140f3fcf609a603cac7a5ad94193cc7212f889296a57cf.
summary SHA256: bd27d7bc63691978437123a1494ac91360e3cf78f3c34bff897af00a20334c62.
Gate fechado/latch mantido; supervisor voltou idle/exit=2.

## Diagnóstico e correção offline

SceneProposalError scene_player_agency_violation, undeclared_player_action,
subject voce, clause_index 0, unauthorized_concepts combat. Amostra descreve
Mara voltando-se ao jogador enquanto a infiltração ameaça a bancada baixa.
O sujeito explícito da ameaça é ambiental, não jogador. Falso positivo confirmado.
Correção mínima em _action_signature_matches: ignora só ameaca na construção
enquanto a infiltracao ameaca a bancada baixa seguida de fronteira; sujeito
você/Mara, ameaças do jogador e ações posteriores continuam rejeitados.
Oito regressões novas; duas falhas antes da correção. Commit R-01 no estado wet,
rejeição atômica, reinício/replay sem RNG/geração adicional demonstrados.
137 testes de agência/integração aprovados; 55 de preparação/supervisora/custo
aprovados em seleção parcialmente sobreposta. Um aviso python_multipart preexistente.
XML eval-results/hyp-007-l30-correction-l31-readiness-2026-10-19.xml.
Não reclassificar L30 nem atualizar seus hashes live após mudança local.

## Próximo experimento

L31 separado, hipótese de progressão integral com atribuição ambiental corrigida.
Mesmos v6/alvo/parâmetros/gates; até 17 chamadas/USD 0.15 total, primeira falha
encerra, sem retry/fallback/admissão. Preflight 17 sintéticos/zero chamadas/
14.457 bytes; 22 hashes válidos. Autorização contínua cobre execução sem novo
pedido de teto. Nenhum narrador admitido, TASK-013/CAMP-24/MVP abertos.
