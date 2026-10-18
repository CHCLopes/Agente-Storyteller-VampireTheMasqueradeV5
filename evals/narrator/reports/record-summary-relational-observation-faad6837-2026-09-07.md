# Compressão relacional — lote faad6837 encerrado

O lote **faad6837-cc0b-408d-85a6-025d0db770b3** terminou com **duas chamadas HTTP 200/stop, rotas Groq/Qwen e schemas válidos, exit 0**. Controle: 19 palavras/128 caracteres; relational: 23 palavras/156 caracteres. Ambos cumprem o limite instrucional de 25 palavras. O trecho espacial é idêntico e ambíguo nos dois; a variante retém o apoio das molduras contra a parede. Não há transferência explícita inequívoca demonstrada nem vencedor declarado.

PID 1096 confirmado finished em **2026-09-07T21:47:25.3117077Z**; credencial descartada, duas posições executadas e nenhum skip. A [preparação](record-summary-relational-v1-2026-09-07.md), o [desenho prévio](record-summary-relational-design-0e7b0ac3-2026-09-07.md) e o [dossiê](record-summary-relational-dossier-0e7b0ac3-2026-09-07.json) permanecem históricos. Os 86 testes pertencem ao preparo, sem repetição nesta análise.

## Fonte e respostas literais

Fonte única gallery-reflection, USER idêntico nos dois braços:

> Na galeria vazia, um espelho reflete uma tapeçaria pendurada diante de uma janela fechada. Um catálogo permanece sobre o banco; à direita da entrada, duas molduras vazias estão apoiadas contra a parede.

Controle:

> Galeria vazia: espelho reflete tapeçaria diante de janela fechada; catálogo no banco; duas molduras vazias à direita da entrada.

Relational:

> Galeria vazia: espelho reflete tapeçaria diante de janela fechada. Catálogo sobre banco; duas molduras vazias apoiadas contra a parede à direita da entrada.

## Matriz de relações — revisão autorada

Cada resposta foi avaliada separadamente pelos critérios prévios antes da comparação. Omissões são permitidas e não informativas; não se exige redação única ou cobertura completa.

| Afirmação da fonte | Controle | Relational |
| --- | --- | --- |
| Galeria vazia | Preservada | Preservada |
| Espelho reflete a tapeçaria | Preservada | Preservada |
| Tapeçaria pendurada | Omitida | Omitida |
| Tapeçaria diante da janela fechada | Vínculo espacial ambíguo | Mesmo vínculo ambíguo, trecho literal idêntico |
| Catálogo sobre o banco | “no banco”: compatível, menos preciso | “sobre banco”: preservada |
| Duas molduras vazias à direita da entrada | Preservada | Compatível com a localização das molduras |
| Molduras apoiadas contra a parede | Omitida | Preservada |

“Espelho reflete tapeçaria diante de janela fechada” admite a leitura fiel, mas a retirada de “pendurada” deixa menos explícito a que se liga “diante de janela”. Não concluir que a posição foi inequivocamente transferida ao espelho nem escolher uma leitura favorável para aprovar. Na variante, a expressão final é compatível com a posição das molduras; não inferir localização independente da parede.

A variante conserva um detalhe adicional apoiado pela fonte, mas não esclarece o mesmo trecho espacial. Nenhuma afirmação explicitamente falsa ou nova ação de jogador/NPC foi demonstrada. A ausência de hipótese modal nesta fonte não testa a preservação de incerteza. Nenhum defeito local de retenção ou medição foi identificado.

## Evidência operacional e limites

Uso controle: 476 entrada + 40 saída = 516; relational: 520 + 46 = 566; total **996 + 86 = 1.082**. Raciocínio não reportado (null, não zero), custo indisponível. Sem retry, fallback, diagnóstico, reparo ou nova chamada nesta análise.

A auditoria final independente reconstruiu metadados, pedidos, summary, contrato, texto literal e medidas. Confirmou **10 arquivos de preparação, 81 históricos, 20 brutos anteriores e os dois brutos novos intactos** no momento da auditoria; esses conjuntos podem se sobrepor. Intervalo UTC local inicial: 60,500035 s; entre inícios: 60,254024 s. [Análise estruturada e auditoria completa](record-summary-relational-observation-faad6837-2026-09-07.json) registram horários, hashes e limites. Reconstrução offline não é captura do tráfego; UTC local não mede chegada remota, espera monotônica exata ou deadline absoluto não persistido.

Brutos preservados: [summary.json](../../../eval-results/20260907T214523Z-c8bd771b-741e-4c06-97ff-085c9882bdf2/summary.json), SHA `49cf7ad2f9abb57be49da3dd8338d04d8329a334716bbccc6e3c18a4935cd178`; [JSONL](../../../eval-results/20260907T214523Z-c8bd771b-741e-4c06-97ff-085c9882bdf2/qwen-3.8-27b-groq-free-synthetic-nonthink.jsonl), SHA `2b8484a9d9f0a122d2d7438224335ad742bcc3c054943b6cd13652fdec5e982c`. A revisão autorada não altera semantic_fidelity_review not_performed/approval null. Schema, rota, palavras ou esta análise não aprovam qualidade narrativa, oito campos, atores, runtime ou CAP-001.

## Encerramento e próximo trabalho local

Uma observação por braço, fonte única e ordem fixa sustentam somente descrição destas saídas. Não há conclusão causal, estimativa de taxa, equivalência ou superioridade. Esta hipótese está encerrada após os dois braços, sem sequência de reformulações.

Consolidar as evidências summary-only, budget, color e relational, separar resultados informativos, ambiguidades, omissões e lacunas, e definir a próxima direção. Nenhum novo SYSTEM, lote ou entrada de chave está agendado; não repetir fontes/lotes fechados ou preencher skips. A autorização contínua cobre esse trabalho local, sem nova confirmação genérica ou bloqueio humano artificial.
