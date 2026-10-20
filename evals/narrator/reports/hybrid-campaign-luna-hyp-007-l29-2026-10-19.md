# HYP-007-L29 — R-07, homógrafo nominal e resultado afirmativo

## Autorização e método

Prossiga em 19/10 aceita conclusão delimitada L28 e autoriza L29 conforme proposta:
até 17 chamadas Luna low/v6, 768 tokens, 20.000 bytes, 60s, USD 0.15 total
estimado, sem retry/fallback/admissão; primeira falha interrompe. 22 hashes
revalidados, trava ausente e supervisor 20604 idle antes do pedido. Sem leitura
de chave/clipboard/ambiente/memória. Manifesto e identidade novos, histórico mantido.

## Observação live

Batch 8eb276ee-09b4-4715-adb4-7498f0796dad em
eval-results/hybrid-campaign-luna-l29-8eb276ee-09b4-4715-adb4-7498f0796dad.
12 chamadas/11 turnos; cinco percursos completos (01 preserved, 02 partial,
03 lost, 04 abandoned, 05 preserved); rejeição R-07/CAMP-EVAL-06;
07/08 não executados. Stop campaign_source_policy_failed. Sem retry.

Custo final estimado USD 0.0102446; 36649 tokens entrada e 2429 saída, todas
as chamadas com usage. Não confirma cobrança, cache/impostos/tarifas.
Geração: mínimo 3110 ms, mediana 3577.5 ms, máximo 4415 ms nesta amostra.
Não é benchmark de produção nem garantia de latência.

records SHA256: fcc5c5c67dfffaaa1c7fee76da3b638256abbfcb75d7a1bc5beec726afe9fa42.
summary SHA256: 1bee2ba767e76622bb722abba573ee6e2a364104881567ebd14f8afc67c5bb75.
Gate fechado; latch preservado; supervisor idle/last_lot=29/exit=2.

## Diagnóstico e correções offline

A amostra recupera informação útil entre as partes ainda legíveis, sem
deslocamento. O teste reproduziu depart indevido no token partes, variante
não coberta por de suas partes ainda legíveis (L28) ou entre as partes
preservadas (L9). Ampliada somente a construção entre as partes para adjetivo
legíveis com ainda opcional e fronteira; preservadas mantém comportamento anterior.
Não ignora verbo partir ou outra ação posterior.

Após essa correção, integração ainda falhou: scene_success_not_honored,
apesar de _realizes_rule=True. O marcador recupera informação útil não estava
no reconhecimento de resultado. Adicionado recupera/recuperou informação útil
somente com sujeito afirmativo explícito você, início de cláusula ou após vírgula.
Permanece sujeito aos filtros de negação e texto assertivo. O mesmo marcador
compartilhado proíbe conceder esse resultado em falha. Não reconhece tentativa,
pergunta, fala de NPC, hipótese, talvez ou NPC como sujeito como prova de sucesso.

Três falhas reproduzidas antes do ajuste nominal; duas restantes reproduzidas
antes do ajuste de resultado. Testes de partes legíveis ampliados de 10 para 26,
incluindo integração R-07/rollback/reinício/replay sem RNG ou geração adicional.
344 relacionados aprovados, um aviso preexistente python_multipart. XML:
eval-results/hyp-007-l29-correction-l30-readiness-2026-10-19.xml.
Diff dos trechos alterados inspecionado. Não houve suite integral de release:
regressão ampliada relacionada cobre detector mecânico, negações e integração.
Sem reclassificar L29 nem atualizar seus hashes para ocultar alteração posterior.

## Limites e próximo checkpoint

L29 continua inconclusivo integral, cinco percursos completos, nenhum narrador
admitido. Falas diretas de Mara observadas, mas linguagem como marcado como
ameaçado permanece observação de imersão, não satisfação medida ou novo gate.
Nenhum default/runtime de provedor foi alterado.

L30 preparado e fechado: mesmo v6/Luna low/17 chamadas/768 tokens/20.000 bytes/
60s/USD 0.15 total estimado, sem retry/fallback/admissão. 22 hashes atuais;
preflight 17 sintéticos/zero envios/máximo 14.457 bytes. Não executado.
Proposta delimitada: aceitar L29 como acima e autorizar uma execução L30.
Continue/prossiga aprova; teto padrão não exige reconfirmação separada.
TASK-013/CAMP-24/MVP continuam abertos.
