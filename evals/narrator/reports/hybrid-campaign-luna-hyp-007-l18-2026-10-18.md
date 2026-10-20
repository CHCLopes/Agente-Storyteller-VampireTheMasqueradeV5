# HYP-007-L18 — dois percursos concluídos; autoria NPC e preparação L19

18/10/2026, gpt-5.6-luna/low, prompt v5.
Batch `7bb9007d-4fa0-4d8c-807e-760a17396d08`.

## Observado e custo

L17 aceito e L18 autorizado por Prossiga. Após chave protegida, sete chamadas/
seis turnos: CAMP-EVAL-01 resgate intacto e CAMP-EVAL-02 resgate parcial completos.
Parada campaign_source_policy_failed no primeiro R-03/CAMP-EVAL-03; demais
percursos não alcançados. Gate L18 fechado, trava mantida, sem retry/fallback/
transferência de dez slots. Nenhum narrador admitido, MVP aberto.

**USD 0,0061390 finais estimados**, não cobrança confirmada. 21.131 tokens
entrada/1.594 saída, sete chamadas com usage/zero sem. Reporter --settled com
hash de records conferido; sem ajustes de cache/tarifas/impostos. Correção/
preparação adicional USD 0, nenhuma chamada real nova.

Originais em eval-results/hybrid-campaign-luna-l18-7bb9007d-4fa0-4d8c-807e-760a17396d08/.
SHA256 records `99d5c25fa2a35d6e9a7240c21f9680a61cbfd42cabb5dee5c5984099d1b69b58`.
SHA256 summary `0cd0bd0a560dc80b6c7a0ce584e77a6a7012501bf02e43c9971a1d8d779a2e94`.
Manifesto fechado L18 `27b80c698893133466d860fbf38cc4b95c50379fed80db20cfca334c4652a9a1`.
Não alterar resposta ou reclassificar rejeição histórica após ajuste.

## Diagnóstico e correção delimitada

"Mara acompanha as marcas de umidade sem tocar no objeto. Ela ergue os olhos
para você e fala em voz baixa:". O scanner atribuiu fala ao jogador, objeto
do olhar, porque a prova anterior de autoria pronominal NPC só cobria outra
oração. Diagnóstico: scene_player_agency_violation, narrative, subject voce,
clause_index 1, unauthorized_concepts social. Dois positivos falharam antes/
oito contraprovas passavam.

Em _mask_known_npc_gaze_report acrescentar somente prova anterior completa
NPC conhecido + acompanha as marcas de umidade sem tocar no objeto. Mantém
unicidade de owner, ausência de sujeito jogador e quadro existente de olhar/
fala. Mascara apenas fala no scan, não conteúdo citado ou ações posteriores.
Não aceitar desconhecido/jogador como antecedente ou coerção. Sem mudar prompt,
schema, catálogo, RNG, persistência ou autoridade; não é correferência geral.

Dez testes novos em tests/test_scene_npc_moisture_gaze_regressions.py; 85 focados
de agência/autoria/terminal e 35 preparação/histórico/exato aprovados, sobrepostos,
um aviso preexistente. Exato confirma R-03/warned/revisão um sem desfecho;
fechamento indevido posterior mantém revisão zero/threatened/sem fonte/entrega.
Reinício/replay conserva envelope/uma geração/entrega, sem RNG novo. Falas
do jogador/coerção/ações em citação não herdam autoria NPC. Manifesto executado
L18 preservado; testes isolam hashes atuais só em manifesto temporário e
provam recusa do runtime corrigido pelo manifesto histórico.

Regressão ampliada: 1.061 aprovados, um aviso preexistente python_multipart,
191,13s; XML eval-results/hyp-007-l19-readiness-2026-10-18.xml, zero errors/
failures. Históricos L5–L18/prospectivo L19, agência, atribuição, visibilidade,
contratos, campanha, persistência, custo e regressões de segurança cobertos.
Contagens focadas sobrepostas. Não rodada suíte integral/frontend/build;
sem alteração nessas camadas, não declarar release verde. Diff inspecionado,
diff --check sem erros; sem commit/push, checkout original preservado.

## L19 prospectivo fechado

Mesmo v5/alvo/corpus/limites/22 hashes, paid/live false: 17 chamadas/768 tokens/
20.000 bytes/60s, teto adicional proposto USD 0,15, sem retry/fallback/admissão.
CLI 17 sintéticos/zero chamadas/13.952 bytes, AST válido; sem chave/terminal/
trava L19. Manifesto fechado:
`86fb3ebdaac12ce622248605c2a852b0540e2749ba3f70aa4929cd47e4284163`.
Prompt v5 preservado `393e0e5c1078e41af20f3ff30639deea34e7cac0614385ccde3524962949bf60`.

Proposta: aceitar L18 inconclusivo integral por falso positivo de autoria NPC,
dois percursos concluídos sem narrador admitido, e autorizar L19 nos limites
acima. Continue/prossiga aprova ambos; depois chave protegida. Não prometer última
tentativa ou eficácia geral v5. Fragilidade lexical/UX/fidelidade semântica
permanecem; TASK-013/CAMP-24/MVP abertos.
