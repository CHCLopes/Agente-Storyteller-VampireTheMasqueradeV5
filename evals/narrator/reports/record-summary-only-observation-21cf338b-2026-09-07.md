# Resumo textual sozinho — observação 21cf338b encerrada

O lote `21cf338b-5783-43a4-91ad-82f8bac86e96` terminou com **sucesso operacional e falha de fidelidade**. Uma chamada recebeu HTTP 200/`stop`, modelo e rota Groq/Qwen verificados e schema válido, exit 0. O resumo tem **21 palavras e 134 caracteres**, dentro do limite de 25 palavras, mas atribui à luz uma cor que a fonte atribui à lanterna. A medição de concisão não altera o exit operacional nem aprova semântica.

PID 26012 confirmado `finished` em `2026-09-07T19:04:30.3081925Z`; chave descartada e limite deste lote esgotado. Nenhuma repetição, fallback, diagnóstico, geração narrativa ou correção da resposta. [Preparação histórica](record-summary-only-v1-2026-09-07.md), [critérios prévios](record-summary-only-design-94a95216-2026-09-07.md), [dossiê congelado](record-summary-only-dossier-94a95216-2026-09-07.json) e [registro detalhado desta análise](record-summary-only-observation-21cf338b-2026-09-07.json).

## Resposta e revisão independente

Texto preservado literalmente em `summary` e `summary_text`:

> No arquivo municipal, luz vermelha ilumina mesa com pastas. Perto da porta fechada, vibração leve sugere possível motor do outro lado.

| Dimensão | Fonte e resposta | Avaliação |
| --- | --- | --- |
| Cor | n0: “a luz de uma lanterna vermelha”; resposta: “luz vermelha” | Falha: transfere a propriedade da lanterna para a luz emitida, sem suporte. Não é mera omissão da lanterna. |
| Local e iluminação | “No arquivo municipal”; “ilumina mesa com pastas” | Local e iluminação preservados. “Com pastas” é compressão legítima de “coberta de pastas”. |
| Vibração e porta | “Perto da porta fechada, vibração leve” | Posição, intensidade e estado da porta preservados. |
| Hipótese | “sugere possível motor do outro lado” | Existência e posição permanecem sob possibilidade; não confirma o motor. |
| Funcionamento | A fonte inclui “funcionando”; o resumo omite essa dimensão | Não informativa, sem penalizar a omissão nem concluir capacidade de resumir essa propriedade. |

Não há ação, emoção ou conclusão inventada para jogador ou NPC. Perguntas e segmentação modal não pertencem ao contrato desta observação; nenhuma falha histórica nessas dimensões foi reclassificada. A revisão não exige uma paráfrase única nem reprodução integral da fonte.

A avaliação semântica acima é autoria dos agentes, separada dos artefatos automáticos. O bruto conserva `semantic_fidelity_review: {status: not_performed, approval: null}` e `semantic_fidelity_evaluated: false`. Não há defeito local demonstrado no medidor ou na retenção literal.

## Operação, integridade e limites

Uso reportado: **472 tokens de entrada + 39 de saída = 511**. Raciocínio não reportado (`null`, não zero); custo indisponível. Uma chamada, zero skips, sem retry/fallback; espera inicial mínima e deadline configurados em 60 segundos, teto de 3.072, temperatura 0,65 e esforço `none`.

A auditoria operacional independente reconstruiu exatamente preflight, metadados preparados/brutos, resumo operacional, contrato e medição. Confirmou 10 fingerprints de preparação, 39 históricos e 12 brutos históricos intactos naquele momento; os conjuntos se sobrepõem e não representam uma soma de arquivos únicos. A evidência está no JSON associado, com SHA `53b96a0d6fb4c851df71b8eb1f90d5865bdf2ee2c38449ccd903bb17687e47f4`. O intervalo UTC entre início do run e início do adaptador foi 60,498576 s; duração UTC do adaptador 1,208069 s e medição perf_counter 1,209086 s. A espera monotônica exata e o deadline absoluto não foram persistidos; UTC não mede chegada remota. O shared auditado nesta execução tinha SHA `ec7113ffafd4dce96442d18494982afbd4cae352438c0d7bd08df0aab794a5d2`; a guarda aditiva da preparação contrastiva foi iniciada depois desta auditoria e não altera essa proveniência histórica.

Os **336 testes** pertencem à preparação (243 novos e 93 existentes); não foram repetidos para analisar esta resposta. Os campos históricos `prepared_metadata`, `files`, `verification`, `scope` e `evidence_files` permanecem literalmente iguais. Nenhum código, prompt, critério anterior ou bruto foi editado neste fechamento.

- [summary.json original](../../../eval-results/20260907T190328Z-33c26c5a-59ef-4ef7-a40e-178fe3a65a16/summary.json): SHA `8ab373f9d31f982fd16f7acf34ad36d1676255e21d87b1dd610dfa3543ccceb2`.
- [JSONL original](../../../eval-results/20260907T190328Z-33c26c5a-59ef-4ef7-a40e-178fe3a65a16/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl): SHA `c4bbd85c68255cb4cdb0aa1125861326e76ac591c0b7f89b187d93a95da5286d`.

Frente ao [Qwen inline 94a95216](record-inline-evidence-qwen-observation-94a95216-2026-09-07.md), a contagem passa descritivamente de 32 para 21 palavras; o texto anterior era cópia fiel, enquanto este contém transferência de cor. SYSTEM, tarefa e schema mudaram em conjunto. Isso não demonstra a causa de qualquer diferença, superioridade, taxa ou generalização. Omissões não demonstram capacidade nas dimensões ausentes.

## Continuidade autorizada

Archive-vibration e este pedido estão encerrados. O próximo trabalho é preparar um par contrastivo de **fontes novas, autoradas e independentes**, mantendo SYSTEM de resumo, schema e parâmetros. Esse trabalho está em curso; este relatório não declara a próxima observação pronta e não registra novo envio. Não repetir o arquivo municipal, acrescentar instruções em sequência para reparar a amostra ou escalar esforço/teto.

A autorização contínua permanece válida; não há nova aprovação genérica pendente. Completar autonomamente o preparo e as verificações antes de depender de credencial ou intervenção direta. Oito campos, atores, runtime e CAP-001 continuam sem aprovação.
