# Escopo mecânico de Alleycat — TASK-015

Data: 2026-09-20

Alleycat é o único tipo de predador `base_reachable`. O livro-base V5 confirma o
pool padrão Strength + Brawl no PDF, página 309 (página impressa 307), e esclarece
que o tipo de predador representa um hábito: outras abordagens continuam possíveis.

O catálogo agora converte o pool em `V5Attribute` e `V5Skill` antes do uso. Uma
ação explícita de alimentação usa esse pool quando não há teste alternativo
escolhido. Tipos adiados falham fechados nesse caminho.

`blood_resonance_preference: choleric` foi classificado como
`narrative_targeting_hint`. Ele pode orientar que tipo de presa combina com o
hábito do personagem, mas não concede dados, sucesso, ressonância ou efeitos
mecânicos. Aquisição e intensidade de ressonância exigem regra separada.

Próximo passo: TASK-016, somente poderes `base_reachable` com dados suficientes.
