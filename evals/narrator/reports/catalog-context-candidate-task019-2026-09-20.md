# TASK-019 — contrato do candidato de contexto de catálogo

Data: 2026-09-20

`CatalogContextCandidate` é uma estrutura imutável e estrita. Ela carrega domínio,
ID canônico, texto mínimo, visibilidade, obrigatoriedade, importância e referências
de origem. Os sinais são explícitos e independentes: menção, seleção, regra
acionada, entidade ativa na cena e relevância textual.

O contrato não escolhe candidatos nem aplica orçamento. Ele apenas impede que a
próxima etapa volte a usar blocos textuais anônimos ou ordem física do catálogo.
