# TASK-025 — lookup fundamentado de lore

Data: 2026-09-20

## Resultado

- `lookup_catalog_lore` reconhece somente IDs e aliases versionados explicitamente presentes na consulta.
- O retorno imutável contém fatos com caminho de campo, domínio, ID e referência de origem.
- Cobertura narrativa e limitações da matriz acompanham o resultado.
- Ausência de entrada ou de fatos permitidos retorna `not_covered`, sem chamada externa e sem texto inventado.

## Verificação

- Lookup e regressão do registro: 25 testes aprovados.
