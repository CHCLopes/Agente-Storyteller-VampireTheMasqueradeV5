# HYP-007-L17 — v5 observado e retirada do registro; preparação L18

18/10/2026, gpt-5.6-luna/low, prompt v5.
Batch `062b4f49-873d-4ffa-9f7e-4a0f2cef6dac`.

## Observado e custo

L16 aceito e L17/v5 autorizado por Continue. Após chave protegida, seis
chamadas/cinco turnos, CAMP-EVAL-01 completo; parada campaign_source_policy_failed
no R-06/02. 03–08 não alcançados. Gate L17 fechado, trava mantida, sem retry/
fallback ou transferir 11 slots. Nenhum narrador admitido, MVP aberto.

Em R-06 o modelo retornou q vazio e narrou encerramento parcial. A violação
terminal observada em L16 não se repetiu nesse caso; amostra única não prova
eficácia geral do v5. O turno foi recusado por outra razão, descrita abaixo.

**USD 0,0051470 finais estimados**, não cobrança confirmada. 18.607 tokens
entrada/1.188 saída, seis chamadas com usage/zero sem. Reporter --settled com
hash conferido; sem ajustes de cache/tarifas/impostos. Correção/preparação
adicional USD 0, nenhuma chamada real nova.

Originais em eval-results/hybrid-campaign-luna-l17-062b4f49-873d-4ffa-9f7e-4a0f2cef6dac/.
SHA256 records `ada06fdec63db14f9f61339b2031e36ad043c8880f48c33f6c7fcb3798736d67`.
SHA256 summary `ccec7449e2499afe02978e17c153345049a9806b508a81346614257f0144cf1f`.
Manifesto fechado L17 `2d6984f6741ba9a9727ca07727857779bea4b6e2ce85879ff52b7201b6823828`.
Não alterar resposta ou reclassificar rejeição histórica após correção.

## Causa e correção delimitada

Texto: "Você retira o registro [...] e o coloca na superfície seca da Galeria,
afastando-o da infiltração." O scanner tratou afastando como move/withdraw do
jogador, não como referência clítica ao registro explicitamente retirado.
Diagnóstico reproduzido: scene_player_agency_violation, narrative, subject voce,
clause_index 0, unauthorized_concepts move. Dois positivos falharam antes/
seis contraprovas passavam.

Em _action_signature_matches reconhecer somente withdraw/afastando seguido
de -o da infiltração + pontuação/fim, com antecedente retira o registro na
mesma oração, antes da vírgula. Não cobrir afastando-se, afastando você, outro
antecedente ou atravessar fronteira de sentença. Mascara apenas a leitura de
movimento pessoal; outros verbos/offsets/texto e gates de cânone permanecem.
Sem mudar prompt/schema/catálogo/RNG/persistência/autoridade. Não é correferência
geral nem autorização de mover jogador ou objeto diferente.

Nove testes em tests/test_scene_record_withdrawal_regressions.py. 82 focados de
políticas/terminal e 48 preparação/histórico/exato aprovados (sobrepostos), um
aviso preexistente. Exato confirma R-06/partial/dry_surface/revisão quatro;
avanço pessoal indevido posterior recusa, mantém wet/revisão três/sem nova
entrega. Reinício/replay conserva envelope, uma geração/entrega do resgate e
nenhum RNG novo. Falta de antecedente local conserva a recusa.

Testes históricos L16/L17 agora isolam hashes atuais só em manifesto temporário
e provam recusa do runtime corrigido pelos manifestos executados preservados.
L16 era válido/fechado antes deste ajuste; não descrever essa nova deriva de
runtime como condição existente na execução histórica.

Regressão ampliada: 1.038 aprovados, um aviso preexistente python_multipart,
184,30s; XML eval-results/hyp-007-l18-readiness-2026-10-18.xml, zero errors/
failures. Históricos L5–L17/prospectivo L18, agência, atribuição, visibilidade,
contratos, campanha, persistência, custo e regressões de segurança cobertos.
Contagens focadas sobrepostas. Não rodada suíte integral/frontend/build;
sem alteração nessas camadas, não declarar release verde. Diff inspecionado,
diff --check sem erros; sem commit/push, checkout original preservado.

## L18 fechado, mesma hipótese v5

22 hashes/paid-live false, mesmo v5/alvo/corpus/limites: 17 chamadas/768 tokens/
20.000 bytes/60s, teto adicional proposto USD 0,15, sem retry/fallback/admissão.
CLI 17 sintéticos/zero chamadas, máximo 13.952 bytes, AST válido; sem chave/
terminal/trava L18. Manifesto fechado:
`27b80c698893133466d860fbf38cc4b95c50379fed80db20cfca334c4652a9a1`.
Prompt v5 intacto `393e0e5c1078e41af20f3ff30639deea34e7cac0614385ccde3524962949bf60`.

Proposta: aceitar L17 inconclusivo integral por falso positivo de movimento
clítico do registro, fechamento terminal observado no caso R-06 mas narrador
não admitido, e autorizar L18 nos limites acima. Continue/prossiga aprova ambos;
depois chave protegida. Não prometer última tentativa ou eficácia geral v5.
Fragilidade lexical/UX/fidelidade semântica permanecem; TASK-013/CAMP-24/MVP abertos.
