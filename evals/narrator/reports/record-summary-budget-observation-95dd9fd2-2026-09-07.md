# Resumo com teto de 768 — observação 95dd9fd2 encerrada

O lote `95dd9fd2-f78f-4467-858f-b3948479aa10` terminou com **uma chamada HTTP 200/stop, rota Groq/Qwen e schema válidos, código operacional 0**. O resumo tem **23 palavras e 120 caracteres** e, nesta revisão independente, não apresentou afirmação retida sem suporte na fonte. Esse resultado é limitado a um pedido; não aprova capacidade geral, qualidade narrativa, runtime ou CAP-001.

PID 21744 confirmado `finished` em `2026-09-07T20:41:18.2606505Z`, chave descartada e limite do lote esgotado. Não houve retry, diagnóstico, fallback ou segundo caso. [Preparação histórica](record-summary-budget-v1-2026-09-07.md), [desenho prévio](record-summary-budget-design-1edf4d3e-2026-09-07.md), [dossiê](record-summary-budget-dossier-1edf4d3e-2026-09-07.json) e [análise detalhada](record-summary-budget-observation-95dd9fd2-2026-09-07.json).

## Fonte e resposta literais

Fonte station-clock:

> Na estação vazia, um relógio parado marca seis horas. Um envelope lacrado repousa sobre o banco; perto da janela aberta, a cortina se move com a brisa.

Resposta summary:

> Na estação vazia, um relógio parado marca seis horas. Um envelope lacrado está no banco e a cortina se move com a brisa.

A estação vazia e o relógio parado marcando seis horas permanecem literais. Manter “parado” conserva a indicação do relógio, sem afirmar que sejam seis horas no momento da cena. “Um envelope lacrado está no banco” preserva objeto e lacre; “no banco” é menos preciso, mas compatível com “repousa sobre o banco”. O movimento da cortina com a brisa permanece literal. Não há ação de jogador/NPC, nova causa, estado contraditório ou aumento de certeza identificados.

A janela aberta e a proximidade da cortina foram omitidas. Isso é compressão permitida: esses detalhes ficam não informativos, sem premiar sua preservação ou inferir distorção. A fonte não contém hipótese modal; este resultado também não informa capacidade de preservar modalizadores. A contagem satisfaz a instrução de até 25 palavras, mas não é um gate semântico. A revisão é autorada e separada do bruto, que permanece `semantic_fidelity_review: not_performed/approval: null`.

## Operação, integridade e limites

Uso reportado: **459 tokens de entrada + 38 de saída = 497**. Raciocínio `null` significa não reportado, não zero; custo indisponível. O observador registrou HTTP 200, `finish_reason=stop` e ID `req_01m1ysn3mheh2sabqbsqh3eftm`; o modelo efetivo Qwen foi reportado e o provedor Groq observado, com identidade verificada. O texto foi preservado sem reparo. Nenhum defeito local de medição ou retenção foi demonstrado.

A auditoria independente reconstruiu exatamente preflight inicial/final, metadados preparados e brutos, corpo congelado, resumo operacional, contrato e medição. Confirmou 10 arquivos de preparação, 60 históricos e 16 brutos históricos preservados; são conjuntos que podem se sobrepor, não uma soma de arquivos únicos. Auditoria SHA `658cc0e2dfb5fd9107700d5c740754c6d2872a03bf4013a42932054923c9d742`, registrada antes de alterações posteriores de preparação na guarda CAP compartilhada. Os fingerprints desta execução permanecem históricos, sem exigir que o código compartilhado nunca evolua.

Entre início do run e início do adaptador decorreram 60,474599 s por UTC. Duração UTC do adaptador: 1,150289 s; perf_counter: 1,151466 s. A espera monotônica exata e o deadline absoluto não foram persistidos; os tempos locais não comprovam chegada remota. Não foi capturado tráfego HTTP bruto: o pedido foi reconstruído contra código e dossiê congelados.

- [summary.json original](../../../eval-results/20260907T204016Z-b929bf2c-302d-4b26-b36b-abb0eec249d9/summary.json): SHA `487117deccd95da1585147a3149b3e8bded146803a3c49a88bea01b1d7c5f211`.
- [JSONL original](../../../eval-results/20260907T204016Z-b929bf2c-302d-4b26-b36b-abb0eec249d9/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl): SHA `91edd2cbe2791da84329ac61465e580f5c8974bfa8d0c1d9daa02a2fdb6de17f`.

Os 65 testes novos pertencem à preparação; nenhum foi repetido nesta análise. Os campos `prepared_metadata`, `files`, `verification`, `scope` e `evidence_files` foram preservados literalmente. Não houve edição de bruto, fonte, prompt, contrato ou runtime neste fechamento.

O pedido anterior 1edf4d3e terminou por 429 sem texto; este pedido novo completou transporte, rota e schema sob teto de 768. USER, número do teto no SYSTEM e teto HTTP diferem. Essa observação demonstra viabilidade operacional deste pedido, sem provar que reduzir o teto causou o sucesso, explicar a estimativa OTPM ou estabelecer taxa de sucesso e estabilidade. O par antigo continua encerrado, sem preencher B.

## Continuidade

Preparar um contraste de atribuição com duas fontes sintéticas novas e independentes, mantendo o SYSTEM record-summary-budget-v1, o schema SummaryOnlyProposal, Qwen/Groq gratuito, reasoning_effort=none, temperatura 0,65 e teto de 768 por chamada (até 1.536 no total). Limite de duas chamadas, espera inicial e intervalo entre inícios de pelo menos 60 segundos, deadline de 60 segundos após a espera e parada no primeiro erro operacional. Não repetir station-clock, archive-vibration, observatory-a/observatory-b ou preencher casos anteriores. A preparação está em curso, ainda não declarada pronta; nenhum novo envio é registrado neste fechamento. Concluir o trabalho local independente antes de depender de uma nova entrada protegida de credencial, sem nova confirmação genérica.

A autorização contínua permanece válida. Esta análise não promove perguntas, anotações inline, oito campos, atores, runtime ou CAP-001; não reclassifica resultados anteriores.
