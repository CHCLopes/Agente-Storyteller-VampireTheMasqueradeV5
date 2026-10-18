# TASK-021 — política determinística de seleção

Data: 2026-09-20

A política `catalog-context-selection.v1` ordena candidatos por obrigatoriedade,
menção ou seleção explícita, regra acionada, presença na cena, relevância textual,
importância e ID estável. Empates não dependem da ordem física dos arquivos.

`unarmed` sem seleção explícita e sem regra de combate é omitido antes de consumir
orçamento. Cada omissão registra apenas ID, motivo, tokens estimados e posição de
prioridade. Conteúdo completo e segredos não entram no diagnóstico.
