# Target-spans 26547182 — término por comprimento

Data: 07/09/2026. Status: **execução encerrada e analisada; não há envelope completo para revisão semântica**. A autorização contínua cobre o próximo passo já em preparação, sem nova pergunta de aprovação.

O lote `26547182-1133-477d-92a7-fa9f5729c423` executou uma abertura. Groq / `openai/gpt-oss-120b` foram verificados. A resposta foi HTTP 200 com **`finish_reason: length`**, teto de 1.536 consumido e erro normalizado `malformed_response / generation_truncated`. Não houve retry, fallback, diagnóstico, Mara ou geração narrativa.

## O que esta observação demonstra

O provedor declarou término por comprimento nesta realização. Isso é evidência explícita; no HTTP 400 histórico havia apenas coincidência entre saída e teto. Não retroagir este motivo ao lote anterior e não atribuir causalmente o truncamento ao parágrafo acrescentado no SYSTEM.

| Medida | b129ceaa — SYSTEM anterior | 26547182 — target-spans |
|---|---:|---:|
| Teto da API | 1.536 | 1.536 |
| HTTP | 200 | 200 |
| Término | stop | length |
| Entrada reportada | 2.320 | 2.484 |
| Saída reportada | 1.112 | 1.536 |
| Raciocínio reportado | 658 | 1.031 |
| Total reportado | 3.432 | 4.020 |
| Envelope disponível | Sim | Não |
| Intervalos de suporte | Cinco inválidos | Não avaliados |
| Revisão de fidelidade | Falha na pressuposição de uma pergunta | Não possível sem registros |

Os 505 tokens resultantes de `1536 − 1031` são somente diferença aritmética dos contadores, não uma tokenização independente do JSON. Nenhum conteúdo de raciocínio foi lido ou retido. O custo continua indisponível.

A comparação é histórica e estocástica, sem controle contemporâneo. Não demonstra regressão semântica ou que a nova instrução aumentou causalmente a necessidade de raciocínio.

## Limites da análise

O JSONL não contém `response_envelope`, `derived_records`, `composed_proposal` ou validação de suportes. O adaptador rejeitou o término incompleto antes de disponibilizar uma proposta. Assim, os valores negativos de schema, envelope, schema final e admissão representam etapas não concluídas; não são quatro validações executadas e reprovadas.

Não é possível saber se a instrução corrigiu os intervalos. Também não há nova evidência sobre cobertura, modalidade ou redação das perguntas. “Quem ou o que está observando?” continua um achado do lote b129ceaa; não sabemos a redação desta realização.

`partial_output:false` indica ausência de conteúdo parcial exposto/persistido pelo adaptador, não ausência de tokens gerados. `usage_aggregate:unavailable` é o estado herdado do adaptador após a falha; os contadores explícitos permanecem disponíveis separadamente em `provider_observation`. Essa distinção foi prevista pelo observador e não exige alterar o runtime.

## Verificação e proveniência

Preflight e summary foram reconstruídos exatamente no início da análise. Código, fontes e parâmetros coincidiram com a preparação. A análise independente chegou ao mesmo limite de conclusão. Não foi encontrado defeito local a corrigir nesta rejeição, nem foi feita outra inferência para tentar obter sucesso.

Início do lote: 14:18:51.505043 UTC. Despacho: 14:19:52.069989. Término observado: 14:19:56.354109. Intervalo inicial 60,564946 s; chamada 4,284120 s. Request `req_01m1y3tqjxe4hsv6x23pkmq1cg`. O launcher confirmou `finished`, exit 1, às 14:19:56.8000499 UTC.

- [summary.json](../../../eval-results/20260907T141851Z-99b5d672-db46-4720-b302-961d7934fa42/summary.json): SHA `378141dba4eadf0106f9e494f9ecd2c0bc1f607c660953367572e0270ab3b7f4`.
- [JSONL](../../../eval-results/20260907T141851Z-99b5d672-db46-4720-b302-961d7934fa42/gpt-oss-120b-groq-free-synthetic-low.jsonl): SHA `f172259d1fb7edb004ef4c827d1971b4ed1bd98c36aaf8ca4ac80aabc8a41b54`.
- [Registro JSON da análise](record-evidence-target-spans-observation-26547182-2026-09-07.json): auditoria, metadados e distinções completas.

Os 479 testes são da preparação; não foram repetidos para inflar a análise. Os artefatos originais ficam imutáveis. O acréscimo posterior de guardas de replay para a nova observação será registrado separadamente.

## Continuidade já autorizada

O [novo desenho de orçamento](record-evidence-target-budget-3072-design-26547182-2026-09-07.md) mantém este SYSTEM, USER, schema, contratos e todos os demais parâmetros; muda somente o teto de 1.536 para 3.072. É uma observação nova, motivada pelo `length` explícito, com identidade própria e uma chamada máxima. A preparação foi iniciada sob a autorização ampliada.

O objetivo é obter uma conclusão observável da mesma tarefa, sem reparar resposta ou relaxar critérios. Qualquer resultado encerra esse novo lote e será analisado. Não haverá escalada mecânica de tetos para buscar aprovação. Chaves continuam dependência humana protegida; não solicitar decisão adicional de escopo. CAP-001 e runtime continuam sem aprovação técnica inferida.
