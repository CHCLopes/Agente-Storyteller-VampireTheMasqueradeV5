---
goal: Corrigir falso positivo delimitado de interesse dependente no gate de agência
version: 1
date_created: 2026-09-13
last_updated: 2026-09-13
owner: Agente Storyteller
status: 'Completed'
tags: [agency, regression, local-fix, dialogue-comparison]
---

# Correção prospectiva após o lote 095e7efd

O lote fechado recusou “dependendo do que você procura” como busca executada.
A revisão principal identificou interesse condicional, não ação consumada.

- Preservar o lote, protocolo, corpus, prompt, respostas e bancos.
- Reconhecer somente a construção terminal observada; não ignorar fala ou oração.
- Preservar recusas de busca com objeto e de ações posteriores.
- Verificar no gate, nas regressões de agência e no fluxo B sem rede.
- Não repetir o comparativo ou reclassificar a proposta histórica.

| Tarefa | Estado |
|---|---|
| Reproduzir texto e evidência do gate | Concluída |
| Aplicar correção mínima e contraprovas | Concluída |
| Executar suíte combinada | Concluída: 525 aprovados |
| Registrar limites e próximo passo | Concluída |

[Relatório](../evals/narrator/reports/dependent-interest-agency-fix-2026-09-13.md).
