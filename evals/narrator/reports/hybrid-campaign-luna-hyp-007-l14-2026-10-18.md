# HYP-007-L14 — realização lexical do resgate parcial e preparação L15

18/10/2026, gpt-5.6-luna/low, prompt v4.
Batch `47ea5162-cd94-4c14-a0e7-2327082164a5`.

## Observado e custo

L13 aceito e L14 autorizado por prossiga. Após chave protegida, seis chamadas/
cinco turnos: CAMP-EVAL-01 completo; aviso/dano/ajuda CAMP-EVAL-02 confirmados,
resgate parcial R-06 rejeitado com campaign_source_policy_failed. 03–08 não
alcançados. Gate L14 fechado, trava mantida, sem retry/fallback/transferência
de 11 slots. Nenhum narrador admitido; TASK-013/CAMP-24/MVP abertos.

Custo final **USD 0,0051728 estimados**, não cobrança confirmada. 18.448 tokens
entrada/1.236 saída, seis chamadas com usage/zero sem. Reporter --settled com
hash de records conferido; sem ajustes de cache/tarifas/impostos. Correção e
preparação USD 0 adicional, nenhuma chamada real nova.

Originais em eval-results/hybrid-campaign-luna-l14-47ea5162-cd94-4c14-a0e7-2327082164a5/.
SHA256 records `7bc25337168f3dc3e2170c414e261052a99fd5d8c7cfe28dc5471e3e4a861cba`.
SHA256 summary `8f03f32e69623f08d966d7e45d1aa3d07abcc2577030b81b24b2218fe204aa1c`.
Manifesto fechado L14 `5517b082a0fd91ce4b314c0377e51823d680dfc4268147b5f1606ae4c3b84f01`.
Não reclassificar rejeição histórica ou editar resposta original após correção.

## Diagnóstico e correções delimitadas

Resposta: "o que ainda permanece legível é salvo, enquanto o dano causado pela
umidade continua visível e não é revertido". Validador geral de agência passou
na reprodução. _realizes_rule R-06 retornou false para packet preparado real
de resgate parcial: grupo lexical exigia parcial/parte/trecho, ausentes na frase
equivalente explícita. Integração exata falhava antes do ajuste.

Em api/campaign_source_profile.py acrescentada apenas alternativa normalizada
"o que ainda permanece legivel e salvo" ao grupo de parcialidade R-06; demais
grupos, obrigações de efeito/dano/agência/cânone preservados. Não adicionar
palavra genérica ainda como escape. Sem mudar prompt/schema/catálogo/RNG/
persistência ou autoridade. Não afeta o validador geral de cena neste ajuste.

Contraprova "O registro continua perdido" revelou lacuna no guard de estado
contraditório: o guard reconhecia foi/está, não continua. Primeira verificação
pós-equivalência teve essa falha; acrescentado continua ao mesmo guard existente
de preserved/partial contra perdido/destruído. Teste não foi retirado/afrouxado.
Isso reforça uma contraprova diretamente relacionada, sem parser semântico geral.

Seis testes em tests/test_campaign_partial_wording_regressions.py: exato,
resgate genérico sem parcialidade, contradição continua perdido, resgate por
Mara, integração segura/insegura. Antes: dois positivos falhavam/quatro
contraprovas passavam. Após ambos ajustes: 33 focados de perfil/integração/
trajetórias e 31 de preparação/histórico/exato aprovados (sobrepostos), um aviso
preexistente. Exato confirma revisão quatro/partial/dry_surface; ação indevida
recusa, mantém revisão três/wet/sem entrega. Reinício/replay conserva envelope,
uma geração/entrega do resgate, nenhum RNG novo.

Regressão ampliada: 976 aprovados, um aviso preexistente python_multipart,
146,77s; XML eval-results/hyp-007-l15-readiness-2026-10-18.xml, zero errors/
failures. Seleção histórica L5–L14/prospectiva L15, agência, atribuição,
visibilidade, contratos, campanha, persistência, custo e regressões de segurança.
Contagens focadas sobrepostas. Não rodada suíte integral/frontend/build,
sem alteração nessas camadas; não declarar release verde. Diff inspecionado,
diff --check sem erros; sem commit/push, checkout original preservado.

## L15 prospectivo fechado

Mesmo prompt v4/modelo low/corpus/limites, 22 hashes/paid-live false.
17 chamadas/768 tokens/20.000 bytes/60s, teto adicional proposto USD 0,15,
sem retry/fallback/admissão automática. CLI 17 sintéticos/zero chamadas,
máximo 13.614 bytes e AST válido; sem chave/terminal/trava L15.
Manifesto fechado `57269d7cdc41013b7d0c12b62f3e1ce6e9384fb1c2958692eeed0519aa8398c2`.
Testes L14 usam hashes atuais só em manifesto temporário isolado e provam
recusa do runtime corrigido pelo manifesto executado preservado.

Proposta: aceitar L14 inconclusivo integral por lacuna lexical de realização
do resgate parcial, nenhum narrador admitido, e autorizar L15 nos limites acima.
Continue/prossiga aprova ambos; depois chave protegida. Não prometer última
tentativa. Fragilidade lexical e limitações semânticas/UX permanecem registradas;
sem refatoração arquitetural ou aceitação narrativa por arrasto.
