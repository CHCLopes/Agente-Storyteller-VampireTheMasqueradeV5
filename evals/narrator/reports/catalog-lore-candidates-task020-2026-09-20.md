# TASK-020 — produção tipada antes do corte

Data: 2026-09-20

`lore_service` agora produz um candidato por entrada relevante e só depois oferece
uma projeção textual temporária aos consumidores antigos. O corte `blocks[:3]` foi
removido. Múltiplos NPCs mencionados não são descartados por posição.

Esta etapa não decide prioridade nem orçamento. Os sinais e a atribuição seguem em
cada candidato para que a TASK-021 faça a seleção determinística e registre
omissões sem depender da ordem física dos catálogos.
