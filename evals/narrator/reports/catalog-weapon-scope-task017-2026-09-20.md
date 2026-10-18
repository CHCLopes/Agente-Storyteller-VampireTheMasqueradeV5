# TASK-017 — escopo de arma determinística

Data: 2026-09-20

## Escopo aprovado

Somente `unarmed`, a única arma `base_reachable` da matriz. Nenhuma arma adiada
foi promovida.

## Evidência de regra

- V5 core, PDF página 303 (impressa 301): ataques desarmados usam Strength + Brawl.
- V5 core, PDF página 306 (impressa 304): o valor da arma é somado à margem; para
  `unarmed`, o modificador catalogado é zero, logo o dano é a margem.

## Implementação

- `unarmed` preserva tipo BRAWL, modificador zero e dano superficial comum.
- Categoria desconhecida falha antes do cálculo; não pode equivaler silenciosamente
  ao modificador zero de `unarmed`.
- Ocultabilidade permanece metadado informativo: não há motor de
  inventário/ocultação no escopo atual.

## Verificação

- Teste positivo cobre tipo BRAWL, modificador zero, ocultabilidade catalogada e
  dano igual à margem.
- Teste negativo cobre rejeição de categoria desconhecida.
- A matriz registra as limitações sem promover ocultabilidade a efeito mecânico.
