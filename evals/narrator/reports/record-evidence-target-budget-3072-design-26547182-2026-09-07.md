# Observação delimitada — target-spans com teto 3.072

Data: 07/09/2026. Status: **autorizada pela instrução contínua; preparação concluída**. Verificação e próximos passos no [relatório da implementação](record-evidence-target-budget-3072-v1-2026-09-07.md). A [observação 26547182](record-evidence-target-spans-observation-26547182-2026-09-07.md) mostrou `finish_reason:length`, saída 1.536 e nenhum envelope disponível. Não é necessário pedir nova aprovação deste desenho.

## Hipótese e alteração exata

A mesma abertura target-spans consegue concluir a resposta com teto 3.072? O [dossiê congelado](record-evidence-target-budget-3072-dossier-26547182-2026-09-07.json) contém o corpo sintético completo, sem headers, credencial ou resposta. A reconstrução local confirmou somente esta mudança:

```diff
- "max_completion_tokens": 1536
+ "max_completion_tokens": 3072
```

Hash canônico anterior: `8138c098ec49cdc768e7c5d9fe19cc952001939f1c54af11bdb1241762526a09`.
Hash canônico novo: `5e376cb4cdee903b0f1a5bbcd3a14fa181d966656102f4c4985d87b4eb9ea186`.
Dossiê SHA: `ae30f021f344c49e97a901685a591602755e836885b890d7e469dad8670f88d0`.
SYSTEM permanece `record-evidence-target-spans-v1`, SHA `fdba32bb00dd20144ec5553d72635c3a2388fee9c4621486f3bddd6f3b1721cb`.

É hash de JSON canônico (`ensure_ascii=False`, chaves ordenadas, separadores compactos, UTF-8), não captura de tráfego. O teto textual histórico 768 do SYSTEM permanece para isolar o parâmetro da API; é limitação conhecida, não drift.

## Limites fixados antes do envio

Identidade `record-evidence-target-spans-3072-v1`, propósito `record_evidence_target_budget_probe`. Uma chamada total, somente opening bb98, Groq direta / openai/gpt-oss-120b, reasoning low, include_reasoning false, temperatura 0,65, structured sem streaming. Saída total até 3.072 tokens, incluindo qualquer raciocínio contabilizado pelo provedor; entrada reportada anteriormente 2.484, sem garantir contagem futura.

Espera inicial conservadora de 60 segundos, um único terminal, deadline de 60 após espera e revalidação. Nenhuma Mara, geração narrativa, diagnóstico de texto/streaming, retry ou fallback. Encerrar esse lote após qualquer resultado. Este desenho não autoriza o próprio runner a aumentar novamente seu teto. A continuidade posterior será escolhida a partir da análise, conforme autorização plena, sem escalada mecânica de orçamento.

## Critérios preservados

Mesmos schema de envelope, validação de referências/intervalos, composição literal da narrativa, schema final, atores e admissão. Não reparar ou completar JSON, recalcular offsets recusados ou remover uma pergunta para tornar a amostra aceita. Preservar observador de metadados seguros, limite de erro 64 KiB, cancelamento e ausência de conteúdo bruto/raciocínio persistido.

Se houver envelope, conferir intervalos e revisar separadamente fidelidade, modalidade, cobertura e pressuposições. Se não houver, não atribuir falha semântica. `stop` e schema válido não provam qualidade; `length` explícito prova o motivo de término somente daquela resposta. Uso acima de 1.536 com término demonstra consumo dessa realização, sem conclusão causal sobre outra amostra.

Comparação histórica não é A/B causal. Uma resposta admitida não aprova CAP-001, runtime ou critérios semânticos. O novo código fica exclusivo do experimento; artefatos e instrumentos anteriores são preservados. Aguardaremos somente a chave protegida após todas as verificações offline.
