# Proveniência dos catálogos e ontologia inicial de poderes

Data: 2026-09-16

## Resultado

TASK-008, TASK-009 e TASK-010 foram concluídas. O registro determinístico agora
possui proveniência editorial explícita para os sete catálogos e metadados tipados
para todos os oito poderes já existentes no inventário.

## Origem editorial

- Caderno: `Vampiro: A Máscara e o Legado Bloodlines`.
- Conversa-fonte citada pelo NotebookLM: `Organizando Regras de Vampiro para IA`.
- Localizador informado pelo usuário:
  `https://notebook.google.com/notebook/a50334b5-5907-45bf-8152-e0a198fdd652?authuser=2`.
- Data visível do caderno: 2026-04-25.
- Natureza: compilação privada de pesquisa fornecida pelo usuário e usada na
  criação anterior do projeto.

O NotebookLM confirmou V5 como edição de referência e indicou material de
expansões e adaptações legadas em alguns itens. Ele não identificou páginas ou
seções dos manuais originais. O manifesto registra exatamente esse alcance. A
anotação de proveniência não constitui validação jurídica nem afirma licença sobre
as publicações subjacentes.

## Poderes

Cada poder possui `discipline_family_id`, `power_id`, `level`,
`prerequisite_power_ids`, `amalgam_requirements`, aliases e estado de origem.
Campos não identificados na compilação permanecem `null` ou vazios. A matriz
mantém `references_valid: partial`, pois não há página original verificável.

Mapeamentos com nível identificado: `feral_weapons` (2), `soaring_leap` (1),
`flesh_of_marble` (5) e `fleshcrafting` (3). `dementation` registra amálgama de
Obfuscate 2; `fleshcrafting` registra pré-requisito Vicissitude/Protean 2 e
amálgama Dominate 2. Os demais campos ausentes não foram inferidos.

## Verificação

- `tests/test_catalog_registry.py` e recorte relevante de `tests/test_perf_sec.py`:
  21 testes aprovados, 19 desmarcados.
- O carregador rejeita campos extras, IDs divergentes, referências inválidas e
  hashes divergentes.
- A migração dos seis consumidores preserva suas APIs existentes.

## Próximo passo

TASK-011: validar os identificadores presentes na ficha e em saves contra o
registro, com leitura compatível dos saves legados e sem reescrita automática.
