# HYP-007-L74 — reação à desistência sem nominal escolha

Batch 22d84fe7-6c48-417a-b1b2-ec6edc80b939: 13 chamadas/12 turnos,
parada R-09/04 campaign_source_policy_failed. Diagnóstico: agência/choice na
cláusula Mara olha para registro e depois para você, recebendo sua escolha sem
insistir. Jogador havia desistido, porém nominal escolha após você aciona
guard conservador. Manter guard como em L45, sem liberar escolha presumida.

Custo final estimado USD 0.0131672; 51.406 entrada/2.405 saída, 13 usages.
Não cobrança confirmada. records SHA256
47101aa9b0d2e0432967ea1ffeb4ffbdde2712710d4e689766f21dc73ff3c24e.
Gate fechado/evidência mantida, sem reclassificação/admissão.

Três regressões novas: original rejeitado, mesma desistência/bench/Mara fala
direta com Mara recebe a desistência aceita, ação extra rejeitada. 12
relacionados de desistência/reação/agência/imobilidade aprovados, reinício/
replay sem RNG extra. Runtime inalterado para esse caso.
V20 troca somente instrução que pedia Mara recebendo essa escolha por reagir
à desistência sem chamar gesto de escolha do jogador, removendo atrito local
entre prompt e guard. Não altera canon, outcome, contrato ou default.

L75 separado com mesmo alvo/matriz integral/ordem/tetos até 17 chamadas/USD
0.15 total, primeira falha encerra/sem retry/fallback/admissão automática.
Autorização contínua/avaliação intermediária delegada mantidas.
