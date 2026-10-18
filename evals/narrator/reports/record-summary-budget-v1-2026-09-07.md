# Sondagem operacional Qwen com teto de 768 — preparação histórica

Na etapa de preparação, **65 testes novos distintos passaram**, sem falhas, mais revisão independente, reconstrução do pedido, preflight real e integração com chave vazia; essa etapa não enviou pedido ao provedor. A execução posterior foi concluída e analisada no [lote 95dd9fd2](record-summary-budget-observation-95dd9fd2-2026-09-07.md): uma chamada HTTP 200/stop, rota/schema válidos e exit 0, resumo de 23 palavras/120 caracteres sem afirmação retida sem suporte identificada na revisão delimitada. Não há aprovação geral de fidelidade, runtime ou CAP-001.

A [recusa anterior 1edf4d3e](record-summary-attachment-observation-1edf4d3e-2026-09-07.md) permanece encerrada: A recebeu 429 e B não foi chamado. O Console atribuiu a recusa à expectativa de saída de 1.096 acima do limite OTPM de 1.000. Essa evidência não revela fórmula, reset ou consumo, e não garante aceitação do novo teto.

## Pedido congelado

O [desenho prévio](record-summary-budget-design-1edf4d3e-2026-09-07.md) e o [dossiê HTTP](record-summary-budget-dossier-1edf4d3e-2026-09-07.json) especificam uma única chamada no mesmo Qwen/Groq gratuito, `reasoning_effort=none`, temperatura 0,65, saída máxima de 768 tokens, espera inicial de 60 segundos e deadline de 60 segundos depois dela.

A fonte nova `station-clock` é inteiramente sintética. Não se repete archive-vibration nem qualquer caso do par anterior. Comparado ao dossiê summary-only, apenas três campos do corpo HTTP mudam: USER, a menção numérica no SYSTEM (`3.072` para `768`) e `max_completion_tokens`. Não é comparação causal de um fator. Schema e protocolo de saída `record-summary-only-v1` permanecem iguais; a variante do prompt é `record-summary-budget-v1`.

Body SHA `d494be582e549a917419c06229fed3acb60f092f7f7bcbc982ebe8caea804eac`.
Dossiê SHA `8df1c12ea57076dd44a5aca2173b06b693f1904fada52bfd8b041bcebc557cac`.
Executor SHA `f2fe52f134df0fd97f843a257f2edb6023be56b233b8f9a50c903f48bb2af3d0`.
Wrapper SHA `303e0da123542587fc9c7d2756fe1a64393e3b4fdc7da38abcf1fc211d238d3f`.

## Implementação e verificação

Novos executor e wrapper derivam do fluxo anterior de uma chamada por substituições finitas de identidade, fonte, prompt, fingerprints e teto. O executor separa a variante do prompt do protocolo. Nenhum algoritmo, contrato ou adaptador de runtime foi alterado. O avaliador compartilhado ganhou apenas 12 linhas que recusam os novos marcadores nas duas entradas de replay CAP.

| Verificação focada | Resultado |
| --- | --- |
| Executor: pedido fixo, orçamento/fonte divergentes, uso único, deadline, 429, truncamento, cancelamento e retenção literal | 23 passaram |
| Wrapper: preflight, fingerprints, SecureString, status/exit, novo artefato único e restauração do ambiente | 31 passaram |
| Fronteira CAP: marcadores isolados no replay direto/CLI e comportamento legado | 11 passaram |

Não foram repetidas as matrizes históricas. O aviso de depreciação Starlette/multipart já existente não pertence à alteração. A integração real PowerShell 7/Python concluiu o preflight e terminou com código 3 na validação de uma chave vazia, sem envio, stderr ou artefato de avaliação novo. A revisão independente não encontrou problema material.

A auditoria confirmou dez arquivos desta preparação, 60 arquivos históricos e 16 artefatos brutos anteriores. A evolução explícita do arquivo compartilhado permanece separada dos hashes históricos de cada execução. Os metadados e resultados antigos não foram reescritos. [Registro completo da preparação e evidências](record-summary-budget-v1-2026-09-07.json).

## Regra de parada e continuidade

Um resultado encerra a sondagem, inclusive 429, truncamento, erro de schema/rota, falha local ou cancelamento. Não há diagnóstico, nova tentativa, fallback, outro caso ou aumento de esforço/teto. Nova recusa não autoriza uma escada automática de orçamentos menores. A contagem de 25 palavras é informativa e não altera o código operacional; schema válido não aprova fidelidade, oito campos, atores, runtime ou CAP-001.

PID 21744 terminou em 2026-09-07T20:41:18.2606505Z, exit 0; chave descartada. O lote 95dd9fd2-f78f-4467-858f-b3948479aa10 está encerrado, com uma chamada e nenhum skip. Não relançar a janela ou o wrapper nem repetir station-clock. [Resultado, revisão independente e auditoria](record-summary-budget-observation-95dd9fd2-2026-09-07.json). Os metadados, fingerprints, escopo e verificações desta preparação permanecem históricos e intactos.

A continuidade autorizada é preparar um contraste de atribuição com duas fontes novas, mesmo prompt record-summary-budget-v1/schema/Qwen none/768 e temperatura 0,65, até duas chamadas e parada no primeiro erro operacional. A preparação está em curso, ainda não declarada pronta; não houve novo envio neste registro. Concluir o trabalho local antes de uma eventual dependência de credencial, sem nova confirmação genérica.
