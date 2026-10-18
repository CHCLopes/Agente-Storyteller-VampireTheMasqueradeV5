# TASK-022 — integração individual no contexto do narrador

Data: 2026-09-20

O caminho de ação passa candidatos tipados para `_assemble_narrator_context`.
A política versionada é aplicada e cada selecionado vira um `ContextItem` próprio,
mantendo ID, visibilidade, obrigatoriedade, importância, sinais e referências.

O `assemble_context` existente continua sendo a autoridade final para filtragem de
visibilidade, orçamento compartilhado e desempate com fatos, memória e relações.
O caminho temporário de texto permanece somente para consultas de cena até a
TASK-023.
