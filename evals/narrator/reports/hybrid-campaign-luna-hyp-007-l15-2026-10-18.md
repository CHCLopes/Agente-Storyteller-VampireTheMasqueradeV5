# HYP-007-L15 — escolha futura e preparação L16

18/10/2026, gpt-5.6-luna/low, prompt v4.
Batch `0edbff66-af8c-4b64-b60e-1ea1dd71acd5`.

## Resultado e custo

L14 aceito e L15 autorizado por Continue. Ao usuário pedir prossiga, artefatos
já mostravam lote terminal: três chamadas/dois turnos, CAMP-EVAL-01 completo;
parada campaign_source_policy_failed no R-03/02. Não foi aberto outro lançador.
Marcador ready é histórico, não prova espera atual. L15 paid/live fechado,
trava mantida, sem retry/fallback/reutilização de 14 slots. Narrador não admitido.

Custo final **USD 0,0022494 estimados**, não cobrança confirmada; 7.695 tokens
entrada/592 saída, três chamadas com usage/zero sem. Reporter --settled com
hash de records conferido; sem ajustes de cache/tarifas/impostos.
Correção/preparação adicional USD 0, nenhuma chamada real nova.

Originais em eval-results/hybrid-campaign-luna-l15-0edbff66-af8c-4b64-b60e-1ea1dd71acd5/.
SHA256 records `322401f0f0c0fe014caec87ca4b3705d274b11614a030086f67e9f480b4bf7bd`.
SHA256 summary `1a4f166674bb0c1333de40b069946d5939849499c70522505e7f13098904dc8e`.
Manifesto fechado L15 `57269d7cdc41013b7d0c12b62f3e1ce6e9384fb1c2958692eeed0519aa8398c2`.
Não reclassificar rejeição histórica nem alterar resposta original após ajuste.

## Diagnóstico e correção

Trecho: "pronta para reagir ao que você decidir fazer". Validador interpretou
choice como decisão já executada: scene_player_agency_violation, narrative,
subject voce, clause_index 2, unauthorized_concepts choice. Dois positivos
falharam antes da correção/seis contraprovas passavam.

Em _validate_declared_player_actions, junto ao quadro existente de decisão
pendente, reconhecer apenas ao que + jogador conhecido + decidir fazer com
fronteira/pontuação/fim. Mascarar somente decidir, mantendo texto/offsets e
ações posteriores. Sem mudar prompt/schema/catálogo/RNG/persistência/autoridade.
Não é mudança de produto ou parser gramatical geral.

Oito testes novos em tests/test_scene_future_choice_regressions.py. 68 focados
de políticas e 33 de preparação/histórico/exato aprovados (sobrepostos), um
aviso preexistente. Exato confirma R-03/warned/revisão um/sem desfecho; decisão
atual e ações posteriores continuam bloqueadas. Fechamento indevido posterior
recusa sem revisão/fonte/entrega. Reinício/replay conserva envelope/uma geração/
uma entrega, sem RNG novo. Contraprovas não dependem só de erros de comprimento.

Regressão ampliada: 997 aprovados, um aviso preexistente python_multipart,
156,15s; XML eval-results/hyp-007-l16-readiness-2026-10-18.xml, zero errors/
failures. Históricos L5–L15/prospectivo L16, agência, atribuição, visibilidade,
contratos, campanha, persistência, custo e regressões de segurança cobertos.
Contagens focadas sobrepostas. Não rodada suíte integral/frontend/build;
sem alteração nessas camadas, não declarar release verde. Diff inspecionado,
diff --check sem erros; sem commit/push, checkout original preservado.

## L16 prospectivo fechado

Mesmo prompt v4/modelo low/corpus/limites, 22 hashes/paid-live false.
17 chamadas/768 tokens/20.000 bytes/60s, teto adicional proposto USD 0,15,
sem retry/fallback/admissão automática. CLI 17 sintéticos/zero chamadas,
máximo 13.614 bytes, AST válido; sem chave/terminal/trava L16.
Manifesto fechado `a3cb71c93d3504843b3ddccb99ba919bfa15e44cf4be1056d437acd6eb3270b3`.
Testes L15 usam hashes atuais só em manifesto temporário e provam recusa do
runtime corrigido pelo manifesto executado preservado.

Proposta: aceitar L15 inconclusivo integral por falso positivo de escolha
futura, nenhum narrador admitido, e autorizar L16 nos limites acima.
Continue/prossiga aprova ambos; depois chave protegida. O prossiga que iniciou
esta análise não aceita resultado ainda não apresentado. Não prometer última
tentativa. Fragilidade lexical/UX/fidelidade semântica permanecem registradas;
sem refatoração geral/aceitação narrativa por arrasto. TASK-013/CAMP-24/MVP abertos.
