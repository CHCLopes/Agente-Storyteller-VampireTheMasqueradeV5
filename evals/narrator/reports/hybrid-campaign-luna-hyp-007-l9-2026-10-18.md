# HYP-007-L9 — resultado, ambiguidade nominal e preparação L10

Data: 18/10/2026. Target `gpt-5.6-luna`, esforço `low`, prompt v4.
Batch: `6c5cbe84-00a9-4aff-b242-5a6ede0af505`.

## Observado

L8 aceito e L9 autorizado por "continue" na proposta delimitada anterior.
Entrada protegida confirmada pelo usuário. L9 fez 12 chamadas e completou
11 turnos, sem retry/fallback, parando em `campaign_source_policy_failed`
no R-07 de CAMP-EVAL-06. CAMP-EVAL-01 a 05 terminaram: resgate intacto,
resgate parcial após dano, perda, abandono e resgate direto. CAMP-EVAL-06
foi rejeitado; 07/08 não foram alcançados. Não reutilizar cinco slots.
Gate L9 paid/live fechado e trava preservada. Nenhum narrador admitido.

Artefatos originais em
`eval-results/hybrid-campaign-luna-l9-6c5cbe84-00a9-4aff-b242-5a6ede0af505/`.
SHA256 records: `715e21b1dd34fdbb6090e3fa1ed38fa7c2327482b7e7e93065be37e047ad9247`.
SHA256 summary: `1ec8c081e89cd7e8ba742308e73ff2178f894ec030bf46727e4ab6c97c78fdf6`.
Manifesto L9 fechado original: `aca5e8156e5aa6083e044962f4f3d9ddb52ccb831cd0a4de757cc713a05bd35f`.
Não reescrever respostas ou reclassificar o turno live após correção.

## Custo e latência

Custo final estimado **USD 0,0097762**, não cobrança confirmada.
34.709 tokens de entrada, 2.362 de saída, 12 chamadas com usage e nenhuma sem.
Reproduzido com `scripts.report_luna_test_cost --settled`, conferindo hash.
Sem ajustes de cache, tarifas ou impostos. Correção e preparação: USD 0 adicional.
Geração: mínimo 2.231 ms, máximo 4.403 ms, média 3.421,25 ms.
Turno: mínimo 2.364 ms, máximo 4.605 ms, média 3.708,08 ms.
São observações de 12 chamadas sintéticas, não SLA nem aceitação de UX.

## Diagnóstico e correção local

Trecho: "recuperar informação útil entre as partes preservadas".
O scanner extraiu `move/depart` do substantivo `partes`, confundido com
flexão do verbo partir. Diagnóstico bruto reproduzido offline:
`scene_player_agency_violation`, campo narrative, subject voce, clause_index 0,
unauthorized_concepts move. R-07 e seus fatos determinísticos autorizavam exame
com sucesso e recuperação parcial de informação, não deslocamento.

Correção em `_action_signature_matches`: ignorar somente família depart,
token partes, precedido por entre as e seguido por preservadas. Mantém texto,
offsets, demais verbos, alvos e gates. Sem mudança de prompt/schema, RNG,
persistência, autoridade, catálogo ou default. Não é interpretação nominal geral.

Oito testes novos em `tests/test_scene_document_parts_regressions.py`:
nominal exato, cinco contraprovas de partida, integração R-07 e rollback.
Resposta exata admite offline com desfecho partial; partida posterior indevida
é rejeitada sem revisão/fonte/entrega parcial. Reinício/replay mantém envelope,
uma geração, uma entrega e nenhum novo RNG. 33 focados conjuntos aprovados
(oito novos, 13 históricos L9, 12 prospectivos L10), um aviso preexistente.
O teste adicional de replay passou novamente nos oito casos.

Regressão ampliada: **871 aprovados**, um aviso preexistente python_multipart,
91,61 segundos. Seleção cobre históricos L5–L9 e prospectivo L10, agência,
atribuição NPC, perguntas, condicionais, diagnóstico, visibilidade, contratos,
campanha, execução/persistência, custo e regressões de segurança. Evidência:
`eval-results/hyp-007-l10-readiness-2026-10-18.xml`, zero errors/failures.
Contagens focadas se sobrepõem, não somar como testes únicos. Não foi rodada
suíte integral/frontend/build; sem alteração nesses componentes. Não declarar
release verde: permanecem pendências históricas e aceitação integral/humana.

O diagnóstico exploratório inicial chegou ao erro de política, mas a limpeza
de seu SQLite temporário encontrou WinError 32; processo terminou. Não afetou
artefatos live. Os testes isolados posteriores concluíram normalmente.

## Limitações narrativas e de alcance

O scanner não prova fidelidade semântica completa. Em R-01 Mara diz "Não o
mova por enquanto", embora o caminho permita resgate imediato. Em R-07 o
texto usa "parcialmente restaurado" e menciona "pista relevante", termos que
merecem avaliação de fidelidade/UX frente à recuperação apenas de informação.
Passagem offline não transforma esses trechos em aceitação humana nem aprova
novos fatos. Sem reescrever a resposta observada para fazê-la passar.
Continuam também as limitações já documentadas de pronomes com alias.

## Próximo lote prospectivo, sem autorização de gasto

L10 separado, mesmo alvo low, prompt v4, oito percursos/17 chamadas máximas,
768 tokens, 20.000 bytes, timeout 60s, sem retry/fallback/admissão automática.
Novo teto adicional estimado proposto USD 0,15; não é saldo L9.
Manifesto com 22 hashes, paid/live false. SHA256 fechado:
`818084ed1cbf9878549a3195a10933ec399cbb91be895e07c18d44fda724ad0d`.
Preflight CLI: 17 turnos sintéticos, zero chamadas, máximo 13.614 bytes.
AST PowerShell sem erros. Nenhum lançador/chave/trava live L10 aberto.
Testes L9 usam hashes atuais somente em manifesto temporário e provam recusa
do runtime corrigido pelo manifesto executado preservado.

Proposta: aceitar L9 inconclusivo para campanha integral por falso positivo
nominal, nenhum narrador admitido, e autorizar L10 nos limites acima.
"Continue"/"prossiga" aprova essa proposta delimitada. Não prometer última
tentativa. Depois, entrada protegida da chave. TASK-013/CAMP-24/MVP abertos.
