# Comparação exploratória de compressão relacional — preparação histórica e lote encerrado

A preparação foi implementada e verificada com **86 testes novos distintos aprovados**, revisão independente, reconstrução dos pedidos, preflight e integração com chave vazia. O lote subsequente **faad6837** foi executado e está encerrado: duas chamadas operacionais válidas, sem skips, controle 19 palavras e relational 23. O trecho espacial permanece ambíguo nos dois; não há aprovação geral de fidelidade. [Resultado, matriz e limites](record-summary-relational-observation-faad6837-2026-09-07.md). Os dados e critérios de preparação abaixo são históricos e permanecem preservados.

O [par anterior 0e7b0ac3](record-summary-color-observation-0e7b0ac3-2026-09-07.md) está encerrado: duas respostas operacionais válidas, ambas com 20 palavras, mas a expressão “luminária azul” deixou ambígua a distinção entre base e luz. Outras relações também perderam clareza. Esse resultado fundamenta a hipótese de preservar relações ao selecionar menos afirmações; não demonstra o mecanismo da perda.

## Pedido congelado

O [desenho prévio](record-summary-relational-design-0e7b0ac3-2026-09-07.md) e o [dossiê HTTP](record-summary-relational-dossier-0e7b0ac3-2026-09-07.json) fixam **uma fonte nova de 32 palavras, gallery-reflection**, e dois braços control→relational. O USER inteiro é idêntico, inclusive case_id e unidades. Só messages[0].content muda entre os corpos.

O controle usa o SYSTEM budget congelado. A variante reformula somente o parágrafo FORMATO, orientando selecionar poucas afirmações completas com participantes e relações explícitos, omitindo afirmações quando não couberem. Mantêm-se limites, proibições e os demais parágrafos. Não há exemplos corretivos, rubrica ou gabarito no USER.

Schema/protocolo record-summary-only-v1, modelo qwen/qwen3.8-27b pela rota direta Groq gratuita declarada, reasoning_effort=none, temperatura 0,65, stream=false e teto de 768 por chamada permanecem iguais. Duas chamadas no máximo/1.536 tokens totais, uma por braço. A segunda é um braço previamente registrado; não é retry.

| Braço | SYSTEM | SHA-256 do corpo |
| --- | --- | --- |
| control | record-summary-budget-v1 | cdd9507caa318b6d74e92863e84e483571bdddce0fbbf618e730121e8177a5c9 |
| relational | record-summary-relational-v1 | 7599cb88ff1f4085ada54469c7749d6ef7aaebbd2287ad207be47e29dd3043ec |

Cada resposta será revisada separadamente antes da comparação: relações retidas fiéis, alteradas, ambíguas ou omitidas. Omitir é permitido e não informativo na dimensão omitida; não se exige cobertura completa ou gabarito. Mais objetos ou menos palavras não demonstram fidelidade. Uma saída por braço, ordem fixa e variação estocástica permitem comparação descritiva, sem conclusão causal, taxa ou superioridade geral.

## Implementação e verificação

Novos executor e wrapper preservam o fluxo delimitado de duas chamadas e adaptam o eixo de execução para braço, com fonte única. inputs.case identifica a fonte; inputs.arms fixa prompt e pedido de cada braço. Registros, observações e medições contêm arm_id e case_id distintos. Cada adaptador é de uso único e aceita apenas seu corpo e operação. A fonte não recebe rótulos artificiais de braço.

| Verificação focada | Resultado |
| --- | --- |
| Executor: fonte comum, SYSTEM/corpo exclusivos, metadados, espera/deadline, ordem, parada e retenção | 26 passaram |
| Wrapper: preflight por braço, fonte única, fingerprints, status/exit e proteção da credencial | 49 passaram |
| Fronteira CAP: marcadores isolados nos dois caminhos e comportamento legado | 11 passaram |

As matrizes históricas não foram repetidas. O aviso Starlette/multipart já existente permanece fora do escopo. A integração real PowerShell 7/Python concluiu o preflight e terminou com exit 3 na validação da chave vazia, sem envio, stderr ou novo artefato. O preflight ocorre antes da conversão/exportação da credencial pelo wrapper.

Revisão independente sem achados materiais. A auditoria confirmou dez arquivos da preparação, 81 históricos e 20 brutos anteriores. O avaliador compartilhado recebeu somente 12 linhas para recusar essa identidade nas duas entradas de replay CAP; contratos, adaptadores e runtime não mudaram. Fingerprints antigos continuam históricos; a evolução compartilhada é explicitamente posterior. [Metadados, fingerprints, testes e evidências](record-summary-relational-v1-2026-09-07.json).

## Parada e continuidade

Espera inicial e intervalo entre inícios de pelo menos 60 segundos; deadline de 60 segundos por chamada após a espera. O primeiro erro operacional encerra chamadas e persiste o braço restante como skip. Palavras e semântica não impedem o segundo braço se o primeiro foi operacionalmente válido. Sem diagnóstico, retry, fallback, substituição, juiz LLM ou geração narrativa.

Encerrar a investigação após as duas posições ou o primeiro erro, sem sequência de reformulações para elevar taxa. Preservar texto literal; a revisão autorada fica separada do bruto not_performed/approval null. Nenhuma resposta promove perguntas, anotações inline, oito campos, atores, runtime ou CAP-001.

Janela única PID 1096 terminou em 2026-09-07T21:47:25.3117077Z, exit 0, batch faad6837-cc0b-408d-85a6-025d0db770b3; credencial descartada. Os dois braços foram executados e analisados. Não relançar, repetir a hipótese ou recuperar credenciais antigas. Próximo trabalho autorizado: consolidar evidências summary-only, budget, color e relational e definir lacunas/próxima direção; nenhum novo SYSTEM, lote ou entrada de chave agendado. A revisão autorada não altera o bruto not_performed/approval null nem aprova runtime/CAP-001.