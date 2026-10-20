# HYP-007-L12 — exposição do registro e preparação L13

18/10/2026. Target gpt-5.6-luna/low, prompt v4.
Batch `33f9877d-1e86-4c0e-a757-0a3bf2ae6973`.

## Observado e custo final

Continue aceitou L11 na conclusão delimitada e autorizou L12. Após entrada
protegida, uma chamada/zero turnos; parada campaign_source_policy_failed
no primeiro R-01/CAMP-EVAL-01. Nenhum percurso completado. Gate L12 fechado,
trava mantida; sem retry/fallback/reutilização de 16 slots. Narrador não admitido.

Custo final **USD 0,0007374 estimados**, não cobrança confirmada. 2.367 tokens
entrada/220 saída, uma chamada com usage/zero sem, reproduzido por reporter
--settled com hash conferido. Sem ajustes de cache, tarifas ou impostos.
Geração 4.664 ms/turno 4.775 ms, amostra única não SLA/aceitação UX.
Correção/preparação adicional USD 0, sem nova chamada real.

Originais em eval-results/hybrid-campaign-luna-l12-33f9877d-1e86-4c0e-a757-0a3bf2ae6973/.
SHA256 records `3efec72954224ed0152943de603b6f78118530e6c543e564f053e9966c1d2ede`.
SHA256 summary `6892163fd8eac3e709438feb3c734d69d6d0fe95a40a0dc07ae250a8aef44000`.
Manifesto L12 fechado `95e85fd707da58394d09bc12771a868b9f8766769740bdc12cf1b04af93c8f5c`.
Não reescrever resposta ou reclassificar rejeição histórica após ajuste.

## Causa e correção local

Trecho: "Você pode ajudar evitando que o registro permaneça exposto ao risco
atual." O validador atribuiu permaneça ao jogador, não ao sujeito registro.
Reprodução: scene_player_agency_violation, narrative, subject voce, clause_index
0, unauthorized_concepts wait. Dois positivos falharam antes/seis contraprovas
passavam. Correção em _action_signature_matches ignora apenas remain/permaneca
precedido de evitando que o registro e seguido de exposto ao risco atual com
pontuação/fim. Texto/offsets/outros verbos preservados. Não muda prompt/schema,
catálogo, RNG, persistência ou autoridade; não é parser gramatical geral.

Oito testes novos em tests/test_scene_record_exposure_regressions.py; 52 focados
de políticas e 33 de preparação/histórico/exato aprovados (sobrepostos), um
aviso preexistente. Resposta exata admite R-01 offline, mantém threatened e
nenhum desfecho. Espera indevida posterior recusa sem revisão/fonte/entrega.
Reinício/replay conserva envelope/uma geração/uma entrega, sem novo RNG.
Sujeito você ou coordenação posterior não recebe exceção de objeto.

Regressão ampliada: 936 aprovados, um aviso preexistente python_multipart,
123,01s; XML eval-results/hyp-007-l13-readiness-2026-10-18.xml, zero errors/
failures. Inclui históricos L5–L12/prospectivo L13, agência, atribuição,
visibilidade, contratos, campanha, persistência, custo e regressões de segurança.
Contagens focadas sobrepostas. Não rodada suíte integral/frontend/build,
sem alteração nessas camadas; não declarar release verde. Diff inspecionado,
diff --check sem erros nos arquivos rastreados alterados; sem commit/push.

## Limitações e próximo lote fechado

Vários lotes recentes pararam em falsos positivos lexicais/atribuição, não em
falha de transporte. Isso evidencia fragilidade operacional do scanner para
variação de prosa; não prova que todas as próximas variantes estão cobertas.
Não ampliar arquitetura ou iniciar refatoração geral por arrasto. Fidelidade
semântica e narrativa/UX permanecem distintas; ressalvas L9 e alias mantidas.

L13 preparado separado, 22 hashes/paid-live false, mesmo prompt v4/alvo/limites:
17 chamadas, 768 tokens/20.000 bytes/60s, teto adicional proposto USD 0,15,
sem retry/fallback/admissão automática. CLI 17 sintéticos/zero chamadas,
máximo 13.614 bytes, AST sem erros. Sem chave/terminal/trava live L13.
Manifesto fechado `5380d04d94ad4299d9646892932f1824c292e4de975a165c3bffd5ff94eb5700`.
Testes históricos L12 usam hashes atuais só em manifesto temporário e provam
recusa do runtime corrigido pelo manifesto executado preservado.

Proposta: aceitar L12 inconclusivo integral por falso positivo de estado do
registro, nenhum narrador admitido, e autorizar L13 nos limites acima.
Continue/prossiga aprova ambos, depois entrada protegida. Não prometer última
tentativa. TASK-013/CAMP-24/MVP continuam abertos.
