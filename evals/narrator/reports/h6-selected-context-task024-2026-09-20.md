# TASK-024 — fronteira final de contexto H6

Data: 2026-09-20

## Resultado

- Candidatos elegíveis são ordenados pela política sem consumir orçamento antecipadamente.
- `assemble_context` aplica o orçamento efetivo uma única vez ao conjunto final.
- Contextos gerais mantêm a ordenação histórica; candidatos de catálogo mantêm a prioridade determinística entre si.
- O caminho de ação deixou de inserir uma segunda cópia do contexto relacional.
- `_context_prompt` projeta apenas selecionados, emite conteúdo idêntico uma vez e mantém itens de Storyteller em `CONFIDENCIAL`.
- O prompt H6 continua exigindo improviso coerente e preservação de agência.

## Verificação

- Suíte focada isolada: 87 testes aprovados.
- Busca estática: nenhum `blocks[:3]`, `_scene_query_static_lore` ou chamada `static_lore=` permanece no orquestrador preparado.
