# Atribuição de cor — observação 1edf4d3e encerrada por disponibilidade

O lote `1edf4d3e-13f0-4161-916c-a178b58c1825` terminou com **HTTP 429 no primeiro caso e nenhum texto retornado**, código operacional 2. Apenas observatory-a foi chamado; observatory-b foi registrado como `previous_operational_failure`, conforme a regra de parada. Não há resultado semântico do par. Um limite de uso não demonstra incapacidade do modelo para resumir.

PID 24720 confirmado `finished` em `2026-09-07T19:36:06.2011876Z`; chave descartada e lote encerrado. Não houve retry, fallback, diagnóstico, reparo ou chamada para preencher B. [Preparação histórica](record-summary-attachment-v1-2026-09-07.md), [desenho e critérios prévios](record-summary-attachment-design-21cf338b-2026-09-07.md), [dossiê](record-summary-attachment-dossier-21cf338b-2026-09-07.json) e [registro detalhado](record-summary-attachment-observation-1edf4d3e-2026-09-07.json).

## Evidência e estágios

| Caso | Operação | Texto, schema e revisão |
| --- | --- | --- |
| observatory-a | Uma chamada HTTP 429; provider_code rate_limit_exceeded | Nenhum summary. Schema e medição não alcançados; fidelidade e vínculo da cor não avaliáveis. |
| observatory-b | Não chamado; skip pela falha operacional anterior | Não há resposta, medição ou avaliação. Não inferir omissão ou erro do modelo. |

O provedor efetivo Groq foi observado, mas o modelo efetivo não foi reportado: a verificação de rota/modelo ficou `unavailable`, não `verified`. Uso, raciocínio, custo e finish_reason são indisponíveis; `null` não significa zero. O erro normalizado é `rate_limited/http_429`, com ID `req_01m1ynxqgxe7etempc1qjyhgjy`. A classificação `retryable: true` não autoriza repetir este lote.

Os metadados locais indicam recurso tokens e origem desconhecida, sem Retry-After. Os headers normalizados exibem quotas de pedidos/dia e tokens/minuto com remaining igual a limit e reset de 0,001 s. Esses dados não identificam a janela que bloqueou a requisição nem estabelecem ETA. O corpo completo do erro foi tratado dentro do limite do observador; o observador registrou failed_generation ausente. Mensagem bruta e raciocínio não foram preservados.

## Conclusão da investigação e integridade

A consulta autenticada ao Console confirmou a linha compatível com horário, modelo solicitado, HTTP 429 e ID abreviado `req_0...hgjy`. O detalhe sanitizado informa serviço `on_demand` e limite de **output tokens per minute (OTPM): 1.000**, com **Requested: 1.096**, descrito pelo provedor como expectativa de saída do pedido acima do limite. Isso documenta o motivo informado pelo provedor; não revela a fórmula de estimativa, consumo efetivo, janela diária, reset ou capacidade restabelecida. A coluna do Console é o modelo solicitado, não confirmação do efetivo, e seus zeros de uso não substituem os `null` da API. A [documentação oficial de limites da Groq](https://console.groq.com/docs/rate-limits), consultada pelo root, distingue ITPM/OTPM em certas organizações e os headers genéricos TPM/RPD. Assim, a anotação externa sobre OTPM permanece separada de `origin: unknown` no bruto local, sem sobrescrevê-lo. Aguardar, por si só, não demonstra que um pedido cuja expectativa excede o limite informado seria aceito.

A auditoria operacional independente reconstruiu exatamente preflight inicial/final, metadados preparados e brutos, resumo operacional e os dois corpos congelados. Confirmou 9 arquivos de preparação, 48 fingerprints históricos e 14 brutos históricos preservados; os conjuntos podem se sobrepor e não devem ser somados como arquivos únicos. O SHA da auditoria é `20bf6150940fdac8c8be8507226aa67f7c8bdb2b14f17cacf3eb23e837ed2676`. Entre início do run e início do adaptador decorreram 60,528013 s por UTC; duração UTC do adaptador 0,755523 s e perf_counter 0,756475 s. A espera monotônica exata e o deadline absoluto não foram persistidos; esses tempos locais não medem chegada remota. Nenhuma contradição operacional ou defeito local foi demonstrado.

Os 199 testes pertencem à preparação (152 novos e 47 existentes); nenhum foi repetido para esta análise. Os campos `prepared_metadata`, `files`, `verification`, `scope` e `evidence_files` permanecem literalmente iguais na preparação. A revisão automática bruta conserva `not_performed/approval: null`; não existe texto sobre o qual realizar revisão semântica. Nenhum artefato bruto foi corrigido ou reclassificado.

- [summary.json original](../../../eval-results/20260907T193504Z-6322b0c6-b87e-4eb2-b0d8-a2404e694515/summary.json): SHA `77090a6559e696e0caecc28c6726cbf4f3d68b4b9187b36f00ae1faa6ad085e5`.
- [JSONL original](../../../eval-results/20260907T193504Z-6322b0c6-b87e-4eb2-b0d8-a2404e694515/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl): SHA `91482cf3cfcfb06fe24e8deab5dfeab93a66838048e587e9bb63aea0743f79da`.

## Continuidade

Preparar offline uma observação operacional independente com orçamento de saída reduzido a no máximo 768 tokens, fonte sintética nova, mesmo Qwen/Groq gratuito e limite de uma chamada. O desenho e a implementação exatos ainda estão em decisão/preparação; não estão declarados prontos e não houve novo envio. A hipótese será observar compatibilidade operacional nesse orçamento, sem garantia de sucesso ou avaliação de narrativa/CAP-001. Não repetir A, preencher B ou reutilizar o par; concluir as verificações locais antes de depender de uma nova entrada protegida de credencial.

Este par e todos os pedidos anteriores continuam encerrados; não repetir A nem preencher B. A autorização contínua permanece válida, sem nova aprovação genérica. Credenciais e intervenção direta só são dependências humanas quando efetivamente necessárias. Nenhuma nova chamada é declarada neste fechamento. Perguntas, anotações inline, oito campos, atores, runtime e CAP-001 continuam sem aprovação.
