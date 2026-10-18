# TASK-023 — catálogos em consultas de cena

Data: 2026-09-20

## Resultado

- O produtor textual `_scene_query_static_lore` e seu corte `blocks[:3]` foram removidos.
- O clã atual e cada NPC reconhecido na cena são candidatos tipados independentes.
- NPCs presentes recebem o sinal `active_in_scene`; identidade e proveniência de catálogo são preservadas.
- A consulta de cena entrega esses candidatos à mesma seleção determinística e ao mesmo orçamento final usados nas ações.

## Limites preservados

- Seleção por orçamento pode omitir candidatos opcionais, mas não por posição de montagem.
- O catálogo fornece fatos mínimos; não fornece prosa de cena pronta nem restringe o improviso coerente do narrador.
