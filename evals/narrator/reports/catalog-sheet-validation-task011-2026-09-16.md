# Validação de catálogos na leitura de ficha — TASK-011

Data: 2026-09-16

## Resultado

`PlayerSheetModel` valida clã, tipo de predador, potência de sangue e cada chave
de disciplina/poder contra o registro determinístico antes de a ficha ser usada.
Níveis aceitos ficam no intervalo 0 a 5.

## Compatibilidade

- IDs canônicos e aliases são aceitos.
- A grafia recebida é preservada no modelo; a leitura não normaliza nem reescreve
  saves legados.
- Famílias são derivadas dos metadados dos poderes, requisitos de amálgama e
  disciplinas favorecidas dos clãs.
- ID desconhecido, potência ausente do catálogo ou nível inválido produz erro de
  validação antes de qualquer mutação.
- `data/schema_save.json` declara o contrato `read_compatible` e a política de
  preservação sem reescrita automática.

## Verificação

O conjunto de registro, regras, persistência e fluxo de turnos executou 168 casos:
167 passaram. A única falha é preexistente e fora do incremento:
`test_narrator_uses_compact_projection_instead_of_full_sheet` exige a frase literal
`conduza a cena por improviso coerente`, enquanto o SYSTEM atual contém
`improviso coerente`. Nenhum prompt foi alterado.

## Próximo passo

TASK-012: centralizar no registro a resolução e autorização de poderes feita pelo
orquestrador, com testes de posse, alias e nível.
